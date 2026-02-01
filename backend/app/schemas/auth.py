from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime

from sqlalchemy.util import deprecated


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

    @deprecated('password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Пароль должен быть не менее 8 символов')
        if not any(c.isupper() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну заглавную букву')
        if not any(c.isdigit() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
        return v


class UserLogin(BaseModel):
    email: EmailStr = Field(..., description="Электронная почта")
    password: str = Field(..., min_length=1, description="Пароль")


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    name: str
    theme: str
    created_at: datetime
    is_verified: bool
    is_deleted: bool

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Token(BaseModel):
    access_token: str
    token_type: str = Field("bearer", description="Тип токена")
    csrf_token: str = Field(..., description="CSRF токен для защиты")

    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "csrf_token": "a1b2c3d4e5f6g7h8i9j0"
            }
        }