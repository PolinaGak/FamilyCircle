import asyncio
import random
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from backend.app.core.config import settings
from backend.app.core.email_utils import email_service
from backend.app.models import User
from backend.app.schemas.auth import (
    UserCreate, UserResponse, PasswordResetRequest,
    PasswordReset, PasswordChange, LogoutResponse
)
from backend.app.core.security import (
    verify_password, create_access_token, create_refresh_token,
    decode_token, decode_verification_token, decode_password_reset_token
)
from backend.app.database import get_db
from backend.app.crud import user_crud
from backend.app.dependencies.auth import get_current_active_user
import logging

from backend.app.schemas.auth import UserUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

ERROR_MESSAGES = {
    "user_not_found": "Пользователь не найден",
    "invalid_credentials": "Неверный email или пароль",
    "email_not_verified": "Ваш email не подтверждён! Проверьте вашу почту.",
    "invalid_token": "Недействительный токен",
    "token_expired": "Ссылка устарела или недействительна",
    "invalid_refresh_token": "Refresh token недействителен",
    "refresh_token_missing": "Refresh token не найден",
    "unauthorized": "Не авторизован",
    "wrong_password": "Неверный текущий пароль",
    "email_send_error": "Ошибка при отправке письма. Пожалуйста, попробуйте позже."
}

SUCCESS_MESSAGES = {
    "register": "Проверьте вашу почту для подтверждения",
    "email_verified": "Email успешно подтвержден! Теперь вы можете войти в систему.",
    "logout": "Вы успешно вышли из системы",
    "password_reset_request": "Если пользователь с таким email существует, мы отправили письмо для сброса пароля",
    "password_reset": "Пароль успешно изменен. Теперь вы можете войти с новым паролем.",
    "password_changed": "Пароль успешно изменен"
}


def create_auth_response(user, response: Response):
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/auth/refresh"
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user)
    }


@router.post("/register")
async def register(user: UserCreate, db: Session = Depends(get_db)):
    try:
        db_user = user_crud.register_user(db, user)

        if not email_service.send_verification_email(db_user.email, db_user.id):
            logger.warning(f"Failed to send verification email to {db_user.email}")

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": SUCCESS_MESSAGES["register"],
                "data": {
                    "redirect_to": f"{settings.FRONTEND_URL}/verify-pending",
                    "email": user.email,
                    "requires_verification": True
                }
            }
        )

    except ValueError as e:
        logger.warning(f"Registration attempt with existing email: {user.email}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при создании пользователя"
        )


@router.get("/verify-email")
async def verify_email(token: str, db: Session = Depends(get_db)):
    user_id = decode_verification_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES["token_expired"]
        )

    if not user_crud.verify_user_email(db, user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось подтвердить email"
        )

    user = user_crud.get_user_by_id(db, user_id)
    if user:
        email_service.send_welcome_email(user.email, user.name)

    return {
        "success": True,
        "message": SUCCESS_MESSAGES["email_verified"],
        "redirect_url": f"{settings.FRONTEND_URL}/login?verified=true"
    }


@router.post("/login")
async def login(
        response: Response,
        db: Session = Depends(get_db),
        form_data: OAuth2PasswordRequestForm = Depends()
):
    await asyncio.sleep(0.5 + random.uniform(0, 0.3))

    user = user_crud.authenticate_user(db, form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES["invalid_credentials"],
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES["email_not_verified"],
            headers={"WWW-Authenticate": "Bearer"}
        )

    logger.info(f"User {user.id} logged in successfully")

    return create_auth_response(user, response)


@router.post("/logout", response_model=LogoutResponse)
async def logout(response: Response):
    response.delete_cookie(
        key="refresh_token",
        path="/auth/refresh",
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax"
    )

    logger.info("User logged out successfully")
    return {"success": True, "message": SUCCESS_MESSAGES["logout"]}


@router.post("/refresh")
async def refresh_token(request: Request, db: Session = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES["refresh_token_missing"]
        )

    payload = decode_token(refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES["invalid_refresh_token"]
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES["invalid_token"]
        )

    user = user_crud.get_user_by_id(db, int(user_id))
    if not user or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES["user_not_found"]
        )

    new_access_token = create_access_token({"sub": str(user.id)})

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user)
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
        current_user: User = Depends(get_current_active_user)
):
    return current_user


@router.post("/password-reset-request")
async def password_reset_request(
        request_data: PasswordResetRequest,
        db: Session = Depends(get_db)
):
    user = user_crud.get_user_by_email_for_reset(db, request_data.email)

    response_message = {"success": True, "message": SUCCESS_MESSAGES["password_reset_request"]}

    if not user or not user.is_verified:
        await asyncio.sleep(1)
        logger.info(f"Password reset requested for {'non-existent' if not user else 'unverified'} email")
        return response_message

    if not email_service.send_password_reset_email(user.email, user.id, user.name):
        logger.error(f"Failed to send password reset email to {user.email}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES["email_send_error"]
        )

    logger.info(f"Password reset email sent to {user.email}")
    return response_message


@router.post("/password-reset")
@router.post("/password-reset")
async def password_reset(reset_data: PasswordReset, db: Session = Depends(get_db)):
    user_id = decode_password_reset_token(reset_data.token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES["token_expired"]
        )

    user = user_crud.get_user_by_id(db, user_id)
    if not user or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES["user_not_found"]
        )

    if verify_password(reset_data.new_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Новый пароль должен отличаться от текущего"
        )

    if not user_crud.update_password(db, user_id, reset_data.new_password):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при обновлении пароля"
        )

    try:
        email_service.send_email(
            user.email,
            "Пароль успешно изменен",
            f"<p>Здравствуйте, {user.name}!</p><p>Ваш пароль в Family Circle был успешно изменен.</p>"
        )
    except Exception:
        pass

    logger.info(f"Password reset successful for user {user.id}")
    return {"success": True, "message": SUCCESS_MESSAGES["password_reset"]}

@router.post("/change-password")
async def change_password(
        password_data: PasswordChange,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES["wrong_password"]
        )

    if not user_crud.update_password(db, current_user.id, password_data.new_password):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при обновлении пароля"
        )

    try:
        email_service.send_email(
            current_user.email,
            "Пароль изменен",
            f"<p>Здравствуйте, {current_user.name}!</p><p>Ваш пароль в Family Circle был успешно изменен.</p>"
        )
    except Exception:
        pass

    logger.info(f"Password changed for user {current_user.id}")
    return {"success": True, "message": SUCCESS_MESSAGES["password_changed"]}


@router.put("/me", response_model=UserResponse)
async def update_current_user(
        user_data: UserUpdate,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """
    Обновить профиль текущего пользователя (только имя).
    """
    updated_user = user_crud.update_user(db, current_user.id, user_data.name)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )

    logger.info(f"User {current_user.id} updated their profile")
    return updated_user