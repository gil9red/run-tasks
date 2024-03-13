#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


from pathlib import Path
from typing import Any

# pip install PyYAML
import yaml


DIR: Path = Path(__file__).resolve().parent

DIR_LOGS: Path = DIR / "logs"

DB_DIR_NAME: Path = DIR / "database"
DB_DIR_NAME.mkdir(parents=True, exist_ok=True)

DB_FILE_NAME: Path = DB_DIR_NAME / "db.sqlite"

CONFIG_FILE_NAME: Path = DIR / "config.yaml"
if not CONFIG_FILE_NAME.exists():
    raise FileNotFoundError(CONFIG_FILE_NAME)

CONFIG: dict[str, Any] = yaml.safe_load(
    CONFIG_FILE_NAME.read_text("utf-8")
)

PROJECT_NAME: str = CONFIG["project_name"]

EMAIL_HOST: str = CONFIG["email"]["host"]
EMAIL_PORT: int = CONFIG["email"]["port"]
EMAIL_SEND_TO: str = CONFIG["email"]["send_to"]
EMAIL_LOGIN: str = CONFIG["email"]["login"]
EMAIL_PASSWORD: str = CONFIG["email"]["password"]
