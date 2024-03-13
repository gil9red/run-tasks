#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


from root_config import CONFIG


HOST: str = CONFIG["web"]["host"]
PORT: int = CONFIG["web"]["port"]
DEBUG: bool = CONFIG["web"]["debug"]
SECRET_KEY: str | None = CONFIG["web"]["secret_key"]
