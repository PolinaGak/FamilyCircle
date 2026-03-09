import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.security import create_verification_token, decode_verification_token


class TestRegister:
    """Тесты регистрации"""

    def test_register_success(self, client: TestClient, test_user_data):
        """Успешная регистрация нового пользователя"""
        response = client.post("/auth/register", json=test_user_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "Проверьте вашу почту для подтверждения"
        assert data["data"]["email"] == test_user_data["email"]

    def test_register_existing_email(self, client: TestClient, test_user_data, db_session: Session):
        """Регистрация с существующим email"""
        # Сначала создаем пользователя
        from app.crud import user_crud
        from app.schemas.auth import UserCreate

        user_create = UserCreate(**test_user_data)
        user_crud.register_user(db_session, user_create)

        # Пытаемся зарегистрироваться снова
        response = client.post("/auth/register", json=test_user_data)

        assert response.status_code == 400
        assert "уже существует" in response.json()["detail"]

    @pytest.mark.parametrize("invalid_data,expected_error", [
        ({"email": "not-email", "password": "Test123456", "name": "Test"}, "value is not a valid email"),
        ({"email": "test@example.com", "password": "short", "name": "Test"}, "at least 8 characters"),
        ({"email": "test@example.com", "password": "onlylowercase", "name": "Test"}, "заглавную букву"),
        ({"email": "test@example.com", "password": "NoDigits", "name": "Test"}, "цифру"),
        ({"email": "test@example.com", "password": "Test123456", "name": "A"}, "min_length"),
    ])
    def test_register_validation(self, client: TestClient, invalid_data, expected_error):
        """Проверка валидации полей"""
        response = client.post("/auth/register", json=invalid_data)
        assert response.status_code == 422
        assert expected_error in str(response.json())


class TestVerifyEmail:
    """Тесты подтверждения email"""

    def test_verify_email_success(self, client: TestClient, db_session: Session, test_user_data):
        """Успешное подтверждение email"""
        # Сначала регистрируем пользователя
        from app.crud import user_crud
        from app.schemas.auth import UserCreate

        user_create = UserCreate(**test_user_data)
        user = user_crud.register_user(db_session, user_create)

        # Создаем токен верификации
        token = create_verification_token(user.id)

        # Подтверждаем email
        response = client.get(f"/auth/verify-email?token={token}")

        assert response.status_code == 200
        assert response.json()["success"] is True

        # Проверяем, что пользователь подтвержден
        verified_user = user_crud.get_user_by_id(db_session, user.id)
        assert verified_user.is_verified is True

    def test_verify_email_invalid_token(self, client: TestClient):
        """Неверный токен верификации"""
        response = client.get("/auth/verify-email?token=invalid-token")

        assert response.status_code == 400
        assert "Ссылка устарела или недействительна" in response.json()["detail"]


class TestLogin:
    """Тесты входа"""

    def test_login_success(self, client: TestClient, verified_user, test_user_data):
        """Успешный вход с подтвержденным email"""
        response = client.post("/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == test_user_data["email"]
        assert data["user"]["is_verified"] is True

        # Проверяем, что refresh token установлен в cookie
        assert "refresh_token" in response.cookies

    def test_login_wrong_password(self, client: TestClient, verified_user, test_user_data):
        """Неверный пароль"""
        response = client.post("/auth/login", json={
            "email": test_user_data["email"],
            "password": "WrongPassword123"
        })

        assert response.status_code == 401
        assert "Неверный email или пароль" in response.json()["detail"]

    def test_login_unverified(self, client: TestClient, db_session: Session, test_user_data):
        """Вход с неподтвержденным email"""
        from app.crud import user_crud
        from app.schemas.auth import UserCreate

        user_create = UserCreate(**test_user_data)
        user_crud.register_user(db_session, user_create)

        response = client.post("/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })

        assert response.status_code == 401
        assert "Неверный email или пароль" in response.json()["detail"]

    def test_login_nonexistent_user(self, client: TestClient):
        """Несуществующий пользователь"""
        response = client.post("/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "Test123456"
        })

        assert response.status_code == 401
        assert "Неверный email или пароль" in response.json()["detail"]


class TestLogout:
    """Тесты выхода"""

    def test_logout_success(self, client: TestClient, verified_user, test_user_data):
        """Успешный выход"""
        # Сначала логинимся
        login_response = client.post("/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        refresh_token = login_response.cookies.get("refresh_token")

        # Выходим
        response = client.post("/auth/logout")

        assert response.status_code == 200
        assert response.json()["success"] is True

        # Проверяем, что cookie удалена
        assert response.cookies.get("refresh_token") is None or response.cookies.get("refresh_token") == ""


class TestRefreshToken:
    """Тесты обновления токена"""

    def test_refresh_token_success(self, client: TestClient, verified_user, test_user_data):
        """Успешное обновление access token"""
        # Логинимся и получаем refresh token
        login_response = client.post("/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })

        refresh_token = login_response.cookies.get("refresh_token")
        client.cookies.set("refresh_token", refresh_token)

        # Обновляем токен
        response = client.post("/auth/refresh")

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == test_user_data["email"]

    def test_refresh_token_missing(self, client: TestClient):
        """Отсутствует refresh token"""
        response = client.post("/auth/refresh")

        assert response.status_code == 401
        assert "Refresh token не найден" in response.json()["detail"]


class TestPasswordReset:
    """Тесты сброса пароля"""

    def test_password_reset_request_success(self, client: TestClient, verified_user):
        """Запрос на сброс пароля"""
        response = client.post("/auth/password-reset-request", json={
            "email": verified_user.email
        })

        assert response.status_code == 200
        assert response.json()["success"] is True
        # Проверяем, что ответ не раскрывает информацию о существовании email
        assert "Если пользователь с таким email существует" in response.json()["message"]

    def test_password_reset_success(self, client: TestClient, verified_user, db_session: Session):
        """Успешный сброс пароля"""
        from app.core.security import create_password_reset_token, verify_password

        # Создаем токен сброса
        token = create_password_reset_token(verified_user.id)

        # Сбрасываем пароль
        new_password = "NewPassword789"
        response = client.post("/auth/password-reset", json={
            "token": token,
            "new_password": new_password
        })

        assert response.status_code == 200
        assert response.json()["success"] is True

        # Проверяем, что пароль действительно изменился
        from app.crud import user_crud
        user = user_crud.get_user_by_id(db_session, verified_user.id)
        assert verify_password(new_password, user.password_hash) is True

    def test_password_reset_invalid_token(self, client: TestClient):
        """Неверный токен сброса"""
        response = client.post("/auth/password-reset", json={
            "token": "invalid-token",
            "new_password": "NewPassword789"
        })

        assert response.status_code == 400
        assert "Ссылка устарела или недействительна" in response.json()["detail"]


class TestChangePassword:
    """Тесты смены пароля (авторизованный пользователь)"""

    def test_change_password_success(self, client: TestClient, verified_user, test_user_data):
        """Успешная смена пароля"""
        # Логинимся
        login_response = client.post("/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        access_token = login_response.json()["access_token"]

        # Меняем пароль
        new_password = "NewPassword789"
        response = client.post(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "current_password": test_user_data["password"],
                "new_password": new_password
            }
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

        # Проверяем, что можно войти с новым паролем
        new_login_response = client.post("/auth/login", json={
            "email": test_user_data["email"],
            "password": new_password
        })
        assert new_login_response.status_code == 200

    def test_change_password_wrong_current(self, client: TestClient, verified_user, test_user_data):
        """Неверный текущий пароль"""
        # Логинимся
        login_response = client.post("/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        access_token = login_response.json()["access_token"]

        # Пытаемся сменить пароль с неверным текущим
        response = client.post(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "current_password": "WrongPassword123",
                "new_password": "NewPassword789"
            }
        )

        assert response.status_code == 400
        assert "Неверный текущий пароль" in response.json()["detail"]

    def test_change_password_unauthorized(self, client: TestClient):
        """Смена пароля без авторизации"""
        response = client.post(
            "/auth/change-password",
            json={
                "current_password": "anything",
                "new_password": "NewPassword789"
            }
        )

        assert response.status_code == 401
        assert "Не авторизован" in response.json()["detail"]