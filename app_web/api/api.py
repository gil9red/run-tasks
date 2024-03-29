#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


from typing import Any

from flask import Blueprint, Response, jsonify, request
from app_web.common import StatusEnum, prepare_response, get_task, get_task_run
from db import Task, TaskRun, TaskRunLog, Notification, NotificationKindEnum


api_bp = Blueprint("api", __name__)


@api_bp.route("/tasks")
def tasks() -> Response:
    return jsonify([obj.to_dict() for obj in Task.select().order_by(Task.id)])


@api_bp.route("/task/update", methods=["POST"])
def task_update() -> Response:
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


@api_bp.route("/task/<int:task_id>/runs")
def task_runs(task_id: int) -> Response:
    return jsonify(
        [obj.to_dict() for obj in get_task(task_id).runs.order_by(TaskRun.id)]
    )


@api_bp.route("/task/<int:task_id>/action/run", methods=["POST"])
def task_action_run(task_id: int) -> Response:
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


@api_bp.route("/task/<int:task_id>/run/<int:task_run_seq>/logs")
def task_run_logs(task_id: int, task_run_seq: int) -> Response:
    return jsonify(
        [
            obj.to_dict()
            for obj in get_task_run(task_id, task_run_seq).logs.order_by(TaskRunLog.id)
        ]
    )


@api_bp.route("/notifications")
def notifications() -> Response:
    return jsonify(
        [obj.to_dict() for obj in Notification.select().order_by(Notification.id)]
    )


@api_bp.route("/notification/create", methods=["POST"])
def notification_create() -> Response:
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
