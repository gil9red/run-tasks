#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


from functools import reduce
from dataclasses import dataclass, field
from http import HTTPStatus
from operator import or_
from typing import Self, Any

from flask import Blueprint, Request, Response, jsonify, request, abort
from werkzeug.exceptions import BadRequest

from peewee import Model, Expression, SQL, ColumnBase, fn, JOIN
from playhouse.shortcuts import model_to_dict

from querystring_parser import parser

from run_tasks.app_web.common import (
    StatusEnum,
    prepare_response,
    get_task,
    get_task_run,
    get_notification,
)
from run_tasks.db import (
    Task,
    TaskRun,
    StopReasonEnum,
    TaskRunLog,
    Notification,
    NotificationKindEnum,
    TaskRunStatusEnum,
    TaskRunWorkStatusEnum,
)
from run_tasks.common import get_scheduled_date_generator


@dataclass(frozen=True, kw_only=True)
class DataTableRequest:
    draw: int
    start: int
    length: int
    search_value: str
    order_by: list[Expression] = field(default_factory=list)

    @classmethod
    def from_request(
        cls,
        request: Request,
        models: list[type[Model]],
        allowed_columns: list[str],
    ) -> Self:
        nested_args: dict[str, Any] = parser.parse(
            request.query_string.decode("utf-8"),
            normalized=True,
        )

        draw = int(nested_args.get("draw", 1))
        start = int(nested_args.get("start", 0))
        length = int(nested_args.get("length", 10))

        search_dict = nested_args.get("search", dict())
        search_value = search_dict.get("value", "").strip()

        order_list: list[Expression] = []

        orders = nested_args.get("order", dict())

        for order_data in orders:
            col_idx = order_data.get("column")  # Индекс колонки
            direction = order_data.get("dir", "asc")

            col_name = order_data.get("name")
            if not col_name:
                abort(400, description=f"Missing name for column index {col_idx}")

            if col_name not in allowed_columns:
                abort(403, description=f"Sorting by field '{col_name}' is forbidden")

            field_obj: ColumnBase | None = None

            if "." in col_name:
                model_part, field_part = col_name.split(".", 1)
                for m in models:
                    if m._meta.name == model_part:
                        field_obj = m._meta.fields.get(field_part)
                        break

            if not field_obj:
                for m in models:
                    if col_name in m._meta.fields:
                        field_obj = m._meta.fields[col_name]
                        break

            if not field_obj:
                field_obj = SQL(col_name)

            order_list.append(
                field_obj.desc() if direction == "desc" else field_obj.asc()
            )

        return cls(
            draw=draw,
            start=start,
            length=length,
            search_value=search_value,
            order_by=order_list,
        )


api_bp = Blueprint("api", __name__)


@api_bp.route("/tasks")
def tasks() -> Response:
    model_type: type[Model] = Task

    subquery_last_started_run = (
        TaskRun.select(
            TaskRun,
            TaskRun.work_status.alias("work_status"),
            fn.MAX(TaskRun.id),
        )
        .where(TaskRun.status != TaskRunStatusEnum.PENDING)
        .group_by(TaskRun.task)
        .alias("last_started_run")
    )

    subquery_nearest_scheduled_run = (
        TaskRun.select(
            TaskRun.task,
            TaskRun.scheduled_date,
            fn.MAX(TaskRun.id),
        )
        .where(
            (TaskRun.status == TaskRunStatusEnum.PENDING)
            & TaskRun.scheduled_date.is_null(False)
        )
        .group_by(TaskRun.task)
        .alias("nearest_scheduled_run")
    )

    # TODO: Подумать над названием свойств с db_ - мб что-то по другому назвать
    #       В ответе их с таким же названием возвращать?
    query = (
        Task.select(
            Task,
            fn.COALESCE(
                subquery_last_started_run.c.work_status,
                TaskRunWorkStatusEnum.NONE,
            ).alias("db_last_work_status"),
            subquery_last_started_run.c.start_date.alias(
                "db_last_started_run_start_date"
            ),
            fn.COALESCE(subquery_last_started_run.c.seq, 0).alias("db_number_of_runs"),
            subquery_last_started_run.c.seq.alias("db_last_started_run_seq"),
            subquery_nearest_scheduled_run.c.scheduled_date.alias(
                "db_next_scheduled_date"
            ),
        )
        .join(
            subquery_last_started_run,
            JOIN.LEFT_OUTER,
            on=(Task.id == subquery_last_started_run.c.task_id),
        )
        .join(
            subquery_nearest_scheduled_run,
            JOIN.LEFT_OUTER,
            on=(Task.id == subquery_nearest_scheduled_run.c.task_id),
        )
    )

    data_table_rq = DataTableRequest.from_request(
        request,
        models=[Task, TaskRun],
        allowed_columns=[
            "id",
            "name",
            "command",
            "description",
            "is_enabled",
            "cron",
            "is_infinite",
            "db_last_started_run_start_date",
            "db_number_of_runs",
            "db_last_started_run_seq",
            "db_next_scheduled_date",
        ],
    )

    total_records = query.count()

    if data_table_rq.search_value:
        search_fields = [
            model_type.name,
            model_type.command,
            model_type.description,
            model_type.cron,
        ]
        conditions = [
            field.contains(data_table_rq.search_value) for field in search_fields
        ]
        query = query.where(reduce(or_, conditions))

    records_filtered = query.count()

    query = (
        query.order_by(*data_table_rq.order_by)
        .offset(data_table_rq.start)
        .limit(data_table_rq.length)
    )

    def to_dict(obj) -> dict[str, Any]:
        return {
            **model_to_dict(obj, recurse=False),
            **{
                "number_of_runs": obj.db_number_of_runs,
                "last_started_run_seq": obj.db_last_started_run_seq,
                "last_started_run_start_date": obj.db_last_started_run_start_date,
                "next_scheduled_date": obj.db_next_scheduled_date,
                "last_work_status": obj.db_last_work_status,
            },
        }

    return jsonify(
        {
            "draw": data_table_rq.draw,
            "recordsTotal": total_records,
            "recordsFiltered": records_filtered,
            "data": [to_dict(obj) for obj in query.objects()],
        }
    )


