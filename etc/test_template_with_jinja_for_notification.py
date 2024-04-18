#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


from jinja2.sandbox import SandboxedEnvironment
from db import TaskRun
from root_config import CONFIG


env = SandboxedEnvironment()

# TODO:
run = TaskRun.get_by_seq(5, 79)
print(run)

print("\n" + "-" * 50 + "\n")

TEMPLATE_SUBJECT = """
[{{ config.project_name }}] Task "{{ run.task.name }}" - run #{{ run.seq }} - {{ run.work_status.capitalize() }}!
""".strip()
print(env.from_string(TEMPLATE_SUBJECT).render(run=run, config=CONFIG))

print("\n" + "-" * 50 + "\n")

TEMPLATE_CONTENT = """
[{{ config.project_name }}] Task "{{ run.task.name }}" - run #{{ run.seq }} - {{ run.work_status.capitalize() }}:

{%- for log in run.logs -%}
{{ log.text }}
{%- endfor %}

Check console output at {{ run.get_url() }} to view the results.
""".strip()
print(env.from_string(TEMPLATE_CONTENT).render(run=run, config=CONFIG))
