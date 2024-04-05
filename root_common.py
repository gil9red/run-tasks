#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import smtplib
import traceback
from datetime import datetime
from email.message import EmailMessage
from typing import Any, Generator

from cron_converter import Cron

from root_config import CONFIG
from third_party.cron_converter__examples.from_jenkins import do_convert


CONFIG_EMAIL: dict[str, Any] = CONFIG["notification"]["email"]
EMAIL_HOST: str = CONFIG_EMAIL["host"]
EMAIL_PORT: int = CONFIG_EMAIL["port"]
EMAIL_SEND_TO: str = CONFIG_EMAIL["send_to"]
EMAIL_LOGIN: str = CONFIG_EMAIL["login"]
EMAIL_PASSWORD: str = CONFIG_EMAIL["password"]


def get_full_exception(e: BaseException) -> str:
    return "".join(traceback.format_exception(e)).strip()


def send_email(
    subject: str,
    text: str,
    send_to: str = EMAIL_SEND_TO,
    host: str = EMAIL_HOST,
    port: int = EMAIL_PORT,
    login: str = EMAIL_LOGIN,
    password: str = EMAIL_PASSWORD,
):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = send_to
    msg["To"] = send_to
    msg.set_content(text)

    with smtplib.SMTP_SSL(host=host, port=port) as s:
        s.login(user=login, password=password)
        s.send_message(msg)


def get_scheduled_date_iter(cron: str) -> Generator[datetime, None, None]:
    cron = do_convert(cron)

    midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    schedule = Cron(cron).schedule(midnight)

    scheduled_date = schedule.next()
    while scheduled_date < datetime.now():
        scheduled_date = schedule.next()

    while True:
        yield scheduled_date
        scheduled_date = schedule.next()
