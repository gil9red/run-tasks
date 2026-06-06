#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


from functools import reduce
from dataclasses import dataclass, field
from http import HTTPStatus
from operator import or_
from typing import Self, Any, Callable

from flask import Blueprint, Request, Response, jsonify, request, abort
from werkzeug.exceptions import BadRequest

from peewee import Model, Field, Expression, SQL, ColumnBase, ModelSelect, JOIN, fn
from playhouse.shortcuts import model_to_dict

from querystring_parser import parser

from run_tasks.app_web.config import API_PAGE_LENGTH_DEFAULT
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
        allowed_columns: list[str | Field],
        default_order: Expression,
    ) -> Self:
        allowed_columns: list[str] = [
            field if isinstance(field, str) else field.name for field in allowed_columns
        ]

        nested_args: dict[str, Any] = parser.parse(
            request.query_string.decode("utf-8"),
            normalized=True,
        )

        draw = int(nested_args.get("draw", 1))
        start = int(nested_args.get("start", 0))
        length = int(nested_args.get("length", API_PAGE_LENGTH_DEFAULT))

        search_dict = nested_args.get("search", dict())
        search_value = search_dict.get("value", "").strip()

        order_list: list[Expression] = []

        orders = nested_args.get("order", dict())

        for order_data in orders:
            col_idx = order_data.get("column")  # Индекс колонки
            direction = order_data.get("dir", "asc")

            col_name = order_data.get("name")
            if not col_name:
                abort(
                    HTTPStatus.BAD_REQUEST,
                    description=f"Missing name for column index {col_idx}",
                )

            if col_name not in allowed_columns:
                abort(
                    HTTPStatus.FORBIDDEN,
                    description=f"Sorting by field '{col_name}' is forbidden",
                )

            field_obj: ColumnBase | None = None

            if "." in col_name:
                model_part, field_part = col_name.split(".", 1)
                model_part = model_part.upper()
                for m in models:
                    if m._meta.name.upper() == model_part:
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

        if not order_list:
            order_list.append(default_order)

        return cls(
            draw=draw,
            start=start,
            length=length,
            search_value=search_value,
            order_by=order_list,
        )


def prepare_datatables_response(
    query: ModelSelect,
    request: Request,
    models: list[type[Model]],
    allowed_columns: list[str | Field],
    search_fields: list[Field],
    default_order: Expression,
    to_dict: Callable[[Model], dict[str, Any]],
) -> Response:
    data_table_rq = DataTableRequest.from_request(
        request,
        models=models,
        allowed_columns=allowed_columns,
        default_order=default_order,
    )

    total_records: int = query.count()
    records_filtered: int = total_records
    items: list[dict[str, Any]] = []

    # Фильтрация, пагинация, сортировки имеют смысл только, если есть записи
    if total_records > 0:
        if data_table_rq.search_value and search_fields:
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
        items = [to_dict(obj) for obj in query.objects()]

    return jsonify(
        {
            "draw": data_table_rq.draw,
            "recordsTotal": total_records,
            "recordsFiltered": records_filtered,
            "data": items,
        }
    )


api_bp = Blueprint("api", __name__)


