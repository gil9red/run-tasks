#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import logging
import sys
from pathlib import Path

from config import DIR_LOG


def get_logger(
    logger_name: str,
    dir_name: Path = DIR_LOG,
    log_stdout: bool = True,
    log_file: bool = True,
) -> logging.Logger:
    log = logging.getLogger(logger_name)
    log.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "[%(asctime)s] %(filename)s[LINE:%(lineno)d] %(levelname)-8s %(message)s"
    )

    if log_file:
        dir_name.mkdir(parents=True, exist_ok=True)
        file_name = dir_name / f"{logger_name}.log"

        fh = logging.FileHandler(file_name, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        log.addHandler(fh)

    if log_stdout:
        ch = logging.StreamHandler(stream=sys.stdout)
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(formatter)
        log.addHandler(ch)

    return log


log = get_logger(__file__)
