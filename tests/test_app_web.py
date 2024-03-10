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

    def test_route_api_tasks(self):
        # TODO: добавить тестовые данные в Task

        app.testing = True
        client = app.test_client()
        # TODO: проверить тестовые данные
        print(client.get("/api/tasks").json)
        # print(client.get("/").text)
