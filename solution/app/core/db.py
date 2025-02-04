# -*- coding: utf-8 -*-

from sqlmodel import SQLModel, create_engine
import redis  # type: ignore

from app.core.config import settings


redis_client: redis.Redis = redis.Redis(host=settings.REDIS_HOST)
metadata = SQLModel.metadata
engine = create_engine((settings.SQLALCHEMY_DATABASE_URI).unicode_string())


async def init_db() -> None:
    SQLModel.metadata.create_all(engine)
