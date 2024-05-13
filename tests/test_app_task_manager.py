#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


from datetime import datetime
from unittest import TestCase

from playhouse.sqlite_ext import SqliteExtDatabase

from db import BaseModel, Task
from app_task_manager.units.scheduler_unit import SchedulerUnit
from app_task_manager.external_task_storage.main import process


class TestSchedulerUnit(TestCase):
    def test__get_scheduled_date(self):
        self.assertGreater(SchedulerUnit._get_scheduled_date("* * * * *"), datetime.now())
        self.assertGreater(SchedulerUnit._get_scheduled_date("0 * * * *"), datetime.now())


class TestRemoteUpdateCreateTasks(TestCase):
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

    def test_process(self):
        self.assertEqual(0, Task.count())

        def _create_data(
                command: str,
                description: str,
                cron: str,
                is_enabled: bool = True,
                is_infinite: bool = False,
        ) -> dict:
            return dict(
                command=command,
                description=description,
                cron=cron,
                is_enabled=is_enabled,
                is_infinite=is_infinite,
            )

        tasks = {
            "task1": _create_data(
                command="command task1",
                description="description task1",
                cron="cron task1",
            ),
            "task2": _create_data(
                command="command task2",
                description="description task2",
                cron="cron task2",
            ),
        }

        with self.subTest(msg="Create"):
            process(tasks)
            self.assertEqual(len(tasks), Task.count())

            process(tasks)
            self.assertEqual(len(tasks), Task.count())

            tasks["task3"] = _create_data(
                command="command task3",
                description="description task3",
                cron="cron task3",
            )
            process(tasks)
            self.assertEqual(len(tasks), Task.count())

            for name, data in tasks.items():
                task = Task.get_by_name(name)
                self.assertEqual(data["command"], task.command)
                self.assertEqual(data["description"], task.description)
                self.assertEqual(data["cron"], task.cron)

        with self.subTest(msg="Update"):
            name = "task1"

            data = tasks[name]

            data["command"] = data["command"][::-1]
            process(tasks)
            self.assertEqual(data["command"], Task.get_by_name(name).command)

            data["description"] = data["description"][::-1]
            process(tasks)
            self.assertEqual(data["description"], Task.get_by_name(name).description)

            data["cron"] = data["cron"][::-1]
            process(tasks)
            self.assertEqual(data["cron"], Task.get_by_name(name).cron)

            data["is_enabled"] = not data["is_enabled"]
            process(tasks)
            self.assertEqual(data["is_enabled"], Task.get_by_name(name).is_enabled)

            data["is_infinite"] = not data["is_infinite"]
            process(tasks)
            self.assertEqual(data["is_infinite"], Task.get_by_name(name).is_infinite)
