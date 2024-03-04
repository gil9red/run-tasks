#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


from pathlib import Path


DIR: Path = Path(__file__).resolve().parent

DIR_LOGS: Path = DIR / "logs"

DB_DIR_NAME: Path = DIR / "database"
DB_DIR_NAME.mkdir(parents=True, exist_ok=True)

DB_FILE_NAME: Path = DB_DIR_NAME / "db.sqlite"

# TODO:
EMAIL_HOST: str = ...
EMAIL_PORT: int = ...
EMAIL_SEND_TO: str = ...
EMAIL_LOGIN: str = ...
EMAIL_PASSWORD: str = ...
