#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import atexit
import sys
import threading
import time
import traceback
from datetime import datetime, timedelta

from psutil import Process, NoSuchProcess, AccessDenied

from app_task_manager.common import log_manager as log
from app_task_manager.config import ENCODING
from app_task_manager.utils import TaskThread, get_prefix_file_name_command, kill_proc_tree
from db import Task, TaskRun, TaskStatusEnum


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

    # TODO: название
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
                        log.debug(f"{log_prefix} Закрытие висящего процесса с id={run.process_id}")
                        kill_proc_tree(run.process_id)

            except (NoSuchProcess, AccessDenied):
                pass

            except Exception as e:
                log.debug(f"{log_prefix} Ошибка при работе с процессом {run.process_id}: {e}")

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

        log.info(
            f"Ожидание {self.timeout_on_stopping_secs} секунд на завершение потоков"
        )

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
