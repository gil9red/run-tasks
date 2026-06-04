#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


from unittest import TestCase

from flask.testing import FlaskClient
from playhouse.sqlite_ext import SqliteExtDatabase

from run_tasks.app_web.app import limiter
from run_tasks.app_web.config import USERS
from run_tasks.app_web.main import app

from run_tasks.db import (
    BaseModel,
    Task,
    TaskRunStatusEnum,
)


class AutoRedirectClient(FlaskClient):
    def open(self, *args, **kwargs):
        kwargs.setdefault("follow_redirects", True)
        return super().open(*args, **kwargs)


class TestBaseAppWeb(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        limiter.enabled = False
        app.testing = True
        app.test_client_class = AutoRedirectClient
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

    def test_task_edit(self) -> None:
        with self.subTest("404 - Not Found"):
            uri: str = "/task/99999/edit"
            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 404)

        with self.subTest("200 - Ok"):
            task = Task.add(
                name="200",
                command="ping 127.0.0.1",
            )
            uri: str = f"/task/{task.id}/edit"

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


class TestIdSlugConverter(TestBaseAppWeb):
    def setUp(self) -> None:
        super().setUp()

        # Создаем запись: id=47, slug="47-veb-pult"
        self.task = Task.create(id=47, name="Веб-пульт", command="...")

    def test_correct_url_returns_200(self) -> None:
        run = self.task.add_or_get_run()

        for uri in [
            "/task/47-veb-pult",
            "/task/47-veb-pult/logs",
            f"/task/47-veb-pult/run/{run.seq}",
            f"/task/47-veb-pult/run/{run.seq}?abc=123&foo=bar",
        ]:
            with self.subTest(uri=uri):
                rs = self.client.get(uri, follow_redirects=False)

                self.assertEqual(rs.status_code, 200)
                self.assertIn(self.task.name, rs.text)

    def test_empty_slug_triggers_308_redirect(self) -> None:
        rs = self.client.get("/task/47-", follow_redirects=False)

        self.assertEqual(rs.status_code, 308)
        self.assertEqual(rs.location, "/task/47-veb-pult")

    def test_incorrect_slug_triggers_308_redirect(self) -> None:
        rs = self.client.get("/task/47-staroe-imya", follow_redirects=False)

        self.assertEqual(rs.status_code, 308)
        self.assertEqual(rs.location, "/task/47-veb-pult")

    def test_only_id_triggers_308_redirect(self) -> None:
        run = self.task.add_or_get_run()

        for uri, expected_uri in [
            ("/task/47", "/task/47-veb-pult"),
            ("/task/47/logs", "/task/47-veb-pult/logs"),
            (f"/task/47/run/{run.seq}", f"/task/47-veb-pult/run/{run.seq}"),
            (
                f"/task/47/run/{run.seq}?abc=123",
                f"/task/47-veb-pult/run/{run.seq}?abc=123",
            ),
        ]:
            with self.subTest(uri=uri, expected_uri=expected_uri):
                rs = self.client.get(uri, follow_redirects=False)

                self.assertEqual(rs.status_code, 308)
                self.assertEqual(rs.location, expected_uri)

    def test_redirect_keeps_query_params(self) -> None:
        rs = self.client.get(
            "/task/47?ref=dashboard&user=admin", follow_redirects=False
        )

        self.assertEqual(rs.status_code, 308)
        self.assertEqual(rs.location, "/task/47-veb-pult?ref=dashboard&user=admin")

    def test_redirect_after_rename_in_db(self) -> None:
        self.task.name = "Новое Имя"
        self.task.save()

        # Стучимся по старому слагу
        rs = self.client.get("/task/47-veb-pult", follow_redirects=False)

        self.assertEqual(rs.status_code, 308)
        self.assertEqual(rs.location, "/task/47-novoe-imia")

    def test_non_existent_id_returns_404(self) -> None:
        rs = self.client.get("/task/999-any-slug", follow_redirects=False)

        self.assertEqual(rs.status_code, 404)
