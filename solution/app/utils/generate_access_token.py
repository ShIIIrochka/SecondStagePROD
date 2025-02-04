# -*- coding: utf-8 -*-

from typing import Any, Literal
from datetime import timedelta


from app.core import settings
from app.core.security import security_companies, security_users


async def generate_access_token(
    object: Any, type: Literal["user", "company"]
) -> str:
    """Генерация токена доступа."""

    if type == "user":
        security = security_users
    elif type == "company":
        security = security_companies
    else:
        raise ValueError

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE)
    return security.create_access_token(
        uid=str(object.id), expiry=access_token_expires
    )
