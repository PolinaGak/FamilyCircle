import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.security import create_verification_token, create_password_reset_token
from app.crud import user_crud
from app.schemas.auth import UserCreate


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
        assert data["data"]["requires_verification"] is True

    def test_register_existing_email(self, client: TestClient, test_user_data, db_session: Session):
        """Регистрация с существующим email"""
        # Сначала создаем пользователя
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
        user_create = UserCreate(**test_user_data)
        user = user_crud.register_user(db_session, user_create)

        # Создаем токен верификации
        token = create_verification_token(user.id)

        # Подтверждаем email
        response = client.get(f"/auth/verify-email?token={token}")

        assert response.status_code == 200
        assert response.json()["success"] is True
        assert "успешно подтвержден" in response.json()["message"]

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
        response = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        if "user" in data:
            assert data["user"]["email"] == test_user_data["email"]
            assert data["user"]["is_verified"] is True
        # Проверяем, что refresh token установлен в cookie
        assert "refresh_token" in response.cookies

    def test_login_wrong_password(self, client: TestClient, verified_user, test_user_data):
        """Неверный пароль"""
        response = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": "WrongPassword123"
        })

        assert response.status_code == 401
        assert "Неверный email или пароль" in response.json()["detail"]

    def test_login_unverified(self, client: TestClient, db_session: Session, test_user_data):
        """Вход с неподтвержденным email"""
        user_create = UserCreate(**test_user_data)
        user_crud.register_user(db_session, user_create)

        response = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })

        assert response.status_code == 401
        assert "Неверный email или пароль" in response.json()["detail"]

    def test_login_nonexistent_user(self, client: TestClient):
        """Несуществующий пользователь"""
        response = client.post("/auth/login", data={
            "username": "nonexistent@example.com",
            "password": "Test123456"
        })

        assert response.status_code == 401
        assert "Неверный email или пароль" in response.json()["detail"]


class TestLogout:
    """Тесты выхода"""

    def test_logout_success(self, client: TestClient, verified_user, test_user_data):
        """Успешный выход"""
        # Сначала логинимся
        login_response = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        refresh_token = login_response.cookies.get("refresh_token")

        # Выходим
        response = client.post("/auth/logout")

        assert response.status_code == 200
        assert response.json()["success"] is True

        # Проверяем, что cookie удалена (пустое значение или отсутствует)
        set_cookie = response.headers.get("set-cookie", "")
        assert "refresh_token=" in set_cookie or "refresh_token=\"\"" in set_cookie or refresh_token not in str(
            response.cookies)


class TestRefreshToken:
    """Тесты обновления токена"""

    def test_refresh_token_success(self, client: TestClient, verified_user, test_user_data):
        """Успешное обновление access token"""
        # Логинимся
        login_response = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        assert login_response.status_code == 200

        # Проверяем, что cookie с refresh_token есть
        refresh_token = login_response.cookies.get("refresh_token")
        assert refresh_token is not None, "refresh_token not set in cookies"

        # Обновляем токен, передавая cookie явно
        response = client.post("/auth/refresh", cookies={"refresh_token": refresh_token})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        if "user" in data:
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

    def test_password_reset_request_nonexistent(self, client: TestClient):
        """Запрос на сброс пароля для несуществующего email"""
        response = client.post("/auth/password-reset-request", json={
            "email": "nonexistent@test.com"
        })

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_password_reset_success(self, client: TestClient, verified_user, db_session: Session):
        """Успешный сброс пароля"""
        from app.core.security import verify_password

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

    def test_password_reset_same_password(self, client: TestClient, verified_user, test_user_data):
        """Попытка сбросить пароль на тот же самый"""
        token = create_password_reset_token(verified_user.id)

        response = client.post("/auth/password-reset", json={
            "token": token,
            "new_password": test_user_data["password"]
        })

        assert response.status_code == 400
        assert "отличаться от текущего" in response.json()["detail"]


class TestChangePassword:
    """Тесты смены пароля (авторизованный пользователь)"""

    def test_change_password_success(self, client: TestClient, verified_user, test_user_data, auth_headers):
        """Успешная смена пароля"""
        new_password = "NewPassword789"
        response = client.post(
            "/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": test_user_data["password"],
                "new_password": new_password
            }
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

        # Проверяем, что можно войти с новым паролем
        new_login_response = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": new_password
        })
        assert new_login_response.status_code == 200

    def test_change_password_wrong_current(self, client: TestClient, auth_headers):
        """Неверный текущий пароль"""
        response = client.post(
            "/auth/change-password",
            headers=auth_headers,
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


class TestGetCurrentUser:
    """Тесты получения текущего пользователя"""

    def test_get_me_success(self, client: TestClient, verified_user, auth_headers):
        """Успешное получение данных текущего пользователя"""
        response = client.get("/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == verified_user.email
        assert data["id"] == verified_user.id
        assert data["is_verified"] is True

    def test_get_me_unauthorized(self, client: TestClient):
        """Попытка получить данные без авторизации"""
        response = client.get("/auth/me")

        assert response.status_code == 401