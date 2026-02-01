from typing import Optional
from pydantic.v1 import EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.user import User
from app.schemas.auth import UserCreate
from datetime import datetime, timezone
from app.core.security import get_password_hash
import logging


logger = logging.getLogger(__name__)


class UserCRUD:
    """CRUD операции для пользователей"""

    @staticmethod
    def get_user_by_email(db: Session, email: EmailStr) -> Optional[User]:
        """Получить пользователя по email (case-insensitive)"""
        return db.query(User).filter(User.email.ilike(email)).first()

    @staticmethod
    def register_user(db: Session, new_user: UserCreate) -> User:
        """Создать нового пользователя"""

        existing_user = UserCRUD.get_user_by_email(db, new_user.email)
        if existing_user:
            raise ValueError(f"Пользователь с email {new_user.email} уже существует")


        hashed_password = get_password_hash(new_user.password)
        db_user = User(
            email=new_user.email.lower().strip(),
            password_hash=hashed_password,
            name=new_user.name.strip(),
            created_at=datetime.now(timezone.utc),
            is_deleted=False,
            is_verified=False
        )

        try:
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            logger.info(f"Создан новый пользователь: {db_user.id}, email: {db_user.email}")
            return db_user
        except Exception as e:
            logger.error(f"Ошибка при создании пользователя: {str(e)}")
            db.rollback()
            raise
