# -*- coding: utf-8 -*-

# mypy: ignore-errors
# ruff: noqa

from typing import Optional, List, Any
import uuid
from urllib.parse import urlparse

from pydantic import EmailStr, model_validator
from sqlmodel import Field, SQLModel, Relationship, AutoString

from app.models.link_models import ActivatePromoByUser, Likes


class UserTargetSettings(SQLModel):
    """Свойства пользователя для таргетирования."""

    age: int = Field(ge=0, le=100, default=0, nullable=False)
    country: str = Field(max_length=2, nullable=False, default=None)


class Author(SQLModel):
    """
    Поля пользователя как автора
    """

    name: str = Field(min_length=1, max_length=100, nullable=False)
    surname: str = Field(min_length=1, max_length=120, nullable=False)
    avatar_url: Optional[str] = Field(
        max_length=350, nullable=True, default=None, sa_type=AutoString
    )

    @model_validator(mode="after")
    @classmethod
    def validate_url(cls, user):
        if user.avatar_url == "":
            raise ValueError

        if user.avatar_url and not (
            (urlparse(user.avatar_url)).scheme
            and (urlparse(user.avatar_url)).netloc
        ):
            raise ValueError
        return user


class UserBase(SQLModel):
    """Общие свойства пользователя."""

    name: str = Field(min_length=1, max_length=100, nullable=False)
    surname: str = Field(min_length=1, max_length=120, nullable=False)
    email: EmailStr = Field(
        min_length=8, max_length=120, nullable=False, unique=True
    )
    avatar_url: Optional[str] = Field(
        max_length=350, nullable=True, default=None, sa_type=AutoString
    )
    password: str = Field(min_length=8, max_length=60, nullable=False)

    @model_validator(mode="after")
    @classmethod
    def validate_url(cls, user):
        if user.avatar_url == "":
            raise ValueError

        if user.avatar_url and not (
            (urlparse(user.avatar_url)).scheme
            and (urlparse(user.avatar_url)).netloc
        ):
            raise ValueError
        return user


class UserCreate(UserBase):
    """Свойства для создания пользователя через API."""

    other: UserTargetSettings


class UserAuth(SQLModel):
    """
    Класс для аутентификации пользователя
    """

    email: EmailStr = Field(
        min_length=8, max_length=120, nullable=False, unique=True
    )
    password: str = Field(min_length=8, max_length=60, nullable=False)


class Profile(UserBase):
    """
    Профиль пользователя
    """

    other: UserTargetSettings


class UserUpdate(SQLModel):
    """Свойства для обновления пользователя, все поля необязательны."""

    name: Optional[str] = Field(
        min_length=1, max_length=100, nullable=True, default=None
    )
    surname: Optional[str] = Field(
        min_length=1, max_length=120, nullable=True, default=None
    )
    email: Optional[EmailStr] = Field(
        min_length=8, max_length=120, nullable=True, default=None, unique=True
    )
    avatar_url: Optional[str] = Field(
        max_length=350, nullable=True, default=None, sa_type=AutoString
    )
    password: Optional[str] = Field(
        min_length=8, max_length=60, nullable=True, default=None
    )

    @model_validator(mode="after")
    @classmethod
    def validate_url(cls, user):
        if user.avatar_url == "":
            raise ValueError

        if user.avatar_url and not (
            (urlparse(user.avatar_url)).scheme
            and (urlparse(user.avatar_url)).netloc
        ):
            raise ValueError
        return user


class UserPublic(UserBase, UserTargetSettings):
    """
    Свойства для возврата данных пользователя через API, id всегда обязателен.
    """

    id: uuid.UUID


class Users(UserBase, UserTargetSettings, table=True):
    """Модель пользователя в базе данных."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    comments: Optional[List["Comments"]] = Relationship(
        back_populates="author"
    )
    activated_promocodes: Optional[List["Promocodes"]] = Relationship(
        back_populates="activations", link_model=ActivatePromoByUser
    )
    liked_promocodes: Optional[List["Promocodes"]] = Relationship(
        back_populates="likes", link_model=Likes
    )
