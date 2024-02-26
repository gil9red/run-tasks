#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


from datetime import datetime

from psutil import Process, NoSuchProcess, AccessDenied

from app_task_manager.utils import get_prefix_file_name_command, kill_proc_tree
from app_task_manager.units.base_unit import BaseUnit
from db import TaskRun, TaskStatusEnum


class MaintenanceUnit(BaseUnit):
    def process(self):
        self.log.debug(f"{self._log_prefix} Запуск")

        date = datetime.now()

        # Разбирательства с "висячими" запусками
        for run in TaskRun.select().where(
            TaskRun.status == TaskStatusEnum.Running,
            TaskRun.create_date < date,
        ):
            log_prefix = f"{self._log_prefix} [Задача #{run.task.id}, запуск #{run.id}]"
            try:
                # Попробуем найти процесс, если задан
                if run.process_id:
                    p = Process(run.process_id)
                    process_command: str = " ".join(p.cmdline())
                    run_command = get_prefix_file_name_command(run.task, run)

                    # Если процесс найден и в аргументах запуска есть часть названия батника
                    if run_command in process_command:
                        self.log.debug(
                            f"{log_prefix} Закрытие висящего процесса с id={run.process_id}"
                        )
                        kill_proc_tree(run.process_id)

            except (NoSuchProcess, AccessDenied):
                pass

            except Exception as e:
                self.log.debug(
                    f"{log_prefix} Ошибка при работе с процессом {run.process_id}: {e}"
                )

            self.log.debug(
                f"{log_prefix} Установка запуску задачи (дата создания {run.create_date}) "
                f"статус {TaskStatusEnum.Unknown.value}"
            )
            run.set_status(TaskStatusEnum.Unknown)
