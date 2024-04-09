#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import logging
from datetime import datetime, date
from http import HTTPStatus

from flask import Flask, Response, request, redirect, url_for, jsonify
from flask.json.provider import DefaultJSONProvider
from werkzeug.exceptions import HTTPException

import flask_login

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

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
    login: User(login, password) for login, password in config.USERS.items()
}


app = Flask(__name__)
app.debug = config.DEBUG
app.json = UpdatedJSONProvider(app)
app.logger = logging.getLogger("werkzeug")
app.secret_key = config.SECRET_KEY

app.register_blueprint(api_bp, url_prefix="/api")

limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri="memory://",
)

login_manager = flask_login.LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def user_loader(id: str) -> User | None:
    return USERS.get(id)


@app.errorhandler(Exception)
def handle_bad_request(e):
    app.logger.error(f"Error: {e}", exc_info=e)

    code: int = e.code if isinstance(e, HTTPException) else 500

    # NOTE: request.blueprint не работает, поэтому другая проверка
    if request.path.startswith(f"/{api_bp.name}/"):
        return (
            jsonify(
                prepare_response(
                    status=StatusEnum.ERROR,
                    text=str(e),
                )
            ),
            code,
        )

    if isinstance(e, HTTPException):
        return e

    raise e


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

    app.logger.warning(f"UNAUTHORIZED in {request} from {request.remote_addr}")

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
