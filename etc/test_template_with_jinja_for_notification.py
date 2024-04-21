#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


# pip install PyYAML
import yaml

from jinja2.sandbox import SandboxedEnvironment

from db import TaskRun, TaskRunStatusEnum
from root_config import DIR


CONFIG: dict = yaml.safe_load((DIR / "etc/example-config.yaml").read_text("utf-8"))

email_template_name = CONFIG["notification"]["email"]["template"]["name"]
email_template_text = CONFIG["notification"]["email"]["template"]["text"]

tg_template_name = CONFIG["notification"]["telegram"]["template"]["name"]
tg_template_text = CONFIG["notification"]["telegram"]["template"]["text"]

run: TaskRun = (
    TaskRun
    .select()
    .where(TaskRun.status != TaskRunStatusEnum.PENDING)
    .order_by(TaskRun.id.desc())
    .first()
)
run = TaskRun.get_by_seq(1, 11841)
print(run)
print("-" * 10)

env = SandboxedEnvironment()

print(env.from_string(email_template_name).render(run=run, config=CONFIG))

print("-" * 10)

print(env.from_string(email_template_text).render(run=run, config=CONFIG))

print("-" * 10)

print(env.from_string(tg_template_name).render(run=run, config=CONFIG))

print("-" * 10)

print(env.from_string(tg_template_text).render(run=run, config=CONFIG))

print("-" * 10)

for log in run.logs:
    print(repr(log.text))
