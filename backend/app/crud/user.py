from typing import Optional
from pydantic.v1 import EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.enums import ThemeType
from app.models.user import User
from app.schemas.auth import UserCreate
from datetime import datetime, timezone
from app.core.security import get_password_hash, verify_password
import logging


logger = logging.getLogger(__name__)


class UserCRUD:
    """CRUD операции для пользователей"""

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """Получить пользователя по ID"""
        return db.query(User).filter(User.id == user_id).first()

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
            is_verified=False,
            theme=ThemeType.light
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

    @staticmethod
    def verify_user_email(db: Session, user_id: int) -> bool:
        """Подтвердить email пользователя"""
        db_user = UserCRUD.get_user_by_id(db, user_id)
        if not db_user:
            logger.warning(f"User {user_id} not found for verification")
            return False

        if db_user.is_verified:
            logger.info(f"User {user_id} already verified")
            return True

        db_user.is_verified = True

        try:
            db.commit()
            db.refresh(db_user)
            logger.info(f"User {user_id} email verified successfully")
            return True
        except Exception as e:
            logger.error(f"Error verifying user {user_id}: {str(e)}")
            db.rollback()
            return False

    @staticmethod
    async def authenticate_user(
            db: Session,
            email: str,
            password: str
    ) -> User | None:
        """
        Аутентификация пользователя.
        Возвращает User или None при ошибке.
        """
        try:
            user = db.query(User).filter(
                User.email == email,
                User.is_deleted == False
            ).first()

            if not user:
                logger.info(f"Login attempt - user not found: {email}")
                return None

            if not verify_password(password, user.password_hash):
                logger.info(f"Login attempt - wrong password: {email}")
                return None

            if not user.is_verified:
                logger.info(f"Login blocked: user {user.id} email not verified")
                return user

            logger.info(f"Successful login: {email}")
            return user

        except Exception as e:
            logger.error(f"Authentication error for {email}: {str(e)}")
            return None

user_crud = UserCRUD()