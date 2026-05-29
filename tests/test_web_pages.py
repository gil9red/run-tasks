#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


from unittest import TestCase

from playhouse.sqlite_ext import SqliteExtDatabase

from run_tasks.app_web.app import limiter
from run_tasks.app_web.config import USERS
from run_tasks.app_web.main import app

from run_tasks.db import (
    BaseModel,
    Task,
    TaskRunStatusEnum,
)


class TestBaseAppWeb(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        limiter.enabled = False
        app.testing = True
        cls.client = app.test_client()

        rs = cls.client.get("/login")
        assert rs.status_code == 200

        login: str = list(USERS.keys())[0]
        password: str = USERS[login]
        cls.client.post("/login", data=dict(login=login, password=password))
        assert rs.status_code == 200

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.get("/logout")

    def setUp(self) -> None:
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

    def tearDown(self) -> None:
        self.test_db.drop_tables(self.models)
        self.test_db.close()


class TestApp(TestBaseAppWeb):
    def test_index(self) -> None:
        uri: str = "/"

        rs = self.client.get(uri)
        self.assertEqual(rs.status_code, 200)

    def test_task(self) -> None:
        with self.subTest("404 - Not Found"):
            rs = self.client.get("/task/99999")
            self.assertEqual(rs.status_code, 404)

        with self.subTest("200 - Ok"):
            task = Task.add(
                name="1",
                command="ping 127.0.0.1",
            )
            uri: str = f"/task/{task.id}"

            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 200)

    def test_task_create(self) -> None:
        uri: str = "/task/create"

        rs = self.client.get(uri)
        self.assertEqual(rs.status_code, 200)

    def test_task_update(self) -> None:
        with self.subTest("404 - Not Found"):
            uri: str = "/task/99999/update"
            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 404)

        with self.subTest("200 - Ok"):
            task = Task.add(
                name="200",
                command="ping 127.0.0.1",
            )
            uri: str = f"/task/{task.id}/update"

            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 200)

    def test_task_run_last(self) -> None:
        with self.subTest("404 - Not Found"):
            uri: str = "/task/99999/run/last"
            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 404)

            task = Task.add(
                name="404",
                command="ping 127.0.0.1",
            )
            uri: str = f"/task/{task.id}/run/last"
            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 404)

            run = task.add_or_get_run()
            self.assertEqual(run.status, TaskRunStatusEnum.PENDING)

            uri: str = f"/task/{task.id}/run/last"
            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 404)

        with self.subTest("200 - Ok"):
            task = Task.add(
                name="200",
                command="ping 127.0.0.1",
            )
            run = task.add_or_get_run()
            run.set_status(TaskRunStatusEnum.RUNNING)

            uri: str = f"/task/{task.id}/run/last"

            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 200)

    def test_task_run(self) -> None:
        with self.subTest("404 - Not Found"):
            uri: str = "/task/99999/run/99999"
            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 404)

            task = Task.add(
                name="404",
                command="ping 127.0.0.1",
            )
            uri: str = f"/task/{task.id}/run/99999"
            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 404)

        with self.subTest("200 - Ok"):
            task = Task.add(
                name="200",
                command="ping 127.0.0.1",
            )
            run = task.add_or_get_run()
            uri: str = f"/task/{task.id}/run/{run.seq}"

            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 200)

    def test_notifications(self) -> None:
        uri: str = "/notifications"

        rs = self.client.get(uri)
        self.assertEqual(rs.status_code, 200)

    def test_favicon(self) -> None:
        uri: str = "/favicon.ico"

        rs = self.client.get(uri)
        self.assertEqual(rs.status_code, 200)

    def test_task_run_get_url(self) -> None:
        run = Task.add(name="*", command="*").add_or_get_run()

        # NOTE: Полный путь не работает с тестовым клиентом
        rs = self.client.get(run.get_url(full=False))
        self.assertEqual(rs.status_code, 200)
