#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import atexit
import sys
import time
import traceback
from datetime import datetime

from app_task_manager.common import log_manager as log
from app_task_manager.config import ENCODING
from app_task_manager.units.base_unit import BaseUnit
from app_task_manager.units.executor_unit import ExecutorUnit
from app_task_manager.units.maintenance_unit import MaintenanceUnit
from app_task_manager.units.scheduler_unit import SchedulerUnit
from app_task_manager.units.notification_unit import NotificationUnit

from db import TaskRun


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

        self.units: list[BaseUnit] = [
            MaintenanceUnit(owner=self),
            SchedulerUnit(owner=self),
            ExecutorUnit(owner=self),
            NotificationUnit(owner=self),
        ]

        self.create_time: datetime = datetime.now()

        self._has_atexit_callback: bool = False

        self._is_stopped: bool = False

    def get_current_task_runs(self) -> list[TaskRun]:
        items = []
        for unit in self.units:
            if isinstance(unit, ExecutorUnit):
                for thread in unit.tasks.values():
                    if thread.current_task_run:
                        items.append(thread.current_task_run)

        return items

    def start_all(self):
        if self._is_stopped:
            log.warn("Нельзя запустить задачи, когда было вызвана остановка")
            return

        for unit in self.units:
            unit.start()

        if not self._has_atexit_callback:
            atexit.register(self.stop_all)
            self._has_atexit_callback = True

    def stop_all(self):
        log.info("Остановка всех задач")
        self._is_stopped = True

        for unit in self.units:
            unit.stop()

        self._is_stopped = False

    def wait_all(self):
        while True:
            time.sleep(0.1)


def main(loop: bool = False):
    while True:
        try:
            task_manager = TaskManager()
            task_manager.start_all()
            task_manager.wait_all()
        except Exception as e:
            if isinstance(e, KeyboardInterrupt):
                return

            log.exception("Error:")
            time.sleep(10)

        if not loop:
            break


if __name__ == "__main__":
    from pathlib import Path
    from third_party.use_filelock import run_with_lock

    run_with_lock(
        file_name=Path(__file__).resolve(),
        on_duplicated_text="Обнаружен запуск второго приложения. Завершение работы",
        func=main,
        loop=True,
    )
