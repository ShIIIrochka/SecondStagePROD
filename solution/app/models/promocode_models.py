# -*- coding: utf-8 -*-

# mypy: ignore-errors
# ruff: noqa

import enum
from datetime import datetime
from typing import Optional, List, Any
import uuid
from urllib.parse import urlparse

from sqlmodel import Field, SQLModel, Relationship, Enum, Column, AutoString
from pydantic import model_validator

from app.models.link_models import ActivatePromoByUser, Likes


class PromoMode(str, enum.Enum):
    COMMON = "COMMON"
    UNIQUE = "UNIQUE"


class PromoBase(SQLModel):
    """
    Общие свойства
    """

    description: str = Field(min_length=10, max_length=300, nullable=False)
    image_url: Optional[str] = Field(
        default=None, max_length=350, nullable=True, sa_type=AutoString
    )

    @model_validator(mode="after")
    @classmethod
    def validate_url(cls, promo):
        if promo.image_url and not (
            (urlparse(promo.image_url)).scheme
            and (urlparse(promo.image_url)).netloc
        ):
            raise ValueError
        return promo


class Target(SQLModel):
    """
    Настройки таргетирования промокодов
    """

    age_from: Optional[int] = Field(default=None, nullable=True, ge=0, le=100)
    age_until: Optional[int] = Field(default=None, nullable=True, ge=0, le=100)
    country: Optional[str] = Field(default=None, max_length=2, nullable=True)
    categories: Optional[List[str]] = Field(default=None, nullable=True)

    @model_validator(mode="before")
    @classmethod
    def validate_age(cls, values):
        age_from = values.get("age_from")
        age_until = values.get("age_until")

        if (
            age_from is not None
            and age_until is not None
            and age_from > age_until
        ):
            raise ValueError(
                "age_from must be less than or equal to age_until"
            )
        if values.get("categories") == [""]:
            raise ValueError("не те категории")
        return values


class PromoCreate(PromoBase):
    active_from: Optional[str] = Field(default=None, nullable=True)
    active_until: Optional[str] = Field(default=None, nullable=True)
    mode: Optional[PromoMode] = Field(sa_column=Column(Enum(PromoMode)))
    max_count: int = Field(nullable=False)
    promo_common: Optional[str] = Field(
        default=None, max_length=30, nullable=True
    )
    promo_unique: Optional[List[str]] = Field(
        default=None, max_length=5000, nullable=True
    )
    target: Target

    @model_validator(mode="after")
    @classmethod
    def validate_max_count(cls, promocode):
        if (promocode.mode == PromoMode.UNIQUE) and (promocode.max_count != 1):
            raise ValueError
        return promocode


class PromoUpdate(SQLModel):
    description: Optional[str] = Field(
        default=None, min_length=10, max_length=300, nullable=True
    )
    image_url: Optional[str] = Field(
        default=None, max_length=350, nullable=True, sa_type=AutoString
    )
    target: Optional[Target] = Field(nullable=True, default=None)
    active_from: Optional[str] = Field(nullable=True, default=None)
    active_until: Optional[str] = Field(nullable=True, default=None)
    max_count: Optional[int] = Field(nullable=True, default=None)
    mode: Optional[PromoMode] = Field(default=None, nullable=True)

    @model_validator(mode="after")
    @classmethod
    def validate_max_count(cls, promocode):
        if (promocode.mode == PromoMode.UNIQUE) and (promocode.max_count != 1):
            raise ValueError
        return promocode

    @model_validator(mode="after")
    @classmethod
    def validate_url(cls, promo):
        if promo.image_url and not (
            (urlparse(promo.image_url)).scheme
            and (urlparse(promo.image_url).netloc)
        ):
            raise ValueError
        return promo


class PromoForUser(PromoBase):
    promo_id: uuid.UUID
    company_id: uuid.UUID
    company_name: str
    active: bool = True
    is_activated_by_user: bool
    like_count: int
    is_liked_by_user: int
    comment_count: int


class PromoReadOnly(PromoBase):
    target: Target
    max_count: int = Field(nullable=False)
    active_from: Optional[str] = Field(default=None, nullable=True)
    active_until: Optional[str] = Field(default=None, nullable=True)
    mode: PromoMode = Field(sa_column=Column(Enum(PromoMode)))
    promo_common: Optional[str] = Field(
        default=None, max_length=30, nullable=True
    )
    promo_unique: Optional[List[str]] = Field(
        default=None, max_length=5000, nullable=True
    )
    promo_id: uuid.UUID
    company_id: uuid.UUID
    company_name: str
    like_count: int
    used_count: int
    active: bool


class Categories(SQLModel, table=True):
    """
    Категории для таргетирования промокодов
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(nullable=False)
    promo_id: uuid.UUID = Field(foreign_key="promocodes.id")
    promocode: "Promocodes" = Relationship(back_populates="categories")


class PromoTargetSettings(SQLModel):
    """
    Свойства купонов для таргетирования
    """

    age_from: Optional[int] = Field(default=None, nullable=True, ge=0, le=100)
    age_until: Optional[int] = Field(default=None, nullable=True, ge=0, le=100)
    country: Optional[str] = Field(default=None, max_length=2, nullable=True)


class PromoUnique(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(nullable=False)
    promo_id: uuid.UUID = Field(foreign_key="promocodes.id")
    promocode: "Promocodes" = Relationship(back_populates="promo_unique")


class Promocodes(PromoBase, PromoTargetSettings, table=True):
    """
    Модель в базе данных
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    active_from: Optional[str] = Field(nullable=True)
    active_until: Optional[str] = Field(nullable=True)
    max_count: int = Field(nullable=False)
    mode: str = Field(nullable=False)
    created_at: datetime = Field(default_factory=datetime.now)
    promo_common: Optional[str] = Field(max_length=30, nullable=True)

    promo_unique: Optional[List["PromoUnique"]] = Relationship(
        back_populates="promocode"
    )

    company_id: uuid.UUID = Field(foreign_key="companies.id")
    company: "Companies" = Relationship(back_populates="promos")

    categories: Optional[List["Categories"]] = Relationship(
        back_populates="promocode"
    )
    activations: Optional[List["Users"]] = Relationship(
        back_populates="activated_promocodes", link_model=ActivatePromoByUser
    )
    likes: Optional[List["Users"]] = Relationship(
        back_populates="liked_promocodes", link_model=Likes
    )
    comments: Optional[List["Comments"]] = Relationship(
        back_populates="promocode"
    )
