from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import exc
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_active_user
from app.crud import family_crud
from app.schemas.family import (
    FamilyCreate, FamilyResponse, FamilyDetailResponse
)
from app.schemas.family_member import (
    FamilyMemberCreate, FamilyMemberResponse,
    FamilyMemberUpdate, FamilyMemberApprove
)

from app.models.user import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/family", tags=["family"])


@router.post("/create", response_model=FamilyResponse)
async def create_family(
        family_data: FamilyCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    try:
        family = family_crud.create_family(db, family_data, current_user.id)
        logger.info(f"Семья '{family.name}' создана пользователем {current_user.id}")
        return family
    except Exception as e:
        logger.error(f"Ошибка при создании семьи: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при создании семьи"
        )


@router.get("/my", response_model=List[FamilyResponse])
async def get_my_families(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    families = family_crud.get_user_families(db, current_user.id)
    return families


@router.get("/{family_id}", response_model=FamilyDetailResponse)
async def get_family_detail(
        family_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    if not family_crud.is_family_member(db, current_user.id, family_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этой семье"
        )

    family = family_crud.get_family_with_members(db, family_id)
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Семья не найдена"
        )

    return family


@router.put("/{family_id}", response_model=FamilyResponse)
async def update_family(
        family_id: int,
        family_data: FamilyCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    if not family_crud.is_family_admin(db, current_user.id, family_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администратор может изменять семью"
        )

    family = family_crud.update_family(db, family_id, family_data.name)
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Семья не найдена"
        )

    return family


@router.delete("/{family_id}")
async def delete_family(
        family_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    if not family_crud.is_family_admin(db, current_user.id, family_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администратор может удалить семью"
        )

    success = family_crud.delete_family(db, family_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Семья не найдена"
        )

    return {"message": "Семья успешно удалена"}


@router.post("/{family_id}/member", response_model=FamilyMemberResponse)
async def add_family_member(
        family_id: int,
        member_data: FamilyMemberCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    is_admin = family_crud.is_family_admin(db, current_user.id, family_id)
    is_member = family_crud.is_family_member(db, current_user.id, family_id)

    if not (is_admin or is_member):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет прав добавлять членов в эту семью"
        )

    if is_admin:
        member_data.approved = True

    try:
        member = family_crud.add_member(db, family_id, member_data, current_user.id)
        return member
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка при добавлении члена семьи: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при добавлении члена семьи"
        )


@router.get("/{family_id}/members", response_model=List[FamilyMemberResponse])
async def get_family_members(
        family_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    if not family_crud.is_family_member(db, current_user.id, family_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этой семье"
        )

    members = family_crud.get_family_members(db, family_id)
    return members


@router.put("/member/{member_id}", response_model=FamilyMemberResponse)
async def update_family_member(
        member_id: int,
        update_data: FamilyMemberUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    member = family_crud.get_member_by_id(db, member_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Член семьи не найден"
        )

    is_admin = family_crud.is_family_admin(db, current_user.id, member.family_id)
    is_self = member.user_id == current_user.id

    if not (is_admin or is_self):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав на редактирование"
        )

    updated = family_crud.update_member(db, member_id, update_data)
    return updated


@router.post("/member/{member_id}/approve", response_model=FamilyMemberResponse)
async def approve_family_member(
        member_id: int,
        approve_data: FamilyMemberApprove,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    member = family_crud.get_member_by_id(db, member_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Член семьи не найден"
        )

    if not family_crud.is_family_admin(db, current_user.id, member.family_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администратор может подтверждать членов семьи"
        )

    updated = family_crud.approve_member(db, member_id, approve_data.approved)
    return updated


@router.delete("/member/{member_id}")
async def remove_family_member(
        member_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    member = family_crud.get_member_by_id(db, member_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Член семьи не найден"
        )

    is_admin = family_crud.is_family_admin(db, current_user.id, member.family_id)
    is_self = member.user_id == current_user.id

    if not (is_admin or is_self):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав на удаление"
        )

    if is_self and member.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Администратор не может удалить себя. Сначала передайте права другому."
        )

    try:
        success = family_crud.remove_member(db, member_id)
        if not success:
            raise HTTPException(status_code=404, detail="Член семьи не найден")
        return {"message": "Член семьи успешно удален"}
    except exc.IntegrityError as e:
        logger.error(f"Ошибка целостности при удалении: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Невозможно удалить, так как есть связанные данные"
        )
    except Exception as e:
        logger.error(f"Ошибка при удалении: {str(e)}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@router.post("/{family_id}/transfer-admin")
async def transfer_admin_rights(
    family_id: int,
    target_member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    try:
        family_crud.transfer_admin_rights(db, current_user.id, family_id, target_member_id)
        return {"success": True, "message": "Права администратора переданы"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{family_id}/leave")
async def leave_family(
    family_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    try:
        family_crud.leave_family(db, current_user.id, family_id)
        return {"success": True, "message": "Вы успешно покинули семью"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))