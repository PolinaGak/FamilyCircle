from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from backend.app.database import get_db
from backend.app.dependencies.auth import get_current_active_user
from backend.app.crud.family import family_crud
from backend.app.models.user import User


def check_family_access(
        family_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Проверить, что пользователь является членом семьи.
    Возвращает текущего пользователя если проверка пройдена.
    """
    if not family_crud.is_family_member(db, current_user.id, family_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этой семье"
        )
    return current_user


def check_family_admin(
        family_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Проверить, что пользователь является администратором семьи.
    Возвращает текущего пользователя если проверка пройдена.
    """
    if not family_crud.is_family_admin(db, current_user.id, family_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администратор семьи может выполнять это действие"
        )
    return current_user


def check_tree_edit_access(
        family_id: int,
        member_id: Optional[int] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Проверить права на редактирование дерева.
    Редактировать может: админ семьи или владелец карточки (если указан member_id).
    """
    if family_crud.is_family_admin(db, current_user.id, family_id):
        return current_user

    if member_id:
        from backend.app.crud.family import family_crud as fc
        member = fc.get_member_by_id(db, member_id)
        if member and member.user_id == current_user.id:
            return current_user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Нет прав на редактирование семейного древа"
    )


def check_family_member_or_admin(
        family_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Проверить что пользователь - член семьи (для операций, доступных членам).
    Отличается от check_family_access только сообщением об ошибке.
    """
    if not family_crud.is_family_member(db, current_user.id, family_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы не являетесь членом этой семьи"
        )
    return current_user