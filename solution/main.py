# -*- coding: utf-8 -*-

import yaml  # type: ignore
from contextlib import asynccontextmanager
from typing import Any
import logging
import uvicorn

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from authx.exceptions import JWTDecodeError

from app.core import init_db
from app.core.security import security_companies, security_users
from app.api import api_router
from app.core import settings


logging.basicConfig(level=logging.DEBUG)


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    await init_db()
    yield


with open("api.yml", "r") as file:
    openapi_schema = yaml.safe_load(file)


app = FastAPI(
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# app.openapi_schema = openapi_schema

app.include_router(router=api_router)  # type: ignore
security_companies.handle_errors(app)  # type: ignore
security_users.handle_errors(app)


@app.post("")


@app.get("/api/ping")  # type: ignore
def send() -> Any:
    return {"status": "ok"}


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
):
    print("SEXXXXXXXXXXXX", exc.errors())
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "чота не то"},
    )


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    print("SEXXXXXXXXXXXX", exc.errors())
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "чота не то"},
    )


@app.exception_handler(JWTDecodeError)
async def jwtdecode_exception_handler(request: Request, exc: JWTDecodeError):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "чота не то"},
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(settings.SERVER_PORT),  # type: ignore
        log_level="debug",
        workers=4,
    )
