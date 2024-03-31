#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import datetime
from unittest import TestCase
from typing import Any

from playhouse.sqlite_ext import SqliteExtDatabase

from db import (
    BaseModel,
    Task,
    TaskRun,
    Notification,
    TaskStatusEnum,
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
        uri: str = "/"

        rs = self.client.get(uri)
        self.assertEqual(rs.status_code, 200)
        self.assertTrue(rs.text)

    def test_task(self):
        with self.subTest("404 - Not Found"):
            rs = self.client.get("/task/99999")
            self.assertEqual(rs.status_code, 404)
            self.assertTrue(rs.text)

        with self.subTest("200 - Ok"):
            task = Task.add(
                name="1",
                command="ping 127.0.0.1",
            )
            uri: str = f"/task/{task.id}"

            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 200)
            self.assertTrue(rs.text)

    def test_task_run(self):
        with self.subTest("404 - Not Found"):
            uri: str = "/task/99999/run/99999"
            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 404)
            self.assertTrue(rs.text)

            task = Task.add(
                name="404",
                command="ping 127.0.0.1",
            )
            uri: str = f"/task/{task.id}/run/99999"
            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 404)
            self.assertTrue(rs.text)

        with self.subTest("200 - Ok"):
            task = Task.add(
                name="200",
                command="ping 127.0.0.1",
            )
            run = task.add_or_get_run()
            uri: str = f"/task/{task.id}/run/{run.seq}"

            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 200)
            self.assertTrue(rs.text)

    def test_notifications(self):
        uri: str = "/notifications"

        rs = self.client.get(uri)
        self.assertEqual(rs.status_code, 200)
        self.assertTrue(rs.text)

    def test_api_tasks(self):
        uri: str = "/api/tasks"

        rs = self.client.get(uri)
        self.assertEqual(rs.status_code, 200)
        self.assertEqual(rs.json, [])

        task_1 = Task.add(
            name="1",
            command="ping 127.0.0.1",
            description="description ping",
            cron="* * * * *",
        )
        rs = self.client.get(uri)
        self.assertEqual(rs.status_code, 200)
        self.assertEqual(rs.json, [task_1.to_dict()])

        task_2 = Task.add(
            name="2",
            command="ping 127.0.0.1\nping 127.0.0.1",
            description="description ping",
            is_infinite=True,
        )
        rs = self.client.get(uri)
        self.assertEqual(rs.status_code, 200)
        self.assertEqual(rs.json, [task_1.to_dict(), task_2.to_dict()])

    def test_api_task_runs(self):
        with self.subTest("404 - Not Found"):
            uri: str = "/api/task/99999/runs"

            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 404)
            # TODO:
            # self.assertEqual(rs.json, [])

        with self.subTest("200 - Ok"):
            task_1 = Task.add(
                name="1",
                command="ping 127.0.0.1",
                description="description ping",
                cron="* * * * *",
            )
            run_1 = task_1.add_or_get_run()
            run_1.set_status(TaskStatusEnum.Running)

            run_2 = task_1.add_or_get_run(datetime.datetime.now())

            run_3 = task_1.add_or_get_run()

            uri: str = f"/api/task/{task_1.id}/runs"
            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 200)

            def get_common_view(d: dict[str, Any]) -> dict[str, Any]:
                return dict(id=d["id"], task=d["task"])

            self.assertEqual(
                [get_common_view(obj) for obj in rs.json],
                [
                    get_common_view(obj.to_dict())
                    for obj in task_1.runs.order_by(TaskRun.id)
                ],
            )
            self.assertEqual(
                [get_common_view(obj) for obj in rs.json],
                [get_common_view(obj.to_dict()) for obj in [run_1, run_2, run_3]],
            )

    def test_api_task_action_run(self):
        with self.subTest("405 - Method Not Allowed"):
            uri: str = "/api/task/99999/action/run"

            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 405)
            # TODO: ?
            # self.assertEqual(rs.json, [])

        with self.subTest("404 - Not Found"):
            uri: str = "/api/task/99999/action/run"

            rs = self.client.post(uri)
            self.assertEqual(rs.status_code, 404)
            # TODO:
            # self.assertEqual(rs.json, [])

        with self.subTest("200 - Ok"):
            task_1 = Task.add(
                name="1",
                command="ping 127.0.0.1",
            )
            self.assertIsNone(task_1.get_last_run())

            uri: str = f"/api/task/{task_1.id}/action/run"

            rs = self.client.post(uri)
            self.assertEqual(rs.status_code, 200)
            self.assertEqual(rs.json["status"], "ok")

            self.assertIsNotNone(task_1.get_last_run())

    def test_api_task_run_logs(self):
        with self.subTest("404 - Not Found"):
            uri: str = "/api/task/99999/run/99999/logs"

            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 404)
            # TODO:
            # self.assertEqual(rs.json, [])

            task_1 = Task.add(
                name="1",
                command="ping 127.0.0.1",
            )

            uri: str = f"/api/task/{task_1.id}/run/99999/logs"
            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 404)
            # TODO:
            # self.assertEqual(rs.json, [])

        with self.subTest("200 - Ok"):
            task_2 = Task.add(
                name="2",
                command="ping 127.0.0.1",
            )
            run_1 = task_2.add_or_get_run()

            uri: str = f"/api/task/{task_2.id}/run/{run_1.id}/logs"

            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 200)
            self.assertEqual(rs.json, [])

            def get_common_view(d: dict[str, Any]) -> dict[str, Any]:
                return dict(
                    id=d["id"], task_run=d["task_run"], text=d["text"], kind=d["kind"]
                )

            items = []
            for i in range(5):
                items.append(run_1.add_log_out(f"out={i}"))
                items.append(run_1.add_log_err(f"out={i}"))

            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 200)
            self.assertEqual(
                [get_common_view(obj) for obj in rs.json],
                [get_common_view(obj.to_dict()) for obj in items],
            )

    def test_api_notifications(self):
        uri: str = "/api/notifications"

        rs = self.client.get(uri)
        self.assertEqual(rs.status_code, 200)

        def get_common_view(d: dict[str, Any]) -> dict[str, Any]:
            return dict(id=d["id"], kind=d["kind"], text=d["text"])

        self.assertEqual(
            [get_common_view(obj) for obj in rs.json],
            [
                get_common_view(obj.to_dict())
                for obj in Notification.select().order_by(Notification.id)
            ],
        )

    def test_api_notification_create(self):
        uri: str = "/api/notification/create"

        with self.subTest("405 - Method Not Allowed"):
            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 405)
            # TODO: ?
            # self.assertEqual(rs.json, [])

        with self.subTest("200 - Ok"):
            data = dict(
                kind=NotificationKindEnum.Email.value,
                name="Title",
                text="Test\nТест",
            )

            rs = self.client.post(uri, json=data)
            self.assertEqual(rs.status_code, 200)

            rs_data = rs.json
            self.assertEqual(rs_data["status"], "ok")
            self.assertTrue(Notification.get_by_id(rs_data["result"][0]["id"]))
            self.assertEqual(rs_data["result"][0]["name"], data["name"])
            self.assertEqual(rs_data["result"][0]["kind"], data["kind"])
            self.assertEqual(rs_data["result"][0]["text"], data["text"])

    def test_favicon(self):
        uri: str = "/favicon.ico"

        rs = self.client.get(uri)
        self.assertEqual(rs.status_code, 200)
        self.assertTrue(rs.data)

    def test_task_run_get_full_url(self):
        run = Task.add(name="*", command="*").add_or_get_run()
        rs = self.client.get(run.get_url())
        self.assertEqual(rs.status_code, 200)
        self.assertTrue(rs.text)
