import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from app.crud.event import event_crud
from app.crud.family import family_crud
from app.crud.user import user_crud
from app.models.event import Event
from app.models.event_participant import EventParticipant
from app.models.chat import Chat
from app.models.chat_member import ChatMember
from app.models.enums import InvitationStatus
from app.schemas.family import FamilyCreate
from app.schemas.auth import UserCreate


class TestEventCreation:
    """Тесты создания событий"""

    def test_create_event_success(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Успешное создание события с автоматическим созданием чата"""
        # Создаем семью
        family = family_crud.create_family(db_session, FamilyCreate(name="Event Test Family"), verified_user.id)

        # Логинимся
        login_response = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Создаем событие
        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)

        response = client.post(
            "/events",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "День рождения бабушки",
                "description": "Празднуем 80-летие",
                "family_id": family.id,
                "start_datetime": start_time.isoformat(),
                "end_datetime": end_time.isoformat(),
                "create_chat": True,
                "invite_members": []
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "День рождения бабушки"
        assert data["family_id"] == family.id
        assert data["created_by_user_id"] == verified_user.id
        assert data["chat_id"] is not None  # Чат создан автоматически

    def test_create_event_without_chat(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Создание события без чата"""
        family = family_crud.create_family(db_session, FamilyCreate(name="No Chat Family"), verified_user.id)

        login_response = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        token = login_response.json()["access_token"]

        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)

        response = client.post(
            "/events",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Встреча без чата",
                "family_id": family.id,
                "start_datetime": start_time.isoformat(),
                "end_datetime": end_time.isoformat(),
                "create_chat": False
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["chat_id"] is None

    def test_create_event_invalid_dates(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Попытка создать событие с end_datetime <= start_datetime"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Invalid Dates"), verified_user.id)

        login_response = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        token = login_response.json()["access_token"]

        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        end_time = start_time - timedelta(hours=2)  # Конец раньше начала

        response = client.post(
            "/events",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Неправильные даты",
                "family_id": family.id,
                "start_datetime": start_time.isoformat(),
                "end_datetime": end_time.isoformat()
            }
        )

        assert response.status_code == 400
        assert "Дата окончания должна быть позже" in response.json()["detail"]

    def test_create_event_unauthorized_family(self, client: TestClient, verified_user, test_user_data,
                                              db_session: Session):
        """Попытка создать событие в чужой семье"""
        # Создаем семью первым пользователем
        family = family_crud.create_family(db_session, FamilyCreate(name="Private Family"), verified_user.id)

        # Создаем другого пользователя
        other_user = user_crud.register_user(db_session, UserCreate(
            email="other@event.com",
            password="Test123456",
            name="Other User"
        ))
        other_user.is_verified = True
        db_session.commit()

        # Логинимся другим пользователем
        login_response = client.post("/auth/login", data={
            "username": "other@event.com",
            "password": "Test123456"
        })
        token = login_response.json()["access_token"]

        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)

        response = client.post(
            "/events",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Чужое событие",
                "family_id": family.id,
                "start_datetime": start_time.isoformat(),
                "end_datetime": end_time.isoformat()
            }
        )

        assert response.status_code == 403


