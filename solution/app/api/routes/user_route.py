# -*- coding: utf-8 -*-

from typing import Union, Optional, List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status, Depends, Query, Body
from fastapi.responses import JSONResponse
from icecream import ic
from authx.exceptions import JWTDecodeError

from app.services import create_user, update_user
from app.services.user_services import (
    authenticate,
    get_promo_by_id,
    get_user_by_email,
    user_feed,
    add_like,
    delete_like,
    activate_promocode_by_user,
)
from app.services.comment_services import (
    add_comment,
    update_comment,
    delete_comment,
    get_comment_by_promo_id,
    get_comments_with_pagination,
)
from app.models import (
    UserCreate,
    Users,
    UserAuth,
    Profile,
    UserTargetSettings,
    PromoForUser,
    UserUpdate,
    Likes,
    CommentView,
    Comments,
    Author,
)
from app.api import SessionDep
from app.core.db import redis_client
from app.utils import password_validator, generate_access_token
from app.core.security import security_users


router = APIRouter(prefix="/user", tags=["B2C"])


@router.post("/auth/sign-up", response_model=None)
async def register_user(
    session: SessionDep, user_in: UserCreate
) -> Union[JSONResponse, HTTPException]:
    """
    Создание нового пользователя.
    Проверяет, существует ли пользователь с указанным email.
    Если нет, создаёт нового пользователя и возвращает токен доступа.

    :param session: Сессия базы данных.
    :param user_in: Данные для создания пользователя.

    :returns: JSONResponse: Ответ с токеном доступа.
    """
    ic(user_in)
    user: Users | None = await get_user_by_email(
        session=session, email=user_in.email
    )
    if user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Такой email уже зарегистрирован.",
        )

    # Валидация пароля
    try:
        await password_validator(password=user_in.password)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректные данные пароля.",
        )

    # Создание нового пользователя
    user = await create_user(session=session, user_create=user_in)

    # Генерация токена доступа
    token = await generate_access_token(object=user, type="user")  # type: ignore

    return JSONResponse(
        content={"token": token},
        headers={"Content-Type": "application/json"},
        status_code=status.HTTP_200_OK,
    )


@router.post("/auth/sign-in", response_model=None)
async def auth_user(
    session: SessionDep,
    user_in: UserAuth,
) -> Union[JSONResponse, HTTPException]:
    """
    Аутентификация пользователя.
    Проверяет, существует ли пользователь с указанным email и правильный ли
    пароль.
    Если аутентификация успешна, возвращает токен доступа.

    :param session: Сессия базы данных.
    :param user_in: Данные для аутентификации пользователя.

    :returns: JSONResponse: Ответ с токеном доступа.
    """
    user: Users | None = await get_user_by_email(
        session=session, email=user_in.email
    )
    ic(user)
    if not user or not await authenticate(
        session=session, email=user_in.email, password=user_in.password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль.",
        )

    if redis_client.exists(f"whitelist:{user.id}") == 1:
        redis_client.delete(f"whitelist:{user.id}")

    # Генерация токена доступа
    token: str = await generate_access_token(user, type="user")  # type: ignore
    redis_client.set(f"whitelist:{user.id}", token, ex=3600)

    return JSONResponse(
        content={"token": token},
        headers={"Content-Type": "application/json"},
        status_code=status.HTTP_200_OK,
    )


@router.get(
    "/profile",
    response_model=Profile,
    dependencies=[Depends(security_users.access_token_required)],
)
async def get_profile(
    session: SessionDep,
    user_in: Users = Depends(security_users.get_current_subject),
):
    other: UserTargetSettings = UserTargetSettings(
        age=user_in.age, country=user_in.country
    )
    user: Profile = Profile.model_validate(
        obj=user_in,
        update={
            "other": other,
        },
    )

    return user


@router.patch(
    "/profile",
    response_model=Profile,
    dependencies=[Depends(security_users.access_token_required)],
)
async def update_profile(
    session: SessionDep,
    user_update: UserUpdate,
    user_in: Users = Depends(security_users.get_current_subject),
) -> Profile:
    db_user: Users = await get_user_by_email(
        session=session, email=user_in.email
    )
    user: Users = await update_user(
        session=session, db_user=db_user, user_in=user_update
    )

    other: UserTargetSettings = UserTargetSettings(
        age=user.age, country=user.country
    )
    profile: Profile = Profile.model_validate(
        obj=user,
        update={
            "other": other,
        },
    )
    ic(profile)
    return profile


@router.get(
    "/promo/{id}",
    response_model=PromoForUser,
    dependencies=[Depends(security_users.access_token_required)],
)
async def get_promocode(
    session: SessionDep,
    id: UUID,
    user_in: Users = Depends(security_users.get_current_subject),
) -> PromoForUser:
    try:
        if not user_in:
            raise JWTDecodeError
        promocode: PromoForUser = await get_promo_by_id(
            session=session, promo_id=id, user_id=user_in.id
        )
        return promocode
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Промокод не найден"
        )
    except JWTDecodeError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


@router.get(
    "/feed",
    response_model=None,
    dependencies=[Depends(security_users.access_token_required)],
)
async def feed(
    session: SessionDep,
    active: Optional[bool] = None,
    limit: int = Query(10, ge=0),
    offset: int = Query(0, ge=0),
    category: Optional[str] = Query(None),
    user_in: Users = Depends(security_users.get_current_subject),
) -> JSONResponse:
    result: Dict[str, Any] = await user_feed(
        session=session,
        active=active,
        limit=limit,
        offset=offset,
        category=category,
        user_in=user_in,
    )
    promocodes: Optional[List[Any]] = result.get("promocodes")
    ic(promocodes)
    return JSONResponse(
        content=promocodes,
        media_type="application/json",
        status_code=status.HTTP_200_OK,
        headers={"x-total-count": f"{result.get('x-total-count')}"},
    )


