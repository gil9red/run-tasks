#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


from abc import ABC, abstractmethod
from logging import Logger
from threading import Thread

from app_task_manager.common import log_manager


class BaseUnit(Thread, ABC):
    def __init__(self, owner: "TaskManager"):
        super().__init__(daemon=True)

        self.owner = owner
        self.log: Logger = log_manager

        # TODO:
        self._is_stopped: bool = False

        self._log_prefix: str = f"[{type(self).__name__}]"

    def log_debug(self, text: str):
        self.log.debug(f"{self._log_prefix} {text}")

    def log_info(self, text: str):
        self.log.info(f"{self._log_prefix} {text}")

    def stop(self):
        self._is_stopped = True

    @abstractmethod
    def process(self):
        pass

    def run(self):
        self.log_debug("Старт")
        self.process()
        self.log_debug("Финиш")
