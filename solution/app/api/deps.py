# -*- coding: utf-8 -*-

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session
from fastapi.security import OAuth2PasswordBearer

from app.core.db import engine


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/business/token")


async def get_db() -> AsyncGenerator[Session, None, None]:  # type: ignore
    with Session(engine) as session:
        yield session


SessionDep: Annotated[Session, Depends(get_db)] = Annotated[
    Session, Depends(get_db)
]
