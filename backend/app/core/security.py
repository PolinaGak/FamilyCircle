from passlib.context import CryptContext
from jose import jwt, JWTError, ExpiredSignatureError
from datetime import datetime, timedelta, timezone
from app.core.config import settings
from typing import Optional, Literal
import logging

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

TokenType = Literal["access", "refresh", "verify"]


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def _create_token(
        data: dict,
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


def create_access_token(data: dict) -> str:
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return _create_token(data, "access", expires_delta)


def create_refresh_token(data: dict) -> str:
    expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return _create_token(data, "refresh", expires_delta)


def create_verification_token(user_id: int) -> str:
    expires_delta = timedelta(hours=settings.VERIFY_TOKEN_EXPIRE_HOURS)
    data = {"sub": str(user_id)}
    return _create_token(data, "verify", expires_delta)


def _decode_token(
        token: str,
        required_fields: list[str] = None,
        token_type: Optional[TokenType] = None
) -> Optional[dict]:
    try:
        if required_fields is None:
            required_fields = ["exp", "iat", "type"]

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

    except ExpiredSignatureError:
        logger.error(f"Token expired: {token_type or 'unknown'} token")
        return None
    except JWTError as e:
        logger.error(f"Invalid token ({token_type or 'unknown'}): {str(e)}")
        return None


def decode_token(token: str) -> Optional[dict]:
    return _decode_token(token)


def decode_verification_token(token: str) -> Optional[int]:
    payload = _decode_token(token, ["exp", "iat", "type", "sub"], "verify")

    if not payload:
        return None

    try:
        return int(payload.get("sub"))
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid user_id in verify token: {str(e)}")
        return None