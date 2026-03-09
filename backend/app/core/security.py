from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from app.core.config import settings
from typing import Optional, Literal, Dict, Any
import logging
import secrets

logger = logging.getLogger(__name__)

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__time_cost=3,
    argon2__memory_cost=65536,
    argon2__parallelism=4,
    argon2__hash_len=32,
    argon2__salt_len=16
)

TokenType = Literal["access", "refresh", "verify", "reset"]


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def _create_token(
        data: Dict[str, Any],
        token_type: TokenType,
        expires_delta: timedelta
) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)

    to_encode.update({
        "exp": now + expires_delta,
        "iat": now,
        "type": token_type
    })

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(data: Dict[str, Any]) -> str:
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return _create_token(data, "access", expires_delta)


def create_refresh_token(data: Dict[str, Any]) -> str:
    expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return _create_token(data, "refresh", expires_delta)


def create_verification_token(user_id: int) -> str:
    expires_delta = timedelta(hours=settings.VERIFY_TOKEN_EXPIRE_HOURS)
    return _create_token({"sub": str(user_id)}, "verify", expires_delta)


def create_password_reset_token(user_id: int) -> str:
    expires_delta = timedelta(hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
    return _create_token({"sub": str(user_id)}, "reset", expires_delta)


def _decode_token(
        token: str,
        token_type: Optional[TokenType] = None,
        required_fields: Optional[list[str]] = None
) -> Optional[Dict[str, Any]]:
    """Универсальная функция декодирования токенов"""
    if required_fields is None:
        required_fields = ["exp", "iat", "type"]

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"require": required_fields}
        )

        if token_type and payload.get("type") != token_type:
            logger.warning(f"Wrong token type. Expected {token_type}, got {payload.get('type')}")
            return None

        return payload

    except JWTError as e:
        logger.error(f"Invalid {token_type or 'unknown'} token: {str(e)}")
        return None


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Декодировать любой токен без проверки типа"""
    return _decode_token(token)


def decode_typed_token(token: str, expected_type: TokenType) -> Optional[int]:
    """Универсальная функция для декодирования типизированных токенов с user_id"""
    payload = _decode_token(token, expected_type, ["exp", "iat", "type", "sub"])

    if not payload:
        return None

    try:
        return int(payload.get("sub"))
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid user_id in {expected_type} token: {str(e)}")
        return None


def decode_verification_token(token: str) -> Optional[int]:
    return decode_typed_token(token, "verify")


def decode_password_reset_token(token: str) -> Optional[int]:
    return decode_typed_token(token, "reset")


def generate_temporary_password(length: int = 12) -> str:
    """Генерация временного пароля для сброса"""
    alphabet = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def get_token_expiration(token: str) -> Optional[datetime]:
    """Получить время истечения токена"""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": False}
        )
        exp = payload.get("exp")
        return datetime.fromtimestamp(exp, timezone.utc) if exp else None
    except JWTError:
        return None


def is_token_expired(token: str) -> bool:
    """Проверить, истек ли токен"""
    exp = get_token_expiration(token)
    return exp is None or exp < datetime.now(timezone.utc)


def get_token_type(token: str) -> Optional[str]:
    """Получить тип токена"""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": False}
        )
        return payload.get("type")
    except JWTError:
        return None