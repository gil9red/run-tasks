#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


from unittest import TestCase

from playhouse.sqlite_ext import SqliteExtDatabase

# TODO:
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

from app_web.main import app


class TestAppWeb(TestCase):
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

        app.testing = True
        self.client = app.test_client()

    def test_index(self):
        # TODO:
        # print(self.client.get("/").text)
        self.fail()

    def test_api_tasks(self):
        uri: str = "/api/tasks"

        rs = self.client.get(uri)
        self.assertEqual(self.client.get(uri).status_code, 200)
        self.assertEqual(rs.json, [])

        task_1 = Task.add(
            name="1",
            command="ping 127.0.0.1",
            description="description ping",
            cron="* * * * *",
        )
        rs = self.client.get(uri)
        self.assertEqual(self.client.get(uri).status_code, 200)
        self.assertEqual(rs.json, [task_1.to_dict()])

        task_2 = Task.add(
            name="2",
            command="ping 127.0.0.1\nping 127.0.0.1",
            description="description ping",
            is_infinite=True,
        )
        rs = self.client.get(uri)
        self.assertEqual(self.client.get(uri).status_code, 200)
        self.assertEqual(rs.json, [task_1.to_dict(), task_2.to_dict()])

    def test_api_task_runs(self):
        # TODO:
        self.fail()

    def test_api_task_run_logs(self):
        # TODO:
        self.fail()

    # TODO:
    # def test_favicon(self):
    #     self.fail()
