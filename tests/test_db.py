#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import time
from datetime import datetime, timedelta
from unittest import TestCase

from playhouse.sqlite_ext import SqliteExtDatabase

from db import (
    NotDefinedParameterException,
    BaseModel,
    Task,
    TaskRun,
    TaskRunLog,
    Notification,
    TaskRunStatusEnum,
    TaskRunWorkStatusEnum,
    StopReasonEnum,
    LogKindEnum,
    NotificationKindEnum,
)


# Минимальное время задержки между вызовами datetime.now(), чтобы даты не совпали
DATETIME_DELAY_SECS: float = 0.001


class BaseTestCaseDb(TestCase):
    def setUp(self):
        self.models = BaseModel.get_inherited_models()
        self.test_db = SqliteExtDatabase(
            ":memory:",
            pragmas={
                "foreign_keys": 1,
            },
        )
        self.test_db.bind(self.models, bind_refs=False, bind_backrefs=False)
        self.test_db.connect()
        self.test_db.create_tables(self.models)


class TestTask(BaseTestCaseDb):
    def test_get_by_name(self):
        self.assertIsNone(Task.get_by_name("task_1"))

        with self.assertRaises(NotDefinedParameterException):
            Task.get_by_name(name="")

        with self.assertRaises(NotDefinedParameterException):
            Task.get_by_name(name=None)

        task_1 = Task.add(name="task_1", command="*")
        self.assertEqual(task_1, Task.get_by_name(task_1.name))

        task_2 = Task.add(name="task_2", command="*")
        self.assertEqual(task_2, Task.get_by_name(task_2.name))

    def test_get_actual_is_enabled(self):
        task = Task.add(name="task_1", command="*")
        task_clone = Task.get_by_name(name=task.name)
        self.assertEqual(task.is_enabled, task_clone.is_enabled)

        # Значение is_enabled изменено и сохранено в базе
        task.set_enabled(False)
        self.assertFalse(task.is_enabled)
        self.assertTrue(task_clone.is_enabled)  # Содержит старое значение is_enabled

        self.assertEqual(task.is_enabled, task_clone.get_actual_is_enabled())

    def test_set_is_enabled(self):
        task = Task.add(name="task_1", command="*")
        self.assertTrue(task.is_enabled)

        task.set_enabled(False)
        self.assertFalse(task.is_enabled)

        task.set_enabled(True)
        self.assertTrue(task.is_enabled)

    def test_set_is_infinite(self):
        task = Task.add(name="task_1", command="*")
        self.assertFalse(task.is_infinite)

        task.set_is_infinite(True)
        self.assertTrue(task.is_infinite)

        task.set_is_infinite(False)
        self.assertFalse(task.is_infinite)

    def test_set_command(self):
        name = "task command one line"
        command_one_line = "ping 127.0.0.1"

        task = Task.add(
            name=name,
            command=command_one_line,
        )
        self.assertEqual(task.command, command_one_line)

        command_one_line = "ping 1.1.1.1"
        task.set_command(command_one_line)
        self.assertEqual(task.command, command_one_line)

    def test_set_description(self):
        name = "task command one line"
        command_one_line = "ping 127.0.0.1"
        description = None

        task = Task.add(
            name=name,
            command=command_one_line,
            description=description,
        )
        self.assertIsNone(task.description)

        description = f"description {name}"
        task.set_description(description)

        self.assertEqual(task.description, description)

    def test_add(self):
        name = "task command one line"
        command_one_line = "ping 127.0.0.1"
        description = None

        with self.subTest(msg="Создание задачи с простой командой"):
            task = Task.add(
                name=name,
                command=command_one_line,
                description=description,
            )
            self.assertEqual(task.name, name)
            self.assertEqual(task.command, command_one_line)
            self.assertEqual(task.description, description)
            self.assertFalse(task.is_infinite)

            self.assertEqual(
                task,
                Task.add(
                    name=name,
                    command=command_one_line,
                    description=description,
                ),
            )

        with self.subTest(msg="Создание новой задачи с одинаковой командой"):
            task = Task.add(
                name=f"copy of {name}",
                command=command_one_line,
                description=description,
            )
            self.assertEqual(task.name, f"copy of {name}")
            self.assertEqual(task.command, command_one_line)
            self.assertEqual(task.description, description)

        with self.subTest(msg="Создание задачи с сложной командой"):
            name = "task command multi line"
            command_multi_line = (
                "SET IP=127.0.0.1\n" "ping %IP%\n" "ping 127.0.0.1\n" "ping 127.0.0.1"
            )
            description = f"description {name}"

            task = Task.add(
                name=name,
                command=command_multi_line,
                description=description,
            )
            self.assertEqual(task.name, name)
            self.assertEqual(task.command, command_multi_line)
            self.assertEqual(task.description, description)

        with self.subTest(msg="Тест description with html"):
            description = (
                "Скрипт для уведомления о завершенных ранобе в "
                '<a href="https://ranobehub.org/">https://ranobehub.org/</a>.'
            )
            task = Task.add(
                name="description with html",
                command=command_one_line,
                description=description,
                is_infinite=True,
            )
            self.assertEqual(task.description, description)

        with self.subTest(msg="Тест cron"):
            cron = "@hourly"
            task = Task.add(
                name="cron task",
                command=command_one_line,
                description=description,
                cron=cron,
            )
            self.assertEqual(cron, task.cron)

        with self.subTest(msg="Тест is_infinite"):
            task = Task.add(
                name="infinite task",
                command=command_one_line,
                description=description,
                is_infinite=True,
            )
            self.assertTrue(task.is_infinite)

    def test_get_last_scheduled_run(self):
        task = Task.add(name="task_1", command="*")

        self.assertIsNone(task.get_last_scheduled_run())

        task_run_1 = task.add_or_get_run()
        self.assertIsNone(task_run_1.scheduled_date)
        self.assertIsNone(task.get_last_scheduled_run())

        time.sleep(DATETIME_DELAY_SECS)
        task_run_2 = task.add_or_get_run(scheduled_date=datetime.now())
        self.assertIsNotNone(task_run_2)
        self.assertNotEqual(task_run_1, task_run_2)
        self.assertEqual(task.get_last_scheduled_run(), task_run_2)

        task_run_2.set_status(TaskRunStatusEnum.RUNNING)
        self.assertEqual(task.get_last_scheduled_run(), task_run_2)

        task_run_2.set_status(TaskRunStatusEnum.FINISHED)
        self.assertEqual(task.get_last_scheduled_run(), task_run_2)

        time.sleep(DATETIME_DELAY_SECS)
        task_run_3 = task.add_or_get_run(scheduled_date=datetime.now())
        self.assertIsNotNone(task_run_3)
        self.assertEqual(task.get_last_scheduled_run(), task_run_3)

        # Последний запуск без scheduled_date, поэтому ничего не вернется
        task_run_1.set_status(TaskRunStatusEnum.STOPPED)
        task_run_4 = task.add_or_get_run()
        self.assertIsNone(task_run_4.scheduled_date)
        self.assertIsNone(task.get_last_scheduled_run())

    def test_get_pending_run(self):
        task = Task.add(name="task_1", command="*")

        task_run_1 = task.get_pending_run()
        self.assertIsNone(task_run_1)
        task_run_1 = task.add_or_get_run()
        self.assertEqual(task_run_1, task.get_pending_run())

        scheduled_date = datetime.now()
        task_run_2 = task.get_pending_run(has_scheduled_date=scheduled_date is not None)
        self.assertIsNone(task_run_2)
        task_run_2 = task.add_or_get_run(scheduled_date)
        self.assertEqual(
            task_run_2,
            task.get_pending_run(has_scheduled_date=scheduled_date is not None),
        )

    def test_add_or_get_run(self):
        task = Task.add(name="task_1", command="*")

        with self.subTest(msg="Общий"):
            task_run = task.add_or_get_run()
            self.assertIsNotNone(task_run)
            self.assertEqual(task_run.seq, 1)
            self.assertEqual(task.command, task_run.command)
            self.assertEqual(task_run.status, TaskRunStatusEnum.PENDING)
            self.assertIsNone(task_run.process_id)
            self.assertIsNone(task_run.process_return_code)
            self.assertIsNotNone(task_run.create_date)
            self.assertIsNone(task_run.start_date)
            self.assertIsNone(task_run.finish_date)
            self.assertIsNone(task_run.scheduled_date)

            # Изменение статуса из Pending, чтобы следующий add_or_get_run вернул новый TaskRun
            task_run.set_status(TaskRunStatusEnum.STOPPED)

            task_run_2 = task.add_or_get_run()
            self.assertNotEqual(task_run, task_run_2)
            self.assertEqual(task_run_2.seq, 2)

            # Изменение статуса из Pending, чтобы следующий add_or_get_run вернул новый TaskRun
            task_run_2.set_status(TaskRunStatusEnum.STOPPED)

        with self.subTest(msg="Обновление команды задачи"):
            task.set_command("**")
            task_run = task.add_or_get_run()
            self.assertIsNotNone(task_run)
            self.assertEqual(task.command, task_run.command)

            # Изменение статуса из Pending, чтобы следующий тест вернул новый TaskRun
            task_run.set_status(TaskRunStatusEnum.STOPPED)

        with self.subTest(
            msg="Проверка ограничения количества TaskRun по has_scheduled_date"
        ):
            task_run_1 = task.add_or_get_run()
            self.assertIsNotNone(task_run_1)
            self.assertEqual(task_run_1, task.add_or_get_run())

            scheduled_date = datetime.now()
            task_run_2 = task.add_or_get_run(scheduled_date=scheduled_date)
            self.assertIsNotNone(task_run_2)
            self.assertEqual(
                task_run_2, task.add_or_get_run(scheduled_date=scheduled_date)
            )

            # Только один запуск с has_scheduled_date разрешен
            self.assertEqual(
                task_run_2,
                task.add_or_get_run(
                    scheduled_date=datetime.now() + timedelta(minutes=1)
                ),
            )

    def test_get_runs_by(self):
        task = Task.add(name="task_1", command="*")
        self.assertEqual(task.get_runs_by([]), [])

        task_run_1 = task.add_or_get_run()

        time.sleep(DATETIME_DELAY_SECS)
        task_run_2 = task.add_or_get_run(
            scheduled_date=datetime.now() + timedelta(hours=1)
        )

        self.assertEqual(
            task.get_runs_by([TaskRunStatusEnum.PENDING]),
            [task_run_1, task_run_2],
        )
        self.assertEqual(task.get_runs_by([TaskRunStatusEnum.RUNNING]), [])

        task_run_2.set_status(TaskRunStatusEnum.RUNNING)
        self.assertEqual(task.get_runs_by([TaskRunStatusEnum.RUNNING]), [task_run_2])

        task_run_1.set_status(TaskRunStatusEnum.RUNNING)
        self.assertEqual(
            task.get_runs_by([TaskRunStatusEnum.RUNNING]),
            [task_run_1, task_run_2],
        )

    def test_get_current_run(self):
        task = Task.add(name="task_1", command="*")
        self.assertIsNone(task.get_current_run())

        run = task.add_or_get_run()
        self.assertIsNone(task.get_current_run())

        run.set_status(TaskRunStatusEnum.RUNNING)
        self.assertEqual(run, task.get_current_run())

        run.set_status(TaskRunStatusEnum.FINISHED)
        self.assertIsNone(task.get_current_run())

    def test_number_of_runs(self):
        task = Task.add(name="*", command="*")
        self.assertEqual(0, task.number_of_runs)

        # Запуск с Pending не считаются
        run = task.add_or_get_run()
        self.assertEqual(0, task.number_of_runs)

        run.set_status(TaskRunStatusEnum.STOPPED)
        self.assertEqual(1, task.number_of_runs)
        run.delete_instance()

        items = []
        for _ in range(5):
            run = task.add_or_get_run()
            run.set_status(TaskRunStatusEnum.STOPPED)
            items.append(run)

        self.assertEqual(len(items), task.number_of_runs)

        # Удаление первых 3 запусков
        for run in items[:3]:
            run.delete_instance()

        self.assertEqual(5, task.number_of_runs)

        run = task.add_or_get_run()
        self.assertEqual(TaskRunStatusEnum.PENDING, run.status)
        # PENDING не считаются
        self.assertEqual(5, task.number_of_runs)

    def test_get_last_started_run(self):
        task = Task.add(name="*", command="*")
        self.assertIsNone(task.get_last_started_run())

        run1 = task.add_or_get_run()
        self.assertIsNone(task.get_last_started_run())

        run1.set_status(TaskRunStatusEnum.RUNNING)
        self.assertEqual(run1, task.get_last_started_run())

        run1.set_status(TaskRunStatusEnum.STOPPED)
        self.assertEqual(run1, task.get_last_started_run())

        def _check_run(prev: TaskRun, status: TaskRunStatusEnum):
            run = task.add_or_get_run()
            self.assertEqual(run.status, TaskRunStatusEnum.PENDING)
            self.assertEqual(prev, task.get_last_started_run())

            run.set_status(TaskRunStatusEnum.RUNNING)
            run.set_status(status)
            self.assertEqual(run, task.get_last_started_run())
            return run

        run2 = _check_run(run1, TaskRunStatusEnum.FINISHED)
        run3 = _check_run(run2, TaskRunStatusEnum.STOPPED)
        run4 = _check_run(run3, TaskRunStatusEnum.ERROR)
        _check_run(run4, TaskRunStatusEnum.UNKNOWN)

    def test_last_started_run_seq(self):
        task = Task.add(name="*", command="*")
        self.assertIsNone(task.last_started_run_seq)

        run = task.add_or_get_run()
        self.assertIsNone(task.last_started_run_seq)

        run.set_status(TaskRunStatusEnum.RUNNING)
        self.assertEqual(run.seq, task.last_started_run_seq)

        run.set_status(TaskRunStatusEnum.FINISHED)
        self.assertEqual(run.seq, task.last_started_run_seq)

        run1 = task.add_or_get_run()
        self.assertEqual(run.seq, task.last_started_run_seq)

        run1.set_status(TaskRunStatusEnum.RUNNING)
        self.assertEqual(run1.seq, task.last_started_run_seq)

    def test_last_started_run_start_date(self):
        task = Task.add(name="*", command="*")
        self.assertIsNone(task.last_started_run_start_date)

        run = task.add_or_get_run()
        self.assertIsNone(task.last_started_run_start_date)

        run.set_status(TaskRunStatusEnum.RUNNING)
        self.assertIsNotNone(run.start_date)
        self.assertEqual(run.start_date, task.last_started_run_start_date)

        run.set_status(TaskRunStatusEnum.FINISHED)
        self.assertEqual(run.start_date, task.last_started_run_start_date)

        run1 = task.add_or_get_run()
        self.assertEqual(run.start_date, task.last_started_run_start_date)

        run1.set_status(TaskRunStatusEnum.RUNNING)
        self.assertIsNotNone(run1.start_date)
        self.assertEqual(run1.start_date, task.last_started_run_start_date)

    def test_last_work_status(self):
        task = Task.add(name="*", command="*")
        self.assertEqual(task.last_work_status, TaskRunWorkStatusEnum.NONE)

        run = task.add_or_get_run()
        self.assertEqual(task.last_work_status, TaskRunWorkStatusEnum.NONE)

        run.set_status(TaskRunStatusEnum.RUNNING)
        self.assertEqual(task.last_work_status, TaskRunWorkStatusEnum.IN_PROCESSED)

        run.process_return_code = 0
        run.set_status(TaskRunStatusEnum.FINISHED)
        self.assertEqual(task.last_work_status, TaskRunWorkStatusEnum.SUCCESSFUL)

        run.process_return_code = 404
        run.save()
        self.assertEqual(task.last_work_status, TaskRunWorkStatusEnum.FAILED)

        run = Task.add(name="*", command="*").add_or_get_run()
        run.set_status(TaskRunStatusEnum.STOPPED)
        self.assertEqual(task.last_work_status, TaskRunWorkStatusEnum.STOPPED)

        run = Task.add(name="*", command="*").add_or_get_run()
        run.set_status(TaskRunStatusEnum.RUNNING)
        run.set_status(TaskRunStatusEnum.UNKNOWN)
        self.assertEqual(task.last_work_status, TaskRunWorkStatusEnum.FAILED)

    def test_get_all_logs(self):
        task = Task.add(name="*", command="*")

        logs: list[TaskRunLog] = []
        for _ in range(10):
            run = task.add_or_get_run()
            run.set_status(TaskRunStatusEnum.RUNNING)

            prefix: str = f"[run#{run.id}-{run.seq}]"
            for i in range(1, 30 + 1):
                if i % 2 == 0:
                    log = run.add_log_out(f"{prefix} OUT#{i}")
                else:
                    log = run.add_log_err(f"{prefix} ERR#{i}")
                logs.append(log)

            run.set_status(TaskRunStatusEnum.FINISHED)

        filter_by_text = "[run#5-"
        filtered_logs = [log for log in logs if filter_by_text in log.text]
        items_per_page = 10
        order_by_id_desc = TaskRunLog.id.desc()

        with self.subTest("Get all logs"):
            self.assertEqual(logs, task.get_all_logs(page=1, items_per_page=len(logs)))
            self.assertEqual(
                logs[::-1],
                task.get_all_logs(
                    order_by=order_by_id_desc,
                    page=1,
                    items_per_page=len(logs),
                ),
            )

        with self.subTest("Filtering by all logs"):
            self.assertEqual(
                filtered_logs,
                task.get_all_logs(
                    filter_by_text=filter_by_text,
                    page=1,
                    items_per_page=len(logs),
                ),
            )

        with self.subTest("Filtering by all reversed logs"):
            self.assertEqual(
                filtered_logs[::-1],
                task.get_all_logs(
                    order_by=order_by_id_desc,
                    filter_by_text=filter_by_text,
                    page=1,
                    items_per_page=len(logs),
                ),
            )

        with self.subTest("Pagination by all logs"):
            cur_logs = logs

            for page in (1, 2, 3):
                self.assertEqual(
                    cur_logs[(page - 1) * items_per_page : page * items_per_page],
                    task.get_all_logs(page=page, items_per_page=items_per_page),
                    msg=f"page#{page}",
                )

        with self.subTest("Pagination by all reversed logs"):
            cur_logs = logs[::-1]

            for page in (1, 2, 3):
                self.assertEqual(
                    cur_logs[(page - 1) * items_per_page : page * items_per_page],
                    task.get_all_logs(
                        order_by=order_by_id_desc,
                        page=page,
                        items_per_page=items_per_page,
                    ),
                    msg=f"page#{page}",
                )

        with self.subTest("Filtering and pagination"):
            cur_logs = filtered_logs

            for page in (1, 2, 3):
                self.assertEqual(
                    cur_logs[(page - 1) * items_per_page : page * items_per_page],
                    task.get_all_logs(
                        filter_by_text=filter_by_text,
                        page=page,
                        items_per_page=items_per_page,
                    ),
                    msg=f"page#{page}",
                )

        with self.subTest("Filtering and pagination by reversed logs"):
            cur_logs = filtered_logs[::-1]

            for page in (1, 2, 3):
                self.assertEqual(
                    cur_logs[(page - 1) * items_per_page : page * items_per_page],
                    task.get_all_logs(
                        filter_by_text=filter_by_text,
                        order_by=order_by_id_desc,
                        page=page,
                        items_per_page=items_per_page,
                    ),
                    msg=f"page#{page}",
                )


