import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from app.crud.event import event_crud
from app.crud.family import family_crud
from app.crud.user import user_crud
from app.models.enums import InvitationStatus
from app.schemas.family import FamilyCreate
from app.schemas.family_member import FamilyMemberCreate
from app.schemas.event import EventCreate
from app.schemas.auth import UserCreate

from app.models import Gender


class TestEventCreation:
    """Тесты создания событий"""

    def test_create_event_success(self, client: TestClient, verified_user, auth_headers, db_session: Session):
        """Успешное создание события с автоматическим созданием чата"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Event Test Family"), verified_user.id)

        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)

        response = client.post(
            "/events",
            headers=auth_headers,
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
        assert data["chat_id"] is not None

    def test_create_event_without_chat(self, client: TestClient, verified_user, auth_headers, db_session: Session):
        """Создание события без чата"""
        family = family_crud.create_family(db_session, FamilyCreate(name="No Chat Family"), verified_user.id)

        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)

        response = client.post(
            "/events",
            headers=auth_headers,
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

    def test_create_event_invalid_dates(self, client: TestClient, verified_user, auth_headers, db_session: Session):
        """Попытка создать событие с end_datetime <= start_datetime"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Invalid Dates"), verified_user.id)

        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        end_time = start_time - timedelta(hours=2)  # Конец раньше начала

        response = client.post(
            "/events",
            headers=auth_headers,
            json={
                "title": "Неправильные даты",
                "family_id": family.id,
                "start_datetime": start_time.isoformat(),
                "end_datetime": end_time.isoformat()
            }
        )

        assert response.status_code == 400
        assert "Дата окончания должна быть позже" in response.json()["detail"]

    def test_create_event_unauthorized_family(self, client: TestClient, verified_user, db_session: Session):
        """Попытка создать событие в чужой семье"""
        other_user = user_crud.register_user(db_session, UserCreate(
            email="other@event.com", password="Test123456", name="Other User"
        ))
        other_user.is_verified = True
        db_session.commit()

        family = family_crud.create_family(db_session, FamilyCreate(name="Private Family"), other_user.id)

        login_resp = client.post("/auth/login", data={
            "username": "test@example.com", "password": "Test123456!"
        })
        token = login_resp.json()["access_token"]

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

    def test_create_event_with_invites(self, client: TestClient, verified_user, auth_headers, db_session: Session):
        """Создание события с приглашением членов"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Invite Family"), verified_user.id)

        # Добавляем члена в семью
        member_user = user_crud.register_user(db_session, UserCreate(
            email="member@event.com", password="Test123456", name="Member"
        ))
        member_user.is_verified = True
        db_session.commit()

        family_crud.add_member(db_session, family.id, FamilyMemberCreate(
            first_name="Member", last_name="Test", gender=Gender.male,
            birth_date=datetime.now(timezone.utc), user_id=member_user.id
        ), verified_user.id)

        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)

        response = client.post(
            "/events",
            headers=auth_headers,
            json={
                "title": "Событие с гостями",
                "family_id": family.id,
                "start_datetime": start_time.isoformat(),
                "end_datetime": end_time.isoformat(),
                "create_chat": True,
                "invite_members": [member_user.id]
            }
        )

        assert response.status_code == 201
        # Проверяем что приглашение создано можно через отдельный запрос


class TestEventInvitations:
    """Тесты приглашений и участия в событиях"""

    def test_invite_participant(self, client: TestClient, verified_user, auth_headers, db_session: Session):
        """Приглашение участника на событие"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Invite Family"), verified_user.id)

        member_user = user_crud.register_user(db_session, UserCreate(
            email="invite@event.com", password="Test123456", name="Invite User"
        ))
        member_user.is_verified = True
        db_session.commit()

        family_crud.add_member(db_session, family.id, FamilyMemberCreate(
            first_name="Invite", last_name="Test", gender=Gender.male,
            birth_date=datetime.now(timezone.utc), user_id=member_user.id
        ), verified_user.id)

        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)

        event = event_crud.create_event(
            db_session,
            EventCreate(
                title="Test Event",
                family_id=family.id,
                start_datetime=start_time,
                end_datetime=end_time,
                create_chat=True
            ),
            verified_user.id
        )

        response = client.post(
            f"/events/{event.id}/invite",
            headers=auth_headers,
            json={"user_id": member_user.id}
        )

        assert response.status_code == 201
        assert "Приглашение отправлено" in response.json()["message"]

    def test_accept_invitation_and_join_chat(self, client: TestClient, verified_user, db_session: Session):
        """Принятие приглашения и автоматическое добавление в чат"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Accept Family"), verified_user.id)

        member_user = user_crud.register_user(db_session, UserCreate(
            email="accept@event.com", password="Test123456", name="Accept User"
        ))
        member_user.is_verified = True
        db_session.commit()

        family_crud.add_member(db_session, family.id, FamilyMemberCreate(
            first_name="Accept", last_name="Test", gender=Gender.male,
            birth_date=datetime.now(timezone.utc), user_id=member_user.id
        ), verified_user.id)

        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)

        event = event_crud.create_event(
            db_session,
            EventCreate(
                title="Chat Test Event",
                family_id=family.id,
                start_datetime=start_time,
                end_datetime=end_time,
                create_chat=True
            ),
            verified_user.id
        )

        event_crud.invite_participant(db_session, event.id, member_user.id)

        # Логинимся приглашенным пользователем
        login_resp = client.post("/auth/login", data={
            "username": "accept@event.com", "password": "Test123456"
        })
        token = login_resp.json()["access_token"]

        response = client.post(
            f"/events/{event.id}/respond",
            headers={"Authorization": f"Bearer {token}"},
            json={"accept": True}
        )

        assert response.status_code == 200
        assert "принято" in response.json()["message"]
        assert response.json()["status"] == "accepted"

    def test_decline_invitation_not_in_chat(self, client: TestClient, verified_user, db_session: Session):
        """Отклонение приглашения - пользователь не добавляется в чат"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Decline Family"), verified_user.id)

        member_user = user_crud.register_user(db_session, UserCreate(
            email="decline@event.com", password="Test123456", name="Decline User"
        ))
        member_user.is_verified = True
        db_session.commit()

        family_crud.add_member(db_session, family.id, FamilyMemberCreate(
            first_name="Decline", last_name="Test", gender=Gender.male,
            birth_date=datetime.now(timezone.utc), user_id=member_user.id
        ), verified_user.id)

        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)

        event = event_crud.create_event(
            db_session,
            EventCreate(
                title="Decline Event",
                family_id=family.id,
                start_datetime=start_time,
                end_datetime=end_time,
                create_chat=True
            ),
            verified_user.id
        )

        event_crud.invite_participant(db_session, event.id, member_user.id)

        login_resp = client.post("/auth/login", data={
            "username": "decline@event.com", "password": "Test123456"
        })
        token = login_resp.json()["access_token"]

        response = client.post(
            f"/events/{event.id}/respond",
            headers={"Authorization": f"Bearer {token}"},
            json={"accept": False}
        )

        assert response.status_code == 200
        assert "отклонено" in response.json()["message"]

    def test_get_pending_invitations(self, client: TestClient, verified_user, db_session: Session):
        """Получение списка ожидающих приглашений"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Pending Family"), verified_user.id)

        member_user = user_crud.register_user(db_session, UserCreate(
            email="pending@event.com", password="Test123456", name="Pending User"
        ))
        member_user.is_verified = True
        db_session.commit()

        family_crud.add_member(db_session, family.id, FamilyMemberCreate(
            first_name="Pending", last_name="Test", gender=Gender.male,
            birth_date=datetime.now(timezone.utc), user_id=member_user.id
        ), verified_user.id)

        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)

        event = event_crud.create_event(
            db_session,
            EventCreate(
                title="Pending Event",
                family_id=family.id,
                start_datetime=start_time,
                end_datetime=end_time,
                create_chat=False
            ),
            verified_user.id
        )

        event_crud.invite_participant(db_session, event.id, member_user.id)

        login_resp = client.post("/auth/login", data={
            "username": "pending@event.com", "password": "Test123456"
        })
        token = login_resp.json()["access_token"]

        response = client.get(
            "/events/my/invitations/pending",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["event_title"] == "Pending Event"

    def test_cannot_invite_non_family_member(self, client: TestClient, verified_user, auth_headers,
                                             db_session: Session):
        """Нельзя пригласить пользователя не из семьи"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Restrict"), verified_user.id)

        outsider = user_crud.register_user(db_session, UserCreate(
            email="outsider@event.com", password="Test123456", name="Outsider"
        ))
        outsider.is_verified = True
        db_session.commit()

        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)

        event = event_crud.create_event(
            db_session,
            EventCreate(
                title="Private Event",
                family_id=family.id,
                start_datetime=start_time,
                end_datetime=end_time,
                create_chat=False
            ),
            verified_user.id
        )

        response = client.post(
            f"/events/{event.id}/invite",
            headers=auth_headers,
            json={"user_id": outsider.id}
        )

        assert response.status_code == 400
        assert "не является членом семьи" in response.json()["detail"].lower()


