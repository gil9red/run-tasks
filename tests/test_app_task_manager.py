#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


from datetime import datetime
from unittest import TestCase

from app_task_manager.units.scheduler_unit import SchedulerUnit


class TestSchedulerUnit(TestCase):
    def test__get_scheduled_date(self):
        self.assertGreater(SchedulerUnit._get_scheduled_date("* * * * *"), datetime.now())
        self.assertGreater(SchedulerUnit._get_scheduled_date("0 * * * *"), datetime.now())
