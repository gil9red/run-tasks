#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import logging.config
import shutil
import warnings

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
CONFIG_EXAMPLE_FILE_NAME: Path = DIR / "etc" / "example-config.yaml"
if not CONFIG_FILE_NAME.exists():
    print(f"Не найден файл конфига {CONFIG_FILE_NAME}")

    if not CONFIG_EXAMPLE_FILE_NAME.exists():
        raise FileNotFoundError(CONFIG_EXAMPLE_FILE_NAME)

    print(f"Файл конфига скопирован из примера {CONFIG_EXAMPLE_FILE_NAME}")
    shutil.copy(CONFIG_EXAMPLE_FILE_NAME, CONFIG_FILE_NAME)

CONFIG: dict[str, Any] = yaml.safe_load(
    CONFIG_FILE_NAME.read_text("utf-8")
)
CONFIG_EXAMPLE: dict[str, Any] = yaml.safe_load(
    CONFIG_EXAMPLE_FILE_NAME.read_text("utf-8")
)


def dict_key_path_diff(dict_a: dict, dict_b: dict) -> list[str]:
    def get_path(d: dict | list | tuple | set, prefix: str = "") -> list[str]:
        result = []
        for k, v in d.items() if isinstance(d, dict) else enumerate(d):
            name = f"{prefix}/{k}"
            result.append(name)
            if isinstance(v, (dict, list, tuple, set)):
                result += get_path(v, name)
        return result

    path_a: list[str] = get_path(dict_a)
    path_b: list[str] = get_path(dict_b)

    result = []
    for a in path_a:
        if a not in path_b:
            result.append(a)
    return result


diff_config: list[str] = dict_key_path_diff(CONFIG_EXAMPLE, CONFIG)
if diff_config:
    result: str = "\n".join(diff_config)
    warnings.warn(
        f"Найдены различия конфиге {CONFIG_FILE_NAME.relative_to(DIR)} "
        f"в сравнении с {CONFIG_EXAMPLE_FILE_NAME.relative_to(DIR)}:\n{result}"
    )


for handler in CONFIG["logging"]["handlers"].values():
    try:
        handler["filename"] = str(DIR_LOGS / handler["filename"])
    except KeyError:
        pass
logging.config.dictConfig(CONFIG["logging"])

PROJECT_NAME: str = CONFIG["project_name"]
CONFIG_NOTIFICATION: dict[str, Any] = CONFIG["notification"]
