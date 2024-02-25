#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import atexit
import sys
import threading
import time
import traceback
from datetime import datetime

from psutil import Process, NoSuchProcess, AccessDenied

from app_task_manager.common import log_manager as log
from app_task_manager.config import ENCODING
from app_task_manager.utils import get_prefix_file_name_command, kill_proc_tree
from app_task_manager.units.executor_unit import ExecutorUnit
from db import TaskRun, TaskStatusEnum


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

        self._has_atexit_callback: bool = False

        self._is_stopped: bool = False

    # TODO: В отдельный Unit?
    def _search_unknown_task_runs(self, date: datetime):
        for run in TaskRun.select().where(
            TaskRun.status == TaskStatusEnum.Running, TaskRun.create_date < date
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
                        log.debug(
                            f"{log_prefix} Закрытие висящего процесса с id={run.process_id}"
                        )
                        kill_proc_tree(run.process_id)

            except (NoSuchProcess, AccessDenied):
                pass

            except Exception as e:
                log.debug(
                    f"{log_prefix} Ошибка при работе с процессом {run.process_id}: {e}"
                )

            log.debug(
                f"{log_prefix} Установка запуску задачи (дата создания {run.create_date}) "
                f"статус {TaskStatusEnum.Unknown.value}"
            )
            run.set_status(TaskStatusEnum.Unknown)

    def start_all(self):
        if self._is_stopped:
            log.warn("Нельзя запустить задачи, когда было вызвана остановка")
            return

        log.info("Запуск всех задач из базы")

        threading.Thread(
            target=self._search_unknown_task_runs,
            args=(datetime.now(),),
            daemon=True,  # Thread dies with the program
        ).start()

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
