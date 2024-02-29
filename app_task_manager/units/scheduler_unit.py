#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import time
from datetime import datetime

from cron_converter import Cron

from app_task_manager.units.base_unit import BaseUnit
from db import Task
from third_party.cron_converter__examples.from_jenkins import do_convert


class SchedulerUnit(BaseUnit):
    # TODO: сделать тесты
    @classmethod
    def _get_scheduled_date(cls, cron: str) -> datetime:
        cron = do_convert(cron)

        midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        schedule = Cron(cron).schedule(midnight)

        scheduled_date = schedule.next()
        while scheduled_date < datetime.now():
            scheduled_date = schedule.next()

        return scheduled_date

    def process(self):
        while True:
            for task in Task.select().where(Task.is_enabled == True):
                if task.cron:
                    scheduled_date = self._get_scheduled_date(task.cron)
                elif task.is_infinite:
                    # Без запланированного времени
                    scheduled_date = None
                else:
                    continue

                run = task.get_pending_run(scheduled_date=scheduled_date)
                if not run:
                    run = task.add_or_get_run(scheduled_date=scheduled_date)
                    self.log_info(
                        f"Запланирован запуск:\n"
                        f"    Задача: {task}\n"
                        f"    Запуск: {run}"
                    )

            time.sleep(5)
