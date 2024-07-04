#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


# SOURCE: http://docs.peewee-orm.com/en/latest/peewee/playhouse.html#schema-migrations


from playhouse.migrate import SqliteDatabase, SqliteMigrator, migrate
from db import DB_FILE_NAME, EnumField, TaskRun, StopReasonEnum


db = SqliteDatabase(DB_FILE_NAME)
migrator = SqliteMigrator(db)


with db.atomic():
    migrate(
        migrator.add_column(
            TaskRun._meta.table_name,
            "stop_reason",
            EnumField(choices=StopReasonEnum, null=True),
        ),
    )
