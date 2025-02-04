# mypy: ignore-errors
# -*- coding: utf-8 -*-

import uuid

from sqlmodel import Field, SQLModel


class ActivatePromoByUser(SQLModel, table=True):
    """
    Таблица связи для хранения информации о тех пользователях,
    кто применил промокод.
    """

    user_id: uuid.UUID = Field(primary_key=True, foreign_key="users.id")
    promocode_id: uuid.UUID = Field(
        primary_key=True, foreign_key="promocodes.id"
    )


class Likes(SQLModel, table=True):
    """
    Таблица связи для хранения лайков.
    """

    user_id: uuid.UUID = Field(primary_key=True, foreign_key="users.id")
    promocode_id: uuid.UUID = Field(
        primary_key=True, foreign_key="promocodes.id"
    )
