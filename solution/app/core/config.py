# -*- coding: utf-8 -*-

import os
import uuid
from typing import Optional, Union, List
import logging

from pydantic import computed_field, PostgresDsn
from pydantic_core import MultiHostUrl
from pydantic_settings import SettingsConfigDict, BaseSettings


class Settings(BaseSettings):  # type: ignore
    model_config = SettingsConfigDict(env_file="../.env")

    DEBUG: bool = os.getenv("DEBUG") == "True"
    SERVER_ADRESS: Optional[str] = os.getenv("SERVER_ADRESS")
    SERVER_PORT: Optional[str] = os.getenv("SERVER_PORT")

    RANDOM_SECRET: str = os.getenv("RANDOM_SECRET", str(uuid.uuid4()))
    ACCESS_TOKEN_EXPIRE: int = 60 * 60 * 3  # Три часа
    JWT_ALGORITHM: str = "HS256"
    JWT_TOKEN_LOCATION: List[str] = ["headers"]
    JWT_HEADER_TYPE: str = "Bearer"
    JWT_HEADER_NAME: str = "Authorization"

    POSTGRES_JDBC_URL: Optional[str] = os.getenv("POSTGRES_JDBC_URL")
    POSTGRES_HOST: Optional[str] = os.getenv("POSTGRES_HOST")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_USER: Optional[str] = os.getenv("POSTGRES_USERNAME")
    POSTGRES_PASSWORD: Optional[str] = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_DB: Optional[str] = os.getenv("POSTGRES_DATABASE")

    REDIS_HOST: Optional[str] = os.getenv("REDIS_HOST")
    REDIS_PORT: str = os.getenv("REDIS_PORT", "6379")
    REDIS_USER: Optional[str] = os.getenv("REDIS_USERNAME")
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")

    @computed_field  # type: ignore
    def SQLALCHEMY_DATABASE_URI(self) -> Union[PostgresDsn, str]:
        if self.POSTGRES_HOST == "":
            return "sqlite:///local.db"
        logging.debug(self.POSTGRES_HOST)
        url: MultiHostUrl = MultiHostUrl.build(
            scheme="postgresql+psycopg2",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=int(self.POSTGRES_PORT),
            path=self.POSTGRES_DB,
        )
        return PostgresDsn(url)


settings = Settings()
