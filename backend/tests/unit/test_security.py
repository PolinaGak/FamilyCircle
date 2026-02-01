import pytest
from app.core.security import verify_password, get_password_hash


def test_password_hashing():
    """Тестирует хеширование паролей с argon2"""
    password = "secure_password_123!"
    hashed = get_password_hash(password)

    # Проверяем, что хеш начинается с $argon2id$
    assert hashed.startswith("$argon2id$")

    # Проверяем, что пароль верифицируется
    assert verify_password(password, hashed) is True

    # Проверяем, что неверный пароль не проходит
    assert verify_password("wrong_password", hashed) is False

    # Проверяем, что разные пароли дают разные хеши
    hashed2 = get_password_hash("another_password")
    assert hashed != hashed2
