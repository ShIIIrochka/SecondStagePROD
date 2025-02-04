# -*- coding: utf-8 -*-

from typing import Any, Dict, Optional, List
from uuid import UUID

from fastapi import Query
from sqlmodel import select, Session

from app.api.deps import SessionDep
from app.services.promocode_services import PromoService
from app.models import (
    Users,
    UserUpdate,
    UserCreate,
    PromoForUser,
    Promocodes,
    Companies,
    ActivatePromoByUser,
    Likes,
    Comments,
    Categories,
)
from app.core import get_password_hash, verify_password
from app.core.db import engine
from app.core.security import security_users


async def create_user(session: Session, user_create: UserCreate) -> Users:
    """
    Создание нового пользователя в базе данных

    :param session: Сессия базы данных.
    :param user_create: Входные данные для создания юзера

    :returns: Объект Users в бд
    """

    db_obj: Users = Users.model_validate(
        user_create,
        update={
            "password": await get_password_hash(user_create.password),
            "age": user_create.other.age,
            "country": user_create.other.country,
        },
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


async def update_user(
    session: Session, db_user: Users, user_in: UserUpdate
) -> Users:
    """
    Обновление существующего пользователя в базе данных

    :param session: Сессия базы данных.
    :param db_user: Объект пользователя в бд
    :param user_in: Входные данные для редактирования пользователя

    :returns: Объект пользователя в бд
    """
    user_data: Dict[str, Any] = user_in.model_dump(exclude_unset=True)
    if "password" in user_data:
        user_data["password"] = await get_password_hash(
            user_data.pop("password")
        )
    db_user.sqlmodel_update(user_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


async def get_user_by_email(session: Session, email: str) -> Users:
    """
    Получение пользователя по email.

    :param session: Сессия базы данных.
    :param email: Email компании.

    :return: Объект пользователя или None, если он не найден.
    """
    statement = select(Users).where(Users.email == email)
    return (session.exec(statement)).first()


@security_users.set_subject_getter
def get_user_by_id(id: UUID) -> Optional[Users]:
    """
    Получение пользователя по id

    :param session: Сессия базы данных.
    :param id: Id пользователя

    :return: Объект пользователя или None, если он не найден
    """
    statement = select(Users).where(Users.id == id)
    session_company = (SessionDep(engine).exec(statement)).first()
    return session_company


async def authenticate(
    session: Session, email: str, password: str
) -> Optional[Users]:
    """
    Аутентификация пользователя по email и паролю.

    :param session: Сессия базы данных
    :param email: Email пользователя
    :param password: Пароль пользователя

    :return: Объект пользователя или None, если он не найден
    """
    db_user = await get_user_by_email(session=session, email=email)
    if db_user and await verify_password(password, db_user.password):
        return db_user
    return None


async def is_activated_by_user(
    session: Session, promo_id: UUID, user_id: UUID
) -> bool:
    """
    Проверка активирован ли промокод пользователем

    :param session: Сессия базы данных
    :param promo_id: Id промокода
    :param user_id: Id пользователя

    :returns: True, если активирован
    """
    activations: list[
        ActivatePromoByUser
    ] = await PromoService.get_activations(
        session=session, promocode_id=promo_id
    )
    for activation in activations:
        if activation.user_id == user_id:
            return True
    return False


async def is_liked_by_user(
    session: Session, promo_id: UUID, user_id: UUID
) -> bool:
    """
    Проверка лайкнут ли промокод пользователем

    :param session: Сессия базы данных
    :param promo_id: Id промокода
    :param user_id: Id пользователя

    :returns: True, если лайкнут
    """
    likes: Optional[List[Likes]] = await PromoService.get_likes(
        session=session, promocode_id=promo_id
    )
    if likes:
        for like in likes:
            if like.user_id == user_id:
                return True
    return False


async def get_promo_by_id(
    session: Session, promo_id: UUID, user_id: UUID
) -> PromoForUser:
    """
    Получение промокода по id для пользователя

    :param session: Сессия базы данных
    :param promo_id: Id промокода
    :param user_id: Id пользователя

    :returns: Объект PromoForUser
    """
    promocode: Optional[Promocodes] = await PromoService.get_promo_by_id(
        session=session, id=promo_id
    )
    if not promocode:
        raise ValueError

    company_name: str = session.exec(
        select(Companies.name).where(Companies.id == promocode.company_id)
    ).first()

    is_active: bool = await PromoService.is_active(
        session=session, promocode=promocode
    )

    is_activated_by_user_: bool = await is_activated_by_user(
        session=session, promo_id=promo_id, user_id=user_id
    )

    like_count: Optional[List[Likes]] = await PromoService.get_likes(
        session=session, promocode_id=promo_id
    )

    is_liked_by_user_: bool = await is_liked_by_user(
        session=session, promo_id=promo_id, user_id=user_id
    )

    comment_count: Optional[List[Comments]] = await PromoService.get_comments(
        session=session, promocode_id=promo_id
    )

    promo_for_user: PromoForUser = PromoForUser.model_validate(
        obj=promocode,
        update={
            "promo_id": promocode.id,
            "company_id": promocode.company_id,
            "company_name": company_name,
            "active": is_active,
            "is_activated_by_user": is_activated_by_user_,
            "like_count": len(like_count) if like_count else 0,
            "is_liked_by_user": is_liked_by_user_,
            "comment_count": len(comment_count) if comment_count else 0,
        },
    )

    return promo_for_user


async def user_feed(
    session: Session,
    user_in: Users,
    active: Optional[bool] = None,
    limit: int = Query(10, ge=0),
    offset: int = Query(0, ge=0),
    category: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """
    Получение ленты промокодов с пагинацией.

    :param session: Объект сессии базы данных.
    :param active: Будут возвращены промокоды с соответствующим значением поля
    active
    :param offset: Сдвиг начала на
    :param limit: Максимальное количество записей.
    :param category: Будут возвращены промокоды с указанной категорией.

    :returns: Словарь с количеством и списком промокодов.
    """

    query = select(Promocodes)

    if category:
        query = query.where(
            Promocodes.categories.any(Categories.name.ilike(category))  # type: ignore
        )

    # Сортировка по убыванию даты создания
    query = query.order_by(Promocodes.created_at.desc())  # type: ignore

    # Применение пагинации
    # query = query.offset(offset).limit(limit)
    results: List[Promocodes] = session.exec(query).all()

    promocodes: List[Dict[str, Any]] = []
    for promo in results:
        if promo.age_from and promo.age_from > user_in.age:
            continue

        if promo.age_until and promo.age_until < user_in.age:
            continue

        if promo.country and promo.country != user_in.country:
            continue

        if active is not None:
            if (
                await PromoService.is_active(session=session, promocode=promo)
                != active
            ):
                continue

        active_status = await PromoService.is_active(session, promo)
        activated_by_user: bool = await is_activated_by_user(
            session=session, promo_id=promo.id, user_id=user_in.id
        )
        likes: Optional[List[Likes]] = await PromoService.get_likes(
            session, promo.id
        )
        liked_by_user: bool = await is_liked_by_user(
            session=session, promo_id=promo.id, user_id=user_in.id
        )
        comments: Optional[List[Comments]] = await PromoService.get_comments(
            session=session, promocode_id=promo.id
        )
        promocodes.append(
            {
                "promo_id": str(promo.id),
                "company_id": str(promo.company_id),
                "company_name": promo.company.name,
                "description": promo.description,
                "image_url": promo.image_url,
                "active": active_status,
                "is_activated_by_user": activated_by_user,
                "like_count": len(likes) if likes is not None else 0,
                "is_liked_by_user": liked_by_user,
                "comment_count": len(comments) if comments is not None else 0,
            }
        )

    return {
        "x-total-count": len(promocodes),
        "promocodes": promocodes[offset : (limit + offset)],
    }


async def add_like(session: Session, promo_id: UUID, user_id: UUID) -> Likes:
    if not await PromoService.get_promo_by_id(session=session, id=promo_id):
        raise ValueError

    existing_like = session.exec(
        select(Likes).where(
            Likes.user_id == user_id, Likes.promocode_id == promo_id
        )
    ).first()

    if existing_like:
        return existing_like
    like: Likes = Likes(user_id=user_id, promocode_id=promo_id)
    session.add(like)
    session.commit()
    session.refresh(like)
    return like


async def delete_like(
    session: Session, promo_id: UUID, user_id: UUID
) -> Dict[str, str]:
    if not await PromoService.get_promo_by_id(session=session, id=promo_id):
        raise ValueError

    existing_like = session.exec(
        select(Likes).where(
            Likes.user_id == user_id, Likes.promocode_id == promo_id
        )
    ).first()

    if not existing_like:
        return {"status": "ok"}

    session.delete(existing_like)
    session.commit()
    return {"status": "ok"}


async def activate_promocode_by_user(
    session: Session, promo_id: UUID, user_in: Users
) -> Dict[str, str]:
    db_promo: Promocodes = await PromoService.get_promo_by_id(
        session=session, id=promo_id
    )

    if not db_promo:
        raise ValueError

    if not await PromoService.is_active(session=session, promocode=db_promo):
        raise KeyError

    if db_promo.age_from and db_promo.age_from > user_in.age:
        raise KeyError

    if db_promo.age_until and db_promo.age_until < user_in.age:
        raise KeyError

    if db_promo.country != user_in.country:
        raise KeyError

    activation: ActivatePromoByUser = ActivatePromoByUser(
        user_id=user_in.id, promocode_id=promo_id
    )
    session.add(activation)
    session.commit()
    session.refresh(activation)
    return {"promo": db_promo.description}


async def activate_promocode_history(
    session: Session,
    limit: int = Query(10, ge=0),
    offset: int = Query(0, ge=0),
):
    pass
