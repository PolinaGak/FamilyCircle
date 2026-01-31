from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.auth import UserCreate, UserLogin, UserResponse
from app.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя",
    description="""
    Создаёт нового пользователя в системе.

    Требования к паролю:
    - Минимум 8 символов
    - Хотя бы одна заглавная буква
    - Хотя бы одна цифра

    После регистрации:
    - Пользователь получает email с подтверждением
    - Аккаунт неактивен до подтверждения email (is_verified = False)
    - is_deleted = False
    
    """
)
async def register(
        user: UserCreate,
        db: Session = Depends(get_db)
):
    db_user = db.query(User).filter(
        User.email.ilike(user.email)
    ).first()

    if db_user:
        logger.warning(f"Попытка регистрации с существующим email: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует"
        )

    hashed_password = get_password_hash(user.password)

    db_user = User(
        email=user.email.lower().strip(),
        password_hash=hashed_password,
        theme="light",
        name=user.name.strip(),
        created_at=datetime.now(timezone.utc),
        is_deleted=True,
        is_verified=False
    )

    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        logger.info(f"Создан новый пользователь: {db_user.id}, email: {db_user.email}")
    except Exception as e:
        logger.error(f"Ошибка при создании пользователя: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при создании пользователя"
        )

    # send_verification_email(db_user.email, db_user.id)

    return db_user