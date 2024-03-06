#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import time
from datetime import datetime, timedelta

from psutil import Process, NoSuchProcess, AccessDenied

from app_task_manager.config import STORAGE_PERIOD_OF_TASK_RUN_IN_DAYS
from app_task_manager.utils import get_prefix_file_name_command, kill_proc_tree
from app_task_manager.units.base_unit import BaseUnit
from db import TaskRun, TaskStatusEnum


class MaintenanceUnit(BaseUnit):
    def __processing_hanging_runs(self):
        task_runs: list[TaskRun] = self.owner.get_current_task_runs()
        min_start_date: datetime = min(
            [
                run.start_date
                for run in task_runs
                if run.get_actual_status() == TaskStatusEnum.Running
            ],
            default=datetime.now(),
        )
        # Небольшая фора
        min_start_date -= timedelta(seconds=10)

        # Разбирательства с "висячими" запусками
        for run in TaskRun.select().where(
            TaskRun.status == TaskStatusEnum.Running,
            TaskRun.start_date < min_start_date,
        ):
            log_prefix = f"[Задача #{run.task.id}, запуск #{run.id}]"
            try:
                # Попробуем найти процесс, если задан
                if run.process_id:
                    p = Process(run.process_id)
                    process_command: str = " ".join(p.cmdline())
                    run_command = get_prefix_file_name_command(run.task, run)

                    # Если процесс найден и в аргументах запуска есть часть названия батника
                    if run_command in process_command:
                        self.log_info(
                            f"{log_prefix} Закрытие висящего процесса с id={run.process_id}"
                        )
                        kill_proc_tree(run.process_id)

            except (NoSuchProcess, AccessDenied):
                pass

            except Exception as e:
                self.log_exception(
                    f"{log_prefix} Ошибка при работе с процессом {run.process_id}:", e
                )

            self.log_info(
                f"{log_prefix} Установка запуску задачи (дата создания {run.create_date}) "
                f"статус {TaskStatusEnum.Unknown.value}"
            )
            run.set_status(TaskStatusEnum.Unknown)

    def __removing_old_runs(self):
        date = datetime.now() - timedelta(days=STORAGE_PERIOD_OF_TASK_RUN_IN_DAYS)

        for run in TaskRun.select().where(
            TaskRun.status.not_in([TaskStatusEnum.Pending, TaskStatusEnum.Running]),
            TaskRun.create_date < date,
        ):
            try:
                self.log_info(f"Удаление запуска {run}")
                run.delete_instance()
            except Exception as e:
                self.log_exception(f"Ошибка при удалении запуска {run}:", e)

    def process(self):
        while not self._is_stopped:
            self.__processing_hanging_runs()
            self.__removing_old_runs()

            time.sleep(60)
