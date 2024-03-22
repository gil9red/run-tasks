#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


from typing import Any
from root_config import CONFIG


CONFIG_WEB: dict[str, Any] = CONFIG["web"]

HOST: str = CONFIG_WEB["host"]
PORT: int = CONFIG_WEB["port"]
DEBUG: bool = CONFIG_WEB["debug"]
SECRET_KEY: str | None = CONFIG_WEB["secret_key"]

USERS: dict[str, str] = {
    CONFIG_WEB["login"]: CONFIG_WEB["password"],
}