@api_bp.route("/task/create", methods=["POST"])
def task_create() -> Response | tuple[Response, int]:
    data: dict[str, Any] = request.json

    task: Task = Task.get_by_name(data["name"])
    if task:
        return (
            jsonify(
                prepare_response(
                    status=StatusEnum.ERROR,
                    text=f"Задача с {task.name!r} уже существует",
                ),
            ),
            HTTPStatus.BAD_REQUEST.value,
        )

    task = Task.add(**data)

    return jsonify(
        prepare_response(
            status=StatusEnum.OK,
            result=[task.to_dict()],
        ),
    )


@api_bp.route("/task/<int:task_id>")
def task_get(task_id: int) -> Response:
    return jsonify(
        prepare_response(
            status=StatusEnum.OK,
            result=[get_task(task_id).to_dict()],
        ),
    )


@api_bp.route("/task/<int:task_id>/update", methods=["POST"])
def task_update(task_id: int) -> Response:
    task: Task = get_task(task_id)

    data: dict[str, Any] = request.json

    if "command" in data:
        task.command = data["command"]

    if "cron" in data:
        task.cron = data["cron"]

    if "is_enabled" in data:
        task.is_enabled = data["is_enabled"]

    if "is_infinite" in data:
        task.is_infinite = data["is_infinite"]

    if "description" in data:
        task.description = data["description"]

    task.save()

    return jsonify(
        prepare_response(
            status=StatusEnum.OK,
            result=[task.to_dict()],
        ),
    )


@api_bp.route("/task/<int:task_id>/logs")
def task_logs(task_id: int) -> Response:
    task: Task = get_task(task_id)

    # TODO: Нужно будет анализировать данные фильтрации, сортировки и пагинации
    # data: dict[str, Any] = request.json

    return jsonify(
        [
            obj.to_dict()
            for obj in task.get_all_logs(
                items_per_page=999_999_999  # TODO: Временное решение для возврата всех записей
            )
        ]
    )


@api_bp.route("/task/<int:task_id>/delete", methods=["DELETE"])
def task_delete(task_id: int) -> Response:
    task: Task = get_task(task_id)
    task.delete_instance()

    return jsonify(
        prepare_response(
            status=StatusEnum.OK,
            text=f"Задача #{task.id} успешно удалена",
        ),
    )


@api_bp.route("/task/<int:task_id>/runs")
def task_runs(task_id: int) -> Response:
    return jsonify(
        [obj.to_dict() for obj in get_task(task_id).runs.order_by(TaskRun.id)]
    )


@api_bp.route("/task/<int:task_id>/do-run", methods=["POST"])
def task_do_run(task_id: int) -> Response:
    run = get_task(task_id).add_or_get_run()
    return jsonify(
        prepare_response(
            status=StatusEnum.OK,
            text=(
                f"Создан запуск {run.seq} (#{run.id}) "
                f'<a href="{run.get_url(full=False)}" target=”_blank”>'
                '<i class="bi bi-box-arrow-up-right"></i>'
                "</a>"
            ),
        ),
    )


@api_bp.route("/task/<int:task_id>/run/<int:task_run_seq>")
def task_run_get(task_id: int, task_run_seq: int) -> Response:
    return jsonify(
        prepare_response(
            status=StatusEnum.OK,
            result=[get_task_run(task_id, task_run_seq).to_dict()],
        ),
    )


