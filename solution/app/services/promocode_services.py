# -*- coding: utf-8 -*-

import uuid
from typing import Optional, List, Any, Dict
import datetime

from sqlmodel import Session, select
from sqlalchemy import case, func
from fastapi import Query
from fastapi.exceptions import RequestValidationError

from app.models import (
    Promocodes,
    Categories,
    Likes,
    ActivatePromoByUser,
    PromoUnique,
    PromoReadOnly,
    Target,
    Companies,
    PromoUpdate,
    PromoMode,
    PromoCreate,
    Comments,
)


class PromoService:
    """Сервис для работы с промокодами"""

    @staticmethod
    async def create_promocode(
        *, session: Session, promo_create: PromoCreate, company_id: uuid.UUID
    ) -> Promocodes:
        """
        Создание нового промокода в базе данных

        :param session: Объект сессии базы данных
        :param promo_create: Объект с входными данными для создания
        :param company_id: Id компании, которой принадлежит промокод

        :returns: Объект промокода в базе данных
        """
        target_settings = promo_create.target

        categories_instances: List[Categories] = []
        if target_settings.categories:
            for category_name in target_settings.categories:
                category_instance = Categories(name=category_name)
                categories_instances.append(category_instance)

        promo_unique_instances: List[PromoUnique] = []
        if promo_create.promo_unique:
            for unique_name in promo_create.promo_unique:
                unique_instance = PromoUnique(name=unique_name)
                promo_unique_instances.append(unique_instance)

        db_promocode: Promocodes = Promocodes.model_validate(
            obj=promo_create,
            update={
                "company_id": company_id,
                "country": target_settings.country,
                "age_until": target_settings.age_until,
                "age_from": target_settings.age_from,
                "categories": categories_instances,
                "promo_unique": promo_unique_instances,
            },
        )

        session.add(db_promocode)
        session.commit()
        session.refresh(db_promocode)
        return db_promocode

    @staticmethod
    async def update_promocode(
        session: Session, id: uuid.UUID, promo_update: PromoUpdate
    ) -> Promocodes:
        """
        Обновление промокода по ID.

        :param session: Объект сессии базы данных.
        :param id: ID промокода для обновления.
        :param promo_update: Данные для обновления промокода.

        :returns: Обновленный объект промокода.
        :raises ValueError: Если промокод не найден.
        :raises RequestValidationError: Если данные обновления некорректны.
        """

        db_promo: Optional[Promocodes] = session.exec(
            select(Promocodes).where(Promocodes.id == id)
        ).first()

        if not db_promo:
            raise ValueError("Промокод не найден")

        promo_data: Dict[str, Any] = promo_update.model_dump(
            exclude_unset=True
        )

        if (
            promo_data.get("max_count") != 1
            and db_promo.mode == PromoMode.UNIQUE
        ):
            raise RequestValidationError(
                errors={"max_count": "Должно быть 1 для UNIQUE режима."}
            )

        db_promo.sqlmodel_update(promo_data)
        await PromoService._update_categories(
            db_promo, promo_data.get("target")
        )
        await PromoService._update_target(db_promo, promo_data.get("target"))

        session.add(db_promo)
        session.commit()
        session.refresh(db_promo)
        return db_promo

    @staticmethod
    async def _update_target(
        db_promo: Promocodes, target: Optional[Dict[str, Any]]
    ) -> None:
        """
        Обновление настроек таргетирования промокода.

        :param db_promo: Объект промокода для обновления.
        :param target: Данные настроек таргетирования для обновления.
        """
        if target:
            for key, value in target.items():
                if (value is not None) and (key != "categories"):
                    setattr(db_promo, key, value)

    @staticmethod
    async def _update_categories(
        db_promo: Promocodes, target: Optional[Dict[str, Any]]
    ) -> None:
        """
        Обновление категорий промокода.

        :param db_promo: Объект промокода для обновления.
        :param target: Данные категорий для обновления.
        """

        if target and "categories" in target:
            db_promo.categories.clear()  # type: ignore
            for category_name in target["categories"]:
                category_instance = Categories(
                    name=category_name, promo_id=db_promo.id
                )
                db_promo.categories.append(category_instance)  # type: ignore

    @staticmethod
    async def get_promo_by_id(session: Session, id: uuid.UUID) -> Promocodes:
        """
        Получение промокода по ID.

        :param session: Объект сессии базы данных.
        :param id: ID промокода для получения.

        :returns: Объект промокода или None, если не найден.
        """

        return session.exec(
            select(Promocodes).where(Promocodes.id == id)
        ).first()

    @staticmethod
    async def get_likes(
        session: Session, promocode_id: uuid.UUID
    ) -> Optional[List[Likes]]:
        """
        Получение лайков промокода.

        :param session: Объект сессии базы данных.
        :param promocode_id: ID промокода.

        :returns: Список объектов лайков.
        """

        return session.exec(
            select(Likes).where(Likes.promocode_id == promocode_id)
        ).all()

    @staticmethod
    async def get_activations(
        session: Session, promocode_id: uuid.UUID
    ) -> List[ActivatePromoByUser]:
        """
        Получение активаций промокода.

        :param session: Объект сессии базы данных.
        :param promocode_id: ID промокода.

        :returns: Список объектов активаций промокода.
        """

        return session.exec(
            select(ActivatePromoByUser).where(
                ActivatePromoByUser.promocode_id == promocode_id
            )
        ).all()

    @staticmethod
    async def get_unique_promocodes(
        session: Session, promocode_id: uuid.UUID
    ) -> List[PromoUnique]:
        """
        Получение уникальных промокодов, принадлежащих купону.

        :param session: Объект сессии базы данных.
        :param promocode_id: ID промокода.

        :returns: Список уникальных промокодов.
        """

        return session.exec(
            select(PromoUnique).where(PromoUnique.promo_id == promocode_id)
        ).all()

    @staticmethod
    async def get_categories(
        session: Session, promocode_id: uuid.UUID
    ) -> List[str]:
        """
        Получение категорий промокода.
        :param session: Объект сессии базы данных.
        :param promocode_id: ID промокода.
        :returns: Список названий категорий.
        """

        return session.exec(
            select(Categories.name).where(Categories.promo_id == promocode_id)
        ).all()

    @staticmethod
    async def get_comments(
        session: Session, promocode_id: uuid.UUID
    ) -> list[Comments]:
        """
        Получение комментариев промокода
        :param session: Объект сессии базы данных.
        :param promocode_id: ID промокода.

        :returns: Список комментариев промокода.
        """
        return session.exec(
            select(Comments).where(Comments.promocode_id == promocode_id)
        ).all()

    @staticmethod
    async def is_active(session: Session, promocode: Promocodes) -> bool:
        """
        Проверка активен ли промокод.

        Промокод считается активным, если:
        - Текущая дата входит в указанный промежуток [active_from;
        active_until] (при наличии).
        - Для mode = COMMON число активаций меньше max_count.
        - Для mode = UNIQUE остались неактивированные значения.

        :param session: Объект сессии базы данных.
        :param promocode: Объект промокода.

        :returns: True, если промокод активен, иначе False.
        """

        today: datetime.date = datetime.date.today()
        date_active_from: datetime.date = (
            datetime.datetime.strptime(
                promocode.active_from, "%Y-%m-%d"
            ).date()
            if promocode.active_from
            else today
        )
        date_active_until: datetime.date = (
            datetime.datetime.strptime(
                promocode.active_until, "%Y-%m-%d"
            ).date()
            if promocode.active_until
            else today
        )

        if promocode.active_from and today < date_active_from:
            return False

        if promocode.active_until and today > date_active_until:
            return False

        activations: List[
            ActivatePromoByUser
        ] = await PromoService.get_activations(session, promocode.id)
        unique_promocodes: List[
            PromoUnique
        ] = await PromoService.get_unique_promocodes(session, promocode.id)

        if promocode.mode == "COMMON":
            return len(activations) < promocode.max_count

        if promocode.mode == "UNIQUE":
            return len(activations) != len(unique_promocodes)

        return True

    @staticmethod
    async def get_promocodes(
        session: Session,
        company_id: uuid.UUID,
        offset: int = 0,
        limit: int = Query(default=100, le=100),
        sort_by: Optional[str] = Query(
            None, enum=["active_from", "active_until"]
        ),
        country: Optional[List[str]] = Query(None),
    ) -> Dict[str, Any]:
        """
        Получение промокодов с пагинацией.

        :param session: Объект сессии базы данных.
        :param company_id: ID компании, для которой получаем промокоды.
        :param offset: Сдвиг начала на.
        :param limit: Максимальное количество записей.
        :param sort_by: Сортировать по дате начала/конца действия промокода.
        :param country: Список стран целевой аудитории, по которому нужно
        фильтровать промокоды.

        :returns: Словарь с количеством и списком промокодов.
        """

        query = select(Promocodes).where(Promocodes.company_id == company_id)
        x_total_count: int = len(session.exec(query).all())

        if country:
            query = query.where(
                func.lower(Promocodes.country).in_(
                    [c.lower() for c in country]
                )
                | (Promocodes.country.is_(None))  # type: ignore
            )
            x_total_count = len(session.exec(query).all())

        # Сортировка
        if sort_by == "active_from":
            query = query.order_by(
                case(
                    (
                        Promocodes.active_from.isnot(None),  # type: ignore
                        Promocodes.active_from,
                    ),
                    else_="-inf",
                ).desc()  # type: ignore
            )
        elif sort_by == "active_until":
            query = query.order_by(
                case(
                    (
                        Promocodes.active_until.isnot(None),  # type: ignore
                        Promocodes.active_until,
                    ),
                    else_="+inf",
                ).desc()  # type: ignore
            )
        else:
            query = query.order_by(Promocodes.created_at.desc())  # type: ignore

        # Пагинация
        query = query.offset(offset).limit(limit)
        promocodes: List[Promocodes] = session.exec(query).all()

        return {"x-total-count": x_total_count, "promocodes": promocodes}

    @staticmethod
    async def get_promocodes_readonly(
        session: Session, promocodes: List[Promocodes]
    ) -> List[PromoReadOnly]:
        """
        Конвертация списка промокодов-объектов БД в список промокодов для
        чтения.

        :param session: Объект сессии базы данных.
        :param promocodes: Список из промокодов-объектов БД
        :returns: Список промокодов для чтения.
        """
        promocodes_pydantic: List[PromoReadOnly] = []
        for promo in promocodes:
            likes_count: Optional[List[Likes]] = await PromoService.get_likes(
                session, promocode_id=promo.id
            )
            used_count: int = len(
                await PromoService.get_activations(
                    session, promocode_id=promo.id
                )
            )
            is_active_: bool = await PromoService.is_active(
                session, promocode=promo
            )

            target: Target = Target(
                age_from=promo.age_from,
                age_until=promo.age_until,
                country=promo.country,
                categories=await PromoService.get_categories(
                    session, promocode_id=promo.id
                ),
            )

            company_name: str = session.exec(
                select(Companies.name).where(Companies.id == promo.company_id)
            ).first()

            promo_unique_names: Optional[List[str]] = None
            if promo.promo_unique:
                promo_unique: List[
                    PromoUnique
                ] = await PromoService.get_unique_promocodes(
                    session, promocode_id=promo.id
                )
                promo_unique_names = [p.name for p in promo_unique]

            promocodes_pydantic.append(
                PromoReadOnly.model_validate(
                    obj=promo,
                    update={
                        "promo_id": promo.id,
                        "like_count": len(likes_count) if likes_count else 0,
                        "used_count": used_count,
                        "active": is_active_,
                        "promo_unique": promo_unique_names,
                        "target": target,
                        "company_name": company_name,
                    },
                )
            )
        return promocodes_pydantic
