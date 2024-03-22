#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import logging
import sys
from datetime import datetime, date
from logging.handlers import RotatingFileHandler

from flask import Flask
from flask.json.provider import DefaultJSONProvider

import flask_login

from app_web import config
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


app = Flask(__name__)
app.debug = config.DEBUG
app.secret_key = config.SECRET_KEY
app.json = UpdatedJSONProvider(app)

login_manager = flask_login.LoginManager()
login_manager.init_app(app)


USERS: dict[str, User] = {
    login: User(login, password)
    for login, password in config.USERS.items()
}


@login_manager.user_loader
def user_loader(id: str) -> User | None:
    return USERS.get(id)


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
