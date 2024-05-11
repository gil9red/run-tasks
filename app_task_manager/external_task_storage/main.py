#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import logging
from typing import Any

# pip install PyYAML
import yaml

from root_config import CONFIG
from db import Task
from third_party.get_gist_file import get_gist_file


CONFIG_GIST: dict[str, Any] = CONFIG["manager"]["external_task_storage"]["gist"]


log = logging.getLogger("external_task_storage")


def process(tasks: dict[str, dict[str, Any]]):
    total = len(tasks)
    updated = 0
    created = 0
    nothing = 0

    log.info("")
    log.info(f"Начата обработка {total} задач")

    for name, data in tasks.items():
        log.info("")
        log.info(f"Обработка задачи {name!r}")

        description = data["description"]
        cron = data["cron"]
        command = data["command"].format(
            root_dir=data["root_dir"],
            name=name,
        )

        task = Task.get_by_name(name)
        if not task:
            log.info("Создание задачи")
            created += 1

            Task.add(
                name=name,
                command=command,
                description=description,
                cron=cron,
            )
            continue

        if task.command != command:
            task.command = command

        if task.description != description:
            task.description = description

        if task.cron != cron:
            task.cron = cron

        if task.is_dirty():
            log.info("Обновление задачи")
            updated += 1
            task.save()
        else:
            log.info("Изменений нет")
            nothing += 1

    log.info("")
    log.info(f"""
Статистика:
Всего задач: {total}
Обновлено: {updated}
Создано: {created}
Без изменений: {nothing}
    """.strip())


def download_and_process():
    log.info("Обработка задач из внешнего хранилища")

    gist_url = CONFIG_GIST["url"]
    file_name = CONFIG_GIST["file_name"]

    log.info(f"Адрес: {gist_url!r}, файл: {file_name!r}")

    text = get_gist_file(gist_url, file_name)
    tasks: dict[str, dict] = {
        k: v
        for k, v in yaml.safe_load(text).items()
        if not k.startswith("__")
    }

    process(tasks)


if __name__ == "__main__":
    download_and_process()
