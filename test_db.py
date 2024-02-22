#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


from unittest import TestCase
from playhouse.sqlite_ext import SqliteExtDatabase
from db import NotDefinedParameterException, BaseModel, Task, TaskRun, TaskRunLog, TaskStatusEnum


class TestTask(TestCase):
    def setUp(self):
        self.models = BaseModel.get_inherited_models()
        self.test_db = SqliteExtDatabase(":memory:")
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

        with self.subTest(msg="Create task with simple command"):
            task_1 = Task.add(name=name, command=command_one_line, description=description)
            self.assertEqual(task_1.name, name)
            self.assertEqual(task_1.command, command_one_line)
            self.assertEqual(task_1.description, description)

            self.assertEqual(task_1.id, Task.add(name=name, command=command_one_line, description=description).id)

        with self.subTest(msg="Update description of task"):
            description = f"description {name}"
            task_1_copy = Task.add(name=name, command=command_one_line, description=description)
            self.assertEqual(task_1_copy.id, task_1_copy.id)
            self.assertEqual(task_1_copy.name, name)
            self.assertEqual(task_1_copy.command, command_one_line)
            self.assertEqual(task_1_copy.description, description)

        # Разрешено создание задач с одинаковыми командами
        with self.subTest(msg="Create task with copy command"):
            task_2 = Task.add(name=f"copy of {name}", command=command_one_line, description=description)
            self.assertEqual(task_2.name, f"copy of {name}")
            self.assertEqual(task_2.command, command_one_line)
            self.assertEqual(task_2.description, description)

        with self.subTest(msg="Update command of task"):
            command_one_line = "ping 1.1.1.1"
            task_1_copy = Task.add(name=name, command=command_one_line)
            self.assertEqual(task_1_copy.id, task_1_copy.id)
            self.assertEqual(task_1_copy.name, name)
            self.assertEqual(task_1_copy.command, command_one_line)
            self.assertIsNone(task_1_copy.description)  # Описание было затерто, т.к. не передавалось

        with self.subTest(msg="Create task with complex command"):
            name = "task command multi line"
            command_multi_line = "SET IP=127.0.0.1\nping %IP%\nping 127.0.0.1\nping 127.0.0.1"
            description = f"description {name}"

            task_3 = Task.add(name=name, command=command_multi_line, description=description)
            self.assertEqual(task_3.name, name)
            self.assertEqual(task_3.command, command_multi_line)
            self.assertEqual(task_3.description, description)

    def test_add_run(self):
        self.fail()

    def test_get_runs_by(self):
        self.fail()


class TestTaskRun(TestCase):
    def setUp(self):
        self.models = BaseModel.get_inherited_models()
        self.test_db = SqliteExtDatabase(":memory:")
        self.test_db.bind(self.models, bind_refs=False, bind_backrefs=False)
        self.test_db.connect()
        self.test_db.create_tables(self.models)

    def test_set_status(self):
        self.fail()

    def test_set_process_id(self):
        self.fail()

    def test_get_actual_status(self):
        self.fail()

    def test_add_log(self):
        self.fail()

    def test_add_log_out(self):
        self.fail()

    def test_add_log_err(self):
        self.fail()


class TestTaskRunLog(TestCase):
    def setUp(self):
        self.models = BaseModel.get_inherited_models()
        self.test_db = SqliteExtDatabase(":memory:")
        self.test_db.bind(self.models, bind_refs=False, bind_backrefs=False)
        self.test_db.connect()
        self.test_db.create_tables(self.models)
