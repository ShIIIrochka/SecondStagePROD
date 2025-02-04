# -*- coding: utf-8 -*-

from authx import AuthX, AuthXConfig
from passlib.context import CryptContext

from app.core import settings  # type: ignore
from app.models import Companies

pwd_context: CryptContext = CryptContext(schemes=["bcrypt"], deprecated="auto")

config: AuthXConfig = AuthXConfig(
    JWT_ALGORITHM=settings.JWT_ALGORITHM,
    JWT_SECRET_KEY=settings.RANDOM_SECRET,
    JWT_TOKEN_LOCATION=settings.JWT_TOKEN_LOCATION,
    JWT_HEADER_TYPE=settings.JWT_HEADER_TYPE,
    JWT_HEADER_NAME=settings.JWT_HEADER_NAME,
)
security_users: AuthX = AuthX(config=config)
security_companies: AuthX = AuthX(config=config, model=Companies)


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


async def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


"""
@security.set_subject_getter
def get_user_from_uid(uid: str) -> User:
    return User.parse_obj(FAKE_DB.get(uid, {}))
"""
