#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import enum
from pathlib import Path
from typing import Any

from flask import render_template, jsonify, Response, abort, send_from_directory, request
from peewee import DoesNotExist

from app_web import config
from app_web.app import app
from db import Task, TaskRun, TaskRunLog, Notification, NotificationKindEnum
from root_config import PROJECT_NAME


@enum.unique
class StatusEnum(enum.StrEnum):
    OK = enum.auto()
    ERROR = enum.auto()


def prepare_response(
    status: StatusEnum,
    text: str | None = None,
    result: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "text": text,
        "result": result,
    }


def get_task(task_id: int) -> Task:
    try:
        return Task.get_by_id(task_id)
    except DoesNotExist:
        abort(404)


def get_task_run(task_id: int, task_run_seq: int) -> TaskRun:
    try:
        return TaskRun.get_by_seq(task_id, task_run_seq)
    except DoesNotExist:
        abort(404)


@app.route("/")
def index() -> str:
    return render_template(
        "index.html",
        title=PROJECT_NAME,
    )


@app.route("/task/<int:task_id>")
def task(task_id: int) -> str:
    return render_template(
        "task.html",
        title=PROJECT_NAME,
        task=get_task(task_id),
    )


@app.route("/task/<int:task_id>/run/<int:task_run_seq>")
def task_run(task_id: int, task_run_seq: int) -> str:
    return render_template(
        "task_run.html",
        title=PROJECT_NAME,
        task_run=get_task_run(task_id, task_run_seq),
    )


@app.route("/notifications")
def notifications() -> str:
    return render_template(
        "notifications.html",
        title=PROJECT_NAME,
    )


@app.route("/api/tasks")
def api_tasks() -> Response:
    return jsonify([obj.to_dict() for obj in Task.select().order_by(Task.id)])


@app.route("/api/task/update", methods=["POST"])
def api_task_update() -> Response:
    data: dict[str, Any] = request.json

    task: Task = get_task(data["id"])

    if "command" in data:
        task.command = data["command"]

    if "cron" in data:
        task.cron = data["cron"]

    if "is_enabled" in data:
        task.is_enabled = data["is_enabled"]

    if "is_infinite" in data:
        task.is_infinite = data["is_infinite"]

    if "description" in data:
        task.description = data["description"]

    task.save()

    return jsonify(
        prepare_response(
            status=StatusEnum.OK,
            # TODO: Нужно ли?
            # text=f"Создано уведомление #{notification.id}",
            result=[task.to_dict()],
        ),
    )


@app.route("/api/task/<int:task_id>/runs")
def api_task_runs(task_id: int) -> Response:
    return jsonify(
        [obj.to_dict() for obj in get_task(task_id).runs.order_by(TaskRun.id)]
    )


@app.route("/api/task/<int:task_id>/action/run", methods=["POST"])
def api_task_action_run(task_id: int) -> Response:
    run = get_task(task_id).add_or_get_run()
    # TODO: какой-нибудь общий метод для возврата ответа
    return jsonify(
        prepare_response(
            status=StatusEnum.OK,
            text=(
                f"Создан запуск {run.seq} (#{run.id}) "
                f'<a href="{run.get_url(full=False)}" target=”_blank”>'
                '<i class="bi bi-box-arrow-up-right"></i>'
                "</a>"
            ),
        ),
    )


@app.route("/api/task/<int:task_id>/run/<int:task_run_seq>/logs")
def api_task_run_logs(task_id: int, task_run_seq: int) -> Response:
    return jsonify(
        [
            obj.to_dict()
            for obj in get_task_run(task_id, task_run_seq).logs.order_by(TaskRunLog.id)
        ]
    )


@app.route("/api/notifications")
def api_notifications() -> Response:
    return jsonify(
        [obj.to_dict() for obj in Notification.select().order_by(Notification.id)]
    )


@app.route("/api/notification/create", methods=["POST"])
def api_notification_create() -> Response:
    # TODO: добавить проверку полей
    data: dict[str, Any] = request.json

    notification = Notification.add(
        task_run=None,
        name=data["name"],
        text=data["text"],
        kind=NotificationKindEnum(data["kind"]),
    )
    return jsonify(
        prepare_response(
            status=StatusEnum.OK,
            text=f"Создано уведомление #{notification.id}",
            result=[notification.to_dict()],
        ),
    )


@app.route("/favicon.ico")
def favicon() -> Response:
    return send_from_directory(Path(app.root_path) / "static/images", "avatar-256.png")


if __name__ == "__main__":
    app.run(
        host=config.HOST,
        port=config.PORT,
    )
