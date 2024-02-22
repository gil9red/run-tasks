#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import time
from unittest import TestCase

from playhouse.sqlite_ext import SqliteExtDatabase

from db import (
    NotDefinedParameterException,
    BaseModel,
    Task,
    TaskRun,
    TaskStatusEnum,
    LogKindEnum,
)


class TestTask(TestCase):
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
        task_1 = Task.add(name="task_1", command="*")
        task_1_clone = Task.get_by_name(name=task_1.name)
        self.assertEqual(task_1.is_enabled, task_1_clone.is_enabled)

        # Значение is_enabled изменено и сохранено в базе
        task_1.set_enabled(False)
        self.assertFalse(task_1.is_enabled)
        self.assertTrue(task_1_clone.is_enabled)  # Содержит старое значение is_enabled

        self.assertEqual(task_1.is_enabled, task_1_clone.get_actual_is_enabled())

    def test_set_enabled(self):
        task_1 = Task.add(name="task_1", command="*")
        self.assertTrue(task_1.is_enabled)

        task_1.set_enabled(False)
        self.assertFalse(task_1.is_enabled)

        task_1.set_enabled(True)
        self.assertTrue(task_1.is_enabled)

    def test_add(self):
        name = "task command one line"
        command_one_line = "ping 127.0.0.1"
        description = None

        with self.subTest(msg="Создание задачи с простой командой"):
            task_1 = Task.add(
                name=name, command=command_one_line, description=description
            )
            self.assertEqual(task_1.name, name)
            self.assertEqual(task_1.command, command_one_line)
            self.assertEqual(task_1.description, description)

            self.assertEqual(
                task_1.id,
                Task.add(
                    name=name, command=command_one_line, description=description
                ).id,
            )

        with self.subTest(msg="Обновление описания задачи"):
            description = f"description {name}"
            task_1_copy = Task.add(
                name=name, command=command_one_line, description=description
            )
            self.assertEqual(task_1_copy.id, task_1_copy.id)
            self.assertEqual(task_1_copy.name, name)
            self.assertEqual(task_1_copy.command, command_one_line)
            self.assertEqual(task_1_copy.description, description)

        with self.subTest(msg="Создание новой задачи с одинаковой командой"):
            task_2 = Task.add(
                name=f"copy of {name}",
                command=command_one_line,
                description=description,
            )
            self.assertEqual(task_2.name, f"copy of {name}")
            self.assertEqual(task_2.command, command_one_line)
            self.assertEqual(task_2.description, description)

        with self.subTest(msg="Обновление команды задачи"):
            command_one_line = "ping 1.1.1.1"
            task_1_copy = Task.add(name=name, command=command_one_line)
            self.assertEqual(task_1_copy.id, task_1_copy.id)
            self.assertEqual(task_1_copy.name, name)
            self.assertEqual(task_1_copy.command, command_one_line)
            self.assertIsNone(
                task_1_copy.description
            )  # Описание было затерто, т.к. не передавалось

        with self.subTest(msg="Создание задачи с сложной командой"):
            name = "task command multi line"
            command_multi_line = (
                "SET IP=127.0.0.1\nping %IP%\nping 127.0.0.1\nping 127.0.0.1"
            )
            description = f"description {name}"

            task_3 = Task.add(
                name=name, command=command_multi_line, description=description
            )
            self.assertEqual(task_3.name, name)
            self.assertEqual(task_3.command, command_multi_line)
            self.assertEqual(task_3.description, description)

    def test_add_run(self):
        task_1 = Task.add(name="task_1", command="*")
        task_1_run_1 = task_1.add_run()
        self.assertIsNotNone(task_1_run_1)
        self.assertEqual(task_1.command, task_1_run_1.command)
        self.assertEqual(task_1_run_1.status, TaskStatusEnum.Pending)
        self.assertIsNone(task_1_run_1.process_id)
        self.assertIsNone(task_1_run_1.process_return_code)
        self.assertIsNotNone(task_1_run_1.create_date)
        self.assertIsNone(task_1_run_1.start_date)
        self.assertIsNone(task_1_run_1.finish_date)

        # Update task command
        task_1_modified = Task.add(name="task_1", command="**")
        task_1_run_2 = task_1_modified.add_run()
        self.assertIsNotNone(task_1_run_2)
        self.assertEqual(task_1_modified.command, task_1_run_2.command)

    def test_get_runs_by(self):
        task_1 = Task.add(name="task_1", command="*")
        self.assertEqual(task_1.get_runs_by([]), [])

        task_1_run_1 = task_1.add_run()
        time.sleep(0.001)

        task_1_run_2 = task_1.add_run()
        time.sleep(0.001)

        task_1_run_3 = task_1.add_run()

        self.assertEqual(
            task_1.get_runs_by([TaskStatusEnum.Pending]),
            [task_1_run_1, task_1_run_2, task_1_run_3],
        )
        self.assertEqual(task_1.get_runs_by([TaskStatusEnum.Running]), [])

        task_1_run_2.set_status(TaskStatusEnum.Running)
        self.assertEqual(task_1.get_runs_by([TaskStatusEnum.Running]), [task_1_run_2])

        task_1_run_1.set_status(TaskStatusEnum.Running)
        task_1_run_3.set_status(TaskStatusEnum.Running)
        self.assertEqual(
            task_1.get_runs_by([TaskStatusEnum.Running]),
            [task_1_run_1, task_1_run_2, task_1_run_3],
        )


