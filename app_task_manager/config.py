#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import sys
from typing import Any

from root_config import CONFIG


CONFIG_MANAGER: dict[str, Any] = CONFIG["manager"]

ENCODING: str = CONFIG_MANAGER["encoding"] or sys.getdefaultencoding()
PATTERN_FILE_JOB_COMMAND: str = CONFIG_MANAGER["pattern_file_job_command"]
STORAGE_PERIOD_OF_TASK_RUN_IN_DAYS: int = CONFIG_MANAGER["storage_period"]["task_run_in_days"]
