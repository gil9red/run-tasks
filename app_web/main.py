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

from app_web import config
from app_web.app import app, USERS
from app_web.common import get_task, get_task_run, public_route
from root_config import PROJECT_NAME


@app.route("/")
def index() -> str:
    return render_template(
        "index.html",
        title=PROJECT_NAME,
    )


@app.route("/login", methods=["GET", "POST"])
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


@app.route("/task/<int:task_id>")
def task(task_id: int) -> str:
    return render_template(
        "task.html",
        title=PROJECT_NAME,
        task=get_task(task_id),
    )


@app.route("/task/create")
def task_create() -> str:
    return render_template(
        "task_create.html",
        title=PROJECT_NAME,
    )


@app.route("/task/<int:task_id>/run/<int:task_run_seq>")
def task_run(task_id: int, task_run_seq: int) -> str:
    return render_template(
        "task_run.html",
        title=PROJECT_NAME,
        task_run=get_task_run(task_id, task_run_seq),
    )


@app.route("/favicon.ico")
@public_route
def favicon() -> Response:
    return send_from_directory(Path(app.root_path) / "static/images", "avatar-256.png")


if __name__ == "__main__":
    app.run(
        host=config.HOST,
        port=config.PORT,
    )
