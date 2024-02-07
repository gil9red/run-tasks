#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import os
import signal
import time
import subprocess
import threading

from typing import Callable, AnyStr, IO

import psutil

import db
from common import log
from config import ENCODING


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
        command: str,
        on_stdout_callback: Callable[[str], None],
        on_stderr_callback: Callable[[str], None],
        on_start_callback: Callable[[psutil.Popen], None],
        on_finish_callback: Callable[[psutil.Popen], None] = None,
        stop_on: Callable[[], bool] = lambda: False,
        encoding: str = ENCODING,
    ):
        super().__init__()

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
        super().__init__(name=name)

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

        thread = ThreadRunProcess(
            command=task_run_db.command,
            on_stdout_callback=process_stdout,
            on_stderr_callback=process_stderr,
            on_start_callback=start_callback,
            stop_on=stop_on,
            # TODO: "cp866" if windows else "utf-8" ?
            encoding=self.encoding,
        )
        thread.daemon = True
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


class TaskManager:
    def __init__(self, encoding: str = ENCODING):
        self.encoding = encoding
        self.tasks: dict[str, TaskThread] = dict()

        # TODO: Название
        self._thread_observe_tasks_on_database = threading.Thread(
            target=self._thread_wrapper_observe_tasks_on_database,
            daemon=True,  # Thread dies with the program
        )

        self._is_stopped: bool = False

    def add(self, name: str, command: str, description: str = None) -> TaskThread:
        if name in self.tasks:
            # TODO: Другой тип исключения?
            raise Exception(f"Task {name!r} already added!")

        # TODO: >>>>
        # NOTE: Создание/обновление задачи
        task = db.Task.add(
            name=name,
            command=command,
            description=description,
        )
        # Создание запуска
        task.add_run()  # TODO: Это можно оставить, добавив вызов через флаг
        # TODO: <<<<

        task_thread = TaskThread(name=name, encoding=self.encoding)
        task_thread.daemon = True  # Thread dies with the program
        self.tasks[name] = task_thread

        return task_thread

    # TODO: название
    def _thread_wrapper_observe_tasks_on_database(self):
        while not self._is_stopped:
            for task in db.Task.select().where(db.Task.is_enabled == True):
                name = task.name
                if name not in self.tasks:
                    log.info(f"Запуск задачи #{task.id} {name!r}")
                    self.add(name=name, command=task.command).start()
                else:
                    thread = self.tasks[name]
                    if not thread.is_alive():
                        log.info(f"Удаление потока задачи #{task.id} {name!r}")
                        self.tasks.pop(name)

            time.sleep(0.1)  # TODO:

    # TODO: название
    def observe_tasks_on_database(self):
        self._thread_observe_tasks_on_database.start()

    def start_all(self):
        log.info("Запуск всех задач из базы")

        # TODO:
        self.observe_tasks_on_database()

    # TODO:
    def stop_all(self):
        # TODO:
        log.info("Остановка всех задач")
        self._is_stopped = True

        for thread in list(self.tasks.values()):
            if thread.is_alive():
                thread.stop()

        time.sleep(5)

    # TODO:
    def wait_all(self):
        while True:
            time.sleep(0.1)


# TODO: в if __name__ == "__main__":
task_manager = TaskManager()

# TODO: Пример
# TODO: Эти задачи он сам добавляет в базу
# TODO: ... убрать автосоздание запуска из потока?
# task_manager.add(
#     name="example run.bat",
#     command="run.bat",
# )
# task_manager.add(
#     name="example python",
#     command='python -c "import uuid;print(uuid.uuid4())"',
# )
# task_manager.add(
#     name="example python for",
#     command='python -c "import time;[(print(i), time.sleep(1)) for i in range(10)]"',
# )
# task_manager.add(
#     name="example python pyqt gui",
#     command=r'python "C:\Users\ipetrash\PycharmProjects\SimplePyScripts\Base64_examples\gui_base64.py"',
# )

task_manager.start_all()

# TODO:
import atexit
atexit.register(task_manager.stop_all)

# TODO:
task_manager.wait_all()
