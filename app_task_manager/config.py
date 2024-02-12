#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import os
import sys


ENCODING: str = os.environ.get("ENCODING", sys.getdefaultencoding())

PATTERN_FILE_JOB_COMMAND: str = "{script_name}_job{job_id}_run{job_run_id}"

SCRIPT_NAME = "run-tasks"
