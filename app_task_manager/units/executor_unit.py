#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import time
from datetime import datetime, timedelta

from app_task_manager.config import ENCODING
from app_task_manager.units.base_unit import BaseUnit
from app_task_manager.utils import TaskThread
from db import Task


class ExecutorUnit(BaseUnit):
    def __init__(self, owner: "TaskManager", encoding: str = ENCODING):
        super().__init__(owner)

        self.encoding = encoding
        self.timeout_on_stopping_secs: int = 5
        self.tasks: dict[str, TaskThread] = dict()

    def _add(self, name: str) -> TaskThread:
        if name in self.tasks:
            # TODO: Другой тип исключения?
            raise Exception(f"Задача {name!r} уже добавлена!")

        task_thread = TaskThread(name=name, encoding=self.encoding)
        self.tasks[name] = task_thread

        return task_thread

    def process(self):
        self.log_info("Запуск всех задач из базы")

        while not self._is_stopped:
            for task in Task.select().where(Task.is_enabled == True):
                name = task.name
                if name not in self.tasks:
                    self.log_info(f"Запуск задачи #{task.id} {name!r}")
                    self._add(name=name).start()
                    continue

                if not self.tasks[name].is_alive():
                    self.log_info(f"Удаление потока задачи #{task.id} {name!r}")
                    self.tasks.pop(name)

            time.sleep(0.1)  # TODO:

    def stop(self):
        super().stop()

        for t in list(self.tasks.values()):
            if t.is_alive():
                t.stop()

        self.log_info(
            f"Ожидание {self.timeout_on_stopping_secs} секунд на завершение потоков"
        )

        end_date = datetime.now() + timedelta(seconds=self.timeout_on_stopping_secs)
        while True:
            if not any(t.is_alive() for t in list(self.tasks.values())):
                self.log_info("Все потоки завершены")
                break

            if datetime.now() > end_date:
                self.log_info("Вышло время на завершение потоков")
                # TODO: Нужно явно убивать процессы (проверить можно убрав выше t.stop())
                break

            time.sleep(0.1)
