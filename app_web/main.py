#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


from flask import render_template, jsonify, Response, abort

from peewee import DoesNotExist

from app_web import config
from app_web.app import app
from db import Task, TaskRun, TaskRunLog
from root_config import PROJECT_NAME


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


@app.route("/api/tasks")
def api_tasks() -> Response:
    return jsonify([obj.to_dict() for obj in Task.select().order_by(Task.id)])


@app.route("/api/task/<int:task_id>/runs")
def api_task_runs(task_id: int) -> Response:
    return jsonify(
        [obj.to_dict() for obj in get_task(task_id).runs.order_by(TaskRun.id)]
    )


@app.route("/api/task/<int:task_id>/run/<int:task_run_seq>/logs")
def api_task_run_logs(task_id: int, task_run_seq: int) -> Response:
    return jsonify(
        [
            obj.to_dict()
            for obj in get_task_run(task_id, task_run_seq).logs.order_by(TaskRunLog.id)
        ]
    )


# TODO:
# @app.route("/favicon.ico")
# def favicon():
#     return send_from_directory(
#         os.path.join(app.root_path, "static/images"), "favicon.png"
#     )


if __name__ == "__main__":
    app.run(
        host=config.HOST,
        port=config.PORT,
    )
