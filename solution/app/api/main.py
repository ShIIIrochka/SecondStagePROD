# -*- coding: utf-8 -*-

from fastapi import APIRouter

from app.api.routes import user_router, company_router, promo_router

api_router: APIRouter = APIRouter(prefix="/api")
api_router.include_router(router=user_router)  # type: ignore
api_router.include_router(router=company_router)  # type: ignore
api_router.include_router(router=promo_router)  # type: ignore
