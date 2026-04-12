import pytest
import os
import sys
from pathlib import Path
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from datetime import datetime, timezone
from sqlalchemy.types import DateTime

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app.main import app
from app.database import Base, get_db
from app.core.security import get_password_hash
from app.models.user import User
from app.models.enums import ThemeType, Gender, RelationshipType
from app.crud.family import family_crud
from app.crud.user import user_crud
from app.crud.album import album_crud
from app.crud.event import event_crud
from app.crud.chat import chat_crud
from app.schemas.family import FamilyCreate
from app.schemas.family_member import FamilyMemberCreate
from app.schemas.album import AlbumCreate
from app.schemas.event import EventCreate
from app.schemas.chat import ChatCreate
from app.schemas.auth import UserCreate

# Тестовая БД
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@event.listens_for(Session, 'loaded_as_persistent')
def ensure_aware_on_load(session, instance):
    """Делает все datetime поля с timezone=True — aware (UTC) при загрузке в сессию."""
    for column in instance.__table__.columns:
        if isinstance(column.type, DateTime) and column.type.timezone:
            value = getattr(instance, column.name, None)
            if value is not None and value.tzinfo is None:
                setattr(instance, column.name, value.replace(tzinfo=timezone.utc))

def override_get_db() -> Generator[Session, None, None]:
    """Переопределение зависимости get_db для тестов"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Фикстура сессии БД для каждого теста"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Фикстура тестового клиента"""
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user_data():
    """Данные тестового пользователя"""
    return {
        "email": "test@example.com",
        "password": "Test123456!",
        "name": "Test User"
    }


@pytest.fixture
def verified_user(db_session: Session, test_user_data):
    """Создание подтвержденного пользователя в БД"""
    hashed_password = get_password_hash(test_user_data["password"])
    user = User(
        email=test_user_data["email"],
        password_hash=hashed_password,
        name=test_user_data["name"],
        is_verified=True,
        theme=ThemeType.light
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(client: TestClient, verified_user, test_user_data):
    """Получение заголовков авторизации"""
    login_resp = client.post("/auth/login", data={
        "username": test_user_data["email"],
        "password": test_user_data["password"]
    })
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# Фабрики для создания тестовых данных

@pytest.fixture
def user_factory(db_session: Session):
    """Фабрика для создания пользователей"""

    def _create_user(email: str, name: str = "Test", verified: bool = True):
        user = User(
            email=email,
            password_hash=get_password_hash("Test123456!"),
            name=name,
            is_verified=verified,
            theme=ThemeType.light
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _create_user


@pytest.fixture
def family_factory(db_session: Session, verified_user):
    """Фабрика для создания семей"""

    def _create_family(name: str = "Test Family", admin_id: int = None):
        if admin_id is None:
            admin_id = verified_user.id
        return family_crud.create_family(
            db_session,
            FamilyCreate(name=name),
            admin_id
        )

    return _create_family


@pytest.fixture
def family_member_factory(db_session: Session):
    """Фабрика для создания членов семьи"""

    def _create_member(family_id: int, creator_id: int, **kwargs):
        defaults = {
            "first_name": "Иван",
            "last_name": "Иванов",
            "gender": Gender.male,
            "birth_date": datetime.now(timezone.utc),
            "is_admin": False,
            "approved": True
        }
        defaults.update(kwargs)
        member_data = FamilyMemberCreate(**defaults)
        return family_crud.add_member(db_session, family_id, member_data, creator_id)

    return _create_member


@pytest.fixture
def album_factory(db_session: Session):
    """Фабрика для создания альбомов"""

    def _create_album(family_id: int, creator_id: int, title: str = "Test Album"):
        return album_crud.create_album(
            db_session,
            AlbumCreate(title=title, family_id=family_id),
            creator_id
        )

    return _create_album


@pytest.fixture
def event_factory(db_session: Session):
    """Фабрика для создания событий"""

    def _create_event(family_id: int, creator_id: int, title: str = "Test Event",
                      start: datetime = None, end: datetime = None, create_chat: bool = False):
        if start is None:
            start = datetime.now(timezone.utc) + timedelta(days=1)
        if end is None:
            end = start + timedelta(hours=2)

        return event_crud.create_event(
            db_session,
            EventCreate(
                title=title,
                family_id=family_id,
                start_datetime=start,
                end_datetime=end,
                create_chat=create_chat
            ),
            creator_id
        )

    return _create_event


@pytest.fixture
def chat_factory(db_session: Session):
    """Фабрика для создания чатов"""

    def _create_chat(family_id: int, creator_id: int, title: str = "Test Chat"):
        return chat_crud.create_chat(
            db_session,
            ChatCreate(family_id=family_id, title=title),
            creator_id
        )

    return _create_chat

@pytest.fixture(autouse=True)
def make_invitation_expires_aware():
    """Автоматически преобразует expires_at приглашений в aware datetime для всех тестов."""
    from app.crud.invitation import invitation_crud
    original_get = invitation_crud.get_invitation_by_code

    def aware_get(db, code):
        invitation = original_get(db, code)
        if invitation and invitation.expires_at and invitation.expires_at.tzinfo is None:
            invitation.expires_at = invitation.expires_at.replace(tzinfo=timezone.utc)
        return invitation

    invitation_crud.get_invitation_by_code = aware_get
    yield
    invitation_crud.get_invitation_by_code = original_get