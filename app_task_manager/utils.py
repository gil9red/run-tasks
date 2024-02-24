#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import os
import signal
import subprocess
import sys
import threading
import traceback
import time
from tempfile import NamedTemporaryFile
from typing import Callable, IO, AnyStr

import psutil

from app_task_manager.common import log_manager as log
from app_task_manager.config import ENCODING, PATTERN_FILE_JOB_COMMAND, SCRIPT_NAME
from db import Task, TaskRun, TaskStatusEnum


IS_WIN: bool = sys.platform == "win32"


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


def get_shell_command(file_name_command: str) -> list[str]:
    command: list[str] = []
    if IS_WIN:
        command += ["cmd", "/c", "call"]
    else:
        command += ["/bin/bash", "-xe"]

    command.append(file_name_command)

    return command


def get_prefix_file_name_command(task: Task, task_run: TaskRun) -> str:
    return PATTERN_FILE_JOB_COMMAND.format(
        script_name=SCRIPT_NAME,
        job_id=task.id,
        job_run_id=task_run.id,
    )


def create_temp_file(task: Task, task_run: TaskRun) -> IO:
    file_name_command: str = get_prefix_file_name_command(
        task=task,
        task_run=task_run,
    )

    # NOTE: Пример названия файла "run-tasks_job4_run163__cx6w_2zk.bat"
    temp_file = NamedTemporaryFile(
        mode="w",
        prefix=f"{file_name_command}__",
        suffix=".bat" if IS_WIN else ".sh",
        encoding="UTF-8",
        delete_on_close=False,
    )
    temp_file.write(task_run.command)
    temp_file.flush()

    return temp_file


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
                    log.info(f"Нужно остановить процесс #{self.process.pid}")
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
        self.current_task_run: TaskRun | None = None
        self._is_stopped: bool = False

    def stop(self):
        if self.current_task_run and self.current_task_run.status == TaskStatusEnum.Running:
            self.current_task_run.set_status(TaskStatusEnum.Stopped)

        self._is_stopped = True

    def run(self):
        while not self._is_stopped:
            task: Task | None = Task.get_by_name(self.name)
            if not task:
                log.warn(f"Задача {self.name!r} не найдена!")
                return

            if not task.is_enabled:
                log.info(f"Задача {self.name!r} не активна!")
                return

            task_runs = task.get_runs_by([TaskStatusEnum.Pending])
            if task_runs:
                task_run = task_runs[0]
                self._start_task_run(task, task_run)

            time.sleep(1)  # TODO:

    def _start_task_run(self, task: Task, task_run: TaskRun):
        def start_callback(process: psutil.Popen):
            log.debug(f"{log_prefix} process_id: {process.pid}")
            task_run.set_process_id(process.pid)

        def process_stdout(text: str):
            log.debug(f"{log_prefix} stdout: {text!r}")
            task_run.add_log_out(text)

        def process_stderr(text: str):
            log.debug(f"{log_prefix} stderr: {text!r}")
            task_run.add_log_err(text)

        def stop_on() -> bool:
            if not task.get_actual_is_enabled():
                task_run.set_status(TaskStatusEnum.Stopped)

            status = task_run.get_actual_status()
            need_stop = status != TaskStatusEnum.Running
            if need_stop:
                log.debug(f"{log_prefix} нужно остановить задачу, текущий статус {status.value}")

            return need_stop

        log_prefix = f"[Задача #{task.id}, запуск #{task_run.id}]"
        try:
            log.info(f"{log_prefix} Старт запуска задачи")

            self.current_task_run = task_run

            task_run.set_status(TaskStatusEnum.Running)

            temp_file = create_temp_file(task, task_run)

            thread = ThreadRunProcess(
                command=get_shell_command(temp_file.name),
                on_stdout_callback=process_stdout,
                on_stderr_callback=process_stderr,
                on_start_callback=start_callback,
                stop_on=stop_on,
                encoding=self.encoding,
            )
            thread.start()
            thread.join()

            temp_file.close()

            process_return_code = thread.process_return_code
            log.debug(f"{log_prefix} process_return_code: {process_return_code}")

            if process_return_code is not None:
                task_run.process_return_code = process_return_code

            # Статус может поменяться, поэтому нужно его заново получить из базы
            final_status = task_run.get_actual_status()

            # Если текущий статус running
            if final_status == TaskStatusEnum.Running:
                final_status = TaskStatusEnum.Finished
            task_run.set_status(final_status)

            task_run.save()

        except Exception:
            log.exception(f"{log_prefix} error:")

            text = traceback.format_exc()
            task_run.set_error(text)

        finally:
            log.debug(f"{log_prefix} Завершение с статусом {task_run.status.value}")
