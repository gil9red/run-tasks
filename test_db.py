#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


from unittest import TestCase
from playhouse.sqlite_ext import SqliteExtDatabase
from db import BaseModel, Task, TaskRun, TaskRunLog, TaskStatusEnum


class TestTask(TestCase):
    def setUp(self):
        self.models = BaseModel.get_inherited_models()
        self.test_db = SqliteExtDatabase(":memory:")
        self.test_db.bind(self.models, bind_refs=False, bind_backrefs=False)
        self.test_db.connect()
        self.test_db.create_tables(self.models)

    def test_get_by_name(self):
        self.fail()

    def test_get_actual_is_enabled(self):
        self.fail()

    def test_add(self):
        name = "task command one line"
        command_one_line = "ping 127.0.0.1"
        description = None

        task_1 = Task.add(name=name, command=command_one_line, description=description)
        self.assertEqual(task_1.name, name)
        self.assertEqual(task_1.command, command_one_line)
        self.assertEqual(task_1.description, description)

        self.assertEqual(task_1.id, Task.add(name=name, command=command_one_line, description=description).id)

        description = f"description {name}"
        task_1_copy = Task.add(name=name, command=command_one_line, description=description)
        self.assertEqual(task_1_copy.id, task_1_copy.id)
        self.assertEqual(task_1_copy.name, name)
        self.assertEqual(task_1_copy.command, command_one_line)
        self.assertEqual(task_1_copy.description, description)

        name = "task command multi line"
        command_one_line = "SET IP=127.0.0.1\nping %IP%\nping 127.0.0.1\nping 127.0.0.1"
        description = f"description {name}"

        task_2 = Task.add(name=name, command=command_one_line, description=description)
        self.assertEqual(task_2.name, name)
        self.assertEqual(task_2.command, command_one_line)
        self.assertEqual(task_2.description, description)

    def test_set_enabled(self):
        self.fail()

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
