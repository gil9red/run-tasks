#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import atexit
import sys
import time
import traceback

from app_task_manager.common import log_manager as log
from app_task_manager.config import ENCODING
from app_task_manager.units.executor_unit import ExecutorUnit
from app_task_manager.units.maintenance_unit import MaintenanceUnit


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

        self.executor_unit = ExecutorUnit(encoding=self.encoding)
        self.maintenance_unit = MaintenanceUnit()

        self._has_atexit_callback: bool = False

        self._is_stopped: bool = False

    def start_all(self):
        if self._is_stopped:
            log.warn("Нельзя запустить задачи, когда было вызвана остановка")
            return

        self.maintenance_unit.start()

        if not self.executor_unit.is_alive():
            self.executor_unit.start()

        if not self._has_atexit_callback:
            atexit.register(self.stop_all)
            self._has_atexit_callback = True

    def stop_all(self):
        log.info("Остановка всех задач")
        self._is_stopped = True

        self.executor_unit.stop()

        self._is_stopped = False

    def wait_all(self):
        while True:
            time.sleep(0.1)


if __name__ == "__main__":
    task_manager = TaskManager()

    task_manager.start_all()

    # TODO: Запуск всех задач из базы
    from db import Task
    for task in Task.select().where(Task.is_enabled == True):
        task.add_run()

    task_manager.wait_all()
