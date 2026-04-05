from typing import Optional
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

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email.ilike(email)).first()

    @staticmethod
    def get_active_user_by_email(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(
            User.email.ilike(email),
            User.is_deleted == False
        ).first()

    @staticmethod
    def user_exists(db: Session, email: str) -> bool:
        return db.query(User).filter(User.email.ilike(email)).first() is not None

    @staticmethod
    def register_user(db: Session, new_user: UserCreate) -> User:
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
            logger.info(f"Created user: {db_user.id}, email: {db_user.email}")
            return db_user
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            db.rollback()
            raise

    @staticmethod
    def verify_user_email(db: Session, user_id: int) -> bool:
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
    def authenticate_user(
            db: Session,
            email: str,
            password: str
    ) -> Optional[User]:
        try:
            user = UserCRUD.get_active_user_by_email(db, email)

            if not user:
                logger.info(f"Login attempt - user not found: {email}")
                return None

            if not verify_password(password, user.password_hash):
                logger.info(f"Login attempt - wrong password: {email}")
                return None

            if not user.is_verified:
                logger.info(f"Login blocked: user {user.id} email not verified")
                return None

            logger.info(f"Successful login: {email}")
            return user

        except Exception as e:
            logger.error(f"Authentication error for {email}: {str(e)}")
            return None

    @staticmethod
    def update_password(db: Session, user_id: int, new_password: str) -> bool:
        try:
            user = UserCRUD.get_user_by_id(db, user_id)
            if not user:
                logger.warning(f"User {user_id} not found for password update")
                return False

            if verify_password(new_password, user.password_hash):
                logger.warning(f"New password same as old for user {user_id}")
                return False

            user.password_hash = get_password_hash(new_password)
            db.commit()
            db.refresh(user)
            logger.info(f"Password updated for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating password for user {user_id}: {str(e)}")
            db.rollback()
            return False

    @staticmethod
    def get_user_by_email_for_reset(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(
            User.email.ilike(email),
            User.is_deleted == False,
            User.is_verified == True
        ).first()

    @staticmethod
    def soft_delete_user(db: Session, user_id: int) -> bool:
        try:
            user = UserCRUD.get_user_by_id(db, user_id)
            if not user:
                return False

            user.is_deleted = True
            db.commit()
            logger.info(f"User {user_id} soft deleted")
            return True
        except Exception as e:
            logger.error(f"Error soft deleting user {user_id}: {str(e)}")
            db.rollback()
            return False

    @staticmethod
    def get_user_stats(db: Session) -> dict:
        total = db.query(User).count()
        verified = db.query(User).filter(User.is_verified == True).count()
        active = db.query(User).filter(User.is_deleted == False).count()

        return {
            "total": total,
            "verified": verified,
            "active": active,
            "unverified": total - verified,
            "deleted": total - active
        }


user_crud = UserCRUD()