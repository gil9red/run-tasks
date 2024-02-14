#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import atexit
import sys
import threading
import time
import traceback
from datetime import datetime, timedelta

from app_task_manager.common import log_manager as log
from app_task_manager.config import ENCODING
from app_task_manager.utils import TaskThread
from db import Task


def log_uncaught_exceptions(ex_cls, ex, tb):
    # Если было запрошено прерывание
    if isinstance(ex, KeyboardInterrupt):
        sys.exit()

    text = f"{ex_cls.__name__}: {ex}:\n"
    text += "".join(traceback.format_tb(tb))

    log.error(text)

    sys.exit(1)


sys.excepthook = log_uncaught_exceptions


class TaskManager:
    def __init__(self, encoding: str = ENCODING):
        self.encoding = encoding
        self.tasks: dict[str, TaskThread] = dict()
        self.timeout_on_stopping_secs: int = 5

        # TODO: Название
        self._thread_observe_tasks_on_database = threading.Thread(
            target=self._thread_wrapper_observe_tasks_on_database,
            daemon=True,  # Thread dies with the program
        )

        self._has_atexit_callback: bool = False

        self._is_stopped: bool = False

    def _add(self, name: str) -> TaskThread:
        if name in self.tasks:
            # TODO: Другой тип исключения?
            raise Exception(f"Task {name!r} already added!")

        task_thread = TaskThread(name=name, encoding=self.encoding)
        self.tasks[name] = task_thread

        return task_thread

    # TODO: название
    def _thread_wrapper_observe_tasks_on_database(self):
        while not self._is_stopped:
            for task in Task.select().where(Task.is_enabled == True):
                name = task.name
                if name not in self.tasks:
                    log.info(f"Запуск задачи #{task.id} {name!r}")
                    self._add(name=name).start()
                    continue

                if not self.tasks[name].is_alive():
                    log.info(f"Удаление потока задачи #{task.id} {name!r}")
                    self.tasks.pop(name)

            time.sleep(0.1)  # TODO:

    # TODO: название
    def observe_tasks_on_database(self):
        if not self._thread_observe_tasks_on_database.is_alive():
            self._thread_observe_tasks_on_database.start()

    def start_all(self):
        if self._is_stopped:
            log.warn("Нельзя запустить задачи, когда было вызвана остановка")
            return

        log.info("Запуск всех задач из базы")

        # TODO:
        self.observe_tasks_on_database()

        if not self._has_atexit_callback:
            atexit.register(self.stop_all)
            self._has_atexit_callback = True

    def stop_all(self):
        log.info("Остановка всех задач")
        self._is_stopped = True

        for t in list(self.tasks.values()):
            if t.is_alive():
                t.stop()

        log.info(f"Ожидание {self.timeout_on_stopping_secs} секунд на завершение потоков")

        end_date = datetime.now() + timedelta(seconds=self.timeout_on_stopping_secs)
        while True:
            if not any(t.is_alive() for t in list(self.tasks.values())):
                log.info("Все потоки завершены")
                break

            if datetime.now() > end_date:
                log.info("Вышло время на завершение потоков")
                # TODO: Нужно явно убивать процессы (проверить можно убрав выше t.stop())
                break

            time.sleep(0.1)

        self._is_stopped = False

    # TODO:
    def wait_all(self):
        while True:
            time.sleep(0.1)


if __name__ == "__main__":
    task_manager = TaskManager()

    task_manager.start_all()

    # TODO: Запуск всех задач из базы
    for task in Task.select().where(Task.is_enabled == True):
        task.add_run()

    task_manager.wait_all()
