# -*- coding: utf-8 -*-

from typing import List, Optional, Dict
from uuid import UUID
import json

from icecream import ic
from pydantic import TypeAdapter
from fastapi import APIRouter, HTTPException, status, Query, Depends
from fastapi.responses import JSONResponse, Response

from app.models import (
    PromoCreate,
    PromoReadOnly,
    Companies,
    Promocodes,
    PromoUpdate,
)
from app.api import SessionDep
from app.core.security import security_companies
from app.services import PromoService


router = APIRouter(prefix="/business", tags=["B2B"])


@router.post(
    "/promo",
    response_model=None,
    dependencies=[Depends(security_companies.access_token_required)],
)
async def register_promocode(
    session: SessionDep,
    promo_in: PromoCreate,
    company: Companies = Depends(security_companies.get_current_subject),
) -> JSONResponse:
    """
    Регистрация нового промокода.

    :param session: Объект сессии базы данных
    :param promo_in: Данные для создания промокода
    :param company: Информация о компании

    :returns: JSONResponse с ID созданного промокода
    """
    ic(company)
    promocode = await PromoService.create_promocode(
        session=session,
        promo_create=promo_in,
        company_id=company[0].id,
    )
    return JSONResponse(
        content={"id": str(promocode.id)},
        headers={"Content-Type": "application/json"},
        status_code=status.HTTP_201_CREATED,
    )


@router.get(
    "/promo",
    response_model=None,
    dependencies=[Depends(security_companies.access_token_required)],
)
async def get_promocodes(
    session: SessionDep,
    company: Companies = Depends(security_companies.get_current_subject),
    offset: int = 0,
    limit: int = Query(default=100, le=100),
    sort_by: Optional[str] = Query(None, enum=["active_from", "active_until"]),
    country: Optional[List[str]] = Query(None),
) -> Response:
    """
    Получение списка промокодов.

    :param session: Объект сессии базы данных
    :param company: Информация о компании
    :param offset: Сдвиг для пагинации
    :param limit: Максимальное количество записей
    :param sort_by: Поле для сортировки
    :param country: Список стран для фильтрации

    :returns: Response с промокодами
    """
    if not company:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль.",
        )

    result: Dict[str, List[Promocodes]] = await PromoService.get_promocodes(
        session=session,
        company_id=company[0].id,
        offset=offset,
        limit=limit,
        sort_by=sort_by,
        country=country,
    )

    promocodes_: Optional[List[Promocodes]] = result.get("promocodes")

    promocodes_readonly_: List[
        PromoReadOnly
    ] = await PromoService.get_promocodes_readonly(
        session=session,
        promocodes=promocodes_,  # type: ignore
    )

    # Сериализация списка из PromoReadOnly в json(bytes)
    ta = TypeAdapter(List[PromoReadOnly])
    bytes_promocodes_readonly = ta.dump_json(promocodes_readonly_)

    # Сериализация bytes в json
    my_json = bytes_promocodes_readonly.decode("utf8").replace("'", '"')
    promocodes_readonly = json.loads(my_json)

    ic(promocodes_readonly)

    return Response(
        content=json.dumps(promocodes_readonly),
        media_type="application/json",
        status_code=status.HTTP_200_OK,
        headers={"x-total-count": f"{result.get('x-total-count')}"},
    )


@router.get(
    "/promo/{id}",
    dependencies=[Depends(security_companies.access_token_required)],
    response_model=PromoReadOnly,
)
async def get_promocode(
    session: SessionDep,
    id: UUID,
    company: Companies = Depends(security_companies.get_current_subject),
):
    promocode: Promocodes = await PromoService.get_promo_by_id(
        session=session, id=id
    )
    promocode_readonly: List[
        PromoReadOnly
    ] = await PromoService.get_promocodes_readonly(
        session=session, promocodes=[promocode]
    )

    if not promocode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Промокод не найден"
        )
    if promocode_readonly[0].company_id != company[0].id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Не твое!!!"
        )
    ic(promocode_readonly)
    return promocode_readonly[0]


@router.patch(
    "/promo/{id}",
    dependencies=[Depends(security_companies.access_token_required)],
    response_model=PromoReadOnly,
)
async def patch_promocode(
    session: SessionDep,
    id: UUID,
    promo_update: PromoUpdate,
    company: Companies = Depends(security_companies.get_current_subject),
) -> PromoReadOnly:
    """
    Обновление промокода по ID.

    :param session: Объект сессии базы данных.
    :param id: ID промокода для обновления.
    :param promo_update: Данные для обновления промокода.
    :param company: Объект компании, выполняющей запрос.

    :returns: Объект обновленного промокода для чтения.
    :raises HTTPException: Если промокод не найден или не принадлежит компании.
    """

    promocode: Optional[Promocodes] = await PromoService.get_promo_by_id(
        session, id
    )
    if not promocode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Промокод не найден"
        )

    if promocode.company_id != company[0].id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Не твое!!!"
        )

    try:
        updated_promocode: Promocodes = await PromoService.update_promocode(
            session, id, promo_update
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка обновления промокода",
        )

    promocode_readonly: List[
        PromoReadOnly
    ] = await PromoService.get_promocodes_readonly(
        session, [updated_promocode]
    )
    return promocode_readonly[0]
