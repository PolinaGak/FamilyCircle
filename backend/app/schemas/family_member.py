from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List


class FamilyMemberBase(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=50, description="Имя")
    last_name: str = Field(..., min_length=2, max_length=50, description="Фамилия")
    patronymic: Optional[str] = Field(None, max_length=50, description="Отчество")
    birth_date: datetime = Field(..., description="Дата рождения")
    death_date: Optional[datetime] = Field(None, description="Дата смерти (если есть)")
    phone: Optional[str] = Field(None, description="Телефон")
    workplace: Optional[str] = Field(None, max_length=200, description="Место работы")
    residence: Optional[str] = Field(None, max_length=200, description="Место жительства")
    is_admin: bool = False
    user_id: Optional[int] = Field(None, description="id пользователя")
    approved: Optional[bool] = Field(description="Подтверждён ли администратором", default=False)
    is_active: Optional[bool] = Field(description="Зарегистрирован ли в приложении", default=False)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "first_name": "Иван",
                "last_name": "Иванов",
                "patronymic": "Иванович",
                "birth_date": "1990-01-01T00:00:00",
                "death_date": None,
                "phone": "+7-999-123-45-67",
                "workplace": "ООО Пример",
                "residence": "Москва",
                "is_admin": False,
                "user_id": None
            }
        }
    )


class FamilyMemberCreate(FamilyMemberBase):
    user_id: Optional[int] = Field(None, description="ID пользователя, если он зарегистрирован")


class FamilyMemberResponse(FamilyMemberBase):
    id: int
    family_id: int
    user_id: Optional[int]
    is_active: bool
    approved: bool
    created_by_user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FamilyMemberUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=2, max_length=50)
    last_name: Optional[str] = Field(None, min_length=2, max_length=50)
    patronymic: Optional[str] = None
    birth_date: Optional[datetime] = None
    death_date: Optional[datetime] = None
    phone: Optional[str] = None
    workplace: Optional[str] = None
    residence: Optional[str] = None
    is_active: Optional[bool] = None


class FamilyMemberApprove(BaseModel):
    approved: bool = True