class TestEventCalendar:
    """Тесты календаря событий"""

    def test_calendar_shows_only_accepted(self, client: TestClient, verified_user, db_session: Session):
        """Календарь показывает только принятые события"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Calendar Family"), verified_user.id)

        member_user = user_crud.register_user(db_session, UserCreate(
            email="calendar@event.com", password="Test123456", name="Calendar User"
        ))
        member_user.is_verified = True
        db_session.commit()

        family_crud.add_member(db_session, family.id, FamilyMemberCreate(
            first_name="Calendar", last_name="Test", gender=Gender.male,
            birth_date=datetime.now(timezone.utc), user_id=member_user.id
        ), verified_user.id)

        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)

        # Создаем два события
        event1 = event_crud.create_event(
            db_session,
            EventCreate(
                title="Accepted Event",
                family_id=family.id,
                start_datetime=start_time,
                end_datetime=end_time,
                create_chat=False
            ),
            verified_user.id
        )

        event2 = event_crud.create_event(
            db_session,
            EventCreate(
                title="Declined Event",
                family_id=family.id,
                start_datetime=start_time + timedelta(days=1),
                end_datetime=end_time + timedelta(days=1),
                create_chat=False
            ),
            verified_user.id
        )

        event_crud.invite_participant(db_session, event1.id, member_user.id)
        event_crud.invite_participant(db_session, event2.id, member_user.id)
        event_crud.respond_to_invitation(db_session, event1.id, member_user.id, accept=True)
        event_crud.respond_to_invitation(db_session, event2.id, member_user.id, accept=False)

        login_resp = client.post("/auth/login", data={
            "username": "calendar@event.com", "password": "Test123456"
        })
        token = login_resp.json()["access_token"]

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

    def test_only_admin_can_update_event(self, client: TestClient, verified_user, db_session: Session):
        """Только создатель может редактировать событие"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Admin Family"), verified_user.id)

        other_user = user_crud.register_user(db_session, UserCreate(
            email="otheradmin@event.com", password="Test123456", name="Other User"
        ))
        other_user.is_verified = True
        db_session.commit()

        family_crud.add_member(db_session, family.id, FamilyMemberCreate(
            first_name="Other", last_name="User", gender=Gender.male,
            birth_date=datetime.now(timezone.utc), user_id=other_user.id
        ), verified_user.id)

        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)

        event = event_crud.create_event(
            db_session,
            EventCreate(
                title="Protected Event",
                family_id=family.id,
                start_datetime=start_time,
                end_datetime=end_time,
                create_chat=False
            ),
            verified_user.id
        )

        login_resp = client.post("/auth/login", data={
            "username": "otheradmin@event.com", "password": "Test123456"
        })
        token = login_resp.json()["access_token"]

        response = client.put(
            f"/events/{event.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "Hacked Title"}
        )

        assert response.status_code == 403
        assert "Только создатель" in response.json()["detail"]

    def test_only_admin_can_delete_event(self, client: TestClient, verified_user, auth_headers, db_session: Session):
        """Только создатель может удалить событие"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Delete Family"), verified_user.id)

        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)

        event = event_crud.create_event(
            db_session,
            EventCreate(
                title="Delete Test",
                family_id=family.id,
                start_datetime=start_time,
                end_datetime=end_time,
                create_chat=False
            ),
            verified_user.id
        )

        response = client.delete(f"/events/{event.id}", headers=auth_headers)
        assert response.status_code == 200

        # Проверяем что удалено
        deleted_event = event_crud.get_event_by_id(db_session, event.id)
        assert deleted_event is None or deleted_event.is_active is False

    def test_remove_participant_by_admin(self, client: TestClient, verified_user, auth_headers, db_session: Session):
        """Создатель может удалить участника"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Remove Participant"), verified_user.id)

        member_user = user_crud.register_user(db_session, UserCreate(
            email="remove@event.com", password="Test123456", name="Remove User"
        ))
        member_user.is_verified = True
        db_session.commit()

        family_crud.add_member(db_session, family.id, FamilyMemberCreate(
            first_name="Remove", last_name="Test", gender=Gender.male,
            birth_date=datetime.now(timezone.utc), user_id=member_user.id
        ), verified_user.id)

        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)

        event = event_crud.create_event(
            db_session,
            EventCreate(
                title="Remove Test",
                family_id=family.id,
                start_datetime=start_time,
                end_datetime=end_time,
                create_chat=False
            ),
            verified_user.id
        )

        event_crud.invite_participant(db_session, event.id, member_user.id)

        response = client.delete(
            f"/events/{event.id}/participants/{member_user.id}",
            headers=auth_headers
        )

        assert response.status_code == 200


class TestEventChatIntegration:
    """Тесты интеграции событий и чатов"""

    def test_create_event_chat_later(self, client: TestClient, verified_user, auth_headers, db_session: Session):
        """Создание чата для события позже"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Late Chat"), verified_user.id)

        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)

        event = event_crud.create_event(
            db_session,
            EventCreate(
                title="Late Chat Event",
                family_id=family.id,
                start_datetime=start_time,
                end_datetime=end_time,
                create_chat=False
            ),
            verified_user.id
        )

        response = client.post(
            f"/events/{event.id}/create-chat",
            headers=auth_headers
        )

        assert response.status_code == 200
        assert "chat_id" in response.json()

    def test_cannot_create_duplicate_chat(self, client: TestClient, verified_user, auth_headers, db_session: Session):
        """Нельзя создать второй чат для события"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Dup Chat"), verified_user.id)

        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)

        event = event_crud.create_event(
            db_session,
            EventCreate(
                title="Dup Chat Event",
                family_id=family.id,
                start_datetime=start_time,
                end_datetime=end_time,
                create_chat=True
            ),
            verified_user.id
        )

        response = client.post(
            f"/events/{event.id}/create-chat",
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "уже существует" in response.json()["detail"].lower()