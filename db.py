#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import enum
import time
from datetime import datetime
from typing import Any, Type, Iterable, Self

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

from config import DB_FILE_NAME


# SOURCE: https://github.com/gil9red/SimplePyScripts/blob/99b0761d0a69fb410f119aae0caa9edc000ce97f/shorten.py
def shorten(text: str, length: int = 30, placeholder: str = "...") -> str:
    if not text:
        return text

    if len(text) > length:
        text = text[: length - len(placeholder)] + placeholder
    return text


class NotDefinedParameterException(ValueError):
    def __init__(self, parameter_name: str):
        self.parameter_name = parameter_name
        text = f'Parameter "{self.parameter_name}" must be defined!'

        super().__init__(text)


# SOURCE: https://github.com/gil9red/telegram_notifications_bot/blob/5473d04dda61b0a066eb04c75e22a5e3e34c0f17/db.py#L50
class EnumField(CharField):
    """
    This class enable an Enum like field for Peewee
    """

    def __init__(self, choices: Type[enum.Enum], *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.choices: Type[enum.Enum] = choices
        self.max_length = 255

    def db_value(self, value: Any) -> Any:
        return value.value

    def python_value(self, value: Any) -> Any:
        type_value_enum = type(list(self.choices)[0].value)
        value_enum = type_value_enum(value)
        return self.choices(value_enum)


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


@enum.unique
class LogEnum(enum.StrEnum):
    Out = enum.auto()
    Err = enum.auto()


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
    description = TextField(null=True, default=None)
    is_enabled = BooleanField(default=True)

    @classmethod
    def get_by_name(cls, name: str) -> Self | None:
        if not name:
            raise NotDefinedParameterException("name")

        return cls.get_or_none(name=name)

    def get_actual_is_enabled(self) -> bool:
        return Task.get_by_id(self.id).is_enabled

    @classmethod
    def add(cls, name: str, command: str, description: str = None) -> Self:
        obj = cls.get_by_name(name)
        if obj:
            if command != obj.command or description != obj.description:
                obj.command = command
                obj.description = description
                obj.save()

        else:
            obj = cls.create(
                name=name,
                command=command,
                description=description,
            )
        return obj

    def set_enabled(self, value: bool):
        self.is_enabled = value
        self.save()

    def add_run(self) -> "TaskRun":
        run = TaskRun.create(
            task=self,
            command=self.command,
        )

        return run

    def get_runs_by(self, statuses: list[TaskStatusEnum]) -> list["TaskRun"]:
        return list(
            self.runs
            .where(
                TaskRun.status.in_(statuses),
            )
            .order_by(TaskRun.create_date)
        )


class TaskRun(BaseModel):
    task = ForeignKeyField(Task, on_delete="CASCADE", backref="runs")
    command = TextField()
    status = EnumField(choices=TaskStatusEnum, default=TaskStatusEnum.Pending)
    process_id = IntegerField(null=True)
    process_return_code = IntegerField(null=True)
    create_date = DateTimeField(default=datetime.now)
    start_date = DateTimeField(null=True)
    finish_date = DateTimeField(null=True)

    def set_status(self, value: TaskStatusEnum):
        if self.status == value:
            return

        def raise_about_bad_status():
            raise ValueError(f"Нельзя изменить статус {self.status.value!r} в {value!r}")

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
                if self.status not in [TaskStatusEnum.Pending, TaskStatusEnum.Running]:
                    raise_about_bad_status()

                self.finish_date = datetime.now()

        self.status = value

        self.save()

    def set_process_id(self, value: int):
        self.process_id = value
        self.save()

    def get_actual_status(self) -> TaskStatusEnum:
        return TaskRun.get_by_id(self.id).status

    def add_log(self, text: str, kind: LogEnum) -> "TaskRunLog":
        return TaskRunLog.create(
            task_run=self,
            text=text,
            kind=kind,
        )

    def add_log_out(self, text: str) -> "TaskRunLog":
        return self.add_log(text=text, kind=LogEnum.Out)

    def add_log_err(self, text: str) -> "TaskRunLog":
        return self.add_log(text=text, kind=LogEnum.Err)


class TaskRunLog(BaseModel):
    task_run = ForeignKeyField(TaskRun, on_delete="CASCADE", backref="logs")
    text = TextField()
    kind = EnumField(choices=LogEnum)
    date = DateTimeField(default=datetime.now)


db.connect()
db.create_tables(BaseModel.get_inherited_models())


# Задержка в 50мс, чтобы дать время на запуск SqliteQueueDatabase и создание таблиц
# Т.к. в SqliteQueueDatabase запросы на чтение выполняются сразу, а на запись попадают в очередь
time.sleep(0.050)


if __name__ == "__main__":
    BaseModel.print_count_of_tables()
