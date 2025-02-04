# -*- coding: utf-8 -*-

from typing import Union
from uuid import UUID

from sqlalchemy.future import select
from sqlmodel import Session

from app.api.deps import SessionDep
from app.core.db import engine
from app.core import get_password_hash, verify_password
from app.models import Companies, CompanyCreate
from app.core.security import security_companies


async def get_company_by_email(
    *, session: Session, email: str
) -> Companies | None:
    """
    Получение компании по email.

    :param session: Сессия базы данных.
    :param email: Email компании.
    :return: Объект компании или None, если компания не найдена.
    """
    statement = select(Companies).where(Companies.email == email)
    session_company = (session.exec(statement)).first()
    return session_company


@security_companies.set_subject_getter
def get_company_by_id(id: UUID) -> Companies | None:
    """
    Получение компании по email.

    :param session: Сессия базы данных.
    :param id: Id компании.
    :return: Объект компании или None, если компания не найдена.
    """
    statement = select(Companies).where(Companies.id == id)
    session_company = (SessionDep(engine).exec(statement)).first()
    return session_company


async def create_company(
    *, session: Session, company_create: CompanyCreate
) -> Companies:
    """
    Создание новой компании в базе данных.

    :param session: Сессия базы данных.
    :param company_create: Данные для создания компании.
    :return: Объект созданной компании.
    """
    db_obj: Companies = Companies.model_validate(
        company_create,
        update={"password": await get_password_hash(company_create.password)},
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


async def authenticate(
    *, session: Session, email: str, password: str
) -> Union[Companies, None]:
    db_obj: Companies | None = await get_company_by_email(
        session=session, email=email
    )
    if not db_obj:
        return None
    if not await verify_password(password, db_obj[0].password):
        return None
    return db_obj
