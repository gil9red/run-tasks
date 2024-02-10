#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import os
import sys

from pathlib import Path


DIR = Path(__file__).resolve().parent

DIR_LOGS = DIR / "logs"

DB_DIR_NAME = DIR / "database"
DB_DIR_NAME.mkdir(parents=True, exist_ok=True)

DB_FILE_NAME = DB_DIR_NAME / "db.sqlite"

ENCODING: str = os.environ.get("ENCODING", sys.getdefaultencoding())

PATTERN_FILE_JOB_COMMAND: str = "{script_name}_job{job_id}_run{job_run_id}"

SCRIPT_NAME = "run-tasks"
