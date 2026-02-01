from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.auth import UserCreate, UserLogin, UserResponse
from app.database import get_db
from app.crud import UserCRUD
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


async def register(
        user: UserCreate,
        db: Session = Depends(get_db)
):
    try:
        db_user = UserCRUD.register_user(db, user)

        # send_verification_email(db_user.email, db_user.id)

        return db_user

    except ValueError as e:
        logger.warning(f"Попытка регистрации с существующим email: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Ошибка при создании пользователя: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при создании пользователя"
        )