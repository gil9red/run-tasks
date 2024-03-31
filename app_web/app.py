#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


from datetime import datetime, date
from http import HTTPStatus

from flask import Flask, Response, request, redirect, url_for, jsonify
from flask.json.provider import DefaultJSONProvider
from werkzeug.exceptions import HTTPException

import flask_login

from app_web import config
from app_web.api.api import api_bp
from app_web.common import StatusEnum, prepare_response


class UpdatedJSONProvider(DefaultJSONProvider):
    sort_keys = False

    def default(self, o):
        if isinstance(o, (date, datetime)):
            return o.isoformat()
        return super().default(o)


class User(flask_login.UserMixin):
    def __init__(self, login: str, password: str):
        self.id = login
        self.password = password


USERS: dict[str, User] = {
    login: User(login, password)
    for login, password in config.USERS.items()
}


app = Flask("web-server")
app.debug = config.DEBUG
app.secret_key = config.SECRET_KEY
app.json = UpdatedJSONProvider(app)

app.register_blueprint(api_bp, url_prefix="/api")

login_manager = flask_login.LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def user_loader(id: str) -> User | None:
    return USERS.get(id)


@app.errorhandler(HTTPException)
def handle_bad_request(e):
    # NOTE: request.blueprint не работает, поэтому другая проверка
    if request.path.startswith(f"/{api_bp.name}/"):
        return jsonify(
            prepare_response(
                status=StatusEnum.ERROR,
                text=str(e),
            )
        )

    return e


@app.before_request
def check_route_access() -> Response | tuple[Response, int] | None:
    if any(
        [
            not request.endpoint or request.endpoint.startswith("static"),
            flask_login.current_user.is_authenticated,  # From Flask-Login
            getattr(app.view_functions.get(request.endpoint), "is_public", False),
        ]
    ):
        return  # Access granted

    if request.blueprint == api_bp.name:
        return (
            jsonify(
                prepare_response(
                    status=StatusEnum.ERROR,
                    text=HTTPStatus.UNAUTHORIZED.phrase,
                )
            ),
            HTTPStatus.UNAUTHORIZED.value,
        )

    params: dict = {"from": request.path}
    return redirect(url_for("login", **params))
