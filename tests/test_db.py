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
    TaskStatusEnum,
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
                "SET IP=127.0.0.1\n"
                "ping %IP%\n"
                "ping 127.0.0.1\n"
                "ping 127.0.0.1"
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

        task_run_2.set_status(TaskStatusEnum.Running)
        self.assertEqual(task.get_last_scheduled_run(), task_run_2)

        task_run_2.set_status(TaskStatusEnum.Finished)
        self.assertEqual(task.get_last_scheduled_run(), task_run_2)

        time.sleep(DATETIME_DELAY_SECS)
        task_run_3 = task.add_or_get_run(scheduled_date=datetime.now())
        self.assertIsNotNone(task_run_3)
        self.assertEqual(task.get_last_scheduled_run(), task_run_3)

        # Последний запуск без scheduled_date, поэтому ничего не вернется
        task_run_1.set_status(TaskStatusEnum.Stopped)
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
        task_run_2 = task.get_pending_run(scheduled_date=scheduled_date)
        self.assertIsNone(task_run_2)
        task_run_2 = task.add_or_get_run(scheduled_date=scheduled_date)
        self.assertEqual(
            task_run_2, task.get_pending_run(scheduled_date=scheduled_date)
        )

        # Только один запуск с scheduled_date разрешен
        self.assertEqual(
            task_run_2,
            task.get_pending_run(scheduled_date=datetime.now() + timedelta(minutes=1)),
        )

    def test_add_or_get_run(self):
        task = Task.add(name="task_1", command="*")

        with self.subTest(msg="Общий"):
            task_run = task.add_or_get_run()
            self.assertIsNotNone(task_run)
            self.assertEqual(task.command, task_run.command)
            self.assertEqual(task_run.status, TaskStatusEnum.Pending)
            self.assertIsNone(task_run.process_id)
            self.assertIsNone(task_run.process_return_code)
            self.assertIsNotNone(task_run.create_date)
            self.assertIsNone(task_run.start_date)
            self.assertIsNone(task_run.finish_date)
            self.assertIsNone(task_run.scheduled_date)

            # Изменение статуса из Pending, чтобы следующий add_or_get_run вернул новый TaskRun
            task_run.set_status(TaskStatusEnum.Stopped)

            task_run_2 = task.add_or_get_run()
            self.assertNotEqual(task_run, task_run_2)

            # Изменение статуса из Pending, чтобы следующий add_or_get_run вернул новый TaskRun
            task_run_2.set_status(TaskStatusEnum.Stopped)

        with self.subTest(msg="Обновление команды задачи"):
            task.set_command("**")
            task_run = task.add_or_get_run()
            self.assertIsNotNone(task_run)
            self.assertEqual(task.command, task_run.command)

            # Изменение статуса из Pending, чтобы следующий тест вернул новый TaskRun
            task_run.set_status(TaskStatusEnum.Stopped)

        with self.subTest(
            msg="Проверка ограничения количества TaskRun по scheduled_date"
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

            # Только один запуск с scheduled_date разрешен
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
            task.get_runs_by([TaskStatusEnum.Pending]),
            [task_run_1, task_run_2],
        )
        self.assertEqual(task.get_runs_by([TaskStatusEnum.Running]), [])

        task_run_2.set_status(TaskStatusEnum.Running)
        self.assertEqual(task.get_runs_by([TaskStatusEnum.Running]), [task_run_2])

        task_run_1.set_status(TaskStatusEnum.Running)
        self.assertEqual(
            task.get_runs_by([TaskStatusEnum.Running]),
            [task_run_1, task_run_2],
        )

    def test_get_current_run(self):
        task = Task.add(name="task_1", command="*")
        self.assertIsNone(task.get_current_run())

        run = task.add_or_get_run()
        self.assertIsNone(task.get_current_run())

        run.set_status(TaskStatusEnum.Running)
        self.assertEqual(run, task.get_current_run())

        run.set_status(TaskStatusEnum.Finished)
        self.assertIsNone(task.get_current_run())


