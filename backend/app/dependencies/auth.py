from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.crud import user_crud
from app.core.security import decode_token
from app.models.user import User

# ← Критично: используем абсолютный путь "/auth/login"
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login",
    description="JWT токен после логина"
)

async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
) -> Optional[User]:
    # ... ваш код проверки токена ...
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # ... остальная логика ...
    user_id = payload.get("sub")
    if not user_id:
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = user_crud.get_user_by_id(db, int(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

async def get_current_active_user(
        current_user: User = Depends(get_current_user)
) -> User:
    return current_user