@api_bp.route("/tasks")
def tasks() -> Response:
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

    def to_dict(obj: Model) -> dict[str, Any]:
        return {
            **model_to_dict(obj, recurse=False),
            **{
                "url_path": obj.url_path,
                "number_of_runs": obj.db_number_of_runs,
                "last_started_run_seq": obj.db_last_started_run_seq,
                "last_started_run_start_date": obj.db_last_started_run_start_date,
                "next_scheduled_date": obj.db_next_scheduled_date,
                "last_work_status": obj.db_last_work_status,
            },
        }

    return prepare_datatables_response(
        query=query,
        request=request,
        models=[Task],
        allowed_columns=[
            Task.id,
            Task.name,
            Task.command,
            Task.description,
            Task.is_enabled,
            Task.cron,
            Task.is_infinite,
            "db_last_started_run_start_date",
            "db_number_of_runs",
            "db_last_started_run_seq",
            "db_next_scheduled_date",
        ],
        search_fields=[
            Task.name,
            Task.command,
            Task.description,
            Task.cron,
        ],
        default_order=Task.id.asc(),
        to_dict=to_dict,
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
            HTTPStatus.BAD_REQUEST,
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
    query = TaskRunLog.select().where(
        TaskRunLog.task_run.in_(TaskRun.select().where(TaskRun.task == task)),
    )

    return prepare_datatables_response(
        query=query,
        request=request,
        models=[TaskRunLog],
        allowed_columns=[
            TaskRunLog.id,
            TaskRunLog.task_run,
            TaskRunLog.text,
            TaskRunLog.kind,
            TaskRunLog.date,
        ],
        search_fields=[
            TaskRunLog.text,
            TaskRunLog.kind,
        ],
        default_order=TaskRunLog.id.asc(),
        to_dict=lambda obj: obj.to_dict(),
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
    return prepare_datatables_response(
        query=get_task(task_id).runs,
        request=request,
        models=[TaskRun],
        allowed_columns=[
            TaskRun.id,
            TaskRun.task,
            TaskRun.seq,
            TaskRun.command,
            TaskRun.status,
            TaskRun.stop_reason,
            TaskRun.process_id,
            TaskRun.process_return_code,
            TaskRun.create_date,
            TaskRun.start_date,
            TaskRun.finish_date,
            TaskRun.scheduled_date,
        ],
        search_fields=[
            TaskRun.command,
            TaskRun.status,
            TaskRun.stop_reason,
            TaskRun.process_id,
        ],
        default_order=TaskRun.id.asc(),
        to_dict=lambda obj: obj.to_dict(),
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
    task_run_seq: int | None = task.last_started_run_seq
    if not task_run_seq:
        abort(
            HTTPStatus.NOT_FOUND,
            description=f"Task with Id {task_id} has no runs started yet",
        )
    return task_run_get(task_id, task_run_seq)


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
    query = get_task_run(task_id, task_run_seq).logs.order_by(TaskRunLog.id)

    # TODO: Совпадает с task /logs
    return prepare_datatables_response(
        query=query,
        request=request,
        models=[TaskRunLog],
        allowed_columns=[
            TaskRunLog.id,
            # TaskRunLog.task_run,  # TODO: Не нужно
            TaskRunLog.text,
            TaskRunLog.kind,
            TaskRunLog.date,
        ],
        search_fields=[
            TaskRunLog.text,
            TaskRunLog.kind,
        ],
        default_order=TaskRunLog.id.asc(),
        to_dict=lambda obj: obj.to_dict(),
    )


@api_bp.route("/task/<int:task_id>/run/last/logs")
def task_run_logs_last(task_id: int) -> Response:
    task: Task = get_task(task_id)
    task_run_seq: int | None = task.last_started_run_seq
    if not task_run_seq:
        # TODO: Дублирует
        # TODO: По другому вытаскивать draw из запроса
        data_table_rq = DataTableRequest.from_request(
            request,
            models=[TaskRunLog],
            allowed_columns=[
                TaskRunLog.id,
                TaskRunLog.text,
                TaskRunLog.kind,
                TaskRunLog.date,
            ],
            default_order=TaskRunLog.id.asc(),
        )
        return jsonify(
            {
                "draw": data_table_rq.draw,
                "recordsTotal": 0,
                "recordsFiltered": 0,
                "data": [],
            }
        )

    return task_run_logs(task_id, task_run_seq)


@api_bp.route("/notifications")
def notifications() -> Response:
    def to_dict(obj: Notification) -> dict[str, Any]:
        data: dict[str, Any] = obj.to_dict()

        # Добавление task_run как объект, а не идентификатор
        if obj.task_run:
            data["task_run"] = obj.task_run.to_dict()

        return data

    query = Notification.select().join(TaskRun, join_type=JOIN.LEFT_OUTER)

    return prepare_datatables_response(
        query=query,
        request=request,
        models=[Notification, TaskRun],
        allowed_columns=[
            Notification.id,
            Notification.name,
            Notification.text,
            Notification.kind,
            Notification.append_date,
            Notification.sending_date,
            Notification.canceling_date,
            "TaskRun.id",
            "TaskRun.seq",
        ],
        search_fields=[
            Notification.name,
            Notification.text,
            Notification.kind,
        ],
        default_order=Notification.id.asc(),
        to_dict=to_dict,
    )


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
