import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from app.crud.chat import chat_crud
from app.crud.family import family_crud
from app.crud.user import user_crud
from app.crud.message import message_crud
from app.models.enums import InvitationStatus
from app.schemas.family import FamilyCreate
from app.schemas.family_member import FamilyMemberCreate
from app.schemas.chat import ChatCreate
from app.schemas.auth import UserCreate

from app.models import Gender


class TestChatCreation:
    """Тесты создания чатов"""

    def test_create_chat_success(self, client: TestClient, verified_user, auth_headers, db_session: Session):
        """Успешное создание чата"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Chat Test Family"), verified_user.id)

        response = client.post(
            "/chats",
            headers=auth_headers,
            json={
                "family_id": family.id,
                "title": "Test Chat",
                "is_event": False
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Chat"
        assert data["family_id"] == family.id
        assert data["is_admin"] is True

    def test_create_chat_unauthorized_family(self, client: TestClient, verified_user, db_session: Session):
        """Попытка создать чат в чужой семье"""
        other_user = user_crud.register_user(db_session, UserCreate(
            email="other@chat.com", password="Test123456", name="Other"
        ))
        other_user.is_verified = True
        db_session.commit()

        other_family = family_crud.create_family(db_session, FamilyCreate(name="Other Family"), other_user.id)

        login_resp = client.post("/auth/login", data={
            "username": "test@example.com", "password": "Test123456!"
        })
        token = login_resp.json()["access_token"]

        response = client.post(
            "/chats",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "family_id": other_family.id,
                "title": "Hacked Chat"
            }
        )

        assert response.status_code == 403


class TestChatAccess:
    """Тесты доступа к чатам"""

    def test_get_user_chats(self, client: TestClient, verified_user, auth_headers, db_session: Session):
        """Получение списка чатов пользователя"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)
        chat_crud.create_chat(db_session, ChatCreate(family_id=family.id, title="My Chat"), verified_user.id)

        response = client.get("/chats", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data["chats"]) == 1
        assert data["chats"][0]["title"] == "My Chat"

    def test_get_chat_detail(self, client: TestClient, verified_user, auth_headers, db_session: Session):
        """Получение деталей чата"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id, title="Detail Chat"), verified_user.id)

        response = client.get(f"/chats/{chat.id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Detail Chat"
        assert data["is_admin"] is True
        assert "members" in data

    def test_no_access_to_foreign_chat(self, client: TestClient, verified_user, db_session: Session):
        """Нет доступа к чужому чату"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id), verified_user.id)

        other_user = user_crud.register_user(db_session, UserCreate(
            email="foreign@chat.com", password="Test123456", name="Foreign"
        ))
        other_user.is_verified = True
        db_session.commit()

        login_resp = client.post("/auth/login", data={
            "username": "foreign@chat.com", "password": "Test123456"
        })
        token = login_resp.json()["access_token"]

        response = client.get(f"/chats/{chat.id}", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403


class TestChatAdmin:
    """Тесты административных функций"""

    def test_update_chat_by_admin(self, client: TestClient, verified_user, auth_headers, db_session: Session):
        """Администратор может редактировать чат"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id, title="Old"), verified_user.id)

        response = client.put(
            f"/chats/{chat.id}",
            headers=auth_headers,
            json={"title": "New Title"}
        )

        assert response.status_code == 200
        assert response.json()["title"] == "New Title"

    def test_delete_chat_by_admin(self, client: TestClient, verified_user, auth_headers, db_session: Session):
        """Администратор может удалить чат"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id), verified_user.id)

        response = client.delete(f"/chats/{chat.id}", headers=auth_headers)
        assert response.status_code == 200

        # Проверяем что удален
        get_resp = client.get(f"/chats/{chat.id}", headers=auth_headers)
        assert get_resp.status_code == 404

    def test_non_admin_cannot_delete(self, client: TestClient, verified_user, db_session: Session):
        """Не-админ не может удалить чат"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id), verified_user.id)

        member_user = user_crud.register_user(db_session, UserCreate(
            email="member@chat.com", password="Test123456", name="Member"
        ))
        member_user.is_verified = True
        db_session.commit()

        family_crud.add_member(db_session, family.id, FamilyMemberCreate(
            first_name="Member", last_name="Test", gender=Gender.male,
            birth_date=datetime.now(timezone.utc), user_id=member_user.id
        ), verified_user.id)

        chat_crud.add_member(db_session, chat.id, member_user.id, verified_user.id)

        login_resp = client.post("/auth/login", data={
            "username": "member@chat.com", "password": "Test123456"
        })
        token = login_resp.json()["access_token"]

        response = client.delete(f"/chats/{chat.id}", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403


class TestChatMembers:
    """Тесты управления участниками"""

    def test_add_member_by_admin(self, client: TestClient, verified_user, auth_headers, db_session: Session):
        """Админ может добавлять участников (только из семьи)"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id), verified_user.id)

        new_user = user_crud.register_user(db_session, UserCreate(
            email="new@chat.com", password="Test123456", name="New User"
        ))
        new_user.is_verified = True
        db_session.commit()

        family_crud.add_member(db_session, family.id, FamilyMemberCreate(
            first_name="New", last_name="User", gender=Gender.male,
            birth_date=datetime.now(timezone.utc), user_id=new_user.id
        ), verified_user.id)

        response = client.post(
            f"/chats/{chat.id}/members",
            headers=auth_headers,
            json={"user_id": new_user.id}
        )

        assert response.status_code == 200
        assert response.json()["user_id"] == new_user.id

    def test_remove_member_by_admin(self, client: TestClient, verified_user, auth_headers, db_session: Session):
        """Админ может удалять участников"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id), verified_user.id)

        member_user = user_crud.register_user(db_session, UserCreate(
            email="remove@chat.com", password="Test123456", name="Remove"
        ))
        member_user.is_verified = True
        db_session.commit()

        family_crud.add_member(db_session, family.id, FamilyMemberCreate(
            first_name="Remove", last_name="Test", gender=Gender.male,
            birth_date=datetime.now(timezone.utc), user_id=member_user.id
        ), verified_user.id)

        chat_crud.add_member(db_session, chat.id, member_user.id, verified_user.id)

        response = client.delete(
            f"/chats/{chat.id}/members/{member_user.id}",
            headers=auth_headers
        )

        assert response.status_code == 200

    def test_transfer_admin_rights(self, client: TestClient, verified_user, auth_headers, db_session: Session):
        """Передача прав администратора"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id), verified_user.id)

        new_admin = user_crud.register_user(db_session, UserCreate(
            email="newadmin@chat.com", password="Test123456", name="New Admin"
        ))
        new_admin.is_verified = True
        db_session.commit()

        family_crud.add_member(db_session, family.id, FamilyMemberCreate(
            first_name="New", last_name="Admin", gender=Gender.male,
            birth_date=datetime.now(timezone.utc), user_id=new_admin.id
        ), verified_user.id)

        chat_crud.add_member(db_session, chat.id, new_admin.id, verified_user.id)

        response = client.post(
            f"/chats/{chat.id}/transfer-admin",
            headers=auth_headers,
            json={"new_admin_user_id": new_admin.id}
        )

        assert response.status_code == 200

        # Проверяем что новый админ может управлять
        login_resp = client.post("/auth/login", data={
            "username": "newadmin@chat.com", "password": "Test123456"
        })
        new_token = login_resp.json()["access_token"]

        # Добавляем участника новым админом
        third = user_crud.register_user(db_session, UserCreate(
            email="third@chat.com", password="Test123456", name="Third"
        ))
        third.is_verified = True
        db_session.commit()

        family_crud.add_member(db_session, family.id, FamilyMemberCreate(
            first_name="Third", last_name="Test", gender=Gender.male,
            birth_date=datetime.now(timezone.utc), user_id=third.id
        ), new_admin.id)  # new_admin теперь админ семьи

        add_resp = client.post(
            f"/chats/{chat.id}/members",
            headers={"Authorization": f"Bearer {new_token}"},
            json={"user_id": third.id}
        )

        assert add_resp.status_code == 200

    def test_leave_chat(self, client: TestClient, verified_user, auth_headers, db_session: Session):
        """Покидание чата"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)

        # Создаем второго админа
        admin2 = user_crud.register_user(db_session, UserCreate(
            email="admin2@chat.com", password="Test123456", name="Admin2"
        ))
        admin2.is_verified = True
        db_session.commit()

        family_crud.add_member(db_session, family.id, FamilyMemberCreate(
            first_name="Admin2", last_name="Test", gender=Gender.male,
            birth_date=datetime.now(timezone.utc), user_id=admin2.id
        ), verified_user.id)

        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id), verified_user.id)
        chat_crud.add_admin(db_session, chat.id, admin2.id, verified_user.id)
        chat_crud.transfer_admin_rights(db_session, chat.id, verified_user.id, admin2.id)

        response = client.post(f"/chats/{chat.id}/leave", headers=auth_headers)
        assert response.status_code == 200

    def test_leave_chat_last_admin_fails(self, client: TestClient, verified_user, auth_headers, db_session: Session):
        """Нельзя покинуть чат, если ты единственный админ"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id), verified_user.id)

        response = client.post(f"/chats/{chat.id}/leave", headers=auth_headers)
        assert response.status_code == 400
        assert "единственный администратор" in response.json()["detail"].lower()


class TestMessages:
    """Тесты сообщений"""

    def test_send_message(self, client: TestClient, verified_user, auth_headers, db_session: Session):
        """Отправка сообщения"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id), verified_user.id)

        response = client.post(
            f"/chats/{chat.id}/messages",
            headers=auth_headers,
            json={"content": "Hello, World!"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["content"] == "Hello, World!"
        assert data["sender_user_id"] == verified_user.id

    def test_get_messages(self, client: TestClient, verified_user, auth_headers, db_session: Session):
        """Получение сообщений"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id), verified_user.id)

        for i in range(5):
            message_crud.create_message(db_session, chat.id, verified_user.id, f"Message {i}")

        response = client.get(f"/chats/{chat.id}/messages", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["messages"]) == 5

    def test_edit_message(self, client: TestClient, verified_user, auth_headers, db_session: Session):
        """Редактирование сообщения"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id), verified_user.id)
        msg = message_crud.create_message(db_session, chat.id, verified_user.id, "Original")

        response = client.put(
            f"/chats/{chat.id}/messages/{msg.id}",
            headers=auth_headers,
            json={"content": "Edited"}
        )

        assert response.status_code == 200
        assert response.json()["content"] == "Edited"
        assert response.json()["is_edited"] is True

    def test_edit_foreign_message_fails(self, client: TestClient, verified_user, db_session: Session):
        """Нельзя редактировать чужое сообщение"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id), verified_user.id)

        other_user = user_crud.register_user(db_session, UserCreate(
            email="other@msg.com", password="Test123456", name="Other"
        ))
        other_user.is_verified = True
        db_session.commit()

        family_crud.add_member(db_session, family.id, FamilyMemberCreate(
            first_name="Other", last_name="Test", gender=Gender.male,
            birth_date=datetime.now(timezone.utc), user_id=other_user.id
        ), verified_user.id)

        chat_crud.add_member(db_session, chat.id, other_user.id, verified_user.id)

        msg = message_crud.create_message(db_session, chat.id, other_user.id, "Foreign message")

        login_resp = client.post("/auth/login", data={
            "username": "test@example.com", "password": "Test123456!"
        })
        token = login_resp.json()["access_token"]

        response = client.put(
            f"/chats/{chat.id}/messages/{msg.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"content": "Hacked"}
        )

        assert response.status_code == 403

    def test_delete_message(self, client: TestClient, verified_user, auth_headers, db_session: Session):
        """Удаление сообщения автором"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id), verified_user.id)
        msg = message_crud.create_message(db_session, chat.id, verified_user.id, "To delete")

        response = client.delete(
            f"/chats/{chat.id}/messages/{msg.id}",
            headers=auth_headers
        )

        assert response.status_code == 200

    def test_admin_can_delete_any_message(self, client: TestClient, verified_user, auth_headers, db_session: Session):
        """Админ может удалить любое сообщение"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id), verified_user.id)

        other_user = user_crud.register_user(db_session, UserCreate(
            email="other@admin.com", password="Test123456", name="Other"
        ))
        other_user.is_verified = True
        db_session.commit()

        family_crud.add_member(db_session, family.id, FamilyMemberCreate(
            first_name="Other", last_name="Test", gender=Gender.male,
            birth_date=datetime.now(timezone.utc), user_id=other_user.id
        ), verified_user.id)

        chat_crud.add_member(db_session, chat.id, other_user.id, verified_user.id)

        msg = message_crud.create_message(db_session, chat.id, other_user.id, "Admin delete test")

        response = client.delete(
            f"/chats/{chat.id}/messages/{msg.id}",
            headers=auth_headers
        )

        assert response.status_code == 200


class TestChatAdminFeatures:
    """Тесты нескольких администраторов"""

    def test_add_member_only_from_family(self, client: TestClient, verified_user, auth_headers, db_session: Session):
        """Нельзя добавить в чат пользователя не из семьи"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Closed Family"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id), verified_user.id)

        outsider = user_crud.register_user(db_session, UserCreate(
            email="outsider@chat.com", password="Test123456", name="Outsider"
        ))
        outsider.is_verified = True
        db_session.commit()

        response = client.post(
            f"/chats/{chat.id}/members",
            headers=auth_headers,
            json={"user_id": outsider.id}
        )

        assert response.status_code == 403
        assert "не является членом" in response.json()["detail"].lower()

    def test_multiple_admins(self, client: TestClient, verified_user, auth_headers, db_session: Session):
        """Несколько администраторов в одном чате"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Multi Admin"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id), verified_user.id)

        admin2 = user_crud.register_user(db_session, UserCreate(
            email="admin2@chat.com", password="Test123456", name="Admin2"
        ))
        admin2.is_verified = True
        db_session.commit()

        family_crud.add_member(db_session, family.id, FamilyMemberCreate(
            first_name="Admin2", last_name="Test", gender=Gender.male,
            birth_date=datetime.now(timezone.utc), user_id=admin2.id
        ), verified_user.id)

        response = client.post(
            f"/chats/{chat.id}/admins",
            headers=auth_headers,
            json={"user_id": admin2.id}
        )

        assert response.status_code == 200
        assert response.json()["is_admin"] is True

        # Проверяем, что теперь два админа
        members = chat_crud.get_chat_members(db_session, chat.id)
        admins = [m for m in members if m.is_admin]
        assert len(admins) == 2

    def test_remove_admin_keep_member(self, client: TestClient, verified_user, auth_headers, db_session: Session):
        """Снятие прав администратора (пользователь остается участником)"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Demote Test"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id), verified_user.id)

        admin2 = user_crud.register_user(db_session, UserCreate(
            email="demote@chat.com", password="Test123456", name="Demote"
        ))
        admin2.is_verified = True
        db_session.commit()

        family_crud.add_member(db_session, family.id, FamilyMemberCreate(
            first_name="Demote", last_name="Test", gender=Gender.male,
            birth_date=datetime.now(timezone.utc), user_id=admin2.id
        ), verified_user.id)

        chat_crud.add_admin(db_session, chat.id, admin2.id, verified_user.id)

        response = client.delete(
            f"/chats/{chat.id}/admins/{admin2.id}",
            headers=auth_headers
        )

        assert response.status_code == 200

        # Проверяем что больше не админ, но остался в чате
        is_admin = chat_crud.is_chat_admin(db_session, admin2.id, chat.id)
        is_member = chat_crud.is_chat_member(db_session, admin2.id, chat.id)

        assert not is_admin
        assert is_member

    def test_admin_cannot_remove_self(self, client: TestClient, verified_user, auth_headers, db_session: Session):
        """Админ не может снять права с самого себя"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Self Remove"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id), verified_user.id)

        response = client.delete(
            f"/chats/{chat.id}/admins/{verified_user.id}",
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "transfer-admin" in response.json()["detail"].lower()