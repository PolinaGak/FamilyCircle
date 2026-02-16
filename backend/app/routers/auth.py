import random
import time
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse
from app.core.config import settings
from app.core.email_utils import email_service
from app.models.user import User
from app.schemas.auth import UserCreate, UserLogin, TokenResponse, UserResponse
from app.database import get_db
from app.crud import user_crud
from datetime import datetime, timedelta
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
decode_verification_token
)
import logging


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register")
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

    return {
        "success": True,
        "message": "Email успешно подтвержден! Теперь вы можете войти в систему.",
        "redirect_url": f"{settings.FRONTEND_URL}/login?verified=true"
    }


@router.post("/login")
async def login(
        user_data: UserLogin,
        response: Response,
        db: Session = Depends(get_db)
):
    # Защита от timing attacks
    base_delay = 0.5
    random_delay = random.uniform(0, 0.3)
    time.sleep(base_delay + random_delay)


    user = await  user_crud.authenticate_user(db, user_data.email, user_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail= "Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ваш email не подтверждён! Проверьте вашу почту.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})


    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )

    logger.info(f"User {user.id} logged in successfully")

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.from_orm(user)
    }