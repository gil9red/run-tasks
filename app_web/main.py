#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


from flask import render_template

from app_web import config
from app_web.app import app, log
from db import Task, TaskRun, TaskRunLog


@app.route("/")
def index():
    log.debug("Call index")

    return render_template(
        "index.html",

        # Parameters to template
        title="run-tasks",
        tasks=Task.select(),
        task_runs=TaskRun.select(),
        task_run_logs=TaskRunLog.select(),
    )


# TODO:
# @app.route("/favicon.ico")
# def favicon():
#     return send_from_directory(
#         os.path.join(app.root_path, "static/images"), "favicon.png"
#     )


if __name__ == "__main__":
    app.run(port=config.PORT)

    # # Public IP
    # app.run(host='0.0.0.0')
