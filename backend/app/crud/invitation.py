from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from backend.app.models import RelationshipType, Gender
from backend.app.models.invitation import Invitation, generate_invite_code
from backend.app.models.family import Family
from backend.app.models.family_member import FamilyMember
from backend.app.schemas.invitation import InvitationCreateNewMember, InvitationCreateClaimMember
import logging

logger = logging.getLogger(__name__)

def _ensure_aware(dt: datetime | None) -> datetime | None:
    """
    Гарантирует, что datetime имеет timezone info (UTC).
    Если dt уже aware — возвращает как есть.
    Если naive — добавляет UTC timezone.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

class InvitationCRUD:
    """CRUD операции для приглашений"""

    @staticmethod
    def create_new_member_invitation(
            db: Session,
            invitation_data: InvitationCreateNewMember,
            created_by_user_id: int
    ) -> Invitation:
        """Создать приглашение для нового члена семьи"""
        try:
            from backend.app.crud.family import family_crud

            expires_at = datetime.now(timezone.utc) + timedelta(days=invitation_data.expires_in_days)

            invitation = Invitation(
                code=generate_invite_code(),
                family_id=invitation_data.family_id,
                created_by_user_id=created_by_user_id,
                invitation_type='new_member',
                expires_at=expires_at
            )

            db.add(invitation)
            db.commit()
            db.refresh(invitation)

            logger.info(f"Создано приглашение {invitation.code} для семьи {invitation_data.family_id}")
            return invitation

        except Exception as e:
            logger.error(f"Ошибка при создании приглашения: {str(e)}")
            db.rollback()
            raise

    @staticmethod
    def create_claim_member_invitation(
            db: Session,
            invitation_data: InvitationCreateClaimMember,
            created_by_user_id: int
    ) -> Invitation:
        """Создать приглашение для привязки существующей карточки"""
        try:
            from backend.app.crud.family import family_crud as fc
            member = fc.get_member_by_id(db, invitation_data.member_id)
            if not member:
                raise ValueError("Карточка не найдена")
            if member.user_id is not None:
                raise ValueError("Эта карточка уже привязана к пользователю")
            if member.family_id != invitation_data.family_id:
                raise ValueError("Карточка не принадлежит этой семье")

            expires_at = datetime.now(timezone.utc) + timedelta(days=invitation_data.expires_in_days)

            invitation = Invitation(
                code=generate_invite_code(),
                family_id=invitation_data.family_id,
                created_by_user_id=created_by_user_id,
                invitation_type='claim_member',
                target_member_id=invitation_data.member_id,
                expires_at=expires_at
            )

            db.add(invitation)
            db.commit()
            db.refresh(invitation)

            logger.info(f"Создано приглашение для привязки карточки {member.id}")
            return invitation

        except Exception as e:
            logger.error(f"Ошибка при создании приглашения: {str(e)}")
            db.rollback()
            raise

    @staticmethod
    def get_invitation_by_code(db: Session, code: str) -> Optional[Invitation]:
        """Получить приглашение по коду"""
        return db.query(Invitation).filter(
            Invitation.code == code,
            Invitation.is_active == True
        ).first()

    @staticmethod
    def get_family_invitations(db: Session, family_id: int) -> List[Invitation]:
        """Получить все приглашения семьи"""
        return db.query(Invitation).filter(
            Invitation.family_id == family_id
        ).order_by(Invitation.created_at.desc()).all()

    @staticmethod
    def claim_invitation(
            db: Session,
            code: str,
            claiming_user_id: int
    ) -> tuple[bool, str, Optional[FamilyMember]]:
        """
        Активировать приглашение
        Возвращает: (успех, сообщение, член_семьи)
        """
        invitation = InvitationCRUD.get_invitation_by_code(db, code)

        if not invitation:
            return False, "Приглашение не найдено или неактивно", None

        if datetime.now(timezone.utc) > _ensure_aware(invitation.expires_at):
            invitation.is_active = False
            db.commit()
            return False, "Срок действия приглашения истек", None

        if invitation.used_at:
            return False, "Приглашение уже использовано", None

        from backend.app.crud.family import family_crud as fc

        if invitation.invitation_type == 'new_member':
            from backend.app.schemas.family_member import FamilyMemberCreate

            member_data = FamilyMemberCreate(
                first_name="Новый",
                last_name="Член семьи",
                birth_date=datetime.now(),
                gender=Gender.male,
                is_admin=False,
                is_active=True,
                user_id=claiming_user_id,
            )

            try:
                member = fc.add_member(
                    db,
                    invitation.family_id,
                    member_data,
                    claiming_user_id
                )

                invitation.used_at = datetime.now(timezone.utc)
                invitation.used_by_user_id = claiming_user_id
                invitation.is_active = False

                db.commit()

                return True, "Вы успешно присоединились к семье", member

            except Exception as e:
                logger.error(f"Ошибка при создании члена семьи: {str(e)}")
                db.rollback()
                return False, f"Ошибка при создании карточки: {str(e)}", None

        elif invitation.invitation_type == 'claim_member':
            member = fc.get_member_by_id(db, invitation.target_member_id)
            if not member:
                return False, "Карточка не найдена", None

            if member.user_id is not None:
                return False, "Эта карточка уже привязана к другому пользователю", None

            member.user_id = claiming_user_id
            member.is_active = True


            invitation.used_at = datetime.now(timezone.utc)
            invitation.used_by_user_id = claiming_user_id
            invitation.is_active = False

            db.commit()
            db.refresh(member)

            return True, "Карточка успешно привязана к вашему аккаунту", member

        return False, "Неизвестный тип приглашения", None

    @staticmethod
    def deactivate_invitation(db: Session, invitation_id: int, user_id: int) -> bool:
        """Деактивировать приглашение (отозвать)"""
        invitation = db.query(Invitation).filter(Invitation.id == invitation_id).first()
        if not invitation:
            return False

        from backend.app.crud.family import family_crud
        is_admin = family_crud.is_family_admin(db, user_id, invitation.family_id)

        if invitation.created_by_user_id != user_id and not is_admin:
            return False

        invitation.is_active = False
        db.commit()
        return True


invitation_crud = InvitationCRUD()