class TestTaskRun(TestCase):
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

    def test_set_status(self):
        with self.subTest(msg="Статус не меняется вместе с зависимыми полями"):
            run = Task.add(name="*", command="*").add_run()
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

            run_2 = Task.add(name="*", command="*").add_run()
            self.assertEqual(run_2.status, TaskStatusEnum.Pending)
            run_2.set_status(TaskStatusEnum.Stopped)
            self.assertEqual(run_2.status, TaskStatusEnum.Stopped)
            run_2.set_status(TaskStatusEnum.Stopped)
            self.assertEqual(run_2.status, TaskStatusEnum.Stopped)

            run_3 = Task.add(name="*", command="*").add_run()
            self.assertEqual(run_3.status, TaskStatusEnum.Pending)
            run_3.set_status(TaskStatusEnum.Running)
            run_3.set_status(TaskStatusEnum.Unknown)
            self.assertEqual(run_3.status, TaskStatusEnum.Unknown)
            run_3.set_status(TaskStatusEnum.Unknown)
            self.assertEqual(run_3.status, TaskStatusEnum.Unknown)

        with self.subTest(msg="Установка статуса в None -> <error>"):
            run = Task.add(name="*", command="*").add_run()
            self.assertRaises(ValueError, lambda: run.set_status(None))

        with self.subTest(msg="Pending -> Running -> Pending -> <error>"):
            run = Task.add(name="*", command="*").add_run()
            run.set_status(TaskStatusEnum.Running)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskStatusEnum.Pending)
            )

        with self.subTest(msg="Pending -> Running -> Finished -> Pending -> <error>"):
            run = Task.add(name="*", command="*").add_run()
            run.set_status(TaskStatusEnum.Running)
            run.set_status(TaskStatusEnum.Finished)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskStatusEnum.Pending)
            )

        with self.subTest(msg="Pending -> Running -> Stopped -> Pending -> <error>"):
            run = Task.add(name="*", command="*").add_run()
            run.set_status(TaskStatusEnum.Running)
            run.set_status(TaskStatusEnum.Stopped)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskStatusEnum.Pending)
            )

        with self.subTest(msg="Pending -> Running -> Unknown -> Pending -> <error>"):
            run = Task.add(name="*", command="*").add_run()
            run.set_status(TaskStatusEnum.Running)
            run.set_status(TaskStatusEnum.Unknown)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskStatusEnum.Pending)
            )

        with self.subTest(msg="Pending -> Running -> Stopped -> Running -> <error>"):
            run = Task.add(name="*", command="*").add_run()
            run.set_status(TaskStatusEnum.Running)
            run.set_status(TaskStatusEnum.Stopped)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskStatusEnum.Running)
            )

        with self.subTest(msg="Pending -> Running -> Finished -> Running -> <error>"):
            run = Task.add(name="*", command="*").add_run()
            run.set_status(TaskStatusEnum.Running)
            run.set_status(TaskStatusEnum.Finished)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskStatusEnum.Running)
            )

        with self.subTest(msg="Pending -> Running -> Unknown -> Running -> <error>"):
            run = Task.add(name="*", command="*").add_run()
            run.set_status(TaskStatusEnum.Running)
            run.set_status(TaskStatusEnum.Unknown)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskStatusEnum.Running)
            )

        with self.subTest(msg="Pending -> Running -> Finished -> Stopped -> <error>"):
            run = Task.add(name="*", command="*").add_run()
            run.set_status(TaskStatusEnum.Running)
            run.set_status(TaskStatusEnum.Finished)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskStatusEnum.Stopped)
            )

        with self.subTest(msg="Pending -> Running -> Unknown -> Stopped -> <error>"):
            run = Task.add(name="*", command="*").add_run()
            run.set_status(TaskStatusEnum.Running)
            run.set_status(TaskStatusEnum.Unknown)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskStatusEnum.Stopped)
            )

        with self.subTest(msg="Pending -> Finished -> <error>"):
            run = Task.add(name="*", command="*").add_run()
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskStatusEnum.Finished)
            )

        with self.subTest(msg="Pending -> Stopped -> Finished -> <error>"):
            run = Task.add(name="*", command="*").add_run()
            run.set_status(TaskStatusEnum.Stopped)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskStatusEnum.Finished)
            )

        with self.subTest(msg="Pending -> Running -> Unknown -> Finished -> <error>"):
            run = Task.add(name="*", command="*").add_run()
            run.set_status(TaskStatusEnum.Running)
            run.set_status(TaskStatusEnum.Unknown)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskStatusEnum.Finished)
            )

        with self.subTest(msg="Pending -> Unknown -> <error>"):
            run = Task.add(name="*", command="*").add_run()
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskStatusEnum.Unknown)
            )

        with self.subTest(msg="Pending -> Stopped -> Unknown -> <error>"):
            run = Task.add(name="*", command="*").add_run()
            run.set_status(TaskStatusEnum.Stopped)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskStatusEnum.Unknown)
            )

        with self.subTest(msg="Pending -> Running -> Finished -> Unknown -> <error>"):
            run = Task.add(name="*", command="*").add_run()
            run.set_status(TaskStatusEnum.Running)
            run.set_status(TaskStatusEnum.Finished)
            self.assertRaises(
                ValueError, lambda: run.set_status(TaskStatusEnum.Unknown)
            )

        with self.subTest(msg="Pending -> Running -> Finished -> <ok>"):
            run = Task.add(name="*", command="*").add_run()
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
            run = Task.add(name="*", command="*").add_run()
            self.assertEqual(run.status, TaskStatusEnum.Pending)

            run.set_status(TaskStatusEnum.Stopped)
            self.assertEqual(run.status, TaskStatusEnum.Stopped)

        with self.subTest(msg="Pending -> Running -> Stopped -> <ok>"):
            run = Task.add(name="*", command="*").add_run()
            self.assertEqual(run.status, TaskStatusEnum.Pending)

            run.set_status(TaskStatusEnum.Running)
            run.set_status(TaskStatusEnum.Stopped)
            self.assertEqual(run.status, TaskStatusEnum.Stopped)

        with self.subTest(msg="Pending -> Running -> Unknown -> <ok>"):
            run = Task.add(name="*", command="*").add_run()
            self.assertEqual(run.status, TaskStatusEnum.Pending)

            run.set_status(TaskStatusEnum.Running)
            run.set_status(TaskStatusEnum.Unknown)
            self.assertEqual(run.status, TaskStatusEnum.Unknown)

    def test_set_process_id(self):
        run = Task.add(name="*", command="*").add_run()
        self.assertIsNone(run.process_id)

        process_id = 9999
        run.set_process_id(process_id)
        self.assertEqual(process_id, run.process_id)

    def test_get_actual_status(self):
        run = Task.add(name="*", command="*").add_run()
        run_clone = TaskRun.get_by_id(run.id)
        self.assertEqual(run.status, run_clone.status)

        # Значение status изменено и сохранено в базе
        run.set_status(TaskStatusEnum.Running)
        self.assertEqual(run.status, TaskStatusEnum.Running)

        # Содержит старое значение
        self.assertEqual(run_clone.status, TaskStatusEnum.Pending)

        self.assertEqual(run.status, run_clone.get_actual_status())

    def test_add_log(self):
        run = Task.add(name="*", command="*").add_run()

        items = []
        for i in range(5):
            items.append(run.add_log(f"add_log {i + 1}, out", kind=LogKindEnum.Out))
            items.append(run.add_log(f"add_log {i + 1}, err", kind=LogKindEnum.Err))

        self.assertEqual(len(items), run.logs.count())

        run.delete_instance()
        self.assertEqual(0, run.logs.count())

    def test_add_log_out(self):
        run = Task.add(name="*", command="*").add_run()

        items = []
        for i in range(5):
            items.append(run.add_log_out(f"add_log_out {i + 1}"))

        self.assertEqual(len(items), run.logs.count())

        run.delete_instance()
        self.assertEqual(0, run.logs.count())

    def test_add_log_err(self):
        run = Task.add(name="*", command="*").add_run()

        items = []
        for i in range(5):
            items.append(run.add_log_err(f"add_log_err {i + 1}"))

        self.assertEqual(len(items), run.logs.count())

        run.delete_instance()
        self.assertEqual(0, run.logs.count())

    def test_delete_cascade(self):
        task = Task.add(name="*", command="*")
        items = [
            task.add_run(),
            task.add_run(),
            task.add_run(),
            task.add_run(),
            task.add_run(),
        ]
        self.assertEqual(len(items), task.runs.count())

        task.delete_instance()
        self.assertEqual(0, task.runs.count())


class TestTaskRunLog(TestCase):
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

    def test_delete_cascade(self):
        run = Task.add(name="*", command="*").add_run()

        items = []
        for i in range(5):
            items.append(run.add_log(f"add_log {i + 1}, out", kind=LogKindEnum.Out))
            items.append(run.add_log(f"add_log {i + 1}, err", kind=LogKindEnum.Err))

            items.append(run.add_log_out(f"add_log_out {i + 1}"))
            items.append(run.add_log_err(f"add_log_err {i + 1}"))

        self.assertEqual(len(items), run.logs.count())

        run.delete_instance()
        self.assertEqual(0, run.logs.count())
