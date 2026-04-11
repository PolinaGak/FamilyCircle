from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from datetime import datetime
from typing import Optional, List

from app.models.enums import Gender, RelationshipType


class FamilyMemberBase(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=50, description="Имя")
    last_name: str = Field(..., min_length=2, max_length=50, description="Фамилия")
    patronymic: Optional[str] = Field(None, max_length=50, description="Отчество")
    gender: Gender = Field(..., description="Пол (male/female)")
    birth_date: datetime = Field(..., description="Дата рождения")
    death_date: Optional[datetime] = Field(None, description="Дата смерти (если есть)")
    phone: Optional[str] = Field(None, description="Телефон")
    workplace: Optional[str] = Field(None, max_length=200, description="Место работы")
    residence: Optional[str] = Field(None, max_length=200, description="Место жительства")
    is_admin: bool = False
    user_id: Optional[int] = Field(None, description="id пользователя")
    approved: Optional[bool] = Field(description="Подтверждён ли администратором", default=False)
    is_active: Optional[bool] = Field(description="Зарегистрирован ли в приложении", default=False)


class FamilyMemberCreate(FamilyMemberBase):
    user_id: Optional[int] = Field(None, description="ID пользователя, если он зарегистрирован")
    related_member_id: Optional[int] = Field(None, description="ID существующего члена семьи (родитель/супруг/ребенок)")
    relationship_type: Optional[RelationshipType] = Field(None,
                                                          description="Тип связи нового члена к related_member_id")

    @field_validator('relationship_type')
    @classmethod
    def validate_relationship(cls, v, info):
        values = info.data
        if values.get('related_member_id') and not v:
            raise ValueError('При указании related_member_id необходимо указать relationship_type')
        if v and not values.get('related_member_id'):
            raise ValueError('При указании relationship_type необходимо указать related_member_id')
        return v

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
                "user_id": None,
                "related_member_id": 0,
                "relationship_type": "son"
            }
        }
    )


class SiblingCreate(BaseModel):
    """
    Добавление брата или сестры к существующему члену семьи.
    Позволяет отдельно указать мать и/или отца (хотя бы одного рекомендуется).
    """
    existing_member_id: int = Field(..., description="ID существующего члена семьи (к кому добавляем брата/сестру)")
    first_name: str = Field(..., min_length=2, max_length=50, description="Имя")
    last_name: str = Field(..., min_length=2, max_length=50, description="Фамилия")
    patronymic: Optional[str] = Field(None, max_length=50, description="Отчество")
    gender: Gender = Field(..., description="Пол (male/female)")
    birth_date: datetime = Field(..., description="Дата рождения")
    death_date: Optional[datetime] = Field(None, description="Дата смерти")
    phone: Optional[str] = Field(None, description="Телефон")
    workplace: Optional[str] = Field(None, max_length=200, description="Место работы")
    residence: Optional[str] = Field(None, max_length=200, description="Место жительства")
    is_admin: bool = Field(False, description="Является ли администратором")
    user_id: Optional[int] = Field(None, description="ID пользователя, если зарегистрирован")

    # Родители (опционально, но рекомендуется указать хотя бы одного)
    mother_id: Optional[int] = Field(None, description="ID матери в семье (опционально)")
    father_id: Optional[int] = Field(None, description="ID отца в семье (опционально)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "existing_member_id": 1,
                "first_name": "Петр",
                "last_name": "Иванов",
                "patronymic": "Сергеевич",
                "gender": "male",
                "birth_date": "1992-05-15T00:00:00",
                "mother_id": 5,  # ID существующей матери в семье
                "father_id": 6  # ID существующего отца в семье
            }
        }
    )


class ParentCreate(BaseModel):
    """Создание родителя (мамы или папы) с привязкой к нескольким детям"""
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    patronymic: Optional[str] = Field(None, max_length=50)
    gender: Gender = Field(..., description="Пол родителя (male - отец, female - мать)")
    birth_date: datetime = Field(..., description="Дата рождения родителя")
    death_date: Optional[datetime] = None
    phone: Optional[str] = None
    workplace: Optional[str] = None
    residence: Optional[str] = None

    # Главное отличие - список детей, а не один
    children_ids: List[int] = Field(..., min_length=1, description="ID детей, для которых создается родитель")

    # Опционально: можно сразу привязать к супругу/супруге, если известен
    spouse_id: Optional[int] = Field(None, description="ID супруга/супруги (если уже есть в древе)")

    @field_validator('children_ids')
    @classmethod
    def validate_children_not_empty(cls, v):
        if not v:
            raise ValueError('Необходимо выбрать хотя бы одного ребенка')
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "first_name": "Мария",
                "last_name": "Иванова",
                "patronymic": "Петровна",
                "gender": "female",
                "birth_date": "1970-05-15T00:00:00",
                "children_ids": [1, 2, 3],  # Выбрали нескольких детей
                "spouse_id": 5  # Опционально: привязка к отцу, если он есть
            }
        }
    )

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
    gender: Optional[Gender] = Field(None, description="Пол (male/female)")
    related_member_id: Optional[int] = Field(None, description="ID существующего члена семьи (родитель/супруг/ребенок)")
    relationship_type: Optional[RelationshipType] = Field(None,
                                                          description="Тип связи нового члена к related_member_id")
    birth_date: Optional[datetime] = None
    death_date: Optional[datetime] = None
    phone: Optional[str] = None
    workplace: Optional[str] = None
    residence: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator('relationship_type')
    @classmethod
    def validate_relationship(cls, v, info):
        values = info.data
        if values.get('related_member_id') and not v:
            raise ValueError('При указании related_member_id необходимо указать relationship_type')
        if v and not values.get('related_member_id'):
            raise ValueError('При указании relationship_type необходимо указать related_member_id')
        return v

    model_config = ConfigDict(from_attributes=True)


class FamilyMemberApprove(BaseModel):
    approved: bool = True