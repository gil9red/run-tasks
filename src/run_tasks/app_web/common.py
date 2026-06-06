#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import enum
from http import HTTPStatus
from typing import Any

from flask import abort, request, url_for
from peewee import DoesNotExist
from werkzeug.routing import RequestRedirect

from run_tasks.db import Task, TaskRun, Notification


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
        abort(HTTPStatus.NOT_FOUND)


def get_task_by_url_path(url_path: str) -> Task:
    try:
        # Example: "123-foo-bar" -> 123
        task_id: int = int(url_path.split("-", maxsplit=1)[0])
    except (ValueError, IndexError):
        abort(HTTPStatus.NOT_FOUND)

    task: Task = get_task(task_id)
    if url_path != task.url_path:
        url_params = request.view_args.copy()
        url_params.update(request.args)

        url_params["task_identifier"] = task.url_path

        target_url = url_for(request.endpoint, **url_params)
        raise RequestRedirect(target_url)

    return task


def get_task_run(task_id: int, task_run_seq: int) -> TaskRun:
    try:
        return TaskRun.get_by_seq(task_id, task_run_seq)
    except DoesNotExist:
        abort(HTTPStatus.NOT_FOUND)


def get_notification(notification_id: int) -> Notification:
    try:
        return Notification.get_by_id(notification_id)
    except DoesNotExist:
        abort(HTTPStatus.NOT_FOUND)


def public_route(decorated_function: callable) -> callable:
    decorated_function.is_public = True
    return decorated_function
