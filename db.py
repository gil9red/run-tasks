#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import enum
import time
from datetime import datetime
from typing import Type, Iterable, Self, Optional

# pip install peewee
from peewee import (
    Model,
    TextField,
    ForeignKeyField,
    DateTimeField,
    BooleanField,
    CharField,
    IntegerField,
)
from playhouse.shortcuts import model_to_dict
from playhouse.sqliteq import SqliteQueueDatabase

from root_config import DB_FILE_NAME
from third_party.db_enum_field import EnumField
from third_party.shorten import shorten


class NotDefinedParameterException(ValueError):
    def __init__(self, parameter_name: str):
        self.parameter_name = parameter_name
        text = f'Parameter "{self.parameter_name}" must be defined!'

        super().__init__(text)


# This working with multithreading
# SOURCE: http://docs.peewee-orm.com/en/latest/peewee/playhouse.html#sqliteq
db = SqliteQueueDatabase(
    DB_FILE_NAME,
    pragmas={
        "foreign_keys": 1,
        "journal_mode": "wal",  # WAL-mode
        "cache_size": -1024 * 64,  # 64MB page-cache
    },
    use_gevent=False,  # Use the standard library "threading" module.
    autostart=True,
    queue_max_size=64,  # Max. # of pending writes that can accumulate.
    results_timeout=5.0,  # Max. time to wait for query to be executed.
)


@enum.unique
class TaskStatusEnum(enum.StrEnum):
    Pending = enum.auto()
    Running = enum.auto()
    Finished = enum.auto()
    Stopped = enum.auto()
    Unknown = enum.auto()
    Error = enum.auto()


@enum.unique
class LogKindEnum(enum.StrEnum):
    Out = enum.auto()
    Err = enum.auto()


@enum.unique
class NotificationKindEnum(enum.StrEnum):
    Email = enum.auto()
    Telegram = enum.auto()


class BaseModel(Model):
    class Meta:
        database = db

    def get_new(self) -> Self:
        return type(self).get(self._pk_expr())

    @classmethod
    def get_first(cls) -> Self:
        return cls.select().first()

    @classmethod
    def get_last(cls) -> Self:
        return cls.select().order_by(cls.id.desc()).first()

    @classmethod
    def get_inherited_models(cls) -> list[Type[Self]]:
        return sorted(cls.__subclasses__(), key=lambda x: x.__name__)

    @classmethod
    def print_count_of_tables(cls):
        items = []
        for sub_cls in cls.get_inherited_models():
            name = sub_cls.__name__
            count = sub_cls.select().count()
            items.append(f"{name}: {count}")

        print(", ".join(items))

    @classmethod
    def count(cls, filters: Iterable = None) -> int:
        query = cls.select()
        if filters:
            query = query.filter(*filters)
        return query.count()

    def to_dict(self) -> dict:
        return model_to_dict(self)

    def __str__(self):
        fields = []
        for k, field in self._meta.fields.items():
            v = getattr(self, k)

            if isinstance(field, (TextField, CharField)):
                if isinstance(v, enum.Enum):
                    v = v.value

                if v:
                    v = repr(shorten(v, length=30))

            elif isinstance(field, ForeignKeyField):
                k = f"{k}_id"
                if v:
                    v = v.id

            fields.append(f"{k}={v}")

        return self.__class__.__name__ + "(" + ", ".join(fields) + ")"


class Task(BaseModel):
    name = TextField(unique=True)
    command = TextField()
    description = TextField(null=True)
    is_enabled = BooleanField(default=True)
    cron = TextField(null=True)
    is_infinite = BooleanField(default=False)

    @classmethod
    def get_by_name(cls, name: str) -> Self | None:
        if not name:
            raise NotDefinedParameterException("name")

        return cls.get_or_none(name=name)

    def get_actual_is_enabled(self) -> bool:
        return Task.get_by_id(self.id).is_enabled

    @classmethod
    def add(
        cls,
        name: str,
        command: str,
        description: str = None,
        cron: str = None,
        is_infinite: bool = False,
    ) -> Self:
        obj = cls.get_by_name(name)
        if obj:
            return obj

        return cls.create(
            name=name,
            command=command,
            description=description,
            cron=cron,
            is_infinite=is_infinite,
        )

    def set_command(self, command: str):
        if self.command == command:
            return

        self.command = command
        self.save()

    def set_description(self, description: str):
        if self.description == description:
            return

        self.description = description
        self.save()

    def set_enabled(self, value: bool):
        if self.is_enabled == value:
            return

        self.is_enabled = value
        self.save()

    def set_is_infinite(self, value: bool):
        if self.is_infinite == value:
            return

        self.is_infinite = value
        self.save()

    # TODO: Надо ли?
    def get_last_scheduled_run(self) -> Optional["TaskRun"]:
        last_run: TaskRun | None = self.runs.order_by(
            TaskRun.create_date.desc()
        ).first()
        if not last_run or last_run.scheduled_date is None:
            return None

        return last_run

    def get_pending_run(self, scheduled_date: datetime = None) -> Optional["TaskRun"]:
        for run in self.get_runs_by([TaskStatusEnum.Pending]):
            if scheduled_date is None:
                if run.scheduled_date is None:
                    return run
            else:
                if run.scheduled_date is not None:
                    return run

        return None

    def add_or_get_run(self, scheduled_date: datetime = None) -> "TaskRun":
        # Ограничение количества запусков в ожидании, максимум 2: без запланированной даты и с ней
        # Возврат уже ранее добавленного запуска
        run = self.get_pending_run(scheduled_date)
        if not run:
            run = TaskRun.create(
                task=self,
                command=self.command,
                scheduled_date=scheduled_date,
            )
        return run

    def get_runs_by(self, statuses: list[TaskStatusEnum]) -> list["TaskRun"]:
        return list(
            self.runs.where(
                TaskRun.status.in_(statuses),
            ).order_by(TaskRun.create_date)
        )

    def get_current_run(self) -> Optional["TaskRun"]:
        items = self.get_runs_by([TaskStatusEnum.Running])
        return items[0] if items else None


