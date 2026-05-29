#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import time
from datetime import datetime
from enum import Enum
from unittest import TestCase
from typing import Any, Callable

from playhouse.sqlite_ext import SqliteExtDatabase
from playhouse.shortcuts import model_to_dict

from run_tasks.db import (
    BaseModel,
    Task,
    TaskRun,
    Notification,
    TaskRunStatusEnum,
    TaskRunWorkStatusEnum,
    NotificationKindEnum,
    StopReasonEnum,
    TaskRunLog,
)

from run_tasks.app_web.app import limiter
from run_tasks.app_web.config import USERS, API_PAGE_LENGTH_DEFAULT
from run_tasks.app_web.main import app

# Минимальное время задержки между вызовами datetime.now(), чтобы даты не совпали
DATETIME_DELAY_SECS: float = 0.001


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


class TestAppWeb(TestBaseAppWeb):
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


class TestBaseAppApiWeb(TestBaseAppWeb):
    def assert_datatables_response(
        self,
        uri: str,
        records_total: int,
        to_dict: Callable[[Any], dict[str, Any]],
        params: dict[str, Any] | None = None,
        records_filtered: int | None = None,
        expected: list[Any] | None = None,
        draw: int = 1,
        check_only_id: bool = False,
    ) -> None:
        if not params:
            params = dict()

        rs = self.client.get(uri, query_string=params)
        self.assertEqual(200, rs.status_code)

        rs_data = rs.json
        self.assertEqual(draw, rs_data["draw"])
        self.assertEqual(records_total, rs_data["recordsTotal"])

        if records_filtered is None:
            records_filtered = rs_data["recordsTotal"]

        self.assertEqual(records_filtered, rs_data["recordsFiltered"])

        if expected is not None:

            def process_value(v: Any) -> Any:
                match v:
                    case dict():
                        return {k: process_value(val) for k, val in v.items()}
                    case list() | tuple():
                        return [process_value(item) for item in v]
                    case Enum():
                        return v.value
                    case datetime():
                        return v.isoformat()
                    case _:
                        return v

            expected_data: list[dict[str, Any]] = []
            for item in expected:
                data: dict[str, Any] = process_value(to_dict(item))
                expected_data.append(data)

            if length := int(params.get("length", API_PAGE_LENGTH_DEFAULT)):
                expected_data = expected_data[:length]

            if check_only_id:
                self.assertEqual(
                    [obj["id"] for obj in expected_data],
                    [obj["id"] for obj in rs_data["data"]],
                )
            else:
                self.assertEqual(expected_data, rs_data["data"])


class TestAppApiWeb(TestBaseAppWeb):
    def test_api_task_create(self) -> None:
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

    def test_api_task_get(self) -> None:
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

    def test_api_task_update(self) -> None:
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
                "name": "Foo Bar",
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

    def test_api_task_delete(self) -> None:
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

    def test_api_task_do_run(self) -> None:
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

    def test_api_task_run_get(self) -> None:
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
                return dict(id=d["id"], task_run=d["task"], seq=d["seq"])

            self.assertEqual(
                get_common_view(rs.json["result"][0]),
                get_common_view(run_1.to_dict()),
            )

    def test_api_task_run_get_last(self) -> None:
        uri_template: str = "/api/task/{task_id}/run/last"

        with self.subTest("405 - Method Not Allowed"):
            uri: str = uri_template.format(task_id=99999)

            rs = self.client.post(uri)
            self.assertEqual(rs.status_code, 405)
            self.assertEqual(rs.json["status"], "error")

        with self.subTest("[0 tasks, 0 runs] 404 - Not Found"):
            uri: str = uri_template.format(task_id=99999)

            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 404)
            self.assertEqual(rs.json["status"], "error")

        with self.subTest("[1 tasks, 0 runs] 404 - Not Found"):
            task_1 = Task.add(
                name="1",
                command="ping 127.0.0.1",
            )

            uri: str = uri_template.format(task_id=task_1.id)
            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 404)
            self.assertEqual(rs.json["status"], "error")

        with self.subTest("[1 tasks, 1 pending runs] 404 - Not Found"):
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
            run_1.set_status(TaskRunStatusEnum.RUNNING)

            uri: str = uri_template.format(task_id=task_2.id)

            rs = self.client.get(uri)
            self.assertEqual(rs.status_code, 200)

            def get_common_view(d: dict[str, Any]) -> dict[str, Any]:
                return dict(id=d["id"], task_run=d["task"], seq=d["seq"])

            self.assertEqual(
                get_common_view(rs.json["result"][0]),
                get_common_view(run_1.to_dict()),
            )

    def test_api_task_run_do_stop(self) -> None:
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

    def test_api_task_run_do_send_notifications(self) -> None:
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

    def test_api_notification_create(self) -> None:
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

    def test_api_notifications_get_number_of_unsent(self) -> None:
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

    def test_api_notifications_all_do_stop(self) -> None:
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

    def test_api_notification_do_stop(self) -> None:
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

    def test_api_cron_get_next_dates(self) -> None:
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


