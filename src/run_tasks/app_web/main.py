#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


from pathlib import Path

import flask_login
from flask import (
    render_template,
    Response,
    send_from_directory,
    request,
    redirect,
    url_for,
    flash,
)

from run_tasks.app_web import config
from run_tasks.app_web.app import USERS, app, limiter
from run_tasks.app_web.common import (
    get_task_by_url_path,
    get_task_run,
    public_route,
)
from run_tasks.config import PROJECT_NAME
from run_tasks.db import Task


@app.route("/")
def index() -> str:
    return render_template(
        "index.html",
        title=PROJECT_NAME,
    )


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5/minute", methods=["POST"])
@public_route
def login() -> str | Response:
    error_text: str | None = None

    if request.method == "POST":
        login: str = request.form["login"]
        password: str = request.form["password"]

        user = USERS.get(login)
        if user is None or user.password != password:
            error_text = "Неправильный логин или пароль!"
        else:
            flask_login.login_user(user, remember=True)

    if flask_login.current_user.is_authenticated:
        url: str = request.args.get("from", default="/")
        return redirect(url)

    if error_text:
        flash(error_text, category="error")

    return render_template(
        "login.html",
        title=PROJECT_NAME,
        query_string=str(request.query_string, encoding="utf-8"),
    )


@app.route("/logout")
def logout() -> Response:
    flask_login.logout_user()
    return redirect(url_for("index"))


@app.route("/notifications")
def notifications() -> str:
    return render_template(
        "notifications.html",
        title=PROJECT_NAME,
    )


@app.route("/task/<task_identifier>")
def task(task_identifier: str) -> str:
    return render_template(
        "task.html",
        title=PROJECT_NAME,
        task=get_task_by_url_path(task_identifier),
    )


@app.route("/task/create")
def task_create() -> str:
    return render_template(
        "task_create_or_edit.html",
        title=PROJECT_NAME,
        task=None,
        is_mode_edit=False,
    )


@app.route("/task/<task_identifier>/edit")
def task_edit(task_identifier: str) -> str:
    return render_template(
        "task_create_or_edit.html",
        title=PROJECT_NAME,
        task=get_task_by_url_path(task_identifier),
        is_mode_edit=True,
    )


@app.route("/task/<task_identifier>/logs")
def task_logs(task_identifier: str) -> str:
    return render_template(
        "task_all_logs.html",
        title=PROJECT_NAME,
        task=get_task_by_url_path(task_identifier),
    )


@app.route("/task/<task_identifier>/run/last")
def task_run_last(task_identifier: str) -> str:
    task: Task = get_task_by_url_path(task_identifier)
    task_run_seq: int = task.last_started_run_seq
    return render_template(
        "task_run.html",
        title=PROJECT_NAME,
        task_run=get_task_run(task.id, task_run_seq),
        is_last=True,
    )


@app.route("/task/<task_identifier>/run/<int:task_run_seq>")
def task_run(task_identifier: str, task_run_seq: int) -> str:
    task: Task = get_task_by_url_path(task_identifier)
    return render_template(
        "task_run.html",
        title=PROJECT_NAME,
        task_run=get_task_run(task.id, task_run_seq),
    )


@app.route("/favicon.ico")
@public_route
def favicon() -> Response:
    return send_from_directory(
        Path(app.root_path) / "static/images",
        "avatar-256.png",
    )


if __name__ == "__main__":
    import sys
    from run_tasks.third_party.is_free_port import is_free_port

    # Режим отладки использует перезагрузку скриптов, а оно не сочетается с is_free_port
    if not app.debug and not is_free_port(config.PORT):
        print(f"Порт {config.PORT} занят. Завершение работы")
        sys.exit(1)

    app.run(
        host=config.HOST,
        port=config.PORT,
    )
