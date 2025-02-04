# -*- coding: utf-8 -*-

from typing import Any, Dict, List
from uuid import UUID

from fastapi import Query
from sqlmodel import select, Session

from app.services.promocode_services import PromoService
from app.models import (
    Users,
    Comments,
    Author,
)


async def add_comment(
    session: Session, promo_id: UUID, user: Users, text: str
) -> Dict[str, Any]:
    if not await PromoService.get_promo_by_id(session=session, id=promo_id):
        raise ValueError

    author: Author = Author.model_validate(obj=user)
    comment: Comments = Comments(
        author_id=user.id, text=text, promocode_id=promo_id
    )

    session.add(comment)
    session.commit()
    session.refresh(comment)

    comment_view: Dict[str, Any] = {
        "id": str(comment.id),
        "text": comment.text,
        "date": comment.created_at.isoformat(),
        "author": {
            "name": author.name,
            "surname": author.surname,
            "avatar_url": author.avatar_url,
        },
    }

    return comment_view


async def get_comment_by_promo_id(
    session: Session, promocode_id: UUID, comment_id: UUID
) -> Comments:
    """
    Получение комментария по id комментария и id промокда
    """
    if not await PromoService.get_promo_by_id(
        session=session, id=promocode_id
    ):
        raise ValueError
    return session.exec(
        select(Comments)
        .where(Comments.promocode_id == promocode_id)
        .where(Comments.id == comment_id)
    ).first()


async def update_comment(
    session: Session, promo_id: UUID, user: Users, comment_id: UUID, text: str
) -> Dict[str, Any]:
    """
    Редактировать текст комментария с данным айди.
    """
    comment: Comments = await get_comment_by_promo_id(
        session=session, promocode_id=promo_id, comment_id=comment_id
    )
    if not comment:
        raise ValueError
    if comment.author_id != user.id:
        raise KeyError

    comment_update: Dict[str, str] = {"text": text}
    comment.sqlmodel_update(comment_update)
    session.add(comment)
    session.commit()
    session.refresh(comment)

    author: Author = Author.model_validate(obj=user)

    comment_view: Dict[str, Any] = {
        "id": str(comment.id),
        "text": comment.text,
        "date": comment.created_at.isoformat(),
        "author": {
            "name": author.name,
            "surname": author.surname,
            "avatar_url": author.avatar_url,
        },
    }
    return comment_view


async def delete_comment(
    session: Session, promo_id: UUID, user: Users, comment_id: UUID
) -> Dict[str, str]:
    comment: Comments = await get_comment_by_promo_id(
        session=session, promocode_id=promo_id, comment_id=comment_id
    )
    if not comment:
        raise ValueError
    if comment.author_id != user.id:
        raise KeyError

    session.delete(comment)
    session.commit()
    return {"status": "ok"}


async def get_comments_with_pagination(
    session: Session,
    promocode_id: UUID,
    limit: int = Query(10, ge=0),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """
    Получение комментариев промокода с пагинацией
    :param session: Объект сессии базы данных.
    :param promocode_id: ID промокода.
    :param limit: Максимальное количество записей.
    :param offset: Сдвиг начала на

    :returns: Список view комментариев промокода.
    """
    if not await PromoService.get_promo_by_id(
        session=session, id=promocode_id
    ):
        raise ValueError
    query = (
        select(Comments)
        .where(Comments.promocode_id == promocode_id)
        .order_by(Comments.created_at.desc())  # type: ignore
    )
    x_total_count: int = len(session.exec(query).all())
    query = query.offset(offset).limit(limit)
    results: List[Comments] = session.exec(query).all()

    comments = [
        {
            "id": str(comment.id),
            "text": comment.text,
            "date": comment.created_at.isoformat(),
            "author": {
                "name": comment.author.name,
                "surname": comment.author.surname,
                "avatar_url": comment.author.avatar_url,
            },
        }
        for comment in results
    ]

    return {"x-total-count": x_total_count, "comments": comments}