@api_bp.route("/task/<int:task_id>/run/last")
def task_run_get_last(task_id: int) -> Response:
    task = get_task(task_id)
    task_run: TaskRun | None = task.get_last_run()
    if not task_run:
        abort(404)
    return task_run_get(task_id, task_run.seq)


@api_bp.route("/task/<int:task_id>/run/<int:task_run_seq>/do-stop", methods=["POST"])
def task_run_do_stop(task_id: int, task_run_seq: int) -> Response:
    run: TaskRun = get_task_run(task_id, task_run_seq)
    run.set_stop(StopReasonEnum.SERVER_API)

    return jsonify(
        prepare_response(
            status=StatusEnum.OK,
            text=f"Запуск #{run.seq} задачи остановлен",
        ),
    )


@api_bp.route(
    "/task/<int:task_id>/run/<int:task_run_seq>/do-send-notifications",
    methods=["POST"],
)
def task_run_do_send_notifications(task_id: int, task_run_seq: int) -> Response:
    run: TaskRun = get_task_run(task_id, task_run_seq)
    run.send_notifications()

    return jsonify(
        prepare_response(
            status=StatusEnum.OK,
            text="Выполнена отправка уведомлений",
        ),
    )


@api_bp.route("/task/<int:task_id>/run/<int:task_run_seq>/logs")
def task_run_logs(task_id: int, task_run_seq: int) -> Response:
    return jsonify(
        [
            obj.to_dict()
            for obj in get_task_run(task_id, task_run_seq).logs.order_by(TaskRunLog.id)
        ]
    )


@api_bp.route("/task/<int:task_id>/run/last/logs")
def task_run_logs_last(task_id: int) -> Response:
    task = get_task(task_id)
    task_run: TaskRun | None = task.get_last_run()
    if not task_run:
        abort(404)
    return task_run_logs(task_id, task_run.seq)


@api_bp.route("/notifications")
def notifications() -> Response:
    items: list[dict[str, Any]] = []

    for obj in Notification.select().order_by(Notification.id):
        data: dict[str, Any] = obj.to_dict()

        # Добавление task_run как объект, а не идентификатор
        if obj.task_run:
            data["task_run"] = obj.task_run.to_dict()

        items.append(data)

    return jsonify(items)


@api_bp.route("/notification/create", methods=["POST"])
def notification_create() -> Response:
    data: dict[str, Any] = request.json

    notification = Notification.add(
        task_run=None,
        name=data["name"],
        text=data["text"],
        kind=NotificationKindEnum(data["kind"]),
    )
    return jsonify(
        prepare_response(
            status=StatusEnum.OK,
            text=f"Создано уведомление #{notification.id}",
            result=[notification.to_dict()],
        ),
    )


@api_bp.route("/notifications/get-number-of-unsent")
def notifications_get_number_of_unsent() -> Response:
    return jsonify(
        prepare_response(
            status=StatusEnum.OK,
            result=[dict(number=len(Notification.get_unsent()))],
        ),
    )


@api_bp.route("/notifications/all/do-stop", methods=["POST"])
def notifications_all_do_stop() -> Response:
    found = False
    for obj in Notification.get_unsent():
        # Если уведомление было отправлено или отменено
        if not obj.is_ready():
            continue

        found = True
        obj.cancel()

    return jsonify(
        prepare_response(
            status=StatusEnum.OK,
            text=(
                "Неотправленные уведомления были отменены"
                if found
                else "Неотправленных уведомлений не было найдено"
            ),
        ),
    )


@api_bp.route("/notification/<int:notification_id>/do-stop", methods=["POST"])
def notification_do_stop(notification_id: int) -> Response:
    notification = get_notification(notification_id)
    if notification.is_ready():
        notification.cancel()
        status = StatusEnum.OK
        text = f"Уведомление #{notification_id} было отменено"
    else:
        if notification.sending_date:
            status = StatusEnum.ERROR
            text = f"Невозможно отменить уведомление #{notification_id}: оно было отправлено"
        else:
            status = StatusEnum.OK
            text = f"Уведомление #{notification_id} уже было отменено"

    return jsonify(
        prepare_response(
            status=status,
            text=text,
        ),
    )


@api_bp.route("/cron/get-next-dates")
def cron_get_next_dates() -> Response:
    if "cron" not in request.args:
        raise BadRequest('Отсутствует параметр "cron"')

    cron: str = request.args["cron"]
    number: int = int(request.args.get("number", 5))

    status = StatusEnum.OK
    text = None
    try:
        it = get_scheduled_date_generator(cron)
        result = [dict(date=next(it)) for _ in range(number)]
    except Exception:
        status = StatusEnum.ERROR
        text = "Неправильный формат"
        result = None

    return jsonify(
        prepare_response(
            status=status,
            text=text,
            result=result,
        ),
    )
