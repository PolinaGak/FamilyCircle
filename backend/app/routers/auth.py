from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse
from app.core.config import settings
from app.core.email_utils import email_service
from app.schemas.auth import UserCreate, UserLogin, UserResponse
from app.database import get_db
from app.crud import user_crud
from app.core.security import decode_verification_token
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


async def register(
        user: UserCreate,
        db: Session = Depends(get_db)
):
    try:
        db_user = user_crud.register_user(db, user)

        if email_service.send_verification_email(db_user.email, db_user.id):
            logger.info(f"Verification email sent to {db_user.email}")
        else:
            logger.warning(f"Failed to send verification email to {db_user.email}")

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Проверьте вашу почту для подтверждения",
                "data": {
                    "redirect_to": f"{settings.FRONTEND_URL}/verify-pending",
                    "email": user.email,
                    "requires_verification": True
                }
            }
        )

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

@router.get("/verify-email")
async def verify_email(
        token: str,
        db: Session = Depends(get_db)
):
    """
    Подтверждение email по токену из письма
    """
    user_id = decode_verification_token(token)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверная или просроченная ссылка подтверждения"
        )

    success = user_crud.verify_user_email(db, user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось подтвердить email"
        )

    user = user_crud.get_user_by_id(db, user_id)

    if user:
        email_service.send_welcome_email(user.email, user.name)

    # Редирект на страницу успеха
    # Можно вернуть JSON или сделать редирект на фронтенд
    return {
        "success": True,
        "message": "Email успешно подтвержден! Теперь вы можете войти в систему.",
        "redirect_url": f"{settings.FRONTEND_URL}/login?verified=true"
    }


@router.post("/verify-email")
async def verify_email(token: str):
    """Подтверждение email по токену"""
    try:
        user_id = decode_verification_token(token)
        if not user_id:
            raise HTTPException(status_code=400, detail="Неверный или истекший токен")

        user_crud.verify_user_email(user_id)

        return {
            "success": True,
            "message": "Email успешно подтвержден!",
            "data": {
                "redirect_url": f"{settings.FRONTEND_URL}/login",
                "show_notification": True,
                "notification_message": "Email подтвержден! Теперь вы можете войти в систему.",
                "auto_login": False
            }
        }
    except Exception as e:
        logger.error(f"Ошибка подтверждения email: {str(e)}")
        return {
            "success": False,
            "message": "Ошибка подтверждения email",
            "data": {
                "redirect_url": f"{settings.FRONTEND_URL}/register",
                "error": "invalid_token"
            }
        }
