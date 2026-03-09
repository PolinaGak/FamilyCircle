import pytest
from app.schemas.auth import UserCreate, PasswordReset, PasswordChange
from pydantic import ValidationError


class TestUserCreateValidation:
    """Тесты валидации схем"""

    def test_valid_user_create(self):
        """Валидные данные проходят валидацию"""
        user = UserCreate(
            email="test@example.com",
            password="Test123456",
            name="Test User"
        )
        assert user.email == "test@example.com"
        assert user.name == "Test User"

    @pytest.mark.parametrize("email,should_fail", [
        ("test@example.com", False),
        ("invalid-email", True),
        ("test@.com", True),
        ("", True),
    ])
    def test_email_validation(self, email, should_fail):
        """Проверка валидации email"""
        data = {
            "email": email,
            "password": "Test123456",
            "name": "Test"
        }

        if should_fail:
            with pytest.raises(ValidationError):
                UserCreate(**data)
        else:
            user = UserCreate(**data)
            assert user.email == email

    @pytest.mark.parametrize("password,should_fail", [
        ("Test123456", False),
        ("short", True),
        ("onlylowercase123", True),
        ("OnlyUppercase", True),
        ("NoDigitsHere", True),
        ("", True),
    ])
    def test_password_strength(self, password, should_fail):
        """Проверка требований к паролю"""
        data = {
            "email": "test@example.com",
            "password": password,
            "name": "Test"
        }

        if should_fail:
            with pytest.raises(ValidationError):
                UserCreate(**data)
        else:
            user = UserCreate(**data)
            assert user.password == password