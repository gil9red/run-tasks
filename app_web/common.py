#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import enum
from typing import Any

from flask import abort
from peewee import DoesNotExist

from db import Task, TaskRun


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


def public_route(decorated_function: callable) -> callable:
    decorated_function.is_public = True
    return decorated_function
