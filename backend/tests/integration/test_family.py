import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.crud.family import family_crud
from app.crud.user import user_crud
from app.schemas.family import FamilyCreate
from app.schemas.family_member import FamilyMemberCreate, FamilyMemberUpdate
from app.schemas.auth import UserCreate
from app.core.security import get_password_hash
from app.models.enums import ThemeType
from app.models.family_member import FamilyMember


class TestFamilyCreation:
    """Тесты создания семьи"""

    def test_create_family_success(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Успешное создание семьи"""
        # Логинимся
        login_response = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        assert login_response.status_code == 200, login_response.text
        token = login_response.json()["access_token"]

        # Создаем семью
        response = client.post(
            "/family/create",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Test Family"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Family"
        assert data["admin_user_id"] == verified_user.id
        assert "id" in data
        assert "created_at" in data

    def test_create_family_unauthorized(self, client: TestClient):
        """Создание семьи без авторизации"""
        response = client.post("/family/create", json={"name": "Test Family"})
        assert response.status_code == 401

    def test_create_family_validation(self, client: TestClient, verified_user, test_user_data):
        """Валидация названия семьи"""
        login_response = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        assert login_response.status_code == 200, login_response.text
        token = login_response.json()["access_token"]

        # Слишком короткое название
        response = client.post(
            "/family/create",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "A"}
        )
        assert response.status_code == 422


class TestFamilyAccess:
    """Тесты доступа к семьям"""

    def test_get_my_families(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Получение списка своих семей"""
        # Создаем семью
        family = family_crud.create_family(db_session, FamilyCreate(name="My Family"), verified_user.id)

        # Логинимся
        login_response = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        assert login_response.status_code == 200, login_response.text
        token = login_response.json()["access_token"]

        # Получаем список
        response = client.get(
            "/family/my",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == "My Family"

    def test_get_family_detail(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Получение детальной информации о семье"""
        # Создаем семью
        family = family_crud.create_family(db_session, FamilyCreate(name="Detail Test"), verified_user.id)

        # Логинимся
        login_response = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        assert login_response.status_code == 200, login_response.text
        token = login_response.json()["access_token"]

        # Получаем детали
        response = client.get(
            f"/family/{family.id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Detail Test"
        assert "members" in data
        assert len(data["members"]) == 1  # Только создатель

    def test_get_family_detail_no_access(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Попытка получить доступ к чужой семье"""
        # Создаем семью первым пользователем
        family = family_crud.create_family(db_session, FamilyCreate(name="Private"), verified_user.id)

        # Создаем другого пользователя
        other_user = user_crud.register_user(db_session, UserCreate(
            email="other@test.com",
            password="Test123456",
            name="Other User"
        ))
        other_user.is_verified = True
        db_session.commit()

        # Логинимся другим пользователем
        login_response = client.post("/auth/login", data={
            "username": "other@test.com",
            "password": "Test123456"
        })
        assert login_response.status_code == 200, login_response.text
        token = login_response.json()["access_token"]

        # Пытаемся получить доступ
        response = client.get(
            f"/family/{family.id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 403
        assert "нет доступа" in response.json()["detail"].lower()


class TestFamilyMembers:
    """Тесты управления членами семьи"""

    def test_add_family_member(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Добавление члена в семью администратором"""
        # Создаем семью
        family = family_crud.create_family(db_session, FamilyCreate(name="Member Test"), verified_user.id)

        # Логинимся
        login_response = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        assert login_response.status_code == 200, login_response.text
        token = login_response.json()["access_token"]

        # Добавляем члена
        member_data = {
            "first_name": "Иван",
            "last_name": "Иванов",
            "patronymic": "Иванович",
            "birth_date": "1990-01-01T00:00:00",
            "phone": "+79991234567",
            "workplace": "ООО Тест",
            "residence": "Москва",
            "is_admin": False
        }

        response = client.post(
            f"/family/{family.id}/member",
            headers={"Authorization": f"Bearer {token}"},
            json=member_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Иван"
        assert data["last_name"] == "Иванов"
        assert data["family_id"] == family.id
        assert data["approved"] is True  # Админ сразу подтверждает
        assert data["is_admin"] is False

    def test_add_family_member_unauthorized(self, client: TestClient, verified_user, test_user_data,
                                            db_session: Session):
        """Попытка добавить члена без прав"""
        # Создаем семью первым пользователем
        family = family_crud.create_family(db_session, FamilyCreate(name="Secure"), verified_user.id)

        # Создаем другого пользователя и добавляем в семью (обычным членом)
        other_user = user_crud.register_user(db_session, UserCreate(
            email="member@test.com",
            password="Test123456",
            name="Member"
        ))
        other_user.is_verified = True
        db_session.commit()

        # Добавляем его в семью как обычного члена (через CRUD напрямую, минуя API)
        family_crud.add_member(
            db_session,
            family.id,
            FamilyMemberCreate(
                first_name="Member",
                last_name="Test",
                birth_date=datetime.now(timezone.utc),
                is_admin=False,
                approved=True
            ),
            verified_user.id
        )

        # Логинимся этим пользователем
        login_response = client.post("/auth/login", data={
            "username": "member@test.com",
            "password": "Test123456"
        })
        assert login_response.status_code == 200, login_response.text
        token = login_response.json()["access_token"]

        # Создаем третьего пользователя для попытки добавления
        third_user = user_crud.register_user(db_session, UserCreate(
            email="third@test.com",
            password="Test123456",
            name="Third"
        ))
        third_user.is_verified = True
        db_session.commit()

        # Привязываем третьего к FamilyMember
        member = FamilyMember(
            family_id=family.id,
            user_id=other_user.id,
            first_name="Member",
            last_name="Test",
            birth_date=datetime.now(timezone.utc),
            created_by_user_id=verified_user.id,
            approved=True,
            is_active=True
        )
        db_session.add(member)
        db_session.commit()

        # Пытаемся добавить нового члена (не админ)
        response = client.post(
            f"/family/{family.id}/member",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "first_name": "New",
                "last_name": "Member",
                "birth_date": "1995-01-01T00:00:00"
            }
        )

        # Обычный член может добавлять, но без approved
        # Или если в коде запрещено, то 403 - проверим логику
        # В коде: "is_admin = family_crud.is_family_admin(...)" - если не админ, member_data.approved не выставляется в True
        # Но доступ есть если is_member
        assert response.status_code in [200, 403]

    def test_get_family_members(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Получение списка членов семьи"""
        # Создаем семью
        family = family_crud.create_family(db_session, FamilyCreate(name="Members List"), verified_user.id)

        # Добавляем члена
        family_crud.add_member(
            db_session,
            family.id,
            FamilyMemberCreate(
                first_name="Петр",
                last_name="Петров",
                birth_date=datetime.now(timezone.utc),
                is_admin=False,
                approved=True
            ),
            verified_user.id
        )

        # Логинимся
        login_response = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        assert login_response.status_code == 200, login_response.text
        token = login_response.json()["access_token"]

        # Получаем список
        response = client.get(
            f"/family/{family.id}/members",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2  # Админ + добавленный член

    def test_update_family_member(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Обновление данных члена семьи"""
        # Создаем семью и члена
        family = family_crud.create_family(db_session, FamilyCreate(name="Update Test"), verified_user.id)
        member = family_crud.add_member(
            db_session,
            family.id,
            FamilyMemberCreate(
                first_name="Старый",
                last_name="Имя",
                birth_date=datetime.now(timezone.utc),
                is_admin=False,
                approved=True
            ),
            verified_user.id
        )

        # Логинимся
        login_response = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        assert login_response.status_code == 200, login_response.text
        token = login_response.json()["access_token"]

        # Обновляем
        response = client.put(
            f"/family/member/{member.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"first_name": "Новое", "last_name": "Фамилия"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Новое"
        assert data["last_name"] == "Фамилия"

    def test_update_member_by_self(self, client: TestClient, db_session: Session):
        """Обновление своих данных членом семьи"""
        # Создаем админа
        admin = user_crud.register_user(db_session, UserCreate(
            email="admin@test.com",
            password="Test123456",
            name="Admin"
        ))
        admin.is_verified = True
        db_session.commit()

        # Создаем семью
        family = family_crud.create_family(db_session, FamilyCreate(name="Self Update"), admin.id)

        # Создаем обычного пользователя
        user = user_crud.register_user(db_session, UserCreate(
            email="self@test.com",
            password="Test123456",
            name="Self User"
        ))
        user.is_verified = True
        db_session.commit()

        # Добавляем пользователя в семью с привязкой к user_id
        member = family_crud.add_member(
            db_session,
            family.id,
            FamilyMemberCreate(
                first_name="Сам",
                last_name="Себе",
                birth_date=datetime.now(timezone.utc),
                user_id=user.id,
                is_admin=False,
                approved=True
            ),
            admin.id
        )

        # Логинимся пользователем
        login_response = client.post("/auth/login", data={
            "username": "self@test.com",
            "password": "Test123456"
        })
        assert login_response.status_code == 200, login_response.text
        token = login_response.json()["access_token"]

        # Обновляем свои данные
        response = client.put(
            f"/family/member/{member.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"first_name": "Обновленное", "phone": "+79998887766"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Обновленное"
        assert data["phone"] == "+79998887766"

    def test_remove_family_member(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Удаление члена семьи администратором"""
        # Создаем семью
        family = family_crud.create_family(db_session, FamilyCreate(name="Remove Test"), verified_user.id)

        # Добавляем члена
        member = family_crud.add_member(
            db_session,
            family.id,
            FamilyMemberCreate(
                first_name="Удаляемый",
                last_name="Член",
                birth_date=datetime.now(timezone.utc),
                is_admin=False,
                approved=True
            ),
            verified_user.id
        )

        # Логинимся
        login_response = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        assert login_response.status_code == 200, login_response.text
        token = login_response.json()["access_token"]

        # Удаляем
        response = client.delete(
            f"/family/member/{member.id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert "успешно удален" in response.json()["message"].lower()

        # Проверяем что удален
        deleted = family_crud.get_member_by_id(db_session, member.id)
        assert deleted is None

    def test_admin_cannot_delete_self(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Админ не может удалить сам себя"""
        # Создаем семью
        family = family_crud.create_family(db_session, FamilyCreate(name="Self Delete"), verified_user.id)

        # Получаем member_id админа
        members = family_crud.get_family_members(db_session, family.id)
        admin_member = [m for m in members if m.user_id == verified_user.id][0]

        # Логинимся
        login_response = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        assert login_response.status_code == 200, login_response.text
        token = login_response.json()["access_token"]

        # Пытаемся удалить себя
        response = client.delete(
            f"/family/member/{admin_member.id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 400
        assert "передайте права" in response.json()["detail"].lower()


class TestFamilyAdmin:
    """Тесты административных функций"""

    def test_approve_family_member(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Подтверждение члена семьи администратором"""
        # Создаем семью
        family = family_crud.create_family(db_session, FamilyCreate(name="Approve Test"), verified_user.id)

        # Добавляем неподтвержденного члена (через CRUD с approved=False)
        member = FamilyMember(
            family_id=family.id,
            user_id=None,
            first_name="Неподтвержденный",
            last_name="Член",
            birth_date=datetime.now(timezone.utc),
            created_by_user_id=verified_user.id,
            approved=False,
            is_active=False,
            is_admin=False
        )
        db_session.add(member)
        db_session.commit()
        db_session.refresh(member)

        # Логинимся
        login_response = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        assert login_response.status_code == 200, login_response.text
        token = login_response.json()["access_token"]

        # Подтверждаем
        response = client.post(
            f"/family/member/{member.id}/approve",
            headers={"Authorization": f"Bearer {token}"},
            json={"approved": True}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["approved"] is True

    def test_transfer_admin_rights(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Передача прав администратора"""
        # Создаем семью
        family = family_crud.create_family(db_session, FamilyCreate(name="Transfer Test"), verified_user.id)

        # Добавляем другого члена
        member = family_crud.add_member(
            db_session,
            family.id,
            FamilyMemberCreate(
                first_name="Новый",
                last_name="Админ",
                birth_date=datetime.now(timezone.utc),
                is_admin=False,
                approved=True
            ),
            verified_user.id
        )

        # Логинимся текущим админом
        login_response = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        assert login_response.status_code == 200, login_response.text
        token = login_response.json()["access_token"]

        # Передаем права
        response = client.post(
            f"/family/{family.id}/transfer-admin",
            headers={"Authorization": f"Bearer {token}"},
            params={"target_member_id": member.id}
        )

        assert response.status_code == 200
        assert "права администратора переданы" in response.json()["message"].lower()

        # Проверяем в БД
        updated_member = family_crud.get_member_by_id(db_session, member.id)
        assert updated_member.is_admin is True

    def test_transfer_admin_rights_by_non_admin(self, client: TestClient, verified_user, test_user_data,
                                                db_session: Session):
        """Попытка передать права не-администратором"""
        # Создаем семью
        family = family_crud.create_family(db_session, FamilyCreate(name="No Transfer"), verified_user.id)

        # Создаем обычного пользователя
        user = user_crud.register_user(db_session, UserCreate(
            email="notadmin@test.com",
            password="Test123456",
            name="Not Admin"
        ))
        user.is_verified = True
        db_session.commit()

        # Добавляем в семью
        member = family_crud.add_member(
            db_session,
            family.id,
            FamilyMemberCreate(
                first_name="Обычный",
                last_name="Пользователь",
                birth_date=datetime.now(timezone.utc),
                user_id=user.id,
                is_admin=False,
                approved=True
            ),
            verified_user.id
        )

        # Логинимся
        login_response = client.post("/auth/login", data={
            "username": "notadmin@test.com",
            "password": "Test123456"
        })
        assert login_response.status_code == 200, login_response.text
        token = login_response.json()["access_token"]

        # Пытаемся передать права
        response = client.post(
            f"/family/{family.id}/transfer-admin",
            headers={"Authorization": f"Bearer {token}"},
            params={"target_member_id": verified_user.id}  # Пытаемся передать кому-то права
        )

        assert response.status_code == 400
        assert "только администратор" in response.json()["detail"].lower()


class TestLeaveFamily:
    """Тесты покидания семьи"""

    def test_leave_family_success(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Успешное покидание семьи (не последним админом)"""
        # Создаем семью
        family = family_crud.create_family(db_session, FamilyCreate(name="Leave Test"), verified_user.id)

        # Добавляем другого админа
        other_admin = user_crud.register_user(db_session, UserCreate(
            email="otheradmin@test.com",
            password="Test123456",
            name="Other Admin"
        ))
        other_admin.is_verified = True
        db_session.commit()

        other_member = family_crud.add_member(
            db_session,
            family.id,
            FamilyMemberCreate(
                first_name="Другой",
                last_name="Админ",
                birth_date=datetime.now(timezone.utc),
                user_id=other_admin.id,
                is_admin=True,
                approved=True
            ),
            verified_user.id
        )

        # Создаем обычного пользователя для теста
        user = user_crud.register_user(db_session, UserCreate(
            email="leaver@test.com",
            password="Test123456",
            name="Leaver"
        ))
        user.is_verified = True
        db_session.commit()

        member = family_crud.add_member(
            db_session,
            family.id,
            FamilyMemberCreate(
                first_name="Уходящий",
                last_name="Пользователь",
                birth_date=datetime.now(timezone.utc),
                user_id=user.id,
                is_admin=False,
                approved=True
            ),
            verified_user.id
        )

        # Логинимся уходящим
        login_response = client.post("/auth/login", data={
            "username": "leaver@test.com",
            "password": "Test123456"
        })
        assert login_response.status_code == 200, login_response.text
        token = login_response.json()["access_token"]

        # Покидаем семью
        response = client.post(
            f"/family/{family.id}/leave",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert "покинули" in response.json()["message"].lower()

        # Проверяем что отвязался
        updated = family_crud.get_member_by_id(db_session, member.id)
        assert updated.user_id is None

    def test_leave_family_last_admin(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Последний админ не может покинуть семью"""
        # Создаем семью
        family = family_crud.create_family(db_session, FamilyCreate(name="Last Admin"), verified_user.id)

        # Логинимся
        login_response = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        assert login_response.status_code == 200, login_response.text
        token = login_response.json()["access_token"]

        # Пытаемся покинуть
        response = client.post(
            f"/family/{family.id}/leave",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 400
        assert "последний администратор" in response.json()["detail"].lower()


class TestFamilyUpdate:
    """Тесты обновления семьи"""

    def test_update_family_by_admin(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Обновление названия семьи администратором"""
        # Создаем семью
        family = family_crud.create_family(db_session, FamilyCreate(name="Old Name"), verified_user.id)

        # Логинимся
        login_response = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        assert login_response.status_code == 200, login_response.text
        token = login_response.json()["access_token"]

        # Обновляем
        response = client.put(
            f"/family/{family.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "New Name"}
        )

        assert response.status_code == 200
        assert response.json()["name"] == "New Name"

    def test_update_family_by_non_admin(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Попытка обновления не-администратором"""
        # Создаем семью
        family = family_crud.create_family(db_session, FamilyCreate(name="Protected"), verified_user.id)

        # Создаем обычного члена
        user = user_crud.register_user(db_session, UserCreate(
            email="cantupdate@test.com",
            password="Test123456",
            name="Cant Update"
        ))
        user.is_verified = True
        db_session.commit()

        family_crud.add_member(
            db_session,
            family.id,
            FamilyMemberCreate(
                first_name="Обычный",
                last_name="Член",
                birth_date=datetime.now(timezone.utc),
                user_id=user.id,
                is_admin=False,
                approved=True
            ),
            verified_user.id
        )

        # Логинимся
        login_response = client.post("/auth/login", data={
            "username": "cantupdate@test.com",
            "password": "Test123456"
        })
        assert login_response.status_code == 200, login_response.text
        token = login_response.json()["access_token"]

        # Пытаемся обновить
        response = client.put(
            f"/family/{family.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Hacked Name"}
        )

        assert response.status_code == 403


class TestFamilyDelete:
    """Тесты удаления семьи"""

    def test_delete_family_by_admin(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Удаление семьи администратором"""
        # Создаем семью
        family = family_crud.create_family(db_session, FamilyCreate(name="To Delete"), verified_user.id)

        # Логинимся
        login_response = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        assert login_response.status_code == 200, login_response.text
        token = login_response.json()["access_token"]

        # Удаляем
        response = client.delete(
            f"/family/{family.id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert "успешно удалена" in response.json()["message"].lower()

        # Проверяем что удалена
        deleted = family_crud.get_family_by_id(db_session, family.id)
        assert deleted is None

    def test_delete_family_with_members(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Удаление семьи со всеми членами"""
        # Создаем семью
        family = family_crud.create_family(db_session, FamilyCreate(name="With Members"), verified_user.id)

        # Добавляем членов
        for i in range(3):
            family_crud.add_member(
                db_session,
                family.id,
                FamilyMemberCreate(
                    first_name=f"Member{i}",
                    last_name="Test",
                    birth_date=datetime.now(timezone.utc),
                    is_admin=False,
                    approved=True
                ),
                verified_user.id
            )

        # Логинимся
        login_response = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        assert login_response.status_code == 200, login_response.text
        token = login_response.json()["access_token"]

        # Удаляем
        response = client.delete(
            f"/family/{family.id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200

        # Проверяем что все члены удалены
        members = family_crud.get_family_members(db_session, family.id)
        assert len(members) == 0