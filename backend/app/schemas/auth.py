from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from typing import Optional
from datetime import datetime

from backend.app.models.enums import ThemeType


class BasePasswordMixin:
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Пароль должен быть не менее 8 символов')
        if not any(c.isupper() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну заглавную букву')
        if not any(c.isdigit() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
        return v


class BasePasswordField(BaseModel, BasePasswordMixin):
    """Базовый класс для моделей с полем password"""
    password: str = Field(..., min_length=8, description="Пароль (минимум 8 символов)")

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        return cls.validate_password_strength(v)


class BaseNewPasswordField(BaseModel, BasePasswordMixin):
    """Базовый класс для моделей с полем new_password"""
    new_password: str = Field(..., min_length=8, description="Новый пароль (минимум 8 символов)")

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return cls.validate_password_strength(v)



class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=2, max_length=50)

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        return BasePasswordMixin.validate_password_strength(v)

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123",
                "name": "Иван Петров"
            }
        }
    )


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123"
            }
        }
    )


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    name: str
    theme: ThemeType
    created_at: datetime
    is_verified: bool
    is_deleted: bool

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "email": "user@example.com",
                "name": "Иван Петров",
                "theme": "light",
                "created_at": "2026-02-17T10:00:00",
                "is_verified": True,
                "is_deleted": False
            }
        }
    )

class LoginResponse(BaseModel):
    """Ответ при логине (без refresh token в JSON!)"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse

class TokenRefreshResponse(BaseModel):
    """Ответ при обновлении токена"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordReset(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        return BasePasswordMixin.validate_password_strength(v)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        return BasePasswordMixin.validate_password_strength(v)


class LogoutResponse(BaseModel):
    success: bool
    message: str


class UserUpdate(BaseModel):
    name: str = Field(..., min_length=2, max_length=50, description="Новое имя пользователя")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError('Имя должно содержать минимум 2 символа')
        return v

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "Иван Петров"
        }
    })