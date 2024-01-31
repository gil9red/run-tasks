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
        encoding: str = "utf-8",
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

        # TODO:
        def enqueue_stream(stream: IO[AnyStr], on_callback: Callable[[str], None]):
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
            target=enqueue_stream,
            args=(self.process.stdout, self.on_stdout_callback),
            daemon=True,
        )
        thread_stdout.start()

        thread_stderr = threading.Thread(
            target=enqueue_stream,
            args=(self.process.stderr, self.on_stderr_callback),
            daemon=True,
        )
        thread_stderr.start()

        while True:
            try:
                if self.stop_on():
                    # TODO:
                    print("Нужно остановить процесс:", self.process.pid)
                    kill_proc_tree(self.process.pid)

                self.process_return_code = self.process.wait(timeout=0)
                break

            except psutil.TimeoutExpired:
                pass

        self.on_finish_callback and self.on_finish_callback(self.process)


# TODO:
# @dataclass
class TaskThread(threading.Thread):
    def __init__(self, name):
        super().__init__()

        self.name = name

    def run(self) -> None:
        while True:
            task_db: db.Task = db.Task.get_or_none(name=self.name)
            if not task_db:
                # TODO:
                print(f"Task {self.name} not found!")
                return

            # TODO: Проверить эту ситуацию
            if not task_db.is_enabled:
                # TODO:
                print(f"Task {self.name} is not enabled!")
                return

            task_runs = task_db.get_runs_by([db.TaskStatusEnum.Pending])
            if task_runs:
                task_run = task_runs[0]
                print("Start task run:", task_run)  # TODO:
                self._start_task_run(task_db, task_run)

            time.sleep(1)  # TODO:

    # TODO:
    def _start_task_run(self, task_db: db.Task, task_run_db: db.TaskRun):
        task_run_db.set_status(db.TaskStatusEnum.Running)

        def start_callback(process: psutil.Popen):
            print(f"process_id: {process.pid}", type(process))
            task_run_db.process_id = process.pid
            task_run_db.save()

        def process_stdout(text: str):
            print(f"process_stdout[run: {task_run_db.id}]:", repr(text))
            task_run_db.add_log_out(text)

        def process_stderr(text: str):
            print(f"process_stderr[run: {task_run_db.id}]:", repr(text))
            task_run_db.add_log_err(text)

        def stop_on() -> bool:
            # TODO: Интересно, а есть ли какой-нибудь метод для перечитывания?
            #       ... Если нет, то поддержать какой-нибудь статичный метод для получения поля
            if not db.Task.get_by_id(task_db.id).is_enabled:
                task_run_db.set_status(db.TaskStatusEnum.Stopped)

            # TODO: Интересно, а есть ли какой-нибудь метод для перечитывания?
            #       ... Если нет, то поддержать какой-нибудь статичный метод для получения поля
            return db.TaskRun.get_by_id(task_run_db.id).status in [db.TaskStatusEnum.Stopped, db.TaskStatusEnum.Finished]

        # TODO:
        print(f"current_thread[run: {task_run_db.id}]: ", threading.current_thread())

        thread = ThreadRunProcess(
            command=task_run_db.command,
            on_stdout_callback=process_stdout,
            on_stderr_callback=process_stderr,
            on_start_callback=start_callback,
            stop_on=stop_on,
            # TODO: "cp866" if windows else "utf-8" ?
            encoding="cp866",
        )
        thread.daemon = True
        thread.start()
        thread.join()
        process_return_code = thread.process_return_code
        print(f"process_return_code[run: {task_run_db.id}]: {process_return_code}")

        if process_return_code is not None:
            task_run_db.process_return_code = process_return_code

        # TODO: Интересно, а есть ли какой-нибудь метод для перечитывания?
        #       ... Если нет, то поддержать какой-нибудь статичный метод для получения поля
        # Статус может поменяться, поэтому нужно его заново получить из базы
        final_status = db.TaskRun.get_by_id(task_run_db.id).status

        # Если текущий статус pending или running
        if final_status in (db.TaskStatusEnum.Pending, db.TaskStatusEnum.Running):
            final_status = db.TaskStatusEnum.Finished

        task_run_db.set_status(final_status)
        task_run_db.save()

        print("Finished:", task_run_db)


class TaskManager:
    # TODO:
    tasks: dict[str, TaskThread] = dict()

    # TODO:
    # encoding: str = "utf-8"

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

        task_thread = TaskThread(name=name)
        task_thread.daemon = True  # Thread dies with the program
        self.tasks[name] = task_thread

        return task_thread

    # TODO: название
    def _thread_wrapper_observe_tasks_on_database(self):
        while True:
            for task in db.Task.select().where(db.Task.is_enabled == True):
                name = task.name
                if name not in self.tasks:
                    print(f"Started task {name!r}")
                    self.add(name=name, command=task.command).start()
                else:
                    thread = self.tasks[name]
                    if not thread.is_alive():
                        print(f"Deleted task {name!r}")
                        self.tasks.pop(name)

            time.sleep(0.1)  # TODO:

    # TODO: название
    def observe_tasks_on_database(self):
        # TODO: в конструктор
        self._thread_observe_tasks_on_database = threading.Thread(
            target=self._thread_wrapper_observe_tasks_on_database,
            daemon=True,  # Thread dies with the program
        )
        self._thread_observe_tasks_on_database.start()

    # TODO: Какой-нибудь аргумент о запуске в потоке?
    def start_all(self):
        # TODO:
        self.observe_tasks_on_database()

    # TODO:
    def wait_all(self):
        while True:
            time.sleep(0.1)


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
task_manager.wait_all()
