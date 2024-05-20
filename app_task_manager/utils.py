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
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Callable, IO, AnyStr

import psutil

from app_task_manager.common import log_manager as log
from app_task_manager.config import ENCODING, PATTERN_FILE_JOB_COMMAND
from db import Task, TaskRun, TaskRunStatusEnum
from root_config import PROJECT_NAME


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
        project_name=PROJECT_NAME,
        job_id=task.id,
        job_run_id=task_run.id,
    )


def create_temp_file(task: Task, task_run: TaskRun) -> IO:
    file_name_command: str = get_prefix_file_name_command(
        task=task,
        task_run=task_run,
    )

    suffix = ".bat" if IS_WIN else ".sh"
    file_content = f"{task_run.command}\nexit {'%ERRORLEVEL%' if IS_WIN else '$?'}"

    # NOTE: Пример названия файла "run-tasks_job4_run163__cx6w_2zk.bat"
    temp_file = NamedTemporaryFile(
        mode="w",
        prefix=f"{file_name_command}__",
        suffix=suffix,
        encoding="UTF-8",
        delete_on_close=False,
    )
    temp_file.write(file_content)
    temp_file.flush()

    return temp_file


def get_env_for_children_process() -> dict:
    # TODO: Хорошо бы, обойтись без костылей и получать переменные окружения из ОС
    # Дочерние процессы получают переменные окружение родителя
    # и это иногда вызывает проблемы
    env = os.environ.copy()

    # Восстановление пути, измененного venv
    if "_OLD_VIRTUAL_PATH" in env:
        env["PATH"] = env.pop("_OLD_VIRTUAL_PATH")
    if "_OLD_VIRTUAL_PROMPT" in env:
        env["PROMPT"] = env.pop("_OLD_VIRTUAL_PROMPT")

    # Удаление переменных окружения
    env.pop("PYTHONIOENCODING", None)
    env.pop("PYTHONUNBUFFERED", None)
    env.pop("PYTHONPATH", None)

    return env


# SOURCE: https://stackoverflow.com/a/66292378/5909792
class RaisingThread(threading.Thread):
    def run(self):
        self._exc = None
        try:
            super().run()
        except Exception as e:
            self._exc = e

    def join(self, timeout: float | None = None):
        super().join(timeout=timeout)
        if self._exc:
            raise self._exc


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

        self._exc: Exception | None = None

    def run(self):
        try:
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
                text=True,
                encoding=self.encoding,
                cwd=Path.home(),
                env=get_env_for_children_process(),
            )
            self.on_start_callback(self.process)

            thread_stdout = RaisingThread(
                target=read_stream,
                args=(self.process.stdout, self.on_stdout_callback),
                daemon=True,
            )
            thread_stdout.start()

            thread_stderr = RaisingThread(
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

            # Для обработки возможного исключения
            # Тут потоки уже должны были завершиться
            thread_stdout.join()
            thread_stderr.join()

        except Exception as e:
            self._exc = e

        finally:
            self.on_finish_callback and self.on_finish_callback(self.process)

    def join(self, timeout: float | None = None):
        super().join(timeout=timeout)

        if self._exc:
            raise self._exc


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
        if (
            self.current_task_run
            and self.current_task_run.status == TaskRunStatusEnum.RUNNING
        ):
            self.current_task_run.set_status(TaskRunStatusEnum.STOPPED)

        self._is_stopped = True

    def _find_run(self, task: Task) -> TaskRun | None:
        task_runs = task.get_runs_by([TaskRunStatusEnum.PENDING])
        if not task_runs:
            return None

        # Не запланированные запуски более приоритетные
        for run in task_runs:
            if run.scheduled_date is None:
                return run

        for run in task_runs:
            if run.is_scheduled_date_has_arrived():
                return run

        return None

    def run(self):
        while not self._is_stopped:
            task: Task | None = Task.get_by_name(self.name)
            if not task:
                log.warn(f"Задача {self.name!r} не найдена!")
                return

            if not task.is_enabled:
                log.info(f"Задача {self.name!r} не активна!")
                return

            if run := self._find_run(task):
                self._start_task_run(task, run)

            time.sleep(2)  # TODO:

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
                task_run.set_status(TaskRunStatusEnum.STOPPED)

            status = task_run.get_actual_status()
            need_stop = status in [
                TaskRunStatusEnum.STOPPED,
                TaskRunStatusEnum.UNKNOWN,
                TaskRunStatusEnum.ERROR,
            ]
            if need_stop:
                log.debug(
                    f"{log_prefix} нужно остановить задачу, текущий статус {status.value}"
                )

            return need_stop

        log_prefix = f"[Задача #{task.id}, запуск {task_run.seq} (#{task_run.id})]"
        try:
            if task_run.task.is_infinite:
                start_reason = " по бесконечному запуску задачи"
            elif task_run.scheduled_date:
                start_reason = " по расписанию"
            else:
                start_reason = " по ручному запуску"

            log.info(f"{log_prefix} Старт запуска задачи{start_reason}")
            task_run.add_log_out(f"Старт запуска задачи{start_reason}")

            self.current_task_run = task_run

            task_run.set_status(TaskRunStatusEnum.RUNNING)

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
            if final_status == TaskRunStatusEnum.RUNNING:
                final_status = TaskRunStatusEnum.FINISHED
            task_run.set_status(final_status)

            task_run.add_log_out(f"\nProcess return code: {task_run.process_return_code}")
            task_run.add_log_out(f"Finished: {task_run.work_status.value}")

            task_run.save()

            # При неуспешном завершении, но не для остановленных
            if not task_run.is_success and task_run.status != TaskRunStatusEnum.STOPPED:
                task_run.add_log_out("Отправка уведомлений")
                task_run.send_notifications()

            self.current_task_run = None

        except Exception:
            log.exception(f"{log_prefix} error:")

            text = traceback.format_exc()
            task_run.set_error(text)

        finally:
            log.debug(f"{log_prefix} Завершение с статусом {task_run.status.value}")
