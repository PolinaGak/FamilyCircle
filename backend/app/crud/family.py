from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_

from app.models.user import User
from app.models.family import Family
from app.models.family_member import FamilyMember
from app.schemas.family import FamilyCreate
from app.schemas.family_member import FamilyMemberCreate, FamilyMemberUpdate
import logging

logger = logging.getLogger(__name__)


class FamilyCRUD:
    """CRUD операции для семей и членов семьи"""

    # ========== FAMILY METHODS ==========

    @staticmethod
    def create_family(db: Session, family_data: FamilyCreate, admin_user_id: int) -> Family:
        """Создать новую семью (пользователь становится администратором)"""
        try:
            family = Family(
                name=family_data.name.strip(),
                admin_user_id=admin_user_id
            )

            db.add(family)
            db.flush()  # Получаем ID без коммита

            # Создаем запись администратора в family_member
            from datetime import datetime

            admin_member = FamilyMember(
                family_id=family.id,
                user_id=admin_user_id,
                first_name="Администратор",  # Временное имя
                last_name="Семьи",  # Временная фамилия
                birth_date=datetime.now(),  # Сегодняшняя дата
                is_admin=True,
                approved=True,
                is_active=True,
                created_by_user_id=admin_user_id
            )
            db.add(admin_member)

            db.commit()
            db.refresh(family)

            logger.info(f"Семья '{family.name}' создана пользователем {admin_user_id}")
            return family

        except Exception as e:
            logger.error(f"Ошибка при создании семьи: {str(e)}")
            db.rollback()
            raise

    @staticmethod
    def get_family_by_id(db: Session, family_id: int) -> Optional[Family]:
        """Получить семью по ID"""
        return db.query(Family).filter(Family.id == family_id).first()

    @staticmethod
    def get_family_with_members(db: Session, family_id: int) -> Optional[Family]:
        """Получить семью со всеми членами"""
        return db.query(Family) \
            .options(joinedload(Family.members)) \
            .filter(Family.id == family_id) \
            .first()

    @staticmethod
    def get_user_families(db: Session, user_id: int) -> List[Family]:
        """Получить все семьи, где пользователь является членом"""
        return db.query(Family) \
            .join(FamilyMember, Family.id == FamilyMember.family_id) \
            .filter(FamilyMember.user_id == user_id) \
            .all()

    @staticmethod
    def update_family(db: Session, family_id: int, name: str) -> Optional[Family]:
        """Обновить название семьи"""
        family = FamilyCRUD.get_family_by_id(db, family_id)
        if not family:
            return None

        family.name = name.strip()
        db.commit()
        db.refresh(family)
        return family

    @staticmethod
    def delete_family(db: Session, family_id: int) -> bool:
        """Удалить семью (только администратор)"""
        try:
            family = FamilyCRUD.get_family_by_id(db, family_id)
            if not family:
                return False

            # Сначала удаляем всех членов семьи
            db.query(FamilyMember).filter(FamilyMember.family_id == family_id).delete()
            # Потом саму семью
            db.delete(family)
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка при удалении семьи {family_id}: {str(e)}")
            db.rollback()
            return False

    # ========== FAMILY MEMBER METHODS ==========

    @staticmethod
    def add_member(
            db: Session,
            family_id: int,
            member_data: FamilyMemberCreate,
            created_by_user_id: int
    ) -> FamilyMember:
        """Добавить члена в семью"""
        try:
            # Проверяем, не существует ли уже такой член
            if member_data.user_id:
                existing = db.query(FamilyMember).filter(
                    FamilyMember.family_id == family_id,
                    FamilyMember.user_id == member_data.user_id
                ).first()
                if existing:
                    raise ValueError(f"Пользователь уже является членом этой семьи")

            member = FamilyMember(
                family_id=family_id,
                user_id=member_data.user_id,
                first_name=member_data.first_name.strip(),
                last_name=member_data.last_name.strip(),
                patronymic=member_data.patronymic.strip() if member_data.patronymic else None,
                birth_date=member_data.birth_date,
                death_date=member_data.death_date,
                phone=member_data.phone,
                workplace=member_data.workplace,
                residence=member_data.residence,
                is_admin=member_data.is_admin,
                created_by_user_id=created_by_user_id,
                # Если добавляет администратор, сразу подтверждаем
                approved=member_data.approved
            )

            db.add(member)
            db.commit()
            db.refresh(member)

            logger.info(f"Член семьи {member.id} добавлен в семью {family_id}")
            return member

        except Exception as e:
            logger.error(f"Ошибка при добавлении члена семьи: {str(e)}")
            db.rollback()
            raise

    @staticmethod
    def get_member_by_id(db: Session, member_id: int) -> Optional[FamilyMember]:
        """Получить члена семьи по ID"""
        return db.query(FamilyMember).filter(FamilyMember.id == member_id).first()

    @staticmethod
    def get_family_members(db: Session, family_id: int) -> List[FamilyMember]:
        """Получить всех членов семьи"""
        return db.query(FamilyMember) \
            .filter(FamilyMember.family_id == family_id) \
            .order_by(FamilyMember.last_name, FamilyMember.first_name) \
            .all()

    @staticmethod
    def update_member(
            db: Session,
            member_id: int,
            update_data: FamilyMemberUpdate
    ) -> Optional[FamilyMember]:
        """Обновить данные члена семьи"""
        member = FamilyCRUD.get_member_by_id(db, member_id)
        if not member:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            if value is not None:
                setattr(member, key, value)

        db.commit()
        db.refresh(member)
        return member

    @staticmethod
    def approve_member(db: Session, member_id: int, approved: bool = True) -> Optional[FamilyMember]:
        """Подтвердить члена семьи (администратором)"""
        member = FamilyCRUD.get_member_by_id(db, member_id)
        if not member:
            return None

        member.approved = approved
        db.commit()
        db.refresh(member)
        return member

    @staticmethod
    def remove_member(db: Session, member_id: int) -> bool:
        """Удалить члена из семьи"""
        try:
            member = FamilyCRUD.get_member_by_id(db, member_id)
            if not member:
                return False

            from app.models.invitation import \
                Invitation
            db.query(Invitation).filter(Invitation.target_member_id == member_id).update(
                {"target_member_id": None}, synchronize_session=False
            )

            db.delete(member)
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка при удалении члена семьи {member_id}: {str(e)}")
            db.rollback()
            return False

    @staticmethod
    def is_family_admin(db: Session, user_id: int, family_id: int) -> bool:
        """Проверить, является ли пользователь администратором семьи"""
        return db.query(FamilyMember).filter(
            FamilyMember.family_id == family_id,
            FamilyMember.user_id == user_id,
            FamilyMember.is_admin == True
        ).first() is not None

    @staticmethod
    def is_family_member(db: Session, user_id: int, family_id: int) -> bool:
        """Проверить, является ли пользователь членом семьи"""
        return db.query(FamilyMember).filter(
            FamilyMember.family_id == family_id,
            FamilyMember.user_id == user_id
        ).first() is not None

    # В класс FamilyCRUD добавить:

    @staticmethod
    def leave_family(db: Session, user_id: int, family_id: int) -> FamilyMember:
        """
        Пользователь покидает семью: отвязывает свою учётную запись от карточки члена семьи.
        Если пользователь был администратором, проверяет наличие других администраторов.

        Возвращает обновлённый объект FamilyMember.

        Raises:
            ValueError: с описанием причины, если операция невозможна.
        """
        member = db.query(FamilyMember).filter(
            FamilyMember.family_id == family_id,
            FamilyMember.user_id == user_id,
            FamilyMember.is_active == True
        ).first()

        if not member:
            raise ValueError("Вы не являетесь активным членом этой семьи")

        # Если пользователь - администратор, проверяем, есть ли другие администраторы
        if member.is_admin:
            admin_count = db.query(FamilyMember).filter(
                FamilyMember.family_id == family_id,
                FamilyMember.is_admin == True,
                FamilyMember.is_active == True
            ).count()

            if admin_count <= 1:
                raise ValueError(
                    "Вы последний администратор. Невозможно покинуть семью. Назначьте другого администратора или удалите семью.")

        # Отвязываем пользователя от карточки
        member.user_id = None
        # Снимаем права администратора, если были
        if member.is_admin:
            member.is_admin = False

        db.commit()
        db.refresh(member)

        logger.info(f"Пользователь {user_id} покинул семью {family_id}, карточка {member.id} отвязана")
        return member

    @staticmethod
    def transfer_admin_rights(db: Session, current_user_id: int, family_id: int, target_member_id: int) -> FamilyMember:
        """
        Передать права администратора другому члену семьи.

        Возвращает обновлённый объект целевого члена семьи.

        Raises:
            ValueError: с описанием причины, если операция невозможна.
        """
        # Проверяем, что текущий пользователь - администратор
        current_member = db.query(FamilyMember).filter(
            FamilyMember.family_id == family_id,
            FamilyMember.user_id == current_user_id,
            FamilyMember.is_active == True
        ).first()

        if not current_member or not current_member.is_admin:
            raise ValueError("Только администратор может передавать права")

        # Проверяем, что целевой член существует и активен
        target_member = db.query(FamilyMember).filter(
            FamilyMember.id == target_member_id,
            FamilyMember.family_id == family_id,
            FamilyMember.is_active == True
        ).first()

        if not target_member:
            raise ValueError("Целевой член семьи не найден или неактивен")

        if target_member.is_admin:
            raise ValueError("Целевой член уже является администратором")

        # Передаём права
        current_member.is_admin = False
        target_member.is_approved = True
        target_member.is_admin = True

        db.commit()
        db.refresh(target_member)

        logger.info(
            f"Права администратора переданы от пользователя {current_user_id} к члену {target_member_id} в семье {family_id}")
        return target_member

# Создаем экземпляр для импорта
family_crud = FamilyCRUD()