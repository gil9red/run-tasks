#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


from flask import render_template, jsonify, Response, abort

from peewee import DoesNotExist

from app_web import config
from app_web.app import app
from db import Task, TaskRun, TaskRunLog


@app.route("/")
def index() -> str:
    return render_template(
        "index.html",
        # Parameters to template
        title="run-tasks",  # TODO: из конфига
    )


@app.route("/task/<int:task_id>")
def task(task_id: int) -> str:
    try:
        task: Task = Task.get_by_id(task_id)
    except DoesNotExist:
        abort(404)

    return render_template(
        "task.html",
        # Parameters to template
        title="run-tasks",  # TODO: из конфига
        task=task,
    )


@app.route("/api/tasks")
def api_tasks() -> Response:
    return jsonify([obj.to_dict() for obj in Task.select().order_by(Task.id)])


@app.route("/api/task/<int:task_id>/runs")
def api_task_runs(task_id: int) -> Response:
    try:
        task: Task = Task.get_by_id(task_id)
    except DoesNotExist:
        abort(404)

    return jsonify([obj.to_dict() for obj in task.runs.order_by(TaskRun.id)])


@app.route("/api/task/<int:task_id>/run/<int:task_run_id>/logs")
def api_task_run_logs(task_id: int, task_run_id: int) -> Response:
    try:
        run: TaskRun = TaskRun.get_by_id(task_run_id)
    except DoesNotExist:
        abort(404)

    if run.task_id != task_id:
        abort(404)

    return jsonify([obj.to_dict() for obj in run.logs.order_by(TaskRunLog.id)])


# TODO:
# @app.route("/favicon.ico")
# def favicon():
#     return send_from_directory(
#         os.path.join(app.root_path, "static/images"), "favicon.png"
#     )


if __name__ == "__main__":
    app.debug = True

    app.run(
        host=config.HOST,
        port=config.PORT,
    )
