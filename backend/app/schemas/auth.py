from pydantic import BaseModel, EmailStr, Field, validator, ConfigDict, field_validator
from typing import Optional
from datetime import datetime

from sqlalchemy.util import deprecated

from app.models.enums import ThemeType


class UserCreate(BaseModel):
    email: EmailStr = Field(..., description="Электронная почта пользователя")
    password: str = Field(
        ...,
        min_length=8,
        description="Пароль (минимум 8 символов)"
    )
    name: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Имя пользователя"
    )

    @field_validator('password')
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Пароль должен быть не менее 8 символов')
        if not any(c.isupper() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну заглавную букву')
        if not any(c.isdigit() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
        return v

    model_config = ConfigDict(str_strip_whitespace=True)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    name: str
    theme: ThemeType
    created_at: datetime
    is_verified: bool
    is_deleted: bool

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int