class TestTaskRun(BaseTestCaseDb):
    def test_get_by_seq(self):
        task = Task.add(name="*", command="*")

        run_1 = task.add_or_get_run()
        self.assertEqual(run_1.seq, 1)
        self.assertEqual(run_1, TaskRun.get_by_seq(task.id, 1))

        run_1.set_status(TaskRunStatusEnum.RUNNING)

        run_2 = task.add_or_get_run()
        self.assertEqual(run_2.seq, 2)
        self.assertEqual(run_2, TaskRun.get_by_seq(task.id, 2))

        task_2 = Task.add(name="**", command="*")
        run_3 = task_2.add_or_get_run()
        self.assertEqual(run_3.seq, 1)
        self.assertEqual(run_3, TaskRun.get_by_seq(task_2.id, 1))

    def test_set_status(self):
        with self.subTest(msg="Статус не меняется вместе с зависимыми полями"):
            run = Task.add(name="*", command="*").add_or_get_run()
            self.assertEqual(run.status, TaskRunStatusEnum.PENDING)

            run.set_status(TaskRunStatusEnum.PENDING)
            self.assertEqual(run.status, TaskRunStatusEnum.PENDING)

            self.assertIsNone(run.start_date)
            run.set_status(TaskRunStatusEnum.RUNNING)
            self.assertEqual(run.status, TaskRunStatusEnum.RUNNING)
            self.assertIsNotNone(run.start_date)

            start_date = run.start_date
            run.set_status(TaskRunStatusEnum.RUNNING)
            self.assertEqual(run.start_date, start_date)

            self.assertIsNone(run.finish_date)
            run.set_status(TaskRunStatusEnum.FINISHED)
            self.assertEqual(run.status, TaskRunStatusEnum.FINISHED)
            self.assertIsNotNone(run.finish_date)

            finish_date = run.finish_date
            run.set_status(TaskRunStatusEnum.FINISHED)
            self.assertEqual(run.finish_date, finish_date)

            run_2 = Task.add(name="*", command="*").add_or_get_run()
            self.assertEqual(run_2.status, TaskRunStatusEnum.PENDING)
            run_2.set_status(TaskRunStatusEnum.STOPPED)
            self.assertEqual(run_2.status, TaskRunStatusEnum.STOPPED)
            run_2.set_status(TaskRunStatusEnum.STOPPED)
            self.assertEqual(run_2.status, TaskRunStatusEnum.STOPPED)

            run_3 = Task.add(name="*", command="*").add_or_get_run()
            self.assertEqual(run_3.status, TaskRunStatusEnum.PENDING)
            run_3.set_status(TaskRunStatusEnum.RUNNING)
            run_3.set_status(TaskRunStatusEnum.UNKNOWN)
            self.assertEqual(run_3.status, TaskRunStatusEnum.UNKNOWN)
            run_3.set_status(TaskRunStatusEnum.UNKNOWN)
            self.assertEqual(run_3.status, TaskRunStatusEnum.UNKNOWN)

            run_4 = Task.add(name="*", command="*").add_or_get_run()
            self.assertEqual(run_4.status, TaskRunStatusEnum.PENDING)
            run_4.set_status(TaskRunStatusEnum.ERROR)
            self.assertEqual(run_4.status, TaskRunStatusEnum.ERROR)
            run_4.set_status(TaskRunStatusEnum.ERROR)
            self.assertEqual(run_4.status, TaskRunStatusEnum.ERROR)

        with self.subTest(msg="Установка статуса в None -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            self.assertRaises(ValueError, lambda: run.set_status(None))

        with self.subTest(msg="Pending -> Running -> Pending -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskRunStatusEnum.RUNNING)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskRunStatusEnum.PENDING)
            )

        with self.subTest(msg="Pending -> Running -> Finished -> Pending -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskRunStatusEnum.RUNNING)
            run.set_status(TaskRunStatusEnum.FINISHED)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskRunStatusEnum.PENDING)
            )

        with self.subTest(msg="Pending -> Running -> Stopped -> Pending -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskRunStatusEnum.RUNNING)
            run.set_status(TaskRunStatusEnum.STOPPED)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskRunStatusEnum.PENDING)
            )

        with self.subTest(msg="Pending -> Running -> Unknown -> Pending -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskRunStatusEnum.RUNNING)
            run.set_status(TaskRunStatusEnum.UNKNOWN)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskRunStatusEnum.PENDING)
            )

        with self.subTest(msg="Pending -> Running -> Stopped -> Running -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskRunStatusEnum.RUNNING)
            run.set_status(TaskRunStatusEnum.STOPPED)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskRunStatusEnum.RUNNING)
            )

        with self.subTest(msg="Pending -> Running -> Finished -> Running -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskRunStatusEnum.RUNNING)
            run.set_status(TaskRunStatusEnum.FINISHED)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskRunStatusEnum.RUNNING)
            )

        with self.subTest(msg="Pending -> Running -> Unknown -> Running -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskRunStatusEnum.RUNNING)
            run.set_status(TaskRunStatusEnum.UNKNOWN)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskRunStatusEnum.RUNNING)
            )

        with self.subTest(msg="Pending -> Running -> Finished -> Stopped -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskRunStatusEnum.RUNNING)
            run.set_status(TaskRunStatusEnum.FINISHED)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskRunStatusEnum.STOPPED)
            )

        with self.subTest(msg="Pending -> Running -> Unknown -> Stopped -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskRunStatusEnum.RUNNING)
            run.set_status(TaskRunStatusEnum.UNKNOWN)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskRunStatusEnum.STOPPED)
            )

        with self.subTest(msg="Pending -> Finished -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskRunStatusEnum.FINISHED)
            )

        with self.subTest(msg="Pending -> Stopped -> Finished -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskRunStatusEnum.STOPPED)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskRunStatusEnum.FINISHED)
            )

        with self.subTest(msg="Pending -> Running -> Unknown -> Finished -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskRunStatusEnum.RUNNING)
            run.set_status(TaskRunStatusEnum.UNKNOWN)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskRunStatusEnum.FINISHED)
            )

        with self.subTest(msg="Pending -> Unknown -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskRunStatusEnum.UNKNOWN)
            )

        with self.subTest(msg="Pending -> Stopped -> Unknown -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskRunStatusEnum.STOPPED)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskRunStatusEnum.UNKNOWN)
            )

        with self.subTest(msg="Pending -> Running -> Finished -> Unknown -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskRunStatusEnum.RUNNING)
            run.set_status(TaskRunStatusEnum.FINISHED)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskRunStatusEnum.UNKNOWN)
            )

        with self.subTest(msg="Pending -> Error -> Pending -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskRunStatusEnum.ERROR)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskRunStatusEnum.PENDING)
            )

        with self.subTest(msg="Pending -> Error -> Running -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskRunStatusEnum.ERROR)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskRunStatusEnum.RUNNING)
            )

        with self.subTest(msg="Pending -> Error -> Stopped -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskRunStatusEnum.ERROR)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskRunStatusEnum.STOPPED)
            )

        with self.subTest(msg="Pending -> Error -> Finished -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskRunStatusEnum.ERROR)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskRunStatusEnum.FINISHED)
            )

        with self.subTest(msg="Pending -> Error -> Unknown -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskRunStatusEnum.ERROR)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskRunStatusEnum.UNKNOWN)
            )

        with self.subTest(msg="Pending -> Running -> Finished -> <ok>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            self.assertEqual(run.status, TaskRunStatusEnum.PENDING)

            self.assertIsNone(run.start_date)
            run.set_status(TaskRunStatusEnum.RUNNING)
            self.assertEqual(run.status, TaskRunStatusEnum.RUNNING)
            self.assertIsNotNone(run.start_date)

            self.assertIsNone(run.finish_date)
            run.set_status(TaskRunStatusEnum.FINISHED)
            self.assertEqual(run.status, TaskRunStatusEnum.FINISHED)
            self.assertIsNotNone(run.finish_date)

        with self.subTest(msg="Pending -> Stopped -> <ok>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            self.assertEqual(run.status, TaskRunStatusEnum.PENDING)

            run.set_status(TaskRunStatusEnum.STOPPED)
            self.assertEqual(run.status, TaskRunStatusEnum.STOPPED)

        with self.subTest(msg="Pending -> Running -> Stopped -> <ok>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            self.assertEqual(run.status, TaskRunStatusEnum.PENDING)

            run.set_status(TaskRunStatusEnum.RUNNING)
            run.set_status(TaskRunStatusEnum.STOPPED)
            self.assertEqual(run.status, TaskRunStatusEnum.STOPPED)

        with self.subTest(msg="Pending -> Running -> Unknown -> <ok>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            self.assertEqual(run.status, TaskRunStatusEnum.PENDING)

            run.set_status(TaskRunStatusEnum.RUNNING)
            run.set_status(TaskRunStatusEnum.UNKNOWN)
            self.assertEqual(run.status, TaskRunStatusEnum.UNKNOWN)

        with self.subTest(msg="Pending -> Error -> <ok>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskRunStatusEnum.ERROR)

        with self.subTest(msg="Pending -> Running -> Error -> <ok>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskRunStatusEnum.RUNNING)
            run.set_status(TaskRunStatusEnum.ERROR)

        with self.subTest(msg="Pending -> Running -> Stopped -> Error -> <ok>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskRunStatusEnum.RUNNING)
            run.set_status(TaskRunStatusEnum.STOPPED)
            run.set_status(TaskRunStatusEnum.ERROR)

        with self.subTest(msg="Pending -> Running -> Finished -> Error -> <ok>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskRunStatusEnum.RUNNING)
            run.set_status(TaskRunStatusEnum.FINISHED)
            run.set_status(TaskRunStatusEnum.ERROR)

        with self.subTest(msg="Pending -> Running -> Unknown -> Error -> <ok>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskRunStatusEnum.RUNNING)
            run.set_status(TaskRunStatusEnum.UNKNOWN)
            run.set_status(TaskRunStatusEnum.ERROR)

    @staticmethod
    def _prepare_runs(task_name: str) -> tuple[TaskRun, TaskRun, TaskRun, TaskRun]:
        task = Task.add(name=task_name, command="*")

        run_1 = task.add_or_get_run()
        run_1.set_status(TaskRunStatusEnum.STOPPED)

        run_2 = task.add_or_get_run()
        run_2.set_status(TaskRunStatusEnum.STOPPED)

        run_3 = task.add_or_get_run()
        run_3.set_status(TaskRunStatusEnum.STOPPED)

        run_4 = task.add_or_get_run()
        run_4.set_status(TaskRunStatusEnum.STOPPED)

        return run_1, run_2, run_3, run_4

    def test_prev_task_run(self):
        with self.subTest("Case 1"):
            run_1, run_2, run_3, run_4 = self._prepare_runs("Case 1")

            self.assertIsNone(run_1.prev_task_run)

            self.assertIsNone(run_2.prev_task_run.prev_task_run)
            self.assertEqual(run_2.prev_task_run, run_1)

            self.assertIsNone(run_3.prev_task_run.prev_task_run.prev_task_run)
            self.assertEqual(run_3.prev_task_run, run_2)

            self.assertIsNone(
                run_4.prev_task_run.prev_task_run.prev_task_run.prev_task_run
            )
            self.assertEqual(run_4.prev_task_run, run_3)

        with self.subTest("Case 2"):
            run_1, run_2, run_3, run_4 = self._prepare_runs("Case 2")

            run_1.delete_instance()
            self.assertIsNone(run_2.prev_task_run)

            run_2.delete_instance()
            self.assertIsNone(run_3.prev_task_run)

            self.assertEqual(run_4.prev_task_run, run_3)
            self.assertIsNone(run_4.prev_task_run.prev_task_run)

        with self.subTest("Case 3"):
            run_1, run_2, run_3, run_4 = self._prepare_runs("Case 3")

            run_3.delete_instance()
            self.assertEqual(run_4.prev_task_run, run_2)

            run_2.delete_instance()
            self.assertEqual(run_4.prev_task_run, run_1)

            run_1.delete_instance()
            self.assertIsNone(run_4.prev_task_run)

    def test_next_task_run(self):
        with self.subTest("Case 1"):
            run_1, run_2, run_3, run_4 = self._prepare_runs("Case 1")

            self.assertIsNone(run_4.next_task_run)

            self.assertIsNone(run_3.next_task_run.next_task_run)
            self.assertEqual(run_3.next_task_run, run_4)

            self.assertIsNone(run_2.next_task_run.next_task_run.next_task_run)
            self.assertEqual(run_2.next_task_run, run_3)

            self.assertIsNone(
                run_1.next_task_run.next_task_run.next_task_run.next_task_run
            )
            self.assertEqual(run_1.next_task_run, run_2)

        with self.subTest("Case 2"):
            run_1, run_2, run_3, run_4 = self._prepare_runs("Case 2")

            run_4.delete_instance()
            self.assertIsNone(run_4.next_task_run)

            run_3.delete_instance()
            self.assertIsNone(run_2.next_task_run)

            self.assertEqual(run_1.next_task_run, run_2)
            self.assertIsNone(run_1.next_task_run.next_task_run)

        with self.subTest("Case 3"):
            run_1, run_2, run_3, run_4 = self._prepare_runs("Case 3")

            run_2.delete_instance()
            self.assertEqual(run_1.next_task_run, run_3)

            run_3.delete_instance()
            self.assertEqual(run_1.next_task_run, run_4)

            run_4.delete_instance()
            self.assertIsNone(run_1.next_task_run)

    def test_set_error(self):
        run = Task.add(name="*", command="*").add_or_get_run()
        self.assertEqual(run.status, TaskRunStatusEnum.PENDING)

        text = ""
        try:
            1 / 0
        except Exception:
            import traceback

            text = traceback.format_exc()
            run.set_error(text)

        self.assertTrue(text)
        self.assertEqual(run.status, TaskRunStatusEnum.ERROR)

        last_err_log: str = (
            run.logs.where(TaskRunLog.kind == LogKindEnum.ERR)
            .order_by(TaskRunLog.date.desc())
            .first()
        ).text
        self.assertEqual(last_err_log, text + "\n")

    def test_set_stop(self):
        run = Task.add(name="*", command="*").add_or_get_run()
        self.assertEqual(run.status, TaskRunStatusEnum.PENDING)
        self.assertIsNone(run.stop_reason)

        season = StopReasonEnum.SERVER_API
        run.set_stop(season)
        self.assertEqual(run.stop_reason, season)

    def test_is_scheduled_date_has_arrived(self):
        run = Task.add(name="*", command="*").add_or_get_run()
        self.assertFalse(run.is_scheduled_date_has_arrived())

        future = datetime.now() + timedelta(minutes=1)
        run = Task.add(name="task_future", command="*").add_or_get_run(
            scheduled_date=future
        )
        self.assertFalse(run.is_scheduled_date_has_arrived())

        past = datetime.now() - timedelta(minutes=1)
        run = Task.add(name="task_past", command="*").add_or_get_run(
            scheduled_date=past
        )
        self.assertTrue(run.is_scheduled_date_has_arrived())

    def test_set_process_id(self):
        run = Task.add(name="*", command="*").add_or_get_run()
        self.assertIsNone(run.process_id)

        process_id = 9999
        run.set_process_id(process_id)
        self.assertEqual(process_id, run.process_id)

    def test_get_actual_status(self):
        run = Task.add(name="*", command="*").add_or_get_run()
        run_clone = TaskRun.get_by_id(run.id)
        self.assertEqual(run.status, run_clone.status)

        # Значение status изменено и сохранено в базе
        run.set_status(TaskRunStatusEnum.RUNNING)
        self.assertEqual(run.status, TaskRunStatusEnum.RUNNING)

        # Содержит старое значение
        self.assertEqual(run_clone.status, TaskRunStatusEnum.PENDING)

        self.assertEqual(run.status, run_clone.get_actual_status())

    def test_add_log(self):
        with self.subTest(msg="Common"):
            run = Task.add(name="*", command="*").add_or_get_run()

            items = []
            for i in range(5):
                items.append(run.add_log(f"add_log {i + 1}, out", kind=LogKindEnum.OUT))
                items.append(run.add_log(f"add_log {i + 1}, err", kind=LogKindEnum.ERR))

            self.assertEqual(len(items), run.logs.count())

            run.delete_instance()
            self.assertEqual(0, run.logs.count())

        with self.subTest(msg="Checking argument 'end'"):
            run = Task.add(name="*", command="*").add_or_get_run()

            log1 = run.add_log("1234", kind=LogKindEnum.OUT)
            self.assertEqual(log1.text, "1234\n")

            log2 = run.add_log("1234", kind=LogKindEnum.OUT, end="")
            self.assertEqual(log2.text, "1234")

    def test_add_log_out(self):
        with self.subTest(msg="Common"):
            run = Task.add(name="*", command="*").add_or_get_run()

            items = []
            for i in range(5):
                items.append(run.add_log_out(f"add_log_out {i + 1}"))

            self.assertEqual(len(items), run.logs.count())

            run.delete_instance()
            self.assertEqual(0, run.logs.count())

        with self.subTest(msg="Checking argument 'end'"):
            run = Task.add(name="*", command="*").add_or_get_run()

            log1 = run.add_log_out("1234")
            self.assertEqual(log1.text, "1234\n")

            log2 = run.add_log_out("1234", end="")
            self.assertEqual(log2.text, "1234")

    def test_add_log_err(self):
        with self.subTest(msg="Common"):
            run = Task.add(name="*", command="*").add_or_get_run()

            items = []
            for i in range(5):
                items.append(run.add_log_err(f"add_log_err {i + 1}"))

            self.assertEqual(len(items), run.logs.count())

            run.delete_instance()
            self.assertEqual(0, run.logs.count())

        with self.subTest(msg="Checking argument 'end'"):
            run = Task.add(name="*", command="*").add_or_get_run()

            log1 = run.add_log_err("1234")
            self.assertEqual(log1.text, "1234\n")

            log2 = run.add_log_err("1234", end="")
            self.assertEqual(log2.text, "1234")

    def test_send_notifications(self):
        run = Task.add(name="*", command="*").add_or_get_run()
        self.assertEqual(run.notifications.count(), 0)

        run.send_notifications()
        self.assertNotEqual(run.notifications.count(), 0)

    def test_delete_cascade(self):
        task = Task.add(name="*", command="*")

        items = []
        for _ in range(5):
            run = task.add_or_get_run()
            run.set_status(TaskRunStatusEnum.STOPPED)
            items.append(run)

        self.assertEqual(len(items), task.runs.count())

        task.delete_instance()
        self.assertEqual(0, task.runs.count())

    def test_get_full_url(self):
        run = Task.add(name="*", command="*").add_or_get_run()
        self.assertTrue(run.get_url())
        self.assertTrue(str(run.task.id) in run.get_url())
        self.assertTrue(str(run.seq) in run.get_url())

        self.assertTrue(run.get_url(full=False))
        self.assertTrue(str(run.task.id) in run.get_url(full=False))
        self.assertTrue(str(run.seq) in run.get_url(full=False))

        self.assertNotEqual(run.get_url(), run.get_url(full=False))

    def test_is_success(self):
        run = Task.add(name="*", command="*").add_or_get_run()
        self.assertFalse(run.is_success)

        run.set_status(TaskRunStatusEnum.RUNNING)
        self.assertFalse(run.is_success)

        run.process_return_code = 0
        self.assertFalse(run.is_success)

        run.set_status(TaskRunStatusEnum.FINISHED)
        self.assertTrue(run.is_success)

        run.process_return_code = 404
        self.assertFalse(run.is_success)

    def test_work_status(self):
        run = Task.add(name="*", command="*").add_or_get_run()
        self.assertEqual(run.work_status, TaskRunWorkStatusEnum.NONE)

        run.set_status(TaskRunStatusEnum.RUNNING)
        self.assertEqual(run.work_status, TaskRunWorkStatusEnum.IN_PROCESSED)

        run.process_return_code = 0
        run.set_status(TaskRunStatusEnum.FINISHED)
        self.assertEqual(run.work_status, TaskRunWorkStatusEnum.SUCCESSFUL)

        run.process_return_code = 404
        self.assertEqual(run.work_status, TaskRunWorkStatusEnum.FAILED)

        run = Task.add(name="*", command="*").add_or_get_run()
        run.set_status(TaskRunStatusEnum.STOPPED)
        self.assertEqual(run.work_status, TaskRunWorkStatusEnum.STOPPED)

        run = Task.add(name="*", command="*").add_or_get_run()
        run.set_status(TaskRunStatusEnum.RUNNING)
        run.set_status(TaskRunStatusEnum.UNKNOWN)
        self.assertEqual(run.work_status, TaskRunWorkStatusEnum.FAILED)


class TestTaskRunLog(BaseTestCaseDb):
    def test_delete_cascade(self):
        run = Task.add(name="*", command="*").add_or_get_run()

        items = []
        for i in range(5):
            items.append(run.add_log(f"add_log {i + 1}, out", kind=LogKindEnum.OUT))
            items.append(run.add_log(f"add_log {i + 1}, err", kind=LogKindEnum.ERR))

            items.append(run.add_log_out(f"add_log_out {i + 1}"))
            items.append(run.add_log_err(f"add_log_err {i + 1}"))

        self.assertEqual(len(items), run.logs.count())

        run.delete_instance()
        self.assertEqual(0, run.logs.count())


class TestNotification(BaseTestCaseDb):
    def test_add(self):
        run = Task.add(name="*", command="*").add_or_get_run()
        name = "test"
        text = "Hello World!\nПривет Мир!"

        notification_email = Notification.add(
            task_run=run,
            name=name,
            text=text,
            kind=NotificationKindEnum.EMAIL,
        )
        self.assertIsNotNone(notification_email)
        self.assertEqual(notification_email.task_run, run)
        self.assertEqual(notification_email.name, name)
        self.assertEqual(notification_email.text, text)
        self.assertEqual(notification_email.kind, NotificationKindEnum.EMAIL)
        self.assertIsNotNone(notification_email.append_date)
        self.assertIsNone(notification_email.sending_date)
        self.assertNotEqual(
            notification_email,
            Notification.add(
                task_run=run,
                name=name,
                text=text,
                kind=NotificationKindEnum.EMAIL,
            ),
        )

        notification_tg = Notification.add(
            task_run=run,
            name=name,
            text=text,
            kind=NotificationKindEnum.TELEGRAM,
        )
        self.assertIsNotNone(notification_tg)
        self.assertEqual(notification_tg.task_run, run)
        self.assertEqual(notification_tg.name, name)
        self.assertEqual(notification_tg.text, text)
        self.assertEqual(notification_tg.kind, NotificationKindEnum.TELEGRAM)
        self.assertIsNotNone(notification_tg.append_date)
        self.assertIsNone(notification_tg.sending_date)
        self.assertNotEqual(
            notification_tg,
            Notification.add(
                task_run=run,
                name=name,
                text=text,
                kind=NotificationKindEnum.TELEGRAM,
            ),
        )

    def test_get_unsent(self):
        run = Task.add(name="*", command="*").add_or_get_run()

        self.assertEqual(Notification.get_unsent(), [])

        notification_email = Notification.add(
            task_run=run,
            name="name",
            text="text",
            kind=NotificationKindEnum.EMAIL,
        )
        time.sleep(DATETIME_DELAY_SECS)
        self.assertEqual(Notification.get_unsent(), [notification_email])

        notification_tg = Notification.add(
            task_run=run,
            name="name",
            text="text",
            kind=NotificationKindEnum.TELEGRAM,
        )
        time.sleep(DATETIME_DELAY_SECS)
        self.assertEqual(
            Notification.get_unsent(), [notification_email, notification_tg]
        )

        notification_tg_2 = Notification.add(
            task_run=run,
            name="name",
            text="text",
            kind=NotificationKindEnum.TELEGRAM,
        )
        time.sleep(DATETIME_DELAY_SECS)
        self.assertEqual(
            Notification.get_unsent(),
            [notification_email, notification_tg, notification_tg_2],
        )

        notification_email.set_as_send()
        self.assertEqual(
            Notification.get_unsent(), [notification_tg, notification_tg_2]
        )

        notification_tg_2.set_as_send()
        self.assertEqual(Notification.get_unsent(), [notification_tg])

        notification_email_2 = Notification.add(
            task_run=run,
            name="name",
            text="text",
            kind=NotificationKindEnum.EMAIL,
        )
        self.assertEqual(
            Notification.get_unsent(), [notification_tg, notification_email_2]
        )

        notification_email_2.cancel()
        self.assertEqual(Notification.get_unsent(), [notification_tg])

    def test_set_as_send(self):
        run = Task.add(name="*", command="*").add_or_get_run()

        notification = Notification.add(
            task_run=run,
            name="name",
            text="text",
            kind=NotificationKindEnum.EMAIL,
        )
        self.assertIsNone(notification.sending_date)

        notification.set_as_send()
        self.assertIsNotNone(notification.sending_date)

        time.sleep(DATETIME_DELAY_SECS)

        sending_date = notification.sending_date

        notification.set_as_send()
        self.assertEqual(sending_date, notification.sending_date)

        notification.cancel()
        self.assertEqual(sending_date, notification.sending_date)

    def test_cancel(self):
        run = Task.add(name="*", command="*").add_or_get_run()

        notification = Notification.add(
            task_run=run,
            name="name",
            text="text",
            kind=NotificationKindEnum.EMAIL,
        )
        self.assertIsNone(notification.canceling_date)

        notification.cancel()
        self.assertIsNotNone(notification.canceling_date)

        time.sleep(DATETIME_DELAY_SECS)

        canceling_date = notification.canceling_date

        notification.cancel()
        self.assertEqual(canceling_date, notification.canceling_date)

        notification.set_as_send()
        self.assertEqual(canceling_date, notification.canceling_date)

    def test_is_ready(self):
        run = Task.add(name="*", command="*").add_or_get_run()

        with self.subTest("sending_date"):
            notification = Notification.add(
                task_run=run,
                name="name",
                text="text",
                kind=NotificationKindEnum.EMAIL,
            )
            self.assertIsNone(notification.sending_date)
            self.assertIsNone(notification.canceling_date)
            self.assertTrue(notification.is_ready())

            notification.set_as_send()
            self.assertIsNotNone(notification.sending_date)
            self.assertIsNone(notification.canceling_date)
            self.assertFalse(notification.is_ready())

        with self.subTest("canceling_date"):
            notification = Notification.add(
                task_run=run,
                name="name",
                text="text",
                kind=NotificationKindEnum.EMAIL,
            )
            self.assertIsNone(notification.canceling_date)
            self.assertIsNone(notification.sending_date)
            self.assertTrue(notification.is_ready())

            notification.cancel()
            self.assertIsNone(notification.sending_date)
            self.assertIsNotNone(notification.canceling_date)
            self.assertFalse(notification.is_ready())
