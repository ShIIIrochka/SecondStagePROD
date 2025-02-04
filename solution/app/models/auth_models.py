# -*- coding: utf-8 -*-

from pydantic import BaseModel


class AuthHeader(BaseModel):
    Authorization: str


class Token(BaseModel):
    access_token: str
    token_type: str
