#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


from datetime import datetime
from unittest import TestCase
from typing import Any

from playhouse.sqlite_ext import SqliteExtDatabase

from db import (
    BaseModel,
    Task,
    TaskRun,
    Notification,
    TaskRunStatusEnum,
    NotificationKindEnum,
)

from app_web.config import USERS
from app_web.main import app


class TestBaseAppWeb(TestCase):
    @classmethod
    def setUpClass(cls):
        app.testing = True
        cls.client = app.test_client()

        rs = cls.client.get("/login")
        assert rs.status_code == 200

        login: str = list(USERS.keys())[0]
        password: str = USERS[login]
        cls.client.post("/login", data=dict(login=login, password=password))
        assert rs.status_code == 200

    @classmethod
    def tearDownClass(cls):
        cls.client.get("/logout")

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


class TestAppWeb(TestBaseAppWeb):
    def test_index(self):
        uri: str = "/"

        rs = self.client.get(uri)
        self.assertEqual(rs.status_code, 200)

    def test_task(self):
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

    def test_task_create(self):
        uri: str = "/task/create"

        rs = self.client.get(uri)
        self.assertEqual(rs.status_code, 200)

    def test_task_update(self):
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

    def test_task_run_last(self):
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

    def test_task_run(self):
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

    def test_notifications(self):
        uri: str = "/notifications"

        rs = self.client.get(uri)
        self.assertEqual(rs.status_code, 200)

    def test_favicon(self):
        uri: str = "/favicon.ico"

        rs = self.client.get(uri)
        self.assertEqual(rs.status_code, 200)

    def test_task_run_get_url(self):
        run = Task.add(name="*", command="*").add_or_get_run()

        # NOTE: Полный путь не работает с тестовым клиентом
        rs = self.client.get(run.get_url(full=False))
        self.assertEqual(rs.status_code, 200)


