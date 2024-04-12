#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import logging.config
import shutil

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
    print(f"Не найден файл конфига {CONFIG_FILE_NAME}")

    config_file_example_name: Path = DIR / "etc" / "example-config.yaml"
    if not config_file_example_name.exists():
        raise FileNotFoundError(config_file_example_name)

    print(f"Файл конфига скопирован из примера {config_file_example_name}")
    shutil.copy(config_file_example_name, CONFIG_FILE_NAME)

CONFIG: dict[str, Any] = yaml.safe_load(CONFIG_FILE_NAME.read_text("utf-8"))

for handler in CONFIG["logging"]["handlers"].values():
    try:
        handler["filename"] = str(DIR_LOGS / handler["filename"])
    except KeyError:
        pass
logging.config.dictConfig(CONFIG["logging"])

PROJECT_NAME: str = CONFIG["project_name"]
