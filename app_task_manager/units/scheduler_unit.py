#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


from datetime import datetime

from app_task_manager.units.base_unit import BaseUnit
from db import Task, TaskRunStatusEnum
from root_common import get_scheduled_date_generator


class SchedulerUnit(BaseUnit):
    def __init__(self, owner: "TaskManager"):
        super().__init__(owner)

        self._process_iter_delay_secs = 5

    @classmethod
    def _get_scheduled_date(cls, cron: str) -> datetime:
        return next(
            get_scheduled_date_generator(cron)
        )

    def process(self):
        for task in Task.select().where(Task.is_enabled == True):
            if task.is_infinite and not task.get_runs_by(
                [TaskRunStatusEnum.RUNNING]
            ):
                # Без запланированного времени
                scheduled_date = None
            elif task.cron:
                scheduled_date = self._get_scheduled_date(task.cron)
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
