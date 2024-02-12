#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import os
import signal
import subprocess
import sys
import threading
import time
from tempfile import NamedTemporaryFile
from typing import Callable, IO, AnyStr

import psutil

import db

from app_task_manager.config import ENCODING, PATTERN_FILE_JOB_COMMAND, SCRIPT_NAME
from app_task_manager.common import log_manager as log


# SOURCE: https://psutil.readthedocs.io/en/latest/index.html#kill-process-tree
def kill_proc_tree(
    pid, sig=signal.SIGTERM, include_parent=True, timeout=None, on_terminate=None
):
    """Kill a process tree (including grandchildren) with signal
    "sig" and return a (gone, still_alive) tuple.
    "on_terminate", if specified, is a callback function which is
    called as soon as a child terminates.
    """
    assert pid != os.getpid(), "won't kill myself"
    parent = psutil.Process(pid)
    children = parent.children(recursive=True)
    if include_parent:
        children.append(parent)
    for p in children:
        try:
            p.send_signal(sig)
        except psutil.NoSuchProcess:
            pass
    gone, alive = psutil.wait_procs(children, timeout=timeout, callback=on_terminate)
    return gone, alive


class ThreadRunProcess(threading.Thread):
    def __init__(
        self,
        command: str | list[str],
        on_stdout_callback: Callable[[str], None],
        on_stderr_callback: Callable[[str], None],
        on_start_callback: Callable[[psutil.Popen], None],
        on_finish_callback: Callable[[psutil.Popen], None] = None,
        stop_on: Callable[[], bool] = lambda: False,
        encoding: str = ENCODING,
    ):
        super().__init__(
            daemon=True,  # Thread dies with the program
        )

        self.command = command

        self.on_stdout_callback = on_stdout_callback
        self.on_stderr_callback = on_stderr_callback
        self.on_start_callback = on_start_callback
        self.on_finish_callback = on_finish_callback

        self.stop_on = stop_on

        self.encoding = encoding

        self.process: psutil.Popen | None = None
        self.process_return_code = None

    def run(self):
        if self.stop_on():
            return

        def read_stream(stream: IO[AnyStr], on_callback: Callable[[str], None]):
            for text in iter(stream.readline, ""):
                on_callback(text)
                if self.stop_on():
                    break
            stream.close()

        log.info(f"Запуск: {self.command}")
        self.process = psutil.Popen(
            self.command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding=self.encoding,
        )
        self.on_start_callback(self.process)

        thread_stdout = threading.Thread(
            target=read_stream,
            args=(self.process.stdout, self.on_stdout_callback),
            daemon=True,
        )
        thread_stdout.start()

        thread_stderr = threading.Thread(
            target=read_stream,
            args=(self.process.stderr, self.on_stderr_callback),
            daemon=True,
        )
        thread_stderr.start()

        while True:
            try:
                if self.stop_on():
                    log.info(f"Нужно остановить процесс: {self.process.pid}")
                    kill_proc_tree(self.process.pid)

                self.process_return_code = self.process.wait(timeout=0)
                break

            except psutil.TimeoutExpired:
                pass

        self.on_finish_callback and self.on_finish_callback(self.process)


class TaskThread(threading.Thread):
    def __init__(self, name: str, encoding: str = ENCODING):
        super().__init__(
            name=name,
            daemon=True,  # Thread dies with the program
        )

        self.encoding = encoding
        self.current_task_run: db.TaskRun | None = None
        self._is_stopped: bool = False

    def stop(self):
        if self.current_task_run and self.current_task_run.status == db.TaskStatusEnum.Running:
            self.current_task_run.set_status(db.TaskStatusEnum.Stopped)

        self._is_stopped = True

    def run(self):
        while not self._is_stopped:
            task_db: db.Task | None = db.Task.get_by_name(self.name)
            if not task_db:
                log.warn(f"Задача {self.name!r} не найдена!")
                return

            if not task_db.is_enabled:
                log.info(f"Задача {self.name!r} не активна!")
                return

            task_runs = task_db.get_runs_by([db.TaskStatusEnum.Pending])
            if task_runs:
                task_run = task_runs[0]
                log.info(f"[Задача #{task_db.id}] Старт запуска задачи: #{task_run.id}")
                self._start_task_run(task_db, task_run)

            time.sleep(1)  # TODO:

    def _start_task_run(self, task_db: db.Task, task_run_db: db.TaskRun):
        log_prefix = f"[Задача #{task_db.id}, запуск #{task_run_db.id}]"

        self.current_task_run = task_run_db

        task_run_db.set_status(db.TaskStatusEnum.Running)

        def start_callback(process: psutil.Popen):
            log.debug(f"{log_prefix} process_id: {process.pid}")
            task_run_db.set_process_id(process.pid)

        def process_stdout(text: str):
            log.debug(f"{log_prefix} stdout: {text!r}")
            task_run_db.add_log_out(text)

        def process_stderr(text: str):
            log.debug(f"{log_prefix} stderr: {text!r}")
            task_run_db.add_log_err(text)

        def stop_on() -> bool:
            if not task_db.get_actual_is_enabled():
                task_run_db.set_status(db.TaskStatusEnum.Stopped)

            return task_run_db.get_actual_status() in [db.TaskStatusEnum.Stopped, db.TaskStatusEnum.Finished]

        is_win = sys.platform == "win32"
        file_name_command: str = PATTERN_FILE_JOB_COMMAND.format(
            script_name=SCRIPT_NAME,
            job_id=task_db.id,
            job_run_id=task_run_db.id,
        )

        # NOTE: Пример имени "run-tasks_job4_run163__cx6w_2zk.bat"
        temp_file = NamedTemporaryFile(
            mode="w",
            prefix=f"{file_name_command}__",
            suffix=".bat" if is_win else ".sh",
            encoding="UTF-8",
            delete_on_close=False,
        )
        temp_file.write(task_run_db.command)
        temp_file.close()

        full_file_name_command = temp_file.name

        command: list[str] = []
        if is_win:
            command += ["cmd", "/c", "call"]
        else:
            command += ["/bin/bash", "-xe"]
        command.append(full_file_name_command)

        thread = ThreadRunProcess(
            command=command,
            on_stdout_callback=process_stdout,
            on_stderr_callback=process_stderr,
            on_start_callback=start_callback,
            stop_on=stop_on,
            # TODO: "cp866" if windows else "utf-8" ?
            encoding=self.encoding,
        )
        thread.start()
        thread.join()
        process_return_code = thread.process_return_code
        log.debug(f"{log_prefix} process_return_code: {process_return_code}")

        if process_return_code is not None:
            task_run_db.process_return_code = process_return_code

        # Статус может поменяться, поэтому нужно его заново получить из базы
        final_status = task_run_db.get_actual_status()

        # Если текущий статус pending или running
        if final_status in (db.TaskStatusEnum.Pending, db.TaskStatusEnum.Running):
            final_status = db.TaskStatusEnum.Finished

        task_run_db.set_status(final_status)
        task_run_db.save()

        log.debug(f"{log_prefix} Завершение с статусом {task_run_db.status.value}")