class TestTaskRun(BaseTestCaseDb):
    def test_set_status(self):
        with self.subTest(msg="Статус не меняется вместе с зависимыми полями"):
            run = Task.add(name="*", command="*").add_or_get_run()
            self.assertEqual(run.status, TaskStatusEnum.Pending)

            run.set_status(TaskStatusEnum.Pending)
            self.assertEqual(run.status, TaskStatusEnum.Pending)

            self.assertIsNone(run.start_date)
            run.set_status(TaskStatusEnum.Running)
            self.assertEqual(run.status, TaskStatusEnum.Running)
            self.assertIsNotNone(run.start_date)

            start_date = run.start_date
            run.set_status(TaskStatusEnum.Running)
            self.assertEqual(run.start_date, start_date)

            self.assertIsNone(run.finish_date)
            run.set_status(TaskStatusEnum.Finished)
            self.assertEqual(run.status, TaskStatusEnum.Finished)
            self.assertIsNotNone(run.finish_date)

            finish_date = run.finish_date
            run.set_status(TaskStatusEnum.Finished)
            self.assertEqual(run.finish_date, finish_date)

            run_2 = Task.add(name="*", command="*").add_or_get_run()
            self.assertEqual(run_2.status, TaskStatusEnum.Pending)
            run_2.set_status(TaskStatusEnum.Stopped)
            self.assertEqual(run_2.status, TaskStatusEnum.Stopped)
            run_2.set_status(TaskStatusEnum.Stopped)
            self.assertEqual(run_2.status, TaskStatusEnum.Stopped)

            run_3 = Task.add(name="*", command="*").add_or_get_run()
            self.assertEqual(run_3.status, TaskStatusEnum.Pending)
            run_3.set_status(TaskStatusEnum.Running)
            run_3.set_status(TaskStatusEnum.Unknown)
            self.assertEqual(run_3.status, TaskStatusEnum.Unknown)
            run_3.set_status(TaskStatusEnum.Unknown)
            self.assertEqual(run_3.status, TaskStatusEnum.Unknown)

            run_4 = Task.add(name="*", command="*").add_or_get_run()
            self.assertEqual(run_4.status, TaskStatusEnum.Pending)
            run_4.set_status(TaskStatusEnum.Error)
            self.assertEqual(run_4.status, TaskStatusEnum.Error)
            run_4.set_status(TaskStatusEnum.Error)
            self.assertEqual(run_4.status, TaskStatusEnum.Error)

        with self.subTest(msg="Установка статуса в None -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            self.assertRaises(ValueError, lambda: run.set_status(None))

        with self.subTest(msg="Pending -> Running -> Pending -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskStatusEnum.Running)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskStatusEnum.Pending)
            )

        with self.subTest(msg="Pending -> Running -> Finished -> Pending -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskStatusEnum.Running)
            run.set_status(TaskStatusEnum.Finished)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskStatusEnum.Pending)
            )

        with self.subTest(msg="Pending -> Running -> Stopped -> Pending -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskStatusEnum.Running)
            run.set_status(TaskStatusEnum.Stopped)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskStatusEnum.Pending)
            )

        with self.subTest(msg="Pending -> Running -> Unknown -> Pending -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskStatusEnum.Running)
            run.set_status(TaskStatusEnum.Unknown)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskStatusEnum.Pending)
            )

        with self.subTest(msg="Pending -> Running -> Stopped -> Running -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskStatusEnum.Running)
            run.set_status(TaskStatusEnum.Stopped)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskStatusEnum.Running)
            )

        with self.subTest(msg="Pending -> Running -> Finished -> Running -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskStatusEnum.Running)
            run.set_status(TaskStatusEnum.Finished)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskStatusEnum.Running)
            )

        with self.subTest(msg="Pending -> Running -> Unknown -> Running -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskStatusEnum.Running)
            run.set_status(TaskStatusEnum.Unknown)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskStatusEnum.Running)
            )

        with self.subTest(msg="Pending -> Running -> Finished -> Stopped -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskStatusEnum.Running)
            run.set_status(TaskStatusEnum.Finished)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskStatusEnum.Stopped)
            )

        with self.subTest(msg="Pending -> Running -> Unknown -> Stopped -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskStatusEnum.Running)
            run.set_status(TaskStatusEnum.Unknown)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskStatusEnum.Stopped)
            )

        with self.subTest(msg="Pending -> Finished -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskStatusEnum.Finished)
            )

        with self.subTest(msg="Pending -> Stopped -> Finished -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskStatusEnum.Stopped)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskStatusEnum.Finished)
            )

        with self.subTest(msg="Pending -> Running -> Unknown -> Finished -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskStatusEnum.Running)
            run.set_status(TaskStatusEnum.Unknown)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskStatusEnum.Finished)
            )

        with self.subTest(msg="Pending -> Unknown -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskStatusEnum.Unknown)
            )

        with self.subTest(msg="Pending -> Stopped -> Unknown -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskStatusEnum.Stopped)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskStatusEnum.Unknown)
            )

        with self.subTest(msg="Pending -> Running -> Finished -> Unknown -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskStatusEnum.Running)
            run.set_status(TaskStatusEnum.Finished)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskStatusEnum.Unknown)
            )

        with self.subTest(msg="Pending -> Error -> Pending -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskStatusEnum.Error)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskStatusEnum.Pending)
            )

        with self.subTest(msg="Pending -> Error -> Running -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskStatusEnum.Error)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskStatusEnum.Running)
            )

        with self.subTest(msg="Pending -> Error -> Stopped -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskStatusEnum.Error)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskStatusEnum.Stopped)
            )

        with self.subTest(msg="Pending -> Error -> Finished -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskStatusEnum.Error)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskStatusEnum.Finished)
            )

        with self.subTest(msg="Pending -> Error -> Unknown -> <error>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskStatusEnum.Error)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskStatusEnum.Unknown)
            )

        with self.subTest(msg="Pending -> Running -> Finished -> <ok>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            self.assertEqual(run.status, TaskStatusEnum.Pending)

            self.assertIsNone(run.start_date)
            run.set_status(TaskStatusEnum.Running)
            self.assertEqual(run.status, TaskStatusEnum.Running)
            self.assertIsNotNone(run.start_date)

            self.assertIsNone(run.finish_date)
            run.set_status(TaskStatusEnum.Finished)
            self.assertEqual(run.status, TaskStatusEnum.Finished)
            self.assertIsNotNone(run.finish_date)

        with self.subTest(msg="Pending -> Stopped -> <ok>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            self.assertEqual(run.status, TaskStatusEnum.Pending)

            run.set_status(TaskStatusEnum.Stopped)
            self.assertEqual(run.status, TaskStatusEnum.Stopped)

        with self.subTest(msg="Pending -> Running -> Stopped -> <ok>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            self.assertEqual(run.status, TaskStatusEnum.Pending)

            run.set_status(TaskStatusEnum.Running)
            run.set_status(TaskStatusEnum.Stopped)
            self.assertEqual(run.status, TaskStatusEnum.Stopped)

        with self.subTest(msg="Pending -> Running -> Unknown -> <ok>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            self.assertEqual(run.status, TaskStatusEnum.Pending)

            run.set_status(TaskStatusEnum.Running)
            run.set_status(TaskStatusEnum.Unknown)
            self.assertEqual(run.status, TaskStatusEnum.Unknown)

        with self.subTest(msg="Pending -> Error -> <ok>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskStatusEnum.Error)

        with self.subTest(msg="Pending -> Running -> Error -> <ok>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskStatusEnum.Running)
            run.set_status(TaskStatusEnum.Error)

        with self.subTest(msg="Pending -> Running -> Stopped -> Error -> <ok>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskStatusEnum.Running)
            run.set_status(TaskStatusEnum.Stopped)
            run.set_status(TaskStatusEnum.Error)

        with self.subTest(msg="Pending -> Running -> Finished -> Error -> <ok>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskStatusEnum.Running)
            run.set_status(TaskStatusEnum.Finished)
            run.set_status(TaskStatusEnum.Error)

        with self.subTest(msg="Pending -> Running -> Unknown -> Error -> <ok>"):
            run = Task.add(name="*", command="*").add_or_get_run()
            run.set_status(TaskStatusEnum.Running)
            run.set_status(TaskStatusEnum.Unknown)
            run.set_status(TaskStatusEnum.Error)

    def test_set_error(self):
        run = Task.add(name="*", command="*").add_or_get_run()
        self.assertEqual(run.status, TaskStatusEnum.Pending)

        text = ""
        try:
            1 / 0
        except Exception:
            import traceback

            text = traceback.format_exc()
            run.set_error(text)

        self.assertTrue(text)
        self.assertEqual(run.status, TaskStatusEnum.Error)

        last_err_log: str = (
            run.logs.where(TaskRunLog.kind == LogKindEnum.Err)
            .order_by(TaskRunLog.date.desc())
            .first()
        ).text
        self.assertEqual(last_err_log, text)

    def test_is_scheduled_date_has_arrived(self):
        run = Task.add(name="*", command="*").add_or_get_run()
        self.assertFalse(run.is_scheduled_date_has_arrived())

        future = datetime.now() + timedelta(minutes=1)
        run = Task.add(name="task_future", command="*").add_or_get_run(scheduled_date=future)
        self.assertFalse(run.is_scheduled_date_has_arrived())

        past = datetime.now() - timedelta(minutes=1)
        run = Task.add(name="task_past", command="*").add_or_get_run(scheduled_date=past)
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
        run.set_status(TaskStatusEnum.Running)
        self.assertEqual(run.status, TaskStatusEnum.Running)

        # Содержит старое значение
        self.assertEqual(run_clone.status, TaskStatusEnum.Pending)

        self.assertEqual(run.status, run_clone.get_actual_status())

    def test_add_log(self):
        run = Task.add(name="*", command="*").add_or_get_run()

        items = []
        for i in range(5):
            items.append(run.add_log(f"add_log {i + 1}, out", kind=LogKindEnum.Out))
            items.append(run.add_log(f"add_log {i + 1}, err", kind=LogKindEnum.Err))

        self.assertEqual(len(items), run.logs.count())

        run.delete_instance()
        self.assertEqual(0, run.logs.count())

    def test_add_log_out(self):
        run = Task.add(name="*", command="*").add_or_get_run()

        items = []
        for i in range(5):
            items.append(run.add_log_out(f"add_log_out {i + 1}"))

        self.assertEqual(len(items), run.logs.count())

        run.delete_instance()
        self.assertEqual(0, run.logs.count())

    def test_add_log_err(self):
        run = Task.add(name="*", command="*").add_or_get_run()

        items = []
        for i in range(5):
            items.append(run.add_log_err(f"add_log_err {i + 1}"))

        self.assertEqual(len(items), run.logs.count())

        run.delete_instance()
        self.assertEqual(0, run.logs.count())

    def test_delete_cascade(self):
        task = Task.add(name="*", command="*")

        items = []
        for _ in range(5):
            run = task.add_or_get_run()
            run.set_status(TaskStatusEnum.Stopped)
            items.append(run)

        self.assertEqual(len(items), task.runs.count())

        task.delete_instance()
        self.assertEqual(0, task.runs.count())


class TestTaskRunLog(BaseTestCaseDb):
    def test_delete_cascade(self):
        run = Task.add(name="*", command="*").add_or_get_run()

        items = []
        for i in range(5):
            items.append(run.add_log(f"add_log {i + 1}, out", kind=LogKindEnum.Out))
            items.append(run.add_log(f"add_log {i + 1}, err", kind=LogKindEnum.Err))

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
            kind=NotificationKindEnum.Email,
        )
        self.assertIsNotNone(notification_email)
        self.assertEqual(notification_email.task_run, run)
        self.assertEqual(notification_email.name, name)
        self.assertEqual(notification_email.text, text)
        self.assertEqual(notification_email.kind, NotificationKindEnum.Email)
        self.assertIsNotNone(notification_email.append_date)
        self.assertIsNone(notification_email.sending_date)
        self.assertNotEqual(
            notification_email,
            Notification.add(
                task_run=run,
                name=name,
                text=text,
                kind=NotificationKindEnum.Email,
            ),
        )

        notification_tg = Notification.add(
            task_run=run,
            name=name,
            text=text,
            kind=NotificationKindEnum.Telegram,
        )
        self.assertIsNotNone(notification_tg)
        self.assertEqual(notification_tg.task_run, run)
        self.assertEqual(notification_tg.name, name)
        self.assertEqual(notification_tg.text, text)
        self.assertEqual(notification_tg.kind, NotificationKindEnum.Telegram)
        self.assertIsNotNone(notification_tg.append_date)
        self.assertIsNone(notification_tg.sending_date)
        self.assertNotEqual(
            notification_tg,
            Notification.add(
                task_run=run,
                name=name,
                text=text,
                kind=NotificationKindEnum.Telegram,
            ),
        )

    def test_get_unsent(self):
        run = Task.add(name="*", command="*").add_or_get_run()

        self.assertEqual(Notification.get_unsent(), [])

        notification_email = Notification.add(
            task_run=run,
            name="name",
            text="text",
            kind=NotificationKindEnum.Email,
        )
        time.sleep(DATETIME_DELAY_SECS)
        self.assertEqual(Notification.get_unsent(), [notification_email])

        notification_tg = Notification.add(
            task_run=run,
            name="name",
            text="text",
            kind=NotificationKindEnum.Telegram,
        )
        time.sleep(DATETIME_DELAY_SECS)
        self.assertEqual(
            Notification.get_unsent(), [notification_email, notification_tg]
        )

        notification_tg_2 = Notification.add(
            task_run=run,
            name="name",
            text="text",
            kind=NotificationKindEnum.Telegram,
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

    def test_set_as_send(self):
        run = Task.add(name="*", command="*").add_or_get_run()

        notification = Notification.add(
            task_run=run,
            name="name",
            text="text",
            kind=NotificationKindEnum.Email,
        )
        self.assertIsNone(notification.sending_date)

        notification.set_as_send()
        self.assertIsNotNone(notification.sending_date)

        time.sleep(DATETIME_DELAY_SECS)
        sending_date = notification.sending_date
        notification.set_as_send()
        self.assertEqual(sending_date, notification.sending_date)
