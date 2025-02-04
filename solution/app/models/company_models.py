# -*- coding: utf-8 -*-

# ruff: noqa

import uuid
from typing import List, Optional

from pydantic import EmailStr
from sqlmodel import Field, SQLModel, Relationship


class CompanyBase(SQLModel):
    email: EmailStr = Field(
        min_length=8, max_length=120, nullable=False, unique=True
    )
    password: str = Field(min_length=8, max_length=60, nullable=False)


class CompanyCreate(CompanyBase):
    name: str = Field(min_length=5, max_length=50, nullable=False, unique=True)


class CompanyAuth(CompanyBase):
    pass


class CompanyPublic(CompanyBase):
    id: uuid.UUID


class Companies(CompanyBase, table=True):
    name: str = Field(min_length=5, max_length=50, nullable=False)
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    promos: Optional[List["Promocodes"]] = Relationship(  # type: ignore
        back_populates="company"
    )
