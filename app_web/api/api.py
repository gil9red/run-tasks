#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


from http import HTTPStatus
from typing import Any

from flask import Blueprint, Response, jsonify, request
from werkzeug.exceptions import BadRequest

from app_web.common import StatusEnum, prepare_response, get_task, get_task_run
from db import Task, TaskRun, TaskRunLog, Notification, NotificationKindEnum
from root_common import get_scheduled_date_generator


api_bp = Blueprint("api", __name__)


@api_bp.route("/tasks")
def tasks() -> Response:
    return jsonify([obj.to_dict() for obj in Task.select().order_by(Task.id)])


@api_bp.route("/task/create", methods=["POST"])
def task_create() -> Response | tuple[Response, int]:
    data: dict[str, Any] = request.json

    task: Task = Task.get_by_name(data["name"])
    if task:
        return (
            jsonify(
                prepare_response(
                    status=StatusEnum.ERROR,
                    text=f"Задача с {task.name!r} уже существует",
                ),
            ),
            HTTPStatus.BAD_REQUEST.value,
        )

    task = Task.add(**data)

    return jsonify(
        prepare_response(
            status=StatusEnum.OK,
            result=[task.to_dict()],
        ),
    )


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
            result=[task.to_dict()],
        ),
    )


@api_bp.route("/task/<int:task_id>/delete", methods=["DELETE"])  # TODO: в тесты
def task_delete(task_id: int) -> Response:
    task: Task = get_task(task_id)
    task.delete_instance()

    return jsonify(
        prepare_response(
            status=StatusEnum.OK,
            text=f"Задача #{task.id} успешно удалена",
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


@api_bp.route("/notifications/get-number-of-unsent")  # TODO: в тест
def notifications_get_number_of_unsent() -> Response:
    return jsonify(
        prepare_response(
            status=StatusEnum.OK,
            result=[dict(number=len(Notification.get_unsent()))],
        ),
    )


@api_bp.route("/cron/get-next-dates")
def cron_get_next_dates() -> Response:
    if "cron" not in request.args:
        raise BadRequest('Отсутствует параметр "cron"')

    cron: str = request.args["cron"]

    status = StatusEnum.OK
    text = None
    try:
        it = get_scheduled_date_generator(cron)
        result = [dict(date=next(it)) for _ in range(5)]
    except Exception:
        status = StatusEnum.ERROR
        text = "Неправильный формат"
        result = None

    return jsonify(
        prepare_response(
            status=status,
            text=text,
            result=result,
        ),
    )