class TestEventInvitations:
    """Тесты приглашений и участия в событиях"""

    def test_invite_participant(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Приглашение участника на событие"""
        # Создаем семью и событие
        family = family_crud.create_family(db_session, FamilyCreate(name="Invite Family"), verified_user.id)

        # Добавляем члена в семью
        member_user = user_crud.register_user(db_session, UserCreate(
            email="member@event.com",
            password="Test123456",
            name="Member User"
        ))
        member_user.is_verified = True
        db_session.commit()

        from app.schemas.family_member import FamilyMemberCreate
        family_crud.add_member(
            db_session,
            family.id,
            FamilyMemberCreate(
                first_name="Member",
                last_name="Test",
                birth_date=datetime.now(timezone.utc),
                user_id=member_user.id,
                is_admin=False,
                approved=True
            ),
            verified_user.id
        )

        # Создаем событие
        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)

        event = event_crud.create_event(
            db_session,
            type('obj', (object,), {
                'title': 'Test Event',
                'description': None,
                'family_id': family.id,
                'start_datetime': start_time,
                'end_datetime': end_time,
                'create_chat': True,
                'invite_members': None
            })(),
            verified_user.id
        )

        # Логинимся создателем
        login_response = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        token = login_response.json()["access_token"]

        # Приглашаем участника
        response = client.post(
            f"/events/{event.id}/invite",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": member_user.id}
        )

        assert response.status_code == 201
        assert "Приглашение отправлено" in response.json()["message"]

        # Проверяем что приглашение создано
        participant = db_session.query(EventParticipant).filter(
            EventParticipant.event_id == event.id,
            EventParticipant.user_id == member_user.id
        ).first()
        assert participant is not None
        assert participant.status == InvitationStatus.invited

    def test_accept_invitation_and_join_chat(self, client: TestClient, verified_user, test_user_data,
                                             db_session: Session):
        """Принятие приглашения и автоматическое добавление в чат"""
        # Создаем семью и событие с чатом
        family = family_crud.create_family(db_session, FamilyCreate(name="Accept Family"), verified_user.id)

        member_user = user_crud.register_user(db_session, UserCreate(
            email="accept@event.com",
            password="Test123456",
            name="Accept User"
        ))
        member_user.is_verified = True
        db_session.commit()

        from app.schemas.family_member import FamilyMemberCreate
        family_crud.add_member(
            db_session,
            family.id,
            FamilyMemberCreate(
                first_name="Accept",
                last_name="Test",
                birth_date=datetime.now(timezone.utc),
                user_id=member_user.id,
                is_admin=False,
                approved=True
            ),
            verified_user.id
        )

        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)

        event = event_crud.create_event(
            db_session,
            type('obj', (object,), {
                'title': 'Chat Test Event',
                'description': None,
                'family_id': family.id,
                'start_datetime': start_time,
                'end_datetime': end_time,
                'create_chat': True,
                'invite_members': None
            })(),
            verified_user.id
        )

        # Приглашаем участника напрямую через CRUD
        event_crud.invite_participant(db_session, event.id, member_user.id)

        # Логинимся приглашенным пользователем
        login_response = client.post("/auth/login", data={
            "username": "accept@event.com",
            "password": "Test123456"
        })
        token = login_response.json()["access_token"]

        # Принимаем приглашение
        response = client.post(
            f"/events/{event.id}/respond",
            headers={"Authorization": f"Bearer {token}"},
            json={"accept": True}
        )

        assert response.status_code == 200
        assert "принято" in response.json()["message"]
        assert response.json()["status"] == "accepted"

        # Проверяем что пользователь добавлен в чат
        chat_member = db_session.query(ChatMember).join(Chat).filter(
            Chat.event_id == event.id,
            ChatMember.user_id == member_user.id
        ).first()
        assert chat_member is not None
        assert chat_member.status == InvitationStatus.accepted

    def test_decline_invitation_not_in_chat(self, client: TestClient, verified_user, test_user_data,
                                            db_session: Session):
        """Отклонение приглашения - пользователь не добавляется в чат"""
        # Создаем семью и событие
        family = family_crud.create_family(db_session, FamilyCreate(name="Decline Family"), verified_user.id)

        member_user = user_crud.register_user(db_session, UserCreate(
            email="decline@event.com",
            password="Test123456",
            name="Decline User"
        ))
        member_user.is_verified = True
        db_session.commit()

        from app.schemas.family_member import FamilyMemberCreate
        family_crud.add_member(
            db_session,
            family.id,
            FamilyMemberCreate(
                first_name="Decline",
                last_name="Test",
                birth_date=datetime.now(timezone.utc),
                user_id=member_user.id,
                is_admin=False,
                approved=True
            ),
            verified_user.id
        )

        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)

        event = event_crud.create_event(
            db_session,
            type('obj', (object,), {
                'title': 'Decline Event',
                'description': None,
                'family_id': family.id,
                'start_datetime': start_time,
                'end_datetime': end_time,
                'create_chat': True,
                'invite_members': None
            })(),
            verified_user.id
        )

        event_crud.invite_participant(db_session, event.id, member_user.id)

        # Логинимся и отклоняем
        login_response = client.post("/auth/login", data={
            "username": "decline@event.com",
            "password": "Test123456"
        })
        token = login_response.json()["access_token"]

        response = client.post(
            f"/events/{event.id}/respond",
            headers={"Authorization": f"Bearer {token}"},
            json={"accept": False}
        )

        assert response.status_code == 200
        assert "отклонено" in response.json()["message"]

        # Проверяем что пользователь НЕ в чате
        chat_member = db_session.query(ChatMember).join(Chat).filter(
            Chat.event_id == event.id,
            ChatMember.user_id == member_user.id
        ).first()
        assert chat_member is None

    def test_get_pending_invitations(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Получение списка ожидающих приглашений"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Pending Family"), verified_user.id)

        member_user = user_crud.register_user(db_session, UserCreate(
            email="pending@event.com",
            password="Test123456",
            name="Pending User"
        ))
        member_user.is_verified = True
        db_session.commit()

        from app.schemas.family_member import FamilyMemberCreate
        family_crud.add_member(
            db_session,
            family.id,
            FamilyMemberCreate(
                first_name="Pending",
                last_name="Test",
                birth_date=datetime.now(timezone.utc),
                user_id=member_user.id,
                is_admin=False,
                approved=True
            ),
            verified_user.id
        )

        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)

        event = event_crud.create_event(
            db_session,
            type('obj', (object,), {
                'title': 'Pending Event',
                'description': None,
                'family_id': family.id,
                'start_datetime': start_time,
                'end_datetime': end_time,
                'create_chat': False,
                'invite_members': None
            })(),
            verified_user.id
        )

        event_crud.invite_participant(db_session, event.id, member_user.id)

        # Логинимся приглашенным
        login_response = client.post("/auth/login", data={
            "username": "pending@event.com",
            "password": "Test123456"
        })
        token = login_response.json()["access_token"]

        response = client.get(
            "/events/my/invitations/pending",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["event_title"] == "Pending Event"


class TestEventCalendar:
    """Тесты календаря событий"""

    def test_calendar_shows_only_accepted(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Календарь показывает только принятые события"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Calendar Family"), verified_user.id)

        member_user = user_crud.register_user(db_session, UserCreate(
            email="calendar@event.com",
            password="Test123456",
            name="Calendar User"
        ))
        member_user.is_verified = True
        db_session.commit()

        from app.schemas.family_member import FamilyMemberCreate
        family_crud.add_member(
            db_session,
            family.id,
            FamilyMemberCreate(
                first_name="Calendar",
                last_name="Test",
                birth_date=datetime.now(timezone.utc),
                user_id=member_user.id,
                is_admin=False,
                approved=True
            ),
            verified_user.id
        )

        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)

        # Создаем два события
        event1 = event_crud.create_event(
            db_session,
            type('obj', (object,), {
                'title': 'Accepted Event',
                'description': None,
                'family_id': family.id,
                'start_datetime': start_time,
                'end_datetime': end_time,
                'create_chat': False,
                'invite_members': None
            })(),
            verified_user.id
        )

        event2 = event_crud.create_event(
            db_session,
            type('obj', (object,), {
                'title': 'Declined Event',
                'description': None,
                'family_id': family.id,
                'start_datetime': start_time + timedelta(days=1),
                'end_datetime': end_time + timedelta(days=1),
                'create_chat': False,
                'invite_members': None
            })(),
            verified_user.id
        )

        # Приглашаем на оба
        event_crud.invite_participant(db_session, event1.id, member_user.id)
        event_crud.invite_participant(db_session, event2.id, member_user.id)

        # Принимаем первое, отклоняем второе
        event_crud.respond_to_invitation(db_session, event1.id, member_user.id, accept=True)
        event_crud.respond_to_invitation(db_session, event2.id, member_user.id, accept=False)

        # Логинимся и проверяем календарь
        login_response = client.post("/auth/login", data={
            "username": "calendar@event.com",
            "password": "Test123456"
        })
        token = login_response.json()["access_token"]

        response = client.get(
            "/events/my/calendar",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Accepted Event"


class TestEventAdminAccess:
    """Тесты административных прав на события"""

    def test_only_admin_can_update_event(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Только создатель может редактировать событие"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Admin Family"), verified_user.id)

        other_user = user_crud.register_user(db_session, UserCreate(
            email="otheradmin@event.com",
            password="Test123456",
            name="Other User"
        ))
        other_user.is_verified = True
        db_session.commit()

        from app.schemas.family_member import FamilyMemberCreate
        family_crud.add_member(
            db_session,
            family.id,
            FamilyMemberCreate(
                first_name="Other",
                last_name="User",
                birth_date=datetime.now(timezone.utc),
                user_id=other_user.id,
                is_admin=False,
                approved=True
            ),
            verified_user.id
        )

        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)

        event = event_crud.create_event(
            db_session,
            type('obj', (object,), {
                'title': 'Protected Event',
                'description': None,
                'family_id': family.id,
                'start_datetime': start_time,
                'end_datetime': end_time,
                'create_chat': False,
                'invite_members': None
            })(),
            verified_user.id
        )

        # Логинимся другим пользователем
        login_response = client.post("/auth/login", data={
            "username": "otheradmin@event.com",
            "password": "Test123456"
        })
        token = login_response.json()["access_token"]

        # Пытаемся редактировать
        response = client.put(
            f"/events/{event.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "Hacked Title"}
        )

        assert response.status_code == 403
        assert "Только создатель" in response.json()["detail"]

    def test_only_admin_can_delete_event(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Только создатель может удалить событие"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Delete Family"), verified_user.id)

        other_user = user_crud.register_user(db_session, UserCreate(
            email="nodelete@event.com",
            password="Test123456",
            name="No Delete User"
        ))
        other_user.is_verified = True
        db_session.commit()

        from app.schemas.family_member import FamilyMemberCreate
        family_crud.add_member(
            db_session,
            family.id,
            FamilyMemberCreate(
                first_name="No",
                last_name="Delete",
                birth_date=datetime.now(timezone.utc),
                user_id=other_user.id,
                is_admin=False,
                approved=True
            ),
            verified_user.id
        )

        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)

        event = event_crud.create_event(
            db_session,
            type('obj', (object,), {
                'title': 'Delete Test',
                'description': None,
                'family_id': family.id,
                'start_datetime': start_time,
                'end_datetime': end_time,
                'create_chat': False,
                'invite_members': None
            })(),
            verified_user.id
        )

        login_response = client.post("/auth/login", data={
            "username": "nodelete@event.com",
            "password": "Test123456"
        })
        token = login_response.json()["access_token"]

        response = client.delete(
            f"/events/{event.id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 403

    def test_admin_can_update_event(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Создатель успешно редактирует событие"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Update Family"), verified_user.id)

        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)

        event = event_crud.create_event(
            db_session,
            type('obj', (object,), {
                'title': 'Updatable Event',
                'description': None,
                'family_id': family.id,
                'start_datetime': start_time,
                'end_datetime': end_time,
                'create_chat': False,
                'invite_members': None
            })(),
            verified_user.id
        )

        login_response = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        token = login_response.json()["access_token"]

        response = client.put(
            f"/events/{event.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "Updated Title", "description": "New description"}
        )

        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"
        assert response.json()["description"] == "New description"


class TestEventChatCreation:
    """Тесты создания чата для существующего события"""

    def test_create_chat_for_existing_event(self, client: TestClient, verified_user, test_user_data,
                                            db_session: Session):
        """Создание чата для события, созданного без чата"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Chat Create Family"), verified_user.id)

        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)

        event = event_crud.create_event(
            db_session,
            type('obj', (object,), {
                'title': 'No Chat Event',
                'description': None,
                'family_id': family.id,
                'start_datetime': start_time,
                'end_datetime': end_time,
                'create_chat': False,  # Без чата при создании
                'invite_members': None
            })(),
            verified_user.id
        )

        assert event.chat is None

        login_response = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        token = login_response.json()["access_token"]

        # Создаем чат отдельно
        response = client.post(
            f"/events/{event.id}/create-chat",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert response.json()["success"] is True
        assert "chat_id" in response.json()

    def test_cannot_create_second_chat(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Нельзя создать второй чат для события"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Second Chat Family"), verified_user.id)

        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)

        event = event_crud.create_event(
            db_session,
            type('obj', (object,), {
                'title': 'One Chat Event',
                'description': None,
                'family_id': family.id,
                'start_datetime': start_time,
                'end_datetime': end_time,
                'create_chat': True,  # С чатом
                'invite_members': None
            })(),
            verified_user.id
        )

        login_response = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        token = login_response.json()["access_token"]

        # Пытаемся создать еще один чат
        response = client.post(
            f"/events/{event.id}/create-chat",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 400
        assert "Чат для этого события уже существует" in response.json()["detail"]


class TestEventParticipantsManagement:
    """Тесты управления участниками"""

    def test_remove_participant(self, client: TestClient, verified_user, test_user_data, db_session: Session):
        """Удаление участника из события"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Remove Participant Family"), verified_user.id)

        member_user = user_crud.register_user(db_session, UserCreate(
            email="removeme@event.com",
            password="Test123456",
            name="Remove Me"
        ))
        member_user.is_verified = True
        db_session.commit()

        from app.schemas.family_member import FamilyMemberCreate
        family_crud.add_member(
            db_session,
            family.id,
            FamilyMemberCreate(
                first_name="Remove",
                last_name="Me",
                birth_date=datetime.now(timezone.utc),
                user_id=member_user.id,
                is_admin=False,
                approved=True
            ),
            verified_user.id
        )

        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)

        event = event_crud.create_event(
            db_session,
            type('obj', (object,), {
                'title': 'Remove Test',
                'description': None,
                'family_id': family.id,
                'start_datetime': start_time,
                'end_datetime': end_time,
                'create_chat': True,
                'invite_members': None
            })(),
            verified_user.id
        )

        # Приглашаем и принимаем
        event_crud.invite_participant(db_session, event.id, member_user.id)
        event_crud.respond_to_invitation(db_session, event.id, member_user.id, accept=True)

        # Проверяем что в чате
        chat_member_before = db_session.query(ChatMember).join(Chat).filter(
            Chat.event_id == event.id,
            ChatMember.user_id == member_user.id
        ).first()
        assert chat_member_before is not None

        login_response = client.post("/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        token = login_response.json()["access_token"]

        # Удаляем участника
        response = client.delete(
            f"/events/{event.id}/participants/{member_user.id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200

        # Проверяем что удален из события
        participant = db_session.query(EventParticipant).filter(
            EventParticipant.event_id == event.id,
            EventParticipant.user_id == member_user.id
        ).first()
        assert participant is None

        # Проверяем что удален из чата
        chat_member_after = db_session.query(ChatMember).join(Chat).filter(
            Chat.event_id == event.id,
            ChatMember.user_id == member_user.id
        ).first()
        assert chat_member_after is None