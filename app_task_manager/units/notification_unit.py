#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import time

from app_task_manager.units.base_unit import BaseUnit
from db import Notification, NotificationKindEnum
from root_common import get_full_exception, send_email
from root_config import CONFIG

import third_party.add_notify_telegram
from third_party.add_notify_telegram import add_notify


# Установка адреса сервера, через который отправляются уведомления
third_party.add_notify_telegram.URL = CONFIG["notification"]["telegram"][
    "add_notify_url"
]


class NotificationUnit(BaseUnit):
    def process(self):
        for notify in Notification.get_unsent():
            try:
                self.log_info(
                    f"Отправка уведомления #{notify.id} в {notify.kind.value}"
                )

                match notify.kind:
                    case NotificationKindEnum.Email:
                        send_email(notify.name, notify.text)

                    case NotificationKindEnum.Telegram:
                        add_notify(
                            notify.name,
                            notify.text,
                            type="ERROR",
                            url=(
                                notify.task_run.get_url()
                                if notify.task_run
                                else CONFIG["notification"]["base_url"]
                            ),
                            has_delete_button=True,
                        )

                    case _:
                        raise Exception(
                            f"Неизвестный вид уведомления {notify.kind.value}"
                        )

                notify.set_as_send()

            except Exception as e:
                text = "Ошибка при отправке уведомления"
                self.log_exception(text, e)

                if notify.task_run:
                    notify.task_run.add_log_err(f"{text}:\n{get_full_exception(e)}")

                time.sleep(60)

        time.sleep(5)
