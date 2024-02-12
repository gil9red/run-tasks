#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from root_config import DIR_LOGS


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
