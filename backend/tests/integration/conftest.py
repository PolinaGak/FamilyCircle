import pytest
import os
import sys
from pathlib import Path
import asyncio
from typing import Generator, AsyncGenerator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app.main import app
from app.database import Base, get_db
from app.core.config import settings
from app.core.security import get_password_hash
from app.models.user import User
from app.models.enums import ThemeType


# Тестовая БД
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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