@router.post(
    "/promo/{id}/like",
    response_model=None,
    dependencies=[Depends(security_users.access_token_required)],
)
async def add_like_to_promo(
    session: SessionDep,
    id: UUID,
    user_in: Users = Depends(security_users.get_current_subject),
):
    ic(id)
    ic(user_in)
    try:
        like: Likes = await add_like(
            session=session, promo_id=id, user_id=user_in.id
        )
        ic(like)
        if like:
            return JSONResponse(
                content={"status": "ok"},
                status_code=status.HTTP_200_OK,
                headers={"Content-Type": "application/json"},
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Не нашев такого промокода",
        )


@router.delete(
    "/promo/{id}/like",
    response_model=None,
    dependencies=[Depends(security_users.access_token_required)],
)
async def delete_like_from_promo(
    session: SessionDep,
    id: UUID,
    user_in: Users = Depends(security_users.get_current_subject),
) -> JSONResponse:
    try:
        status_: Dict[str, str] = await delete_like(
            session=session, promo_id=id, user_id=user_in.id
        )
        return JSONResponse(
            content=status_,
            status_code=status.HTTP_200_OK,
            media_type="application/json",
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Не нашев такого промокода",
        )


@router.post(
    "/promo/{id}/comments",
    response_model=None,
    dependencies=[Depends(security_users.access_token_required)],
)
async def add_comment_to_promo(
    session: SessionDep,
    id: UUID,
    text=Body(...),
    user_in: Users = Depends(security_users.get_current_subject),
) -> JSONResponse:
    print(f"Received text: {text.get('text')}")
    try:
        comment: Dict[str, Any] = await add_comment(
            session=session, promo_id=id, user=user_in, text=text.get("text")
        )
        return JSONResponse(
            content=comment,
            status_code=status.HTTP_201_CREATED,
            headers={"Content-Type": "application/json"},
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Не нашев такого промокода",
        )


@router.get(
    "/promo/{id}/comments",
    response_model=List[CommentView],
    dependencies=[Depends(security_users.access_token_required)],
)
async def get_comments(
    session: SessionDep,
    id: UUID,
    limit: int = Query(10, ge=0),
    offset: int = Query(0, ge=0),
    user_in: Users = Depends(security_users.get_current_subject),
):
    try:
        result: Dict[str, Any] = await get_comments_with_pagination(
            session=session, promocode_id=id, limit=limit, offset=offset
        )
        comments: List[Dict[str, Any]] = result.get("comments")  # type: ignore

        return JSONResponse(
            content=comments,
            status_code=status.HTTP_200_OK,
            headers={"x-total-count": f"{result.get('x-total-count')}"},
        )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Не нашев такого промокода",
        )


@router.get(
    "/promo/{id}/comments/{comment_id}",
    response_model=CommentView,
    dependencies=[Depends(security_users.access_token_required)],
)
async def get_comment(
    session: SessionDep,
    id: UUID,
    comment_id: UUID,
    user_in: Users = Depends(security_users.get_current_subject),
) -> CommentView:
    try:
        comment: Comments = await get_comment_by_promo_id(
            session=session, promocode_id=id, comment_id=comment_id
        )
        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Не нашев такого промокода",
            )

        author_: Author = Author.model_validate(comment.author)
        comment_view = CommentView.model_validate(
            obj=comment, update={"date": comment.created_at, "author": author_}
        )
        return comment_view
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Не нашев такого промокода",
        )


@router.put(
    "/promo/{id}/comments/{comment_id}",
    response_model=None,
    dependencies=[Depends(security_users.access_token_required)],
)
async def update_comment_route(
    session: SessionDep,
    id: UUID,
    comment_id: UUID,
    body=Body(...),
    user_in: Users = Depends(security_users.get_current_subject),
) -> JSONResponse:
    try:
        comment: Dict[str, Any] = await update_comment(
            session=session,
            promo_id=id,
            user=user_in,
            comment_id=comment_id,
            text=body.get("text"),
        )
        return JSONResponse(
            content=comment,
            status_code=status.HTTP_200_OK,
            headers={"Content-Type": "application/json"},
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Не нашев такого промокода или комментария",
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="комментарий или промокод не принадлежит пользователю",
        )


@router.delete(
    "/promo/{id}/comments/{comment_id}",
    response_model=None,
    dependencies=[Depends(security_users.access_token_required)],
)
async def delete_comment_route(
    session: SessionDep,
    id: UUID,
    comment_id: UUID,
    user_in: Users = Depends(security_users.get_current_subject),
):
    try:
        status_: Dict[str, str] = await delete_comment(
            session=session, promo_id=id, user=user_in, comment_id=comment_id
        )
        return JSONResponse(
            content=status_,
            status_code=status.HTTP_200_OK,
            media_type="application/json",
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Не нашев такого промокода или комментария",
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="комментарий или промокод не принадлежит пользователю",
        )


@router.post(
    "/promo/{id}/activate",
    response_model=None,
    dependencies=[Depends(security_users.access_token_required)],
)
async def activate_promo(
    session: SessionDep,
    id: UUID,
    user_in: Users = Depends(security_users.get_current_subject),
):
    try:
        status_: Dict[str, str] = await activate_promocode_by_user(
            session=session, promo_id=id, user_in=user_in
        )
        return JSONResponse(
            content=status_,
            status_code=status.HTTP_200_OK,
            media_type="application/json",
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Не нашев такого промокода или комментария",
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нельзя использовать!!!",
        )
