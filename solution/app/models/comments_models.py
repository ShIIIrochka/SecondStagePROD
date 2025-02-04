# -*- coding: utf-8 -*-

# ruff: noqa

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel, Relationship

from app.models import Author


class CommentView(SQLModel):
    id: uuid.UUID
    text: str = Field(nullable=False, min_length=10, max_length=1000)
    author: Author
    date: datetime = Field(default_factory=datetime.now)


class Comments(SQLModel, table=True):
    """Комментарии к промокодам"""

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        unique=True,
        nullable=False,
        primary_key=True,
    )
    author_id: uuid.UUID = Field(foreign_key="users.id")
    text: str = Field(nullable=False, min_length=10, max_length=1000)
    created_at: datetime = Field(default_factory=datetime.now)
    promocode_id: uuid.UUID = Field(foreign_key="promocodes.id")
    author: "Users" = Relationship(back_populates="comments")  # type: ignore
    promocode: "Promocodes" = Relationship(back_populates="comments")  # type: ignore