class TestAppApiWeb(TestBaseAppWeb):
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

    def test_api_task_create(self):
        uri: str = "/api/task/create"

        data = {
            "name": "str",
            "command": "Command",
            "description": "Description",
            "cron": "* * * * *",
            "is_enabled": True,
            "is_infinite": False,
        }
        self.assertIsNone(Task.get_by_name(data["name"]))

        with self.subTest("405 - Method Not Allowed"):
            rs = self.client.get(uri, json=data)
            self.assertEqual(rs.status_code, 405)
            self.assertEqual(rs.json["status"], "error")

        with self.subTest("200 - Ok"):
            rs = self.client.post(uri, json=data)
            self.assertEqual(rs.status_code, 200)
            self.assertEqual(rs.json["status"], "ok")
            self.assertEqual(rs.json["result"][0]["name"], data["name"])

            task = Task.get_by_id(rs.json["result"][0]["id"])
            self.assertEqual(task.name, data["name"])

            task = Task.get_by_name(rs.json["result"][0]["name"])
            self.assertEqual(task.name, data["name"])
            self.assertEqual(task.command, data["command"])
            self.assertEqual(task.description, data["description"])
            self.assertEqual(task.cron, data["cron"])
            self.assertEqual(task.is_enabled, data["is_enabled"])
            self.assertEqual(task.is_infinite, data["is_infinite"])

    def test_api_task_get(self):
        with self.subTest("404 - Not Found"):
            uri: str = "api/task/99999"
            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 404)

        with self.subTest("405 - Method Not Allowed"):
            uri: str = "api/task/99999"
            rs = self.client.post(uri)
            self.assertEqual(rs.status_code, 405)
            self.assertEqual(rs.json["status"], "error")

        with self.subTest("200 - Ok"):
            task = Task.add(
                name="200",
                command="ping 127.0.0.1",
            )
            uri: str = f"api/task/{task.id}"

            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 200)
            self.assertEqual(rs.json["result"], [task.to_dict()])

    def test_api_task_update(self):
        with self.subTest("405 - Method Not Allowed"):
            uri: str = "/api/task/404/update"
            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 405)
            self.assertEqual(rs.json["status"], "error")

        with self.subTest("404 - Not Found"):
            uri: str = "/api/task/404/update"
            rs = self.client.post(uri)
            self.assertEqual(rs.status_code, 404)
            self.assertEqual(rs.json["status"], "error")

        with self.subTest("200 - Ok"):
            data = {
                "name":  "Foo Bar",
                "command": "Command",
                "description": "Description",
                "cron": "* * * * *",
                "is_enabled": False,
                "is_infinite": True,
            }

            task = Task.add(
                name=data["name"],
                command=data["command"],
            )
            uri: str = f"/api/task/{task.id}/update"

            rs = self.client.post(uri, json=data)
            self.assertEqual(rs.status_code, 200)
            self.assertEqual(rs.json["status"], "ok")
            self.assertEqual(rs.json["result"][0]["name"], data["name"])

            task = Task.get_by_id(rs.json["result"][0]["id"])
            self.assertEqual(task.name, data["name"])

            task = Task.get_by_name(rs.json["result"][0]["name"])
            self.assertEqual(task.name, data["name"])
            self.assertEqual(task.command, data["command"])
            self.assertEqual(task.description, data["description"])
            self.assertEqual(task.cron, data["cron"])
            self.assertEqual(task.is_enabled, data["is_enabled"])
            self.assertEqual(task.is_infinite, data["is_infinite"])

    def test_api_task_delete(self):
        uri: str = f"/api/task/404/delete"

        with self.subTest("405 - Method Not Allowed"):
            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 405)
            self.assertEqual(rs.json["status"], "error")

            rs = self.client.post(uri)
            self.assertEqual(rs.status_code, 405)
            self.assertEqual(rs.json["status"], "error")

        with self.subTest("404 - Not Found"):
            rs = self.client.delete(uri)
            self.assertEqual(rs.status_code, 404)
            self.assertEqual(rs.json["status"], "error")

        with self.subTest("200 - Ok"):
            task = Task.add(
                name="name",
                command="command",
            )
            uri: str = f"/api/task/{task.id}/delete"

            rs = self.client.delete(uri)
            self.assertEqual(rs.status_code, 200)
            self.assertIsNone(task.get_by_name(task.name))

    def test_api_task_runs(self):
        with self.subTest("404 - Not Found"):
            uri: str = "/api/task/99999/runs"

            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 404)
            self.assertEqual(rs.json["status"], "error")

        with self.subTest("200 - Ok"):
            task_1 = Task.add(
                name="1",
                command="ping 127.0.0.1",
                description="description ping",
                cron="* * * * *",
            )
            run_1 = task_1.add_or_get_run()
            run_1.set_status(TaskRunStatusEnum.RUNNING)

            run_2 = task_1.add_or_get_run(datetime.now())

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

    def test_api_task_do_run(self):
        with self.subTest("405 - Method Not Allowed"):
            uri: str = "/api/task/99999/do-run"

            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 405)
            self.assertEqual(rs.json["status"], "error")

        with self.subTest("404 - Not Found"):
            uri: str = "/api/task/99999/do-run"

            rs = self.client.post(uri)
            self.assertEqual(rs.status_code, 404)
            self.assertEqual(rs.json["status"], "error")

        with self.subTest("200 - Ok"):
            task_1 = Task.add(
                name="1",
                command="ping 127.0.0.1",
            )
            self.assertIsNone(task_1.get_last_run())

            uri: str = f"/api/task/{task_1.id}/do-run"

            rs = self.client.post(uri)
            self.assertEqual(rs.status_code, 200)
            self.assertEqual(rs.json["status"], "ok")

            self.assertIsNotNone(task_1.get_last_run())

    def test_api_task_run_get(self):
        with self.subTest("405 - Method Not Allowed"):
            uri: str = "/api/task/99999/run/99999"

            rs = self.client.post(uri)
            self.assertEqual(rs.status_code, 405)
            self.assertEqual(rs.json["status"], "error")

        with self.subTest("404 - Not Found"):
            uri: str = "/api/task/99999/run/99999"

            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 404)
            self.assertEqual(rs.json["status"], "error")

            task_1 = Task.add(
                name="1",
                command="ping 127.0.0.1",
            )

            uri: str = f"/api/task/{task_1.id}/run/99999"
            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 404)
            self.assertEqual(rs.json["status"], "error")

        with self.subTest("200 - Ok"):
            task_2 = Task.add(
                name="2",
                command="ping 127.0.0.1",
            )
            run_1 = task_2.add_or_get_run()

            uri: str = f"/api/task/{task_2.id}/run/{run_1.id}"

            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 200)

            def get_common_view(d: dict[str, Any]) -> dict[str, Any]:
                return dict(
                    id=d["id"], task_run=d["task"], seq=d["seq"]
                )

            self.assertEqual(
                get_common_view(rs.json["result"][0]),
                get_common_view(run_1.to_dict())
            )

    def test_api_task_run_get_last(self):
        uri_template: str = "/api/task/{task_id}/run/last"

        with self.subTest("405 - Method Not Allowed"):
            uri: str = uri_template.format(task_id=99999)

            rs = self.client.post(uri)
            self.assertEqual(rs.status_code, 405)
            self.assertEqual(rs.json["status"], "error")

        with self.subTest("404 - Not Found"):
            uri: str = uri_template.format(task_id=99999)

            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 404)
            self.assertEqual(rs.json["status"], "error")

            task_1 = Task.add(
                name="1",
                command="ping 127.0.0.1",
            )

            uri: str = uri_template.format(task_id=task_1.id)
            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 404)
            self.assertEqual(rs.json["status"], "error")

        with self.subTest("200 - Ok"):
            task_2 = Task.add(
                name="2",
                command="ping 127.0.0.1",
            )
            run_1 = task_2.add_or_get_run()

            uri: str = uri_template.format(task_id=task_2.id)

            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 200)

            def get_common_view(d: dict[str, Any]) -> dict[str, Any]:
                return dict(
                    id=d["id"], task_run=d["task"], seq=d["seq"]
                )

            self.assertEqual(
                get_common_view(rs.json["result"][0]),
                get_common_view(run_1.to_dict())
            )

    def test_api_task_run_do_stop(self):
        with self.subTest("405 - Method Not Allowed"):
            uri: str = "/api/task/99999/run/99999/do-stop"

            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 405)
            self.assertEqual(rs.json["status"], "error")

        with self.subTest("404 - Not Found"):
            uri: str = "/api/task/99999/run/99999/do-stop"

            rs = self.client.post(uri)
            self.assertEqual(rs.status_code, 404)
            self.assertEqual(rs.json["status"], "error")

            task_1 = Task.add(
                name="1",
                command="ping 127.0.0.1",
            )

            uri: str = f"/api/task/{task_1.id}/run/99999/do-stop"
            rs = self.client.post(uri)
            self.assertEqual(rs.status_code, 404)
            self.assertEqual(rs.json["status"], "error")

        with self.subTest("200 - Ok"):
            task_2 = Task.add(
                name="2",
                command="ping 127.0.0.1",
            )
            run_1 = task_2.add_or_get_run()

            uri: str = f"/api/task/{task_2.id}/run/{run_1.id}/do-stop"

            rs = self.client.post(uri)
            self.assertEqual(rs.status_code, 200)
            self.assertEqual(rs.json["status"], "ok")

            run_1 = run_1.get_new()
            self.assertEqual(run_1.status, TaskRunStatusEnum.STOPPED)

    def test_api_task_run_do_send_notifications(self):
        with self.subTest("405 - Method Not Allowed"):
            uri: str = "/api/task/99999/run/99999/do-send-notifications"

            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 405)
            self.assertEqual(rs.json["status"], "error")

        with self.subTest("404 - Not Found"):
            uri: str = "/api/task/99999/run/99999/do-send-notifications"

            rs = self.client.post(uri)
            self.assertEqual(rs.status_code, 404)
            self.assertEqual(rs.json["status"], "error")

            task_1 = Task.add(
                name="1",
                command="ping 127.0.0.1",
            )

            uri: str = f"/api/task/{task_1.id}/run/99999/do-send-notifications"
            rs = self.client.post(uri)
            self.assertEqual(rs.status_code, 404)
            self.assertEqual(rs.json["status"], "error")

        with self.subTest("200 - Ok"):
            task_2 = Task.add(
                name="2",
                command="ping 127.0.0.1",
            )
            run_1 = task_2.add_or_get_run()
            self.assertEqual(run_1.notifications.count(), 0)

            uri: str = f"/api/task/{task_2.id}/run/{run_1.id}/do-send-notifications"

            rs = self.client.post(uri)
            self.assertEqual(rs.status_code, 200)
            self.assertEqual(rs.json["status"], "ok")

            self.assertNotEqual(run_1.notifications.count(), 0)

    def test_api_task_run_logs(self):
        with self.subTest("404 - Not Found"):
            uri: str = "/api/task/99999/run/99999/logs"

            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 404)
            self.assertEqual(rs.json["status"], "error")

            task_1 = Task.add(
                name="1",
                command="ping 127.0.0.1",
            )

            uri: str = f"/api/task/{task_1.id}/run/99999/logs"
            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 404)
            self.assertEqual(rs.json["status"], "error")

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

    def test_api_task_run_last_logs(self):
        uri_template: str = "/api/task/{task_id}/run/last/logs"

        with self.subTest("404 - Not Found"):
            uri: str = uri_template.format(task_id=99999)

            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 404)
            self.assertEqual(rs.json["status"], "error")

        with self.subTest("200 - Ok"):
            task_1 = Task.add(
                name="2",
                command="ping 127.0.0.1",
            )
            run_1 = task_1.add_or_get_run()

            uri: str = uri_template.format(task_id=task_1.id)

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
            self.assertEqual(rs.json["status"], "error")

        with self.subTest("200 - Ok"):
            data = dict(
                kind=NotificationKindEnum.EMAIL.value,
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

    def test_api_notifications_get_number_of_unsent(self):
        uri: str = "/api/notifications/get-number-of-unsent"

        rs = self.client.get(uri)
        self.assertEqual(rs.status_code, 200)
        self.assertEqual(rs.json["status"], "ok")
        self.assertEqual(rs.json["result"][0]["number"], 0)

        notification1 = Notification.add(
            kind=NotificationKindEnum.EMAIL,
            name="Title",
            text="Test\nТест",
            task_run=None,
        )
        rs = self.client.get(uri)
        self.assertEqual(rs.status_code, 200)
        self.assertEqual(rs.json["status"], "ok")
        self.assertEqual(rs.json["result"][0]["number"], 1)

        notification2 = Notification.add(
            kind=NotificationKindEnum.EMAIL,
            name="Title",
            text="Test\nТест",
            task_run=None,
        )
        rs = self.client.get(uri)
        self.assertEqual(rs.status_code, 200)
        self.assertEqual(rs.json["status"], "ok")
        self.assertEqual(rs.json["result"][0]["number"], 2)

        notification1.set_as_send()
        rs = self.client.get(uri)
        self.assertEqual(rs.status_code, 200)
        self.assertEqual(rs.json["status"], "ok")
        self.assertEqual(rs.json["result"][0]["number"], 1)

        notification2.set_as_send()
        rs = self.client.get(uri)
        self.assertEqual(rs.status_code, 200)
        self.assertEqual(rs.json["status"], "ok")
        self.assertEqual(rs.json["result"][0]["number"], 0)

    def test_api_notifications_all_do_stop(self):
        uri: str = "/api/notifications/all/do-stop"

        self.assertEqual(0, len(Notification.get_unsent()))

        with self.subTest("405 - Method Not Allowed"):
            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 405)
            self.assertEqual(rs.json["status"], "error")

        with self.subTest("200 - Ok"):
            rs = self.client.post(uri)
            self.assertEqual(rs.status_code, 200)
            self.assertEqual(rs.json["status"], "ok")

            self.assertEqual(0, len(Notification.get_unsent()))

            notification_1 = Notification.add(
                kind=NotificationKindEnum.EMAIL,
                name="Title",
                text="Test\nТест",
                task_run=None,
            )
            self.assertTrue(notification_1.is_ready())
            self.assertIsNone(notification_1.canceling_date)
            self.assertIsNone(notification_1.sending_date)
            self.assertEqual(1, len(Notification.get_unsent()))

            notification_2 = Notification.add(
                kind=NotificationKindEnum.EMAIL,
                name="Title",
                text="Test\nТест",
                task_run=None,
            )
            self.assertTrue(notification_2.is_ready())
            self.assertIsNone(notification_2.canceling_date)
            self.assertIsNone(notification_2.sending_date)
            self.assertEqual(2, len(Notification.get_unsent()))

            rs = self.client.post(uri)
            self.assertEqual(rs.status_code, 200)
            self.assertEqual(rs.json["status"], "ok")
            self.assertEqual(0, len(Notification.get_unsent()))

            for obj in [notification_1, notification_2]:
                # Нужно перечитать значение из БД
                obj = obj.get_new()

                self.assertFalse(obj.is_ready())
                self.assertIsNotNone(obj.canceling_date)
                self.assertIsNone(obj.sending_date)

    def test_api_notification_do_stop(self):
        uri_format: str = "/api/notification/{id}/do-stop"

        with self.subTest("404 - Not Found"):
            rs = self.client.post(uri_format.format(id=999_999))
            self.assertEqual(rs.status_code, 404)

        with self.subTest("405 - Method Not Allowed"):
            rs = self.client.get(uri_format.format(id=999_999))
            self.assertEqual(rs.status_code, 405)
            self.assertEqual(rs.json["status"], "error")

        with self.subTest("200 - Ok"):
            self.assertEqual(0, len(Notification.get_unsent()))

            notification_1 = Notification.add(
                kind=NotificationKindEnum.EMAIL,
                name="Title",
                text="Test\nТест",
                task_run=None,
            )
            self.assertTrue(notification_1.is_ready())
            self.assertIsNone(notification_1.canceling_date)
            self.assertIsNone(notification_1.sending_date)
            self.assertEqual(1, len(Notification.get_unsent()))

            uri_1 = uri_format.format(id=notification_1.id)
            rs = self.client.post(uri_1)
            self.assertEqual(rs.status_code, 200)
            self.assertEqual(rs.json["status"], "ok")
            self.assertEqual(0, len(Notification.get_unsent()))

            # Отмена отмененного не приведет к ошибке
            rs = self.client.post(uri_1)
            self.assertEqual(rs.status_code, 200)
            self.assertEqual(rs.json["status"], "ok")
            self.assertEqual(0, len(Notification.get_unsent()))

            notification_2 = Notification.add(
                kind=NotificationKindEnum.EMAIL,
                name="Title",
                text="Test\nТест",
                task_run=None,
            )
            self.assertTrue(notification_2.is_ready())
            self.assertIsNone(notification_2.canceling_date)
            self.assertIsNone(notification_2.sending_date)
            self.assertEqual(1, len(Notification.get_unsent()))

            notification_2.set_as_send()
            self.assertEqual(0, len(Notification.get_unsent()))

            # Отмена отправленного приведет к ошибке
            uri_2 = uri_format.format(id=notification_2.id)
            rs = self.client.post(uri_2)
            self.assertEqual(rs.status_code, 200)
            self.assertEqual(rs.json["status"], "error")

    def test_api_cron_get_next_dates(self):
        uri: str = "/api/cron/get-next-dates"

        with self.subTest(msg="ERROR"):
            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 400)
            self.assertEqual(rs.json["status"], "error")

            rs = self.client.get(uri, query_string=dict(cron="FOO BAR"))
            self.assertEqual(rs.status_code, 200)
            self.assertEqual(rs.json["status"], "error")

        with self.subTest(msg="Default"):
            now: datetime = datetime.now()

            for cron in ["* * * * *", "0 * * * *"]:
                rs = self.client.get(uri, query_string=dict(cron=cron))
                self.assertEqual(rs.status_code, 200)
                for obj in rs.json["result"]:
                    self.assertGreater(datetime.fromisoformat(obj["date"]), now)

        with self.subTest(msg="Define number"):
            now: datetime = datetime.now()
            number: int = 10

            for cron in ["* * * * *", "0 * * * *"]:
                rs = self.client.get(uri, query_string=dict(cron=cron, number=number))
                self.assertEqual(rs.status_code, 200)

                self.assertEqual(len(rs.json["result"]), number)

                for obj in rs.json["result"]:
                    self.assertGreater(datetime.fromisoformat(obj["date"]), now)