class TestAppApiWebTasks(TestBaseAppApiWeb):
    def setUp(self) -> None:
        super().setUp()

        self.uri: str = "/api/tasks"

    @staticmethod
    def _get_expected_json(
        task: Task, overrides: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Преобразует модель Task в ожидаемый API словарь"""

        base = {
            **model_to_dict(task, recurse=False),
            "number_of_runs": 0,
            "last_started_run_seq": None,
            "last_started_run_start_date": None,
            "next_scheduled_date": None,
            "last_work_status": TaskRunWorkStatusEnum.NONE.value,
        }
        if overrides:
            base.update(overrides)
        return base

    def _run_n_runs(self, task: Task, n_times: int) -> None:
        for _ in range(n_times):
            run = task.add_or_get_run()
            run.set_status(TaskRunStatusEnum.RUNNING)
            run.set_status(TaskRunStatusEnum.FINISHED)

    def assert_tasks(
        self,
        params: dict[str, Any] | None = None,
        records_filtered: int | None = None,
        expected: list[Task | tuple[Task, dict]] | None = None,
        draw: int = 1,
        check_only_id: bool = False,
    ) -> None:
        def _to_dict(obj: Task | tuple[Task, dict]) -> dict[str, Any]:
            if isinstance(obj, tuple):
                task, overrides = obj
                return self._get_expected_json(task, overrides)

            return self._get_expected_json(obj)

        self.assert_datatables_response(
            uri=self.uri,
            records_total=Task.select().count(),
            to_dict=_to_dict,
            params=params,
            records_filtered=records_filtered,
            expected=expected,
            draw=draw,
            check_only_id=check_only_id,
        )

    def test_empty(self) -> None:
        self.assert_tasks(expected=[])

    def test_draw_echo(self) -> None:
        self.assert_tasks(params={"draw": 999}, expected=[], draw=999)
        self.assert_tasks(params={"draw": "999"}, expected=[], draw=999)

    def test_errors(self) -> None:
        with self.subTest("Missing name for column index", code=400):
            rs = self.client.get(self.uri, query_string={"order[0][column]": 0})
            self.assertEqual(400, rs.status_code)

        with self.subTest("Sorting by field '...' is forbidden", code=403):
            rs = self.client.get(
                self.uri,
                query_string={"order[0][column]": 0, "order[0][name]": "MEGA_ID"},
            )
            self.assertEqual(403, rs.status_code)

    def test_main(self) -> None:
        tasks = []

        for i in range(5):
            t_tg = Task.add(
                name=f"tg_bot_{i}",
                command="python bot.py",
                description="ping",
                is_infinite=True,
            )
            t_web = Task.add(
                name=f"web_parser_{i}",
                command="uvicorn main:app",
                description="https://127.0.0.1",
                cron="@hourly",
            )
            t_win = Task.add(
                name=f"ping_srv_{i}",
                command=r"C:\Users\admin",
                description="bot",
                cron="0 */8 * * *",
            )
            t_token = Task.add(
                name=f"vk_tool_{i}",
                command="set TOKEN=123",
                description="t.me/link",
                cron="*/5 * * * *",
            )

            tasks.append(t_tg)
            tasks.append(t_web)
            tasks.append(t_win)
            tasks.append(t_token)

        with self.subTest("Пагинация по умолчанию"):
            self.assert_tasks(expected=tasks)

        with self.subTest("Все записи"):
            self.assert_tasks(expected=tasks, params=dict(length=999_999_999))

    def test_pagination(self) -> None:
        """Проверка базовой пагинации"""

        tasks = [
            Task.add(name=f"task_{i}", command="ping", cron=None) for i in range(15)
        ]

        with self.subTest("Первая страница"):
            self.assert_tasks(params={"start": 0, "length": 5}, expected=tasks[:5])

        with self.subTest("Вторая страница"):
            self.assert_tasks(params={"start": 5, "length": 5}, expected=tasks[5:10])

        with self.subTest("Пустой результат при запредельном смещении"):
            self.assert_tasks(
                params={"start": 999, "length": 5},
                expected=[],
            )

    def test_search_filtering(self) -> None:
        """Проверка поиска по полям: name, command, description, cron"""

        t_tg = Task.add(
            name="tg_bot",
            command="python bot.py",
            description="ping",
            is_infinite=True,
        )
        t_web = Task.add(
            name="web_parser",
            command="uvicorn main:app",
            description="https://127.0.0.1",
            cron="@hourly",
        )
        t_win = Task.add(
            name="ping_srv",
            command=r"C:\Users\admin",
            description="bot",
            cron="0 */8 * * *",
        )
        t_token = Task.add(
            name="vk_tool",
            command="set TOKEN=123",
            description="t.me/link",
            cron="*/5 * * * *",
        )

        search_cases: list[tuple[str, str, int, list[Task]]] = [
            ("Поиск по имени 'tg'", "tg", 1, [t_tg]),
            ("Поиск по команде 'uvicorn'", "uvicorn", 1, [t_web]),
            ("Поиск по пути 'C:/Users'", "Users", 1, [t_win]),
            ("Поиск по IP в описании", "127.0.0.1", 1, [t_web]),
            ("Поиск по ссылке в описании", "t.me", 1, [t_token]),
            ("Поиск по cron", "@hourly", 1, [t_web]),
            ("Слово 'bot' в разных полях", "bot", 2, [t_tg, t_win]),
        ]
        for msg, query, filtered, expected in search_cases:
            with self.subTest(msg):
                self.assert_tasks(
                    params={"search[value]": query},
                    records_filtered=filtered,
                    expected=expected,
                )

    def test_search_with_pagination(self) -> None:
        """Проверка совместной работы фильтрации и пагинации."""

        bot_tasks = [Task.add(name=f"bot_{i}", command="python") for i in range(5)]
        for i in range(10):
            Task.add(name=f"other_{i}", command="ping")

        # Общее кол-во: 15. Отфильтрованных (по слову 'bot'): 5
        with self.subTest("Первая страница поиска (3 элемента)"):
            params = {
                "search[value]": "bot",
                "start": 0,
                "length": 3,
                "order[0][name]": "name",
                "order[0][dir]": "asc",
            }
            # Ожидаем первые 3 из 5 найденных
            self.assert_tasks(params=params, records_filtered=5, expected=bot_tasks[:3])

        with self.subTest("Вторая страница поиска (оставшиеся 2 элемента)"):
            params = {
                "search[value]": "bot",
                "start": 3,
                "length": 3,
                "order[0][name]": "name",
                "order[0][dir]": "asc",
            }
            # Ожидаем последние 2 из 5 найденных
            self.assert_tasks(
                params=params, records_filtered=5, expected=bot_tasks[3:5]
            )

        with self.subTest("Поиск 'bot' с сортировкой DESC и пагинацией"):
            params = {
                "search[value]": "bot",
                "start": 0,
                "length": 2,
                "order[0][name]": "name",
                "order[0][dir]": "desc",
            }
            # Ожидаем bot_4, bot_3
            self.assert_tasks(
                params=params,
                records_filtered=5,
                expected=[bot_tasks[4], bot_tasks[3]],
            )

    def test_sorting(self) -> None:
        """Проверка сортировки"""

        task_1 = Task.add(name="Alpha", command="1", cron=None)
        task_2 = Task.add(name="Beta", command="2", cron="@hourly")
        task_3 = Task.add(name="Gamma", command="3", cron=None)

        self._run_n_runs(task_2, n_times=10)
        self._run_n_runs(task_1, n_times=5)

        with self.subTest("Сортировка по имени DESC"):
            self.assert_tasks(
                params={"order[0][name]": "name", "order[0][dir]": "desc"},
                expected=[task_3, task_2, task_1],
                check_only_id=True,
            )

        with self.subTest("Сортировка по cron (задачи с cron первыми)"):
            # Логика ASC ставит значения выше NULL
            self.assert_tasks(
                params={"order[0][name]": "cron", "order[0][dir]": "asc"},
                expected=[task_1, task_3, task_2],
                check_only_id=True,
            )

        with self.subTest("Сортировка db_number_of_runs по возрастанию"):
            self.assert_tasks(
                params={"order[0][name]": "db_number_of_runs", "order[0][dir]": "asc"},
                expected=[task_3, task_1, task_2],
                check_only_id=True,
            )

        with self.subTest("Сортировка db_number_of_runs по убыванию"):
            self.assert_tasks(
                params={"order[0][name]": "db_number_of_runs", "order[0][dir]": "desc"},
                expected=[task_2, task_1, task_3],
                check_only_id=True,
            )

    def test_search_with_sorting_and_pagination(self) -> None:
        # Задачи, которые подходят под фильтр 'bot'
        # Id и алфавитный порядок не совпадают
        task_bot_z = Task.add(name="z_bot", command="python")
        task_bot_a = Task.add(name="a_bot", command="python")
        task_bot_m = Task.add(name="m_bot", command="python")

        # Задачи (не содержат 'bot'), чтобы проверить recordsTotal
        for i in range(5):
            Task.add(name=f"other_{i}", command="ping")

        # Распределение количества запусков:
        # task_bot_m -> 15 запусков (самый посещаемый bot)
        # task_bot_z -> 10 запусков
        # task_bot_a -> 5 запусков  (самый редкий bot)
        self._run_n_runs(task_bot_m, n_times=15)
        self._run_n_runs(task_bot_z, n_times=10)
        self._run_n_runs(task_bot_a, n_times=5)

        # Итого в базе: 8 задач (recordsTotal = 8)
        # Подходят под фильтр 'bot': 3 задачи (recordsFiltered = 3)

        with self.subTest("Фильтр 'bot' + Сортировка по запускам DESC + Первая страница пагинации (2 элемента)"):
            # При сортировке db_number_of_runs DESC полный порядок отфильтрованных:
            # [task_bot_m (15), task_bot_z (10), task_bot_a (5)]
            # Берем length=2 -> ожидаем только первые две задачи
            params = {
                "search[value]": "bot",
                "order[0][name]": "db_number_of_runs",
                "order[0][dir]": "desc",
                "start": 0,
                "length": 2,
            }
            self.assert_tasks(
                params=params,
                records_filtered=3,
                expected=[task_bot_m, task_bot_z],
                check_only_id=True,
            )

        with self.subTest("Фильтр 'bot' + Сортировка по запускам DESC + Смещение на вторую страницу"):
            # Берем хвост отсортированного списка (индекс start=2)
            params = {
                "search[value]": "bot",
                "order[0][name]": "db_number_of_runs",
                "order[0][dir]": "desc",
                "start": 2,
                "length": 2,
            }
            self.assert_tasks(
                params=params,
                records_filtered=3,
                expected=[task_bot_a],
                check_only_id=True,
            )

        with self.subTest("Фильтр 'bot' + Сортировка по запускам ASC + Первая страница"):
            # При сортировке db_number_of_runs ASC полный порядок отфильтрованных:
            # [task_bot_a (5), task_bot_z (10), task_bot_m (15)]
            # Берем length=2 -> ожидаем только первые две задачи
            params = {
                "search[value]": "bot",
                "order[0][name]": "db_number_of_runs",
                "order[0][dir]": "asc",
                "start": 0,
                "length": 2,
            }
            self.assert_tasks(
                params=params,
                records_filtered=3,
                expected=[task_bot_a, task_bot_z],
                check_only_id=True,
            )

    def test_multi_column_sorting(self) -> None:
        """Проверка сортировки по нескольким колонкам одновременно"""

        t_a = Task.add(name="A", command="1", is_enabled=True, is_infinite=False)
        t_b = Task.add(name="B", command="2", is_enabled=True, is_infinite=True)

        params = {
            "order[0][name]": "is_enabled",
            "order[0][dir]": "desc",
            "order[1][name]": "is_infinite",
            "order[1][dir]": "desc",
        }
        self.assert_tasks(params=params, expected=[t_b, t_a])

    def test_task_with_execution_history(self) -> None:
        """Тест отображения данных о запусках"""

        task = Task.add(
            name="ping", command="ping 127.0.0.1", description="ping", cron="@hourly"
        )

        with self.subTest("Без запусков"):
            overrides = {
                "number_of_runs": 0,
                "last_started_run_seq": None,
                "last_work_status": TaskRunWorkStatusEnum.NONE.value,
            }
            self.assertEqual(TaskRunWorkStatusEnum.NONE, task.last_work_status)
            self.assert_tasks(expected=[(task, overrides)])

        run_1 = task.add_or_get_run()
        with self.subTest("Запуск #1 в ожидании"):
            overrides = {
                "number_of_runs": 0,
                "last_started_run_seq": None,
                "last_work_status": TaskRunWorkStatusEnum.NONE.value,
            }
            self.assertEqual(TaskRunWorkStatusEnum.NONE, task.last_work_status)
            self.assertEqual(TaskRunWorkStatusEnum.NONE, run_1.work_status)
            self.assert_tasks(expected=[(task, overrides)])

        with self.subTest("Запуск #1 выполняется"):
            run_1.set_status(TaskRunStatusEnum.RUNNING)
            overrides = {
                "number_of_runs": 1,
                "last_started_run_seq": 1,
                "last_work_status": TaskRunWorkStatusEnum.IN_PROCESSED.value,
                "last_started_run_start_date": run_1.start_date.isoformat(sep=" "),
            }
            self.assertEqual(TaskRunWorkStatusEnum.IN_PROCESSED, task.last_work_status)
            self.assertEqual(TaskRunWorkStatusEnum.IN_PROCESSED, run_1.work_status)
            self.assert_tasks(expected=[(task, overrides)])

        with self.subTest("Запуск #1 завершен"):
            run_1.process_return_code = 0
            run_1.set_status(TaskRunStatusEnum.FINISHED)
            overrides = {
                "number_of_runs": 1,
                "last_started_run_seq": 1,
                "last_work_status": TaskRunWorkStatusEnum.SUCCESSFUL.value,
                "last_started_run_start_date": run_1.start_date.isoformat(sep=" "),
            }
            self.assertEqual(TaskRunWorkStatusEnum.SUCCESSFUL, task.last_work_status)
            self.assertEqual(TaskRunWorkStatusEnum.SUCCESSFUL, run_1.work_status)
            self.assert_tasks(expected=[(task, overrides)])

        run_2 = task.add_or_get_run()
        with self.subTest("Запуск #2 в ожидании"):
            overrides = {
                "number_of_runs": 1,
                "last_started_run_seq": 1,
                "last_work_status": TaskRunWorkStatusEnum.SUCCESSFUL.value,
                "last_started_run_start_date": run_1.start_date.isoformat(sep=" "),
            }
            self.assertEqual(TaskRunWorkStatusEnum.SUCCESSFUL, task.last_work_status)
            self.assertEqual(TaskRunWorkStatusEnum.NONE, run_2.work_status)
            self.assert_tasks(expected=[(task, overrides)])

        with self.subTest("Запуск #2 выполняется"):
            run_2.set_status(TaskRunStatusEnum.RUNNING)
            overrides = {
                "number_of_runs": 2,
                "last_started_run_seq": 2,
                "last_work_status": TaskRunWorkStatusEnum.IN_PROCESSED.value,
                "last_started_run_start_date": run_2.start_date.isoformat(sep=" "),
            }
            self.assertEqual(TaskRunWorkStatusEnum.IN_PROCESSED, task.last_work_status)
            self.assertEqual(TaskRunWorkStatusEnum.IN_PROCESSED, run_2.work_status)
            self.assert_tasks(expected=[(task, overrides)])

        with self.subTest("Запуск #2 завершен не успешно"):
            run_2.process_return_code = 999
            run_2.set_status(TaskRunStatusEnum.FINISHED)
            overrides = {
                "number_of_runs": 2,
                "last_started_run_seq": 2,
                "last_work_status": TaskRunWorkStatusEnum.FAILED.value,
                "last_started_run_start_date": run_2.start_date.isoformat(sep=" "),
            }
            self.assertEqual(TaskRunWorkStatusEnum.FAILED, task.last_work_status)
            self.assertEqual(TaskRunWorkStatusEnum.FAILED, run_2.work_status)
            self.assert_tasks(expected=[(task, overrides)])

        run_3 = task.add_or_get_run()
        with self.subTest("Запуск #3 в ожидании"):
            overrides = {
                "number_of_runs": 2,
                "last_started_run_seq": 2,
                "last_work_status": TaskRunWorkStatusEnum.FAILED.value,
                "last_started_run_start_date": run_2.start_date.isoformat(sep=" "),
            }
            self.assertEqual(TaskRunWorkStatusEnum.FAILED, task.last_work_status)
            self.assertEqual(TaskRunWorkStatusEnum.NONE, run_3.work_status)
            self.assert_tasks(expected=[(task, overrides)])

        with self.subTest("Запуск #3 выполняется"):
            run_3.set_status(TaskRunStatusEnum.RUNNING)
            overrides = {
                "number_of_runs": 3,
                "last_started_run_seq": 3,
                "last_work_status": TaskRunWorkStatusEnum.IN_PROCESSED.value,
                "last_started_run_start_date": run_3.start_date.isoformat(sep=" "),
            }
            self.assertEqual(TaskRunWorkStatusEnum.IN_PROCESSED, task.last_work_status)
            self.assertEqual(TaskRunWorkStatusEnum.IN_PROCESSED, run_3.work_status)
            self.assert_tasks(expected=[(task, overrides)])

        with self.subTest("Запуск #3 завершен не успешно"):
            run_3.process_return_code = 0
            run_3.set_status(TaskRunStatusEnum.ERROR)
            overrides = {
                "number_of_runs": 3,
                "last_started_run_seq": 3,
                "last_work_status": TaskRunWorkStatusEnum.FAILED.value,
                "last_started_run_start_date": run_3.start_date.isoformat(sep=" "),
            }
            self.assertEqual(TaskRunWorkStatusEnum.FAILED, task.last_work_status)
            self.assertEqual(TaskRunWorkStatusEnum.FAILED, run_3.work_status)
            self.assert_tasks(expected=[(task, overrides)])


class TestBaseAppApiWebTask(TestBaseAppApiWeb):
    def setUp(self) -> None:
        super().setUp()

        self.task = Task.add(
            name="ping",
            command="ping 127.0.0.1",
            description="description ping",
            cron="* * * * *",
        )

    def _add_logs(self, run: TaskRun, n: int) -> list[TaskRunLog]:
        items: list[TaskRunLog] = []
        for i in range(n):
            items.append(run.add_log_out(f"out={i}"))
            items.append(run.add_log_err(f"err={i}"))
        return items

    def assert_task_logs_common(
        self,
        uri: str,
        records_total: int,
        params: dict[str, Any] | None = None,
        records_filtered: int | None = None,
        expected: list[TaskRunLog] | None = None,
        draw: int = 1,
    ) -> None:
        self.assert_datatables_response(
            uri=uri,
            records_total=records_total,
            to_dict=lambda obj: obj.to_dict(),
            params=params,
            records_filtered=records_filtered,
            expected=expected,
            draw=draw,
        )


class TestAppApiWebRunsTask(TestBaseAppApiWebTask):
    def setUp(self) -> None:
        super().setUp()

        self.uri: str = f"/api/task/{self.task.id}/runs"

    def _create_runs(self, n: int, status: TaskRunStatusEnum) -> list[TaskRun]:
        runs = []
        for _ in range(n):
            run = self.task.add_or_get_run()
            run.set_status(TaskRunStatusEnum.RUNNING)
            run.set_status(status)

            runs.append(run)

        return runs

    def assert_task_runs(
        self,
        params: dict[str, Any] | None = None,
        records_filtered: int | None = None,
        expected: list[TaskRun] | None = None,
        draw: int = 1,
    ) -> None:
        self.assert_datatables_response(
            uri=self.uri,
            records_total=TaskRun.select().count(),
            to_dict=lambda obj: obj.to_dict(),
            params=params,
            records_filtered=records_filtered,
            expected=expected,
            draw=draw,
        )

    def test_empty(self) -> None:
        self.assert_task_runs(expected=[])

    def test_draw_echo(self) -> None:
        self.assert_task_runs(params={"draw": 999}, expected=[], draw=999)
        self.assert_task_runs(params={"draw": "999"}, expected=[], draw=999)

    def test_errors(self) -> None:
        with self.subTest("Missing name for column index", code=400):
            rs = self.client.get(self.uri, query_string={"order[0][column]": 0})
            self.assertEqual(400, rs.status_code)

        with self.subTest("Sorting by field '...' is forbidden", code=403):
            rs = self.client.get(
                self.uri,
                query_string={"order[0][column]": 0, "order[0][name]": "MEGA_ID"},
            )
            self.assertEqual(403, rs.status_code)

        with self.subTest("404 Not Found", code=404):
            rs = self.client.get("/api/task/404/runs")
            self.assertEqual(404, rs.status_code)
            self.assertEqual("error", rs.json["status"])

    def test_main(self) -> None:
        runs = self._create_runs(n=20, status=TaskRunStatusEnum.FINISHED)

        with self.subTest("Пагинация по умолчанию"):
            self.assert_task_runs(expected=runs)

        with self.subTest("Все записи"):
            self.assert_task_runs(
                expected=runs,
                params=dict(length=999_999_999),
            )

    def test_pagination(self) -> None:
        """Проверка базовой пагинации"""

        runs = self._create_runs(n=10, status=TaskRunStatusEnum.FINISHED)

        with self.subTest("Первая страница (start=0, length=5)"):
            self.assert_task_runs(
                params={"start": 0, "length": 5},
                expected=runs[:5],
            )

        with self.subTest("Вторая страница (start=5, length=5)"):
            self.assert_task_runs(
                params={"start": 5, "length": 5},
                expected=runs[5:10],
            )

    def test_search_filtering(self) -> None:
        """Проверка поиска по полям: command, status, stop_reason, process_id"""

        # Создаем специфичные запуски
        r1 = self.task.add_or_get_run()
        r1.command = "python script.py"
        r1.set_status(TaskRunStatusEnum.RUNNING)
        r1.process_id = 1234
        r1.set_status(TaskRunStatusEnum.FINISHED)
        r1.save()

        r2 = self.task.add_or_get_run()
        r2.command = "bash script.sh"
        r2.set_status(TaskRunStatusEnum.RUNNING)
        r2.process_id = 5678
        r2.set_stop(StopReasonEnum.SERVER_API)
        r2.save()

        with self.subTest("Поиск по command"):
            self.assert_task_runs(
                params={"search[value]": "python"},
                records_filtered=1,
                expected=[r1],
            )

        with self.subTest("Поиск по status"):
            self.assert_task_runs(
                params={"search[value]": TaskRunStatusEnum.FINISHED.value},
                records_filtered=1,
                expected=[r1],
            )

        with self.subTest("Поиск по stop_reason"):
            self.assert_task_runs(
                params={"search[value]": StopReasonEnum.SERVER_API.value},
                records_filtered=1,
                expected=[r2],
            )

        with self.subTest("Поиск по process_id"):
            self.assert_task_runs(
                params={"search[value]": "5678"},
                records_filtered=1,
                expected=[r2],
            )

    def test_search_with_pagination(self) -> None:
        """Проверка совместной работы фильтрации и пагинации."""

        # Создаем 5 'ошибочных' запусков и 5 'успешных'
        error_runs = self._create_runs(n=5, status=TaskRunStatusEnum.ERROR)
        self._create_runs(n=5, status=TaskRunStatusEnum.FINISHED)

        params = {
            "search[value]": TaskRunStatusEnum.ERROR.value,
            "start": 0,
            "length": 3,
            "order[0][column]": 0,
            "order[0][name]": "id",
            "order[0][dir]": "asc",
        }
        # Ожидаем 5 найденных, но в выдаче только первые 3
        self.assert_task_runs(
            params=params, records_filtered=5, expected=error_runs[:3]
        )

    def test_sorting(self) -> None:
        """Проверка сортировки"""

        runs = self._create_runs(n=10, status=TaskRunStatusEnum.FINISHED)

        with self.subTest("Sort by seq ASC"):
            params = {
                "order[0][column]": 0,
                "order[0][name]": "seq",
                "order[0][dir]": "asc",
            }
            self.assert_task_runs(params=params, expected=runs)

        with self.subTest("Sort by seq DESC"):
            params = {
                "order[0][column]": 0,
                "order[0][name]": "seq",
                "order[0][dir]": "desc",
            }
            self.assert_task_runs(params=params, expected=runs[::-1])

    def test_multi_column_sorting(self) -> None:
        """Проверка сортировки по нескольким колонкам одновременно"""

        r1, r2 = self._create_runs(n=2, status=TaskRunStatusEnum.FINISHED)

        params = {
            "order[0][column]": 0,
            "order[0][name]": "status",
            "order[0][dir]": "asc",
            "order[1][column]": 1,
            "order[1][name]": "seq",
            "order[1][dir]": "desc",
        }
        # Сначала по статусу (одинаковые), потом по seq (desc)
        self.assert_task_runs(params=params, expected=[r2, r1])


class TestAppApiWebLogsTask(TestBaseAppApiWebTask):
    def setUp(self) -> None:
        super().setUp()

        self.uri: str = f"/api/task/{self.task.id}/logs"

    def _create_runs_with_logs(self, n_runs: int, n_logs: int) -> list[TaskRunLog]:
        logs = []
        for _ in range(n_runs):
            run = self.task.add_or_get_run()
            run.set_status(TaskRunStatusEnum.RUNNING)
            run.set_status(TaskRunStatusEnum.FINISHED)

            for i in range(n_logs):
                logs.append(run.add_log_out(f"out={i}"))
                logs.append(run.add_log_err(f"err={i}"))

        return logs

    def assert_task_logs(
        self,
        params: dict[str, Any] | None = None,
        records_filtered: int | None = None,
        expected: list[TaskRunLog] | None = None,
        draw: int = 1,
    ) -> None:
        self.assert_task_logs_common(
            uri=self.uri,
            records_total=TaskRunLog.select().count(),
            params=params,
            records_filtered=records_filtered,
            expected=expected,
            draw=draw,
        )

    def test_empty(self) -> None:
        self.assert_task_logs(expected=[])

    def test_draw_echo(self) -> None:
        self.assert_task_logs(params={"draw": 999}, expected=[], draw=999)
        self.assert_task_logs(params={"draw": "999"}, expected=[], draw=999)

    def test_errors(self) -> None:
        with self.subTest("Missing name for column index", code=400):
            rs = self.client.get(self.uri, query_string={"order[0][column]": 0})
            self.assertEqual(400, rs.status_code)

        with self.subTest("Sorting by field '...' is forbidden", code=403):
            rs = self.client.get(
                self.uri,
                query_string={"order[0][column]": 0, "order[0][name]": "MEGA_ID"},
            )
            self.assertEqual(403, rs.status_code)

        with self.subTest("404 Not Found", code=404):
            rs = self.client.get("/api/task/404/logs")
            self.assertEqual(404, rs.status_code)
            self.assertEqual("error", rs.json["status"])

    def test_main(self) -> None:
        logs = self._create_runs_with_logs(n_runs=5, n_logs=3)

        with self.subTest("Пагинация по умолчанию"):
            self.assert_task_logs(expected=logs)

        with self.subTest("Все записи"):
            self.assert_task_logs(expected=logs, params=dict(length=999_999_999))

    def test_pagination(self) -> None:
        """Проверка базовой пагинации"""

        # Создаст 10 логов (5 out + 5 err)
        logs = self._create_runs_with_logs(n_runs=1, n_logs=5)

        with self.subTest("Первая страница (length=3)"):
            self.assert_task_logs(params={"start": 0, "length": 3}, expected=logs[:3])

        with self.subTest("Смещение на вторую страницу"):
            self.assert_task_logs(params={"start": 3, "length": 3}, expected=logs[3:6])

    def test_search_filtering(self) -> None:
        """Проверка поиска по полям: text, kind"""

        run = self.task.add_or_get_run()
        log_out_1 = run.add_log_out("system status ok")
        log_out_2 = run.add_log_out("api status ok")
        log_err_1 = run.add_log_err("critical database error")

        with self.subTest("Поиск по тексту 'status ok'"):
            self.assert_task_logs(
                params={"search[value]": "status ok"},
                records_filtered=2,
                expected=[log_out_1, log_out_2],
            )

        with self.subTest("Поиск по тексту 'critical'"):
            self.assert_task_logs(
                params={"search[value]": "critical"},
                records_filtered=1,
                expected=[log_err_1],
            )

        with self.subTest("Поиск по типу потока 'stderr'"):
            # Предполагается, что в БД kind хранится как 'err' или 'stderr'
            self.assert_task_logs(
                params={"search[value]": "err"},
                records_filtered=1,
                expected=[log_err_1],
            )

    def test_search_with_pagination(self) -> None:
        """Проверка совместной работы фильтрации и пагинации."""

        run = self.task.add_or_get_run()
        # Создаем 10 записей с общим словом 'ping'
        ping_logs = [run.add_log_out(f"ping response {i}") for i in range(10)]
        # И одну лишнюю
        run.add_log_out("other data")

        params = {
            "search[value]": "ping",
            "start": 0,
            "length": 5,
            "order[0][column]": 0,
            "order[0][name]": "id",
            "order[0][dir]": "asc",
        }

        # Всего 11, отфильтровано 10, на странице 5
        self.assert_task_logs(
            params=params, records_filtered=10, expected=ping_logs[:5]
        )

    def test_sorting(self) -> None:
        """Проверка сортировки по полям id, task_run, text, kind, date"""

        run_1 = self.task.add_or_get_run()
        run_2 = self.task.add_or_get_run()

        l1 = run_1.add_log_out("AAA")
        time.sleep(DATETIME_DELAY_SECS)
        l2 = run_2.add_log_err("BBB")

        sort_cases: list[tuple[str, str, str, list[TaskRunLog]]] = [
            ("По ID DESC", "id", "desc", [l2, l1]),
            ("По тексту ASC", "text", "asc", [l1, l2]),
            (
                # NOTE: В сортировке по тексту: out -> err
                "По типу (kind) DESC",
                "kind",
                "desc",
                [l1, l2],
            ),
            ("По дате DESC", "date", "desc", [l2, l1]),
            ("По ID запуска DESC", "task_run", "desc", [l2, l1]),
        ]

        for msg, field, direction, expected_list in sort_cases:
            with self.subTest(msg):
                self.assert_task_logs(
                    params={
                        "order[0][column]": 0,
                        "order[0][name]": field,
                        "order[0][dir]": direction,
                    },
                    expected=expected_list,
                )

    def test_multi_column_sorting(self) -> None:
        """Проверка сортировки по нескольким колонкам одновременно (text и kind)"""

        run = self.task.add_or_get_run()

        # Одинаковый текст, разные типы
        l1 = run.add_log_out("same_text")
        l2 = run.add_log_err("same_text")

        # Разный текст
        l3 = run.add_log_out("another_text")

        params = {
            "order[0][column]": 0,
            "order[0][name]": "text",
            "order[0][dir]": "asc",
            "order[1][column]": 1,
            "order[1][name]": "kind",
            "order[1][dir]": "desc",
        }

        # Ожидаемый порядок:
        # 1. 'another_text' (по алфавиту текста первый)
        # 2. 'same_text' (одинаковые, поэтому по типу DESC: out -> err)
        self.assert_task_logs(params=params, expected=[l3, l1, l2])


class TestAppApiWebRunLogsTask(TestBaseAppApiWebTask):
    def setUp(self) -> None:
        super().setUp()

        self.run = self.task.add_or_get_run()
        self.uri: str = f"/api/task/{self.task.id}/run/{self.run.seq}/logs"

    def assert_task_logs(
        self,
        params: dict[str, Any] | None = None,
        records_filtered: int | None = None,
        expected: list[TaskRunLog] | None = None,
        draw: int = 1,
    ) -> None:
        self.assert_task_logs_common(
            uri=self.uri,
            records_total=self.run.logs.count(),
            params=params,
            records_filtered=records_filtered,
            expected=expected,
            draw=draw,
        )

    def test_empty(self) -> None:
        self.assert_task_logs(expected=[])

    def test_draw_echo(self) -> None:
        self.assert_task_logs(params={"draw": 999}, expected=[], draw=999)
        self.assert_task_logs(params={"draw": "999"}, expected=[], draw=999)

    def test_errors(self) -> None:
        with self.subTest("Missing name for column index", code=400):
            rs = self.client.get(self.uri, query_string={"order[0][column]": 0})
            self.assertEqual(400, rs.status_code)

        with self.subTest("Sorting by field '...' is forbidden", code=403):
            rs = self.client.get(
                self.uri,
                query_string={"order[0][column]": 0, "order[0][name]": "MEGA_ID"},
            )
            self.assertEqual(403, rs.status_code)

        with self.subTest("Task: 404 Not Found", code=404):
            rs = self.client.get("/api/task/404/run/404/logs")
            self.assertEqual(404, rs.status_code)
            self.assertEqual("error", rs.json["status"])

        with self.subTest("TaskRun: 404 Not Found", code=404):
            rs = self.client.get(f"/api/task/{self.task.id}/run/404/logs")
            self.assertEqual(404, rs.status_code)
            self.assertEqual("error", rs.json["status"])

    def test_main(self) -> None:
        logs = self._add_logs(self.run, n=10)
        self.assertEqual(20, len(logs))

        with self.subTest("Пагинация по умолчанию"):
            self.assert_task_logs(expected=logs)

        with self.subTest("Все записи"):
            self.assert_task_logs(expected=logs, params=dict(length=999_999_999))

    def test_pagination(self) -> None:
        """Проверка базовой пагинации"""

        logs = self._add_logs(self.run, n=10)
        self.assertEqual(20, len(logs))

        with self.subTest("Первая страница (length=3)"):
            self.assert_task_logs(params={"start": 0, "length": 3}, expected=logs[:3])

        with self.subTest("Смещение на вторую страницу"):
            self.assert_task_logs(params={"start": 3, "length": 3}, expected=logs[3:6])

    def test_search_filtering(self) -> None:
        """Проверка поиска по полям: text, kind"""

        log_out_1 = self.run.add_log_out("system status ok")
        log_out_2 = self.run.add_log_out("api status ok")
        log_err = self.run.add_log_err("critical database error")

        with self.subTest("Поиск по тексту 'status ok'"):
            self.assert_task_logs(
                params={"search[value]": "status ok"},
                records_filtered=2,
                expected=[log_out_1, log_out_2],
            )

        with self.subTest("Поиск по тексту 'critical'"):
            self.assert_task_logs(
                params={"search[value]": "critical"},
                records_filtered=1,
                expected=[log_err],
            )

        with self.subTest("Поиск по типу потока 'stderr'"):
            # Предполагается, что в БД kind хранится как 'err' или 'stderr'
            self.assert_task_logs(
                params={"search[value]": "err"}, records_filtered=1, expected=[log_err]
            )

    def test_search_with_pagination(self) -> None:
        """Проверка совместной работы фильтрации и пагинации."""

        # Создаем 10 записей с общим словом 'ping'
        ping_logs = [self.run.add_log_out(f"ping response {i}") for i in range(10)]
        # И одну лишнюю
        self.run.add_log_out("other data")

        params = {
            "search[value]": "ping",
            "start": 0,
            "length": 5,
            "order[0][column]": 0,
            "order[0][name]": "id",
            "order[0][dir]": "asc",
        }

        # Всего 11, отфильтровано 10, на странице 5
        self.assert_task_logs(
            params=params, records_filtered=10, expected=ping_logs[:5]
        )

    def test_sorting(self) -> None:
        """Проверка сортировки по полям id, task_run, text, kind, date"""

        l1 = self.run.add_log_out("AAA")
        time.sleep(DATETIME_DELAY_SECS)
        l2 = self.run.add_log_err("BBB")

        sort_cases: list[tuple[str, str, str, list[TaskRunLog]]] = [
            ("По ID DESC", "id", "desc", [l2, l1]),
            ("По тексту ASC", "text", "asc", [l1, l2]),
            (
                "По типу (kind) DESC",
                "kind",
                "desc",
                [l1, l2],
            ),  # NOTE: В сортировке по тексту: out -> err
            ("По дате DESC", "date", "desc", [l2, l1]),
        ]

        for msg, field, direction, expected_list in sort_cases:
            with self.subTest(msg):
                self.assert_task_logs(
                    params={
                        "order[0][column]": 0,
                        "order[0][name]": field,
                        "order[0][dir]": direction,
                    },
                    expected=expected_list,
                )

    def test_multi_column_sorting(self) -> None:
        """Проверка сортировки по нескольким колонкам одновременно (text и kind)"""

        # Одинаковый текст, разные типы
        l1 = self.run.add_log_out("same_text")
        l2 = self.run.add_log_err("same_text")

        # Разный текст
        l3 = self.run.add_log_out("another_text")

        params = {
            "order[0][column]": 0,
            "order[0][name]": "text",
            "order[0][dir]": "asc",
            "order[1][column]": 1,
            "order[1][name]": "kind",
            "order[1][dir]": "desc",
        }

        # Ожидаемый порядок:
        # 1. 'another_text' (по алфавиту текста первый)
        # 2. 'same_text' (одинаковые, поэтому по типу DESC: out -> err)
        self.assert_task_logs(params=params, expected=[l3, l1, l2])


class TestAppApiWebTaskRunLastLogs(TestBaseAppApiWebTask):
    def setUp(self) -> None:
        super().setUp()

        self.uri: str = f"/api/task/{self.task.id}/run/last/logs"

    def assert_task_logs(
        self,
        params: dict[str, Any] | None = None,
        records_filtered: int | None = None,
        expected: list[TaskRunLog] | None = None,
        draw: int = 1,
    ) -> None:
        run: TaskRun | None = self.task.get_last_started_run()

        self.assert_task_logs_common(
            uri=self.uri,
            records_total=run.logs.count() if run else 0,
            params=params,
            records_filtered=records_filtered,
            expected=expected,
            draw=draw,
        )

    def test_empty(self) -> None:
        with self.subTest("No runs"):
            self.assert_task_logs(expected=[])

        run = self.task.add_or_get_run()
        with self.subTest("Run1-PENDING (0 logs)"):
            self.assert_task_logs(expected=[])

        run1_logs: list[TaskRunLog] = self._add_logs(run, n=10)
        self.assertEqual(20, len(run1_logs))

        with self.subTest("Run1-PENDING (10 logs)"):
            self.assert_task_logs(
                expected=[],
            )

    def test_draw_echo(self) -> None:
        self.assert_task_logs(params={"draw": 999}, expected=[], draw=999)
        self.assert_task_logs(params={"draw": "999"}, expected=[], draw=999)

    def test_errors(self) -> None:
        with self.subTest("Missing name for column index", code=400):
            rs = self.client.get(self.uri, query_string={"order[0][column]": 0})
            self.assertEqual(400, rs.status_code)

        with self.subTest("Sorting by field '...' is forbidden", code=403):
            rs = self.client.get(
                self.uri,
                query_string={"order[0][column]": 0, "order[0][name]": "MEGA_ID"},
            )
            self.assertEqual(403, rs.status_code)

        with self.subTest("Task: 404 Not Found", code=404):
            rs = self.client.get("/api/task/404/run/last/logs")
            self.assertEqual(404, rs.status_code)
            self.assertEqual("error", rs.json["status"])

    def test_main(self) -> None:
        run = self.task.add_or_get_run()
        run.set_status(TaskRunStatusEnum.RUNNING)

        logs = self._add_logs(run, n=10)
        self.assertEqual(20, len(logs))

        with self.subTest("Пагинация по умолчанию"):
            self.assert_task_logs(expected=logs)

        with self.subTest("Все записи"):
            self.assert_task_logs(
                expected=logs,
                params=dict(length=999_999_999),
            )

    def test_status(self) -> None:
        run_1 = self.task.add_or_get_run()

        with self.subTest("Run1-PENDING (0 logs)"):
            self.assert_task_logs(expected=[])

        run1_logs: list[TaskRunLog] = self._add_logs(run_1, n=10)
        self.assertEqual(20, len(run1_logs))

        with self.subTest("Run1-PENDING (10 logs)"):
            self.assert_task_logs(expected=[])

        with self.subTest("Run1-RUNNING (10 logs)"):
            run_1.set_status(TaskRunStatusEnum.RUNNING)
            self.assert_task_logs(expected=run1_logs)

        with self.subTest("Run1-FINISHED (10 logs)"):
            run_1.set_status(TaskRunStatusEnum.FINISHED)
            self.assert_task_logs(expected=run1_logs)

        run_2 = self.task.add_or_get_run()

        with self.subTest("Run1-FINISHED (return -> 10 logs), Run2-PENDING (0 logs)"):
            self.assert_task_logs(expected=run1_logs)

        run2_logs: list[TaskRunLog] = self._add_logs(run_2, n=10)
        self.assertEqual(20, len(run2_logs))

        with self.subTest("Run1-FINISHED (return -> 10 logs), Run2-PENDING (10 logs)"):
            self.assert_task_logs(expected=run1_logs)

        with self.subTest("Run2-RUNNING (10 logs)"):
            run_2.set_status(TaskRunStatusEnum.RUNNING)
            self.assert_task_logs(expected=run2_logs)

        with self.subTest("Run2-FINISHED (10 logs)"):
            run_2.set_status(TaskRunStatusEnum.FINISHED)
            self.assert_task_logs(expected=run2_logs)


class TestAppApiWebNotifications(TestBaseAppApiWeb):
    def setUp(self) -> None:
        super().setUp()

        self.uri: str = "/api/notifications"

    def assert_notifications(
        self,
        params: dict[str, Any] | None = None,
        records_filtered: int | None = None,
        expected: list[Notification] | None = None,
        draw: int = 1,
        check_only_id: bool = False,
    ) -> None:
        def to_dict(obj: Notification) -> dict[str, Any]:
            data: dict[str, Any] = obj.to_dict()

            # Добавление task_run как объект, а не идентификатор
            if obj.task_run:
                data["task_run"] = obj.task_run.to_dict()

            return data

        self.assert_datatables_response(
            uri=self.uri,
            records_total=Notification.select().count(),
            to_dict=to_dict,
            params=params,
            records_filtered=records_filtered,
            expected=expected,
            draw=draw,
            check_only_id=check_only_id,
        )

    def _add_notifications(self, run: TaskRun | None, n: int) -> list[Notification]:
        items: list[Notification] = []
        for i in range(n):
            items.append(
                Notification.add(
                    task_run=run,
                    name=f"[email] {i}",
                    text=f"email={i}",
                    kind=NotificationKindEnum.EMAIL,
                )
            )
            items.append(
                Notification.add(
                    task_run=run,
                    name=f"[tg] {i}",
                    text=f"tg={i}",
                    kind=NotificationKindEnum.TELEGRAM,
                )
            )
        return items

    def test_empty(self) -> None:
        self.assert_notifications(expected=[])

    def test_draw_echo(self) -> None:
        self.assert_notifications(params={"draw": 999}, expected=[], draw=999)
        self.assert_notifications(params={"draw": "999"}, expected=[], draw=999)

    def test_errors(self) -> None:
        with self.subTest("Missing name for column index", code=400):
            rs = self.client.get(self.uri, query_string={"order[0][column]": 0})
            self.assertEqual(400, rs.status_code)

        with self.subTest("Sorting by field '...' is forbidden", code=403):
            rs = self.client.get(
                self.uri,
                query_string={"order[0][column]": 0, "order[0][name]": "MEGA_ID"},
            )
            self.assertEqual(403, rs.status_code)

    def test_main(self) -> None:
        run = Task.add(name="*", command="*").add_or_get_run()

        notifications: list[Notification] = []
        notifications += self._add_notifications(run=None, n=10)
        notifications += self._add_notifications(run, n=10)

        self.assertEqual(40, len(notifications))

        with self.subTest("Пагинация по умолчанию"):
            self.assert_notifications(expected=notifications)

        with self.subTest("Все записи"):
            self.assert_notifications(
                expected=notifications,
                params=dict(length=999_999_999),
            )

    def test_pagination(self) -> None:
        """Проверка базовой пагинации"""

        for start in [0, 10, 999]:
            with self.subTest("Пагинация в пустой таблице", start=start):
                self.assert_notifications(
                    params={"start": start},
                    expected=[],
                )

        with self.subTest("Пагинация в пустой таблице", length=0):
            self.assert_notifications(
                params={"length": 0},
                expected=[],
            )

        # 6 уведомлений (3 email + 3 tg)
        items = self._add_notifications(run=None, n=3)

        with self.subTest("Пагинация вернет пустой список", start=999):
            self.assert_notifications(
                params={"start": 999},
                expected=[],
            )

        with self.subTest("Пагинация вернет пустой список", length=0):
            self.assert_notifications(
                params={"length": 0},
                expected=[],
            )

        with self.subTest("Первая страница (length=4)"):
            self.assert_notifications(
                params={"start": 0, "length": 4}, expected=items[:4]
            )

        with self.subTest("Вторая страница (start=4)"):
            self.assert_notifications(
                params={"start": 4, "length": 4}, expected=items[4:6]
            )

    def test_search_filtering(self) -> None:
        """Проверка поиска по полям: name, text, kind"""

        with self.subTest("Поиск в пустой таблице"):
            self.assert_notifications(
                params={"search[value]": "Urgent"},
                expected=[],
            )

        run = Task.add(name="test", command="*").add_or_get_run()

        n_email = Notification.add(
            task_run=run,
            name="Urgent report",
            text="Database connection failed",
            kind=NotificationKindEnum.EMAIL,
        )
        n_tg = Notification.add(
            task_run=run,
            name="Daily stats",
            text="All tasks finished successfully",
            kind=NotificationKindEnum.TELEGRAM,
        )

        with self.subTest("Поиск вернет пустой список"):
            self.assert_notifications(
                params={"search[value]": "404! 404!"},
                records_filtered=0,
                expected=[],
            )

        with self.subTest("Поиск по полю name ('Urgent')"):
            self.assert_notifications(
                params={"search[value]": "Urgent"},
                records_filtered=1,
                expected=[n_email],
            )

        with self.subTest("Поиск по тексту в поле text ('successfully')"):
            self.assert_notifications(
                params={"search[value]": "successfully"},
                records_filtered=1,
                expected=[n_tg],
            )

        with self.subTest("Поиск по типу уведомления в поле kind"):
            self.assert_notifications(
                params={"search[value]": NotificationKindEnum.TELEGRAM.value},
                records_filtered=1,
                expected=[n_tg],
            )

    def test_search_with_pagination(self) -> None:
        """Проверка совместной работы фильтрации и пагинации."""

        for start in [0, 10, 999]:
            with self.subTest("Пагинация в пустой таблице", start=start):
                self.assert_notifications(
                    params={"start": start},
                    expected=[],
                )

        with self.subTest("Пагинация в пустой таблице", length=0):
            self.assert_notifications(
                params={"length": 0},
                expected=[],
            )

        task = Task.add(name="SortTask", command="*")
        run_1 = task.add_or_get_run()

        # 10 уведомлений со словом 'alert' в тексте
        alert_items = []
        for i in range(5):
            alert_items.append(
                Notification.add(
                    task_run=run_1,
                    name="N",
                    text=f"alert test {i}",
                    kind=NotificationKindEnum.EMAIL,
                )
            )
            alert_items.append(
                Notification.add(
                    task_run=None,
                    name="N",
                    text=f"alert message {i}",
                    kind=NotificationKindEnum.TELEGRAM,
                )
            )

        # И одно лишнее, которое не должно попасть под фильтр
        Notification.add(
            task_run=run_1, name="N", text="normal log", kind=NotificationKindEnum.EMAIL
        )

        params = {
            "search[value]": "alert",  # records_filtered=10
            "start": 0,
            "length": 4,
            "order[0][column]": 0,
            "order[0][name]": "id",
            "order[0][dir]": "asc",
        }

        with self.subTest("Пагинация вернет пустой список", start=999):
            self.assert_notifications(
                params=params | {"start": 999},
                records_filtered=10,
                expected=[],
            )

        with self.subTest("Пагинация вернет пустой список", length=0):
            self.assert_notifications(
                params=params | {"length": 0},
                records_filtered=10,
                expected=[],
            )

        # Всего в базе 11 записей, фильтр отбирает 10, пагинация выводит первые 4
        with self.subTest("Пагинация вернет первую страницу с 4 элементами"):
            self.assert_notifications(
                params=params, records_filtered=10, expected=alert_items[:4]
            )

    def test_sorting(self) -> None:
        """Проверка сортировки по разрешенным полям, включая поля связанной таблицы TaskRun"""

        task = Task.add(name="SortTask", command="*")

        run_1 = task.add_or_get_run()
        run_1.set_status(TaskRunStatusEnum.RUNNING)
        run_1.set_status(TaskRunStatusEnum.FINISHED)

        run_2 = task.add_or_get_run()
        run_2.set_status(TaskRunStatusEnum.RUNNING)
        run_2.set_status(TaskRunStatusEnum.FINISHED)

        n1 = Notification.add(
            task_run=run_1, name="AAA", text="Z", kind=NotificationKindEnum.EMAIL
        )
        n2 = Notification.add(
            task_run=run_2, name="BBB", text="Y", kind=NotificationKindEnum.TELEGRAM
        )

        sort_cases = [
            ("По имени DESC", "name", "desc", [n2, n1]),
            ("По тексту ASC", "text", "asc", [n2, n1]),  # Y перед Z
            (  # Зависит от значений Enum
                "По типу (kind) DESC",
                "kind",
                "desc",
                [n2, n1],
            ),
            ("По связанному TaskRun.id DESC", "TaskRun.id", "desc", [n2, n1]),
            ("По связанному TaskRun.seq DESC", "TaskRun.seq", "desc", [n2, n1]),
        ]

        for msg, field, direction, expected_list in sort_cases:
            with self.subTest(msg):
                self.assert_notifications(
                    params={
                        "order[0][column]": 0,
                        "order[0][name]": field,
                        "order[0][dir]": direction,
                    },
                    expected=expected_list,
                )

    def test_search_with_sorting_and_pagination(self) -> None:
        task = Task.add(name="SortTask", command="*")
        run_1 = task.add_or_get_run()

        # Создание группы уведомлений со словом 'critical'
        # Id и алфавит имен не совпадали (для проверки сортировки)
        n_crit_3 = Notification.add(
            task_run=run_1,
            name="Z_critical",
            text="Error 3",
            kind=NotificationKindEnum.EMAIL,
        )
        n_crit_1 = Notification.add(
            task_run=run_1,
            name="A_critical",
            text="Error 1",
            kind=NotificationKindEnum.TELEGRAM,
        )
        n_crit_2 = Notification.add(
            task_run=None,
            name="M_critical",
            text="Error 2",
            kind=NotificationKindEnum.EMAIL,
        )

        for i in range(5):
            Notification.add(
                task_run=run_1,
                name=f"Normal_{i}",
                text="all links ok",
                kind=NotificationKindEnum.TELEGRAM,
            )

        # Итого в базе: 8 записей (recordsTotal = 8)
        # Подходят под фильтр 'critical': 3 записи (recordsFiltered = 3)
        # Если отсортировать по имени ASC, порядок будет: n_crit_1 ("A"), n_crit_2 ("M"), n_crit_3 ("Z")
        # Если взять length=2, то на первую страницу должны попасть только первые два элемента

        params = {
            "search[value]": "critical",  # Фильтр
            "order[0][column]": 0,  # Сортировка
            "order[0][name]": "name",
            "order[0][dir]": "asc",
            "start": 0,  # Пагинация
            "length": 2,
            "draw": 777,
        }

        self.assert_notifications(
            params=params,
            records_filtered=3,  # Должно быть 3, а не 2!
            expected=[n_crit_1, n_crit_2],  # Только первые два отсортированных элемента
            draw=777,
        )

    def test_multi_column_sorting(self) -> None:
        """Проверка сортировки по нескольким колонкам одновременно"""

        task = Task.add(name="SortTask", command="*")
        run_1 = task.add_or_get_run()

        n1 = Notification.add(
            task_run=run_1,
            name="SameName",
            text="A",
            kind=NotificationKindEnum.EMAIL,
        )
        n2 = Notification.add(
            task_run=run_1,
            name="SameName",
            text="B",
            kind=NotificationKindEnum.TELEGRAM,
        )
        n3 = Notification.add(
            task_run=None,
            name="AnotherName",
            text="C",
            kind=NotificationKindEnum.EMAIL,
        )

        params = {
            "order[0][column]": 0,
            "order[0][name]": "name",
            "order[0][dir]": "asc",
            "order[1][column]": 1,
            "order[1][name]": "text",
            "order[1][dir]": "desc",
        }

        # Ожидаемый порядок:
        # 1. 'AnotherName' (первый по алфавиту имени)
        # 2. 'SameName' с текстом 'B' (имена одинаковые, сортировка по тексту DESC)
        # 3. 'SameName' с текстом 'A'
        self.assert_notifications(params=params, expected=[n3, n2, n1])
