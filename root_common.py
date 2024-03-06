#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import logging
import smtplib
import sys
import traceback
from email.message import EmailMessage
from logging.handlers import RotatingFileHandler
from pathlib import Path

from root_config import (
    DIR_LOGS,
    EMAIL_HOST,
    EMAIL_PORT,
    EMAIL_LOGIN,
    EMAIL_PASSWORD,
    EMAIL_SEND_TO,
)


def get_full_exception(e: BaseException) -> str:
    return "".join(traceback.format_exception(e)).strip()


def get_logger(
    logger_name: str,
    file_name: str = "log.log",
    dir_name: Path = DIR_LOGS,
    log_stdout: bool = True,
    log_file: bool = True,
    encoding: str = "utf-8",
) -> logging.Logger:
    log = logging.getLogger(logger_name)

    # Если обработчики есть, значит логгер уже создавали
    if log.handlers:
        return log

    log.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "[%(asctime)s] %(filename)s[LINE:%(lineno)d] %(levelname)-8s %(message)s"
    )

    if log_file:
        dir_name.mkdir(parents=True, exist_ok=True)
        file_name = dir_name / file_name

        fh = RotatingFileHandler(
            file_name, maxBytes=10_000_000, backupCount=5, encoding=encoding
        )
        fh.setFormatter(formatter)
        log.addHandler(fh)

    if log_stdout:
        ch = logging.StreamHandler(stream=sys.stdout)
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(formatter)
        log.addHandler(ch)

    return log


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
