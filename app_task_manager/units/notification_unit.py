#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import time

from app_task_manager.units.base_unit import BaseUnit
from db import Notification, NotificationKindEnum
from root_common import get_full_exception, send_email
from third_party.add_notify_telegram import add_notify


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
                        add_notify(notify.name, notify.text)

                    case _:
                        raise Exception(
                            f"Неизвестный вид уведомления {notify.kind.value}"
                        )

                notify.set_as_send()

            except Exception as e:
                text = "Ошибка при отправке уведомления"
                self.log_exception(text, e)
                notify.task_run.add_log_err(f"{text}:\n{get_full_exception(e)}")

                time.sleep(60)

        time.sleep(5)
