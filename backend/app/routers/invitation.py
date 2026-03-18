from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_active_user
from app.crud import invitation_crud, family_crud
from app.schemas.invitation import (
    InvitationCreateNewMember, InvitationCreateClaimMember,
    InvitationResponse, InvitationCode, ClaimInvitationResponse
)
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/invitation", tags=["invitation"])


@router.post("/create/new-member", response_model=InvitationResponse)
async def create_new_member_invitation(
        invitation_data: InvitationCreateNewMember,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Создать приглашение для нового члена семьи.
    При активации создастся новая карточка.
    """
    try:
        invitation = invitation_crud.create_new_member_invitation(
            db, invitation_data, current_user.id
        )
        return invitation
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка при создании приглашения: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при создании приглашения"
        )


@router.post("/create/claim-member", response_model=InvitationResponse)
async def create_claim_member_invitation(
        invitation_data: InvitationCreateClaimMember,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Создать приглашение для привязки существующей карточки родственника.
    """
    try:
        invitation = invitation_crud.create_claim_member_invitation(
            db, invitation_data, current_user.id
        )
        return invitation
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка при создании приглашения: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при создании приглашения"
        )


@router.post("/claim", response_model=ClaimInvitationResponse)
async def claim_invitation(
        code_data: InvitationCode,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Активировать приглашение по коду.
    """
    success, message, member = invitation_crud.claim_invitation(
        db, code_data.code, current_user.id
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    # Получаем информацию о семье
    family = family_crud.get_family_by_id(db, member.family_id)
    member.id = current_user.id

    # Проверяем, заполнена ли карточка (есть ли обязательные поля)
    requires_completion = not all([
        member.first_name and member.first_name != "Новый",
        member.last_name and member.last_name != "Член",
        member.birth_date
    ])

    return {
        "success": True,
        "message": message,
        "family_id": family.id,
        "family_name": family.name,
        "member_id": member.id,
        "requires_profile_completion": requires_completion
    }


@router.get("/family/{family_id}", response_model=List[InvitationResponse])
async def get_family_invitations(
        family_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Получить все приглашения семьи (только для администраторов)
    """
    if not family_crud.is_family_admin(db, current_user.id, family_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администратор может просматривать приглашения"
        )

    invitations = invitation_crud.get_family_invitations(db, family_id)
    return invitations


@router.delete("/{invitation_id}")
async def deactivate_invitation(
        invitation_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Деактивировать приглашение (отозвать)
    """
    success = invitation_crud.deactivate_invitation(db, invitation_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Приглашение не найдено или у вас нет прав"
        )

    return {"message": "Приглашение отозвано"}