#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import logging
import sys
from datetime import datetime, date
from logging.handlers import RotatingFileHandler

from flask import Flask, Response, request, redirect, url_for
from flask.json.provider import DefaultJSONProvider

import flask_login

from app_web import config
from app_web.api.api import api_bp
from root_config import DIR_LOGS


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


app = Flask(__name__)
app.debug = config.DEBUG
app.secret_key = config.SECRET_KEY
app.json = UpdatedJSONProvider(app)

app.register_blueprint(api_bp, url_prefix='/api')

login_manager = flask_login.LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def user_loader(id: str) -> User | None:
    return USERS.get(id)


@app.before_request
def check_route_access() -> Response | None:
    if any(
        [
            not request.endpoint or request.endpoint.startswith("static"),
            flask_login.current_user.is_authenticated,  # From Flask-Login
            getattr(app.view_functions.get(request.endpoint), "is_public", False),
        ]
    ):
        return  # Access granted

    params: dict = {"from": request.path}
    return redirect(url_for("login", **params))


log: logging.Logger = app.logger
log.handlers.clear()

formatter = logging.Formatter(
    "[%(asctime)s] %(filename)s:%(lineno)d %(levelname)-8s %(message)s"
)

file_handler = RotatingFileHandler(
    DIR_LOGS / "web.log", maxBytes=10_000_000, backupCount=5, encoding="utf-8"
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler(stream=sys.stdout)
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(formatter)

log.setLevel(logging.DEBUG)
log.addHandler(file_handler)
log.addHandler(stream_handler)

log_werkzeug = logging.getLogger("werkzeug")
log_werkzeug.setLevel(logging.DEBUG)
log_werkzeug.addHandler(file_handler)
log_werkzeug.addHandler(stream_handler)
