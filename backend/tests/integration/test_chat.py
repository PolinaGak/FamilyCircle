# tests/integration/test_chat.py (исправленные тесты)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from app.crud.chat import chat_crud
from app.crud.family import family_crud
from app.crud.user import user_crud
from app.crud.message import message_crud
from app.models.chat import Chat
from app.models.chat_member import ChatMember
from app.models.message import Message
from app.models.enums import InvitationStatus
from app.schemas.family import FamilyCreate
from app.schemas.family_member import FamilyMemberCreate
from app.schemas.chat import ChatCreate
from app.schemas.auth import UserCreate


class TestChatCreation:
    """Тесты создания чатов"""

    def test_create_chat_success(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Успешное создание чата"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Chat Test Family"), verified_user.id)

        login_resp = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        token = login_resp.json()["access_token"]

        resp = client.post("/chats", headers={"Authorization": f"Bearer {token}"}, json={
            "family_id": family.id,
            "title": "Test Chat"
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Test Chat"
        assert data["family_id"] == family.id
        assert data["created_by_user_id"] == verified_user.id
        assert data["is_admin"] is True

    def test_create_chat_unauthorized_family(self, client: TestClient, verified_user, test_user_data,
                                             db_session: Session):
        """Попытка создать чат в чужой семье"""
        other_user = user_crud.register_user(db_session, UserCreate(
            email="other@chat.com", password="Test123456", name="Other"
        ))
        other_user.is_verified = True
        db_session.commit()
        other_family = family_crud.create_family(db_session, FamilyCreate(name="Other Family"), other_user.id)

        login_resp = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        token = login_resp.json()["access_token"]

        resp = client.post("/chats", headers={"Authorization": f"Bearer {token}"}, json={
            "family_id": other_family.id,
            "title": "Hacked Chat"
        })
        assert resp.status_code == 403


class TestChatAccess:
    """Тесты доступа к чатам"""

    def test_get_user_chats(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Получение списка чатов пользователя"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id, title="My Chat"), verified_user.id)

        login_resp = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        token = login_resp.json()["access_token"]

        resp = client.get("/chats", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["chats"]) == 1
        assert data["chats"][0]["title"] == "My Chat"

    def test_get_chat_detail(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Получение деталей чата"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id, title="Detail Chat"), verified_user.id)

        login_resp = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        token = login_resp.json()["access_token"]

        resp = client.get(f"/chats/{chat.id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Detail Chat"
        assert data["is_admin"] is True
        assert "members" in data

    def test_no_access_to_foreign_chat(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Нет доступа к чужому чату"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id), verified_user.id)

        other_user = user_crud.register_user(db_session, UserCreate(
            email="foreign@chat.com", password="Test123456", name="Foreign"
        ))
        other_user.is_verified = True
        db_session.commit()

        login_resp = client.post("/auth/login", data={
            "username": "foreign@chat.com",
            "password": "Test123456"
        })
        token = login_resp.json()["access_token"]

        resp = client.get(f"/chats/{chat.id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403


class TestChatAdmin:
    """Тесты административных функций"""

    def test_update_chat_by_admin(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Администратор может редактировать чат"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id, title="Old"), verified_user.id)

        login_resp = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        token = login_resp.json()["access_token"]

        resp = client.put(f"/chats/{chat.id}", headers={"Authorization": f"Bearer {token}"}, json={
            "title": "New Title"
        })
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Title"

    def test_delete_chat_by_admin(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Администратор может удалить чат"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id), verified_user.id)

        login_resp = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        token = login_resp.json()["access_token"]

        resp = client.delete(f"/chats/{chat.id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

        # Проверяем что удален
        get_resp = client.get(f"/chats/{chat.id}", headers={"Authorization": f"Bearer {token}"})
        assert get_resp.status_code == 404

    def test_non_admin_cannot_delete(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Не-админ не может удалить чат"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id), verified_user.id)

        # Создаем пользователя и добавляем в семью С user_id!
        member = user_crud.register_user(db_session, UserCreate(
            email="member@chat.com", password="Test123456", name="Member"
        ))
        member.is_verified = True
        db_session.commit()

        # ✅ Добавляем в семью с user_id!
        family_crud.add_member(db_session, family.id, FamilyMemberCreate(
            first_name="Member", last_name="Test", birth_date=datetime.now(timezone.utc), user_id=member.id
        ), verified_user.id)

        # Добавляем в чат как обычного участника
        chat_crud.add_member(db_session, chat.id, member.id, verified_user.id)

        login_resp = client.post("/auth/login", data={
            "username": "member@chat.com",
            "password": "Test123456"
        })
        token = login_resp.json()["access_token"]

        resp = client.delete(f"/chats/{chat.id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403


class TestChatMembers:
    """Тесты управления участниками"""

    def test_add_member_by_admin(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Админ может добавлять участников (только из семьи)"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id), verified_user.id)

        # Создаем пользователя и добавляем в семью С user_id!
        new_user = user_crud.register_user(db_session, UserCreate(
            email="new@chat.com", password="Test123456", name="New User"
        ))
        new_user.is_verified = True
        db_session.commit()

        # ✅ Добавляем в семью с user_id!
        family_crud.add_member(db_session, family.id, FamilyMemberCreate(
            first_name="New", last_name="User", birth_date=datetime.now(timezone.utc), user_id=new_user.id
        ), verified_user.id)

        login_resp = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        token = login_resp.json()["access_token"]

        resp = client.post(f"/chats/{chat.id}/members", headers={"Authorization": f"Bearer {token}"}, json={
            "user_id": new_user.id
        })
        assert resp.status_code == 200
        assert resp.json()["user_id"] == new_user.id

    def test_remove_member_by_admin(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Админ может удалять участников"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id), verified_user.id)

        # Создаем и добавляем в семью С user_id!
        member = user_crud.register_user(db_session, UserCreate(
            email="remove@chat.com", password="Test123456", name="Remove"
        ))
        member.is_verified = True
        db_session.commit()

        # ✅ Добавляем в семью с user_id!
        family_crud.add_member(db_session, family.id, FamilyMemberCreate(
            first_name="Remove", last_name="Test", birth_date=datetime.now(timezone.utc), user_id=member.id
        ), verified_user.id)

        chat_crud.add_member(db_session, chat.id, member.id, verified_user.id)

        login_resp = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        token = login_resp.json()["access_token"]

        resp = client.delete(f"/chats/{chat.id}/members/{member.id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_transfer_admin_rights(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Передача прав администратора"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id), verified_user.id)

        # Создаем и добавляем в семью С user_id!
        new_admin = user_crud.register_user(db_session, UserCreate(
            email="newadmin@chat.com", password="Test123456", name="New Admin"
        ))
        new_admin.is_verified = True
        db_session.commit()

        # ✅ Добавляем в семью с user_id!
        family_crud.add_member(db_session, family.id, FamilyMemberCreate(
            first_name="New", last_name="Admin", birth_date=datetime.now(timezone.utc), user_id=new_admin.id
        ), verified_user.id)

        chat_crud.add_member(db_session, chat.id, new_admin.id, verified_user.id)

        login_resp = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        token = login_resp.json()["access_token"]

        resp = client.post(f"/chats/{chat.id}/transfer-admin", headers={"Authorization": f"Bearer {token}"}, json={
            "new_admin_user_id": new_admin.id
        })
        assert resp.status_code == 200

        # Проверяем что новый админ может управлять
        new_login = client.post("/auth/login", data={
            "username": "newadmin@chat.com",
            "password": "Test123456"
        })
        new_token = new_login.json()["access_token"]

        # Добавляем участника новым админом
        third = user_crud.register_user(db_session, UserCreate(
            email="third@chat.com", password="Test123456", name="Third"
        ))
        third.is_verified = True
        db_session.commit()

        # ✅ Добавляем в семью с user_id!
        family_crud.add_member(db_session, family.id, FamilyMemberCreate(
            first_name="Third", last_name="Test", birth_date=datetime.now(timezone.utc), user_id=third.id
        ), new_admin.id)  # new_admin теперь админ семьи

        add_resp = client.post(f"/chats/{chat.id}/members", headers={"Authorization": f"Bearer {new_token}"}, json={
            "user_id": third.id
        })
        assert add_resp.status_code == 200

    def test_leave_chat(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Покидание чата"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)

        # Создаем второго админа и добавляем в семью С user_id!
        admin2 = user_crud.register_user(db_session, UserCreate(
            email="admin2@chat.com", password="Test123456", name="Admin2"
        ))
        admin2.is_verified = True
        db_session.commit()

        # ✅ Добавляем в семью с user_id!
        family_crud.add_member(db_session, family.id, FamilyMemberCreate(
            first_name="Admin2", last_name="Test", birth_date=datetime.now(timezone.utc), user_id=admin2.id
        ), verified_user.id)

        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id), verified_user.id)

        # Добавляем как админа через add_admin
        chat_crud.add_admin(db_session, chat.id, admin2.id, verified_user.id)

        # Передаем права второму
        chat_crud.transfer_admin_rights(db_session, chat.id, verified_user.id, admin2.id)

        login_resp = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        token = login_resp.json()["access_token"]

        resp = client.post(f"/chats/{chat.id}/leave", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

        # Проверяем что вышел
        members = chat_crud.get_chat_members(db_session, chat.id)
        assert len([m for m in members if m.user_id == verified_user.id]) == 0


class TestMessages:
    """Тесты сообщений"""

    def test_send_message(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Отправка сообщения"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id), verified_user.id)

        login_resp = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        token = login_resp.json()["access_token"]

        resp = client.post(f"/chats/{chat.id}/messages", headers={"Authorization": f"Bearer {token}"}, json={
            "content": "Hello, World!"
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["content"] == "Hello, World!"
        assert data["sender_user_id"] == verified_user.id

    def test_get_messages(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Получение сообщений"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id), verified_user.id)

        # Создаем несколько сообщений
        for i in range(5):
            message_crud.create_message(db_session, chat.id, verified_user.id, f"Message {i}")

        login_resp = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        token = login_resp.json()["access_token"]

        resp = client.get(f"/chats/{chat.id}/messages", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert len(data["messages"]) == 5

    def test_edit_message(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Редактирование сообщения"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id), verified_user.id)
        msg = message_crud.create_message(db_session, chat.id, verified_user.id, "Original")

        login_resp = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        token = login_resp.json()["access_token"]

        resp = client.put(f"/chats/{chat.id}/messages/{msg.id}", headers={"Authorization": f"Bearer {token}"}, json={
            "content": "Edited"
        })
        assert resp.status_code == 200
        assert resp.json()["content"] == "Edited"
        assert resp.json()["is_edited"] is True

    def test_delete_message(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Удаление сообщения автором"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id), verified_user.id)
        msg = message_crud.create_message(db_session, chat.id, verified_user.id, "To delete")

        login_resp = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        token = login_resp.json()["access_token"]

        resp = client.delete(f"/chats/{chat.id}/messages/{msg.id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

        # Проверяем что удалено
        get_resp = client.get(f"/chats/{chat.id}/messages", headers={"Authorization": f"Bearer {token}"})
        assert get_resp.json()["total"] == 0


class TestEventChatIntegration:
    """Тесты интеграции чатов с событиями"""

    def test_event_chat_auto_creation(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Автоматическое создание чата при создании события"""
        from app.crud.event import event_crud
        from app.schemas.event import EventCreate

        family = family_crud.create_family(db_session, FamilyCreate(name="Event Family"), verified_user.id)

        login_resp = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        token = login_resp.json()["access_token"]

        start = datetime.now(timezone.utc) + timedelta(days=1)
        end = start + timedelta(hours=2)

        resp = client.post("/events", headers={"Authorization": f"Bearer {token}"}, json={
            "title": "Party",
            "family_id": family.id,
            "start_datetime": start.isoformat(),
            "end_datetime": end.isoformat(),
            "create_chat": True,
            "invite_members": []
        })
        assert resp.status_code == 201
        event_data = resp.json()
        assert event_data["chat_id"] is not None

        # Проверяем что чат создан
        chat = chat_crud.get_chat_by_id(db_session, event_data["chat_id"])
        assert chat is not None
        assert chat.is_event is True
        assert chat.created_by_user_id == verified_user.id

    def test_event_participant_auto_added_to_chat(self, client: TestClient, verified_user, db_session: Session):
        """Участники события автоматически добавляются в чат"""
        from app.crud.event import event_crud
        from app.schemas.event import EventCreate

        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)

        member = user_crud.register_user(db_session, UserCreate(
            email="participant@chat.com", password="Test123456", name="Participant"
        ))
        member.is_verified = True
        db_session.commit()

        # Добавляем в семью с user_id
        family_crud.add_member(db_session, family.id, FamilyMemberCreate(
            first_name="Participant", last_name="Test",
            birth_date=datetime.now(timezone.utc), user_id=member.id
        ), verified_user.id)

        # Создаем событие с чатом
        start = datetime.now(timezone.utc) + timedelta(days=1)
        end = start + timedelta(hours=2)

        event = event_crud.create_event(db_session, type('obj', (object,), {
            'title': 'Test', 'description': None, 'family_id': family.id,
            'start_datetime': start, 'end_datetime': end,
            'create_chat': True, 'invite_members': None
        })(), verified_user.id)

        # Приглашаем участника
        event_crud.invite_participant(db_session, event.id, member.id)

        # Принимаем приглашение
        login_resp = client.post("/auth/login", data={
            "username": "participant@chat.com",
            "password": "Test123456"
        })
        token = login_resp.json()["access_token"]

        resp = client.post(f"/events/{event.id}/respond", headers={"Authorization": f"Bearer {token}"}, json={
            "accept": True
        })
        assert resp.status_code == 200

        # Проверяем что добавлен в чат
        is_member = chat_crud.is_chat_member(db_session, member.id, event.chat.id)
        assert is_member is True


class TestChatAdminFeatures:
    """Тесты нескольких администраторов и проверки семьи"""

    def test_add_member_only_from_family(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Нельзя добавить в чат пользователя не из семьи"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Closed Family"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id), verified_user.id)

        # Создаем пользователя НЕ из семьи
        outsider = user_crud.register_user(db_session, UserCreate(
            email="outsider@chat.com", password="Test123456", name="Outsider"
        ))
        outsider.is_verified = True
        db_session.commit()

        login_resp = client.post("/auth/login", data={
            "username": test_user_data["email"], "password": test_user_data["password"]
        })
        token = login_resp.json()["access_token"]

        resp = client.post(f"/chats/{chat.id}/members",
                           headers={"Authorization": f"Bearer {token}"},
                           json={"user_id": outsider.id})

        assert resp.status_code == 403
        assert "не является членом" in resp.json()["detail"].lower()

    def test_add_member_from_family_success(self, client: TestClient, verified_user, test_user_data,
                                            db_session: Session):
        """Успешное добавление члена семьи"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Open Family"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id), verified_user.id)

        # Создаем пользователя и добавляем в семью с user_id!
        member = user_crud.register_user(db_session, UserCreate(
            email="member@chat.com", password="Test123456", name="Member"
        ))
        member.is_verified = True
        db_session.commit()

        family_crud.add_member(db_session, family.id, FamilyMemberCreate(
            first_name="Member", last_name="Test", birth_date=datetime.now(timezone.utc), user_id=member.id
        ), verified_user.id)

        login_resp = client.post("/auth/login", data={
            "username": test_user_data["email"], "password": test_user_data["password"]
        })
        token = login_resp.json()["access_token"]

        resp = client.post(f"/chats/{chat.id}/members",
                           headers={"Authorization": f"Bearer {token}"},
                           json={"user_id": member.id})

        assert resp.status_code == 200

    def test_multiple_admins(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Несколько администраторов в одном чате"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Multi Admin"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id), verified_user.id)

        # Добавляем второго админа в семью с user_id!
        admin2 = user_crud.register_user(db_session, UserCreate(
            email="admin2@chat.com", password="Test123456", name="Admin2"
        ))
        admin2.is_verified = True
        db_session.commit()

        family_crud.add_member(db_session, family.id, FamilyMemberCreate(
            first_name="Admin2", last_name="Test", birth_date=datetime.now(timezone.utc), user_id=admin2.id
        ), verified_user.id)

        login_resp = client.post("/auth/login", data={
            "username": test_user_data["email"], "password": test_user_data["password"]
        })
        token = login_resp.json()["access_token"]

        # Назначаем второго админа
        resp = client.post(f"/chats/{chat.id}/admins",
                           headers={"Authorization": f"Bearer {token}"},
                           json={"user_id": admin2.id})

        assert resp.status_code == 200
        assert resp.json()["is_admin"] is True

        # Проверяем, что теперь два админа
        members = chat_crud.get_chat_members(db_session, chat.id)
        admins = [m for m in members if m.is_admin]
        assert len(admins) == 2

    def test_remove_admin_keep_member(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Снятие прав администратора (пользователь остается участником)"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Demote Test"), verified_user.id)
        chat = chat_crud.create_chat(db_session, ChatCreate(family_id=family.id), verified_user.id)

        # Добавляем второго админа в семью с user_id!
        admin2 = user_crud.register_user(db_session, UserCreate(
            email="demote@chat.com", password="Test123456", name="Demote"
        ))
        admin2.is_verified = True
        db_session.commit()

        family_crud.add_member(db_session, family.id, FamilyMemberCreate(
            first_name="Demote", last_name="Test", birth_date=datetime.now(timezone.utc), user_id=admin2.id
        ), verified_user.id)

        chat_crud.add_admin(db_session, chat.id, admin2.id, verified_user.id)

        login_resp = client.post("/auth/login", data={
            "username": test_user_data["email"], "password": test_user_data["password"]
        })
        token = login_resp.json()["access_token"]

        # Снимаем права
        resp = client.delete(f"/chats/{chat.id}/admins/{admin2.id}",
                             headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200

        # Проверяем, что больше не админ, но остался в чате
        is_admin = chat_crud.is_chat_admin(db_session, admin2.id, chat.id)
        is_member = chat_crud.is_chat_member(db_session, admin2.id, chat.id)

        assert not is_admin
        assert is_member