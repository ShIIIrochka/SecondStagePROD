# -*- coding: utf-8 -*-

from typing import Union, Annotated
from icecream import ic

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from app.services import get_company_by_email, create_company, authenticate
from app.models import Companies, CompanyCreate, CompanyAuth
from app.api import SessionDep
from app.utils import password_validator, generate_access_token
from app.core.db import redis_client

router = APIRouter(prefix="/business", tags=["B2B"])


@router.post("/auth/sign-up", response_model=None)
async def register_company(
    session: SessionDep, company_in: CompanyCreate
) -> Union[JSONResponse, HTTPException]:
    """
    Создание новой компании.

    Проверяет, существует ли уже компания с указанным email.
    Если нет, создаёт новую компанию, хэширует пароль и
    возвращает токен доступа и идентификатор компании.

    :param session: Сессия базы данных.
    :param company_in: Данные для регистрации компании.

    :returns: Ответ с токеном доступа и идентификатором компании.
    """
    company: Companies | None = await get_company_by_email(
        session=session, email=company_in.email
    )
    if company:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Такой email уже зарегистрирован.",
        )

    # Валидация пароля
    try:
        await password_validator(password=company_in.password)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректные данные пароля.",
        )

    # Создание новой компании
    company = await create_company(session=session, company_create=company_in)

    # Генерация токена доступа
    token = await generate_access_token(object=company, type="company")  # type: ignore

    return JSONResponse(
        content={"token": token, "company_id": str(company.id)},
        headers={"Content-Type": "application/json"},
        status_code=status.HTTP_200_OK,
    )


@router.post("/auth/sign-in", response_model=None)
async def auth_company(
    *,
    session: SessionDep,
    company_in: CompanyAuth,
) -> Union[JSONResponse, HTTPException]:
    """
    Аутентификация компании.

    Проверяет, существует ли компания с указанным email и
    соответствует ли введённый пароль. Если аутентификация успешна,
    возвращает токен доступа и идентификатор компании.

    :param session: Сессия базы данных.
    :param company_in: Данные для аутентификации компании.

    Returns:
        JSONResponse: Ответ с токеном доступа и идентификатором компании.
        HTTPException: Исключение, если email или пароль неверны или произошла
        ошибка.
    """
    ic(company_in)
    company: Companies | None = await get_company_by_email(
        session=session, email=company_in.email
    )
    ic(company)
    if not company or not await authenticate(
        session=session,
        email=company_in.email,
        password=company_in.password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль.",
        )

    if redis_client.exists(f"whitelist:{company[0].id}") == 1:
        redis_client.delete(f"whitelist:{company[0].id}")

    token: str = await generate_access_token(  # type: ignore
        object=company[0], type="company"
    )
    redis_client.set(f"whitelist:{company[0].id}", token, ex=3600)

    return JSONResponse(
        content={"token": token},
        headers={"Content-Type": "application/json"},
        status_code=status.HTTP_200_OK,
    )


@router.post("/token")
async def login_for_access_token(
    *,
    session: SessionDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    """
    Аутентификация компании.
    """
    company_in = CompanyAuth(
        email=form_data.username, password=form_data.password
    )
    ic(company_in)
    company: Companies | None = await get_company_by_email(
        session=session, email=company_in.email
    )
    ic(company)
    if not company or not await authenticate(
        session=session,
        email=company_in.email,
        password=company_in.password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token: str = await generate_access_token(object=company[0], type="company")  # type: ignore
    ic(token)
    return token
