#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import time
import db


# TODO: Пример создания/обновления задач
# db.Task.add(
#     name="example run.bat",
#     command="run.bat",
# )
# db.Task.add(
#     name="example python",
#     command='python -c "import uuid;print(uuid.uuid4())"',
# )
# db.Task.add(
#     name="example python for",
#     command='python -c "import time;[(print(i), time.sleep(1)) for i in range(10)]"',
# )
# db.Task.add(
#     name="example python pyqt gui",
#     command=r'python "C:\Users\ipetrash\PycharmProjects\SimplePyScripts\Base64_examples\gui_base64.py"',
# )


# run = db.Task.get_by_id(1).add_run()
# print(run)
# time.sleep(5)
# run.status = db.TaskStatusEnum.Stopped
# run.save()
# print(run)
task = db.Task.get_by_id(1)
print(task)
task.add_run()
time.sleep(5)
task.is_enabled = False
task.save()
print(task)


# TODO:
# import psutil
# for run in db.TaskRun.select().where(db.TaskRun.status == db.TaskStatusEnum.Running, db.TaskRun.process_id.is_null(False)):
#     print(run)
#     print(run.command)
#     try:
#         process = psutil.Process(run.process_id)
#         print(process)
#         print(process.cmdline())
#     except psutil.NoSuchProcess:
#         # TODO: Установить статус на stopped?
#         print("Not found!")
#     print()


# task = db.Task.add(
#     name="python gui EscapeString",
#     command=r'"C:\Users\ipetrash\AppData\Local\Programs\Python\Python310\python.exe" "C:\Users\ipetrash\PycharmProjects\SimplePyScripts\EscapeString\main.py"',
# )
# print(task)
# task.add_run()

# task = db.Task.add(
#     name="ping this",
#     command="ping 127.0.0.1",
#     description="ping",
# )
# run = task.add_run()

# task = db.Task.add(
#     name="ping ya.ru",
#     command="ping ya.ru",
#     description="ping",
# )
# run = task.add_run()

# task = db.Task.add(
#     name="python hello пример",
#     command="""
#     python -c "print('hello пример')"
#     """.strip(),
# )
# print(task)
# task.add_run()

# task = db.Task.add(
#     name="python sleep(60)",
#     command=r'python -c "import time;time.sleep(60)"',
# )
# print(task)
# task.add_run()

# task: db.Task = db.Task.get_or_none(name="run.bat")
# if not task:
#     task = db.Task.add(
#         name="run.bat",
#         command=r'"C:\Users\ipetrash\PycharmProjects\run-tasks\run.bat"',
#     )
# print(task)
# task.add_run()

# task = db.Task.add(
#     name="run gui.bat",
#     command=r'"C:\Users\ipetrash\PycharmProjects\run-tasks\run gui.bat"',
# )
# print(task)
# task.add_run()

# task: db.Task = db.Task.get_or_none(name="example python pyqt gui")
# if not task:
#     task = db.Task.add(
#         name="example python pyqt gui",
#         command=r'"C:\Users\ipetrash\AppData\Local\Programs\Python\Python310\python.exe" "C:\Users\ipetrash\PycharmProjects\SimplePyScripts\Base64_examples\gui_base64.py"',
#     )
# print(task)
# task.add_run()

# from threading import Timer
# task = db.Task.get_by_id(1)
# Timer(2, lambda: task.add_run()).start()
# Timer(5, lambda: task.add_run()).start()
# Timer(7, lambda: task.add_run()).start()
# for _ in range(20):
#     query = task.runs.where(db.TaskRun.status.in_([db.TaskStatusEnum.Pending, db.TaskStatusEnum.Running]))
#     runs = list(query)
#     print(runs)
#     time.sleep(1)