class TaskRun(BaseModel):
    task = ForeignKeyField(Task, on_delete="CASCADE", backref="runs")
    command = TextField()
    status = EnumField(choices=TaskStatusEnum, default=TaskStatusEnum.Pending)
    process_id = IntegerField(null=True)
    process_return_code = IntegerField(null=True)
    create_date = DateTimeField(default=datetime.now)
    start_date = DateTimeField(null=True)
    finish_date = DateTimeField(null=True)
    scheduled_date = DateTimeField(null=True)

    def set_status(self, value: TaskStatusEnum):
        if value is None:
            raise ValueError(
                f"Нельзя изменить статус {self.status.value!r} в {value!r}"
            )

        if self.status == value:
            return

        def raise_about_bad_status():
            raise ValueError(
                f"Нельзя изменить статус {self.status.value!r} в {value.value!r}"
            )

        match value:
            case TaskStatusEnum.Pending:
                raise_about_bad_status()

            case TaskStatusEnum.Running:
                if self.status != TaskStatusEnum.Pending:
                    raise_about_bad_status()

                self.start_date = datetime.now()

            case TaskStatusEnum.Stopped:
                if self.status not in [TaskStatusEnum.Pending, TaskStatusEnum.Running]:
                    raise_about_bad_status()

            case TaskStatusEnum.Finished:
                if self.status != TaskStatusEnum.Running:
                    raise_about_bad_status()

                self.finish_date = datetime.now()

            case TaskStatusEnum.Unknown:
                if self.status != TaskStatusEnum.Running:
                    raise_about_bad_status()

            case TaskStatusEnum.Error:
                # Ignore
                pass

        self.status = value

        self.save()

    def set_error(self, error_text: str):
        self.set_status(TaskStatusEnum.Error)
        self.add_log_err(text=error_text)

    # TODO: в тесты
    def is_scheduled_date_has_arrived(self) -> bool:
        if self.scheduled_date is None:
            return False

        return self.scheduled_date <= datetime.now()

    def set_process_id(self, value: int):
        self.process_id = value
        self.save()

    def get_actual_status(self) -> TaskStatusEnum:
        return TaskRun.get_by_id(self.id).status

    def add_log(self, text: str, kind: LogKindEnum) -> "TaskRunLog":
        return TaskRunLog.create(
            task_run=self,
            text=text,
            kind=kind,
        )

    def add_log_out(self, text: str) -> "TaskRunLog":
        return self.add_log(text=text, kind=LogKindEnum.Out)

    def add_log_err(self, text: str) -> "TaskRunLog":
        return self.add_log(text=text, kind=LogKindEnum.Err)


class TaskRunLog(BaseModel):
    task_run = ForeignKeyField(TaskRun, on_delete="CASCADE", backref="logs")
    text = TextField()
    kind = EnumField(choices=LogKindEnum)
    date = DateTimeField(default=datetime.now)


class Notification(BaseModel):
    task_run = ForeignKeyField(TaskRun, on_delete="CASCADE", backref="notifications")
    name = TextField()
    text = TextField()
    kind = EnumField(choices=NotificationKindEnum)
    append_date = DateTimeField(default=datetime.now)
    sending_date = DateTimeField(null=True)

    @classmethod
    def add(
        cls,
        task_run: TaskRun,
        name: str,
        text: str,
        kind: NotificationKindEnum,
    ) -> Self:
        return cls.create(
            task_run=task_run,
            name=name,
            text=text,
            kind=kind,
        )

    @classmethod
    def get_unsent(cls) -> list[Self]:
        """
        Функция, что возвращает неотправленные уведомления
        """

        return list(cls.select().where(cls.sending_date.is_null(True)).order_by(cls.append_date))

    def set_as_send(self):
        """
        Функция устанавливает дату отправки и сохраняет ее
        """

        if not self.sending_date:
            self.sending_date = datetime.now()
            self.save()


db.connect()
db.create_tables(BaseModel.get_inherited_models())


# Задержка в 50мс, чтобы дать время на запуск SqliteQueueDatabase и создание таблиц
# Т.к. в SqliteQueueDatabase запросы на чтение выполняются сразу, а на запись попадают в очередь
time.sleep(0.050)


if __name__ == "__main__":
    BaseModel.print_count_of_tables()
