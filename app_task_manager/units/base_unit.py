#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


from abc import ABC, abstractmethod
from logging import Logger
from threading import Thread

from app_task_manager.common import log_manager


class BaseUnit(Thread, ABC):
    def __init__(self):
        super().__init__(daemon=True)

        self.log: Logger = log_manager

        # TODO:
        self._is_stopped: bool = False

        self._log_prefix: str = f"[{type(self).__name__}]"

    def stop(self):
        self._is_stopped = True

    @abstractmethod
    def process(self):
        pass

    def run(self):
        self.process()