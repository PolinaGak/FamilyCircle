import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import io

from app.models.album import Album
from app.models.album_member import AlbumMember
from app.models.photo import Photo
from app.crud.album import album_crud
from app.crud.photo import photo_crud
from app.crud.family import family_crud
from app.crud.user import user_crud
from app.schemas.family import FamilyCreate
from app.schemas.album import AlbumCreate
from app.schemas.auth import UserCreate


class TestAlbumCreation:
    def test_create_album_success(self, client, verified_user, test_user_data, db_session):
        """Успешное создание альбома"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Test Family"), verified_user.id)

        login_resp = client.post("/auth/login",
                                 data={"username": test_user_data["email"], "password": test_user_data["password"]})
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]

        resp = client.post("/albums", headers={"Authorization": f"Bearer {token}"}, json={
            "title": "New Album", "description": "Desc", "family_id": family.id
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "New Album"
        assert data["family_id"] == family.id
        assert data["created_by_user_id"] == verified_user.id
        assert "expires_at" in data
        assert data["hours_until_deletion"] <= 168

    def test_create_album_no_family_access(self, client, verified_user, test_user_data, db_session):
        """Попытка создать альбом в чужой семье"""
        other_user = user_crud.register_user(db_session,
                                             UserCreate(email="other@test.com", password="Test123456", name="Other"))
        other_user.is_verified = True
        db_session.commit()
        other_family = family_crud.create_family(db_session, FamilyCreate(name="Other Family"), other_user.id)

        login_resp = client.post("/auth/login",
                                 data={"username": test_user_data["email"], "password": test_user_data["password"]})
        token = login_resp.json()["access_token"]

        resp = client.post("/albums", headers={"Authorization": f"Bearer {token}"}, json={
            "title": "Album", "family_id": other_family.id
        })
        # Теперь возвращаем 403 вместо 400 (см. обновленный код ниже)
        assert resp.status_code == 403

    def test_create_album_validation(self, client, verified_user, test_user_data, db_session):
        """Проверка валидации полей при создании альбома"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)

        login_resp = client.post("/auth/login",
                                 data={"username": test_user_data["email"], "password": test_user_data["password"]})
        token = login_resp.json()["access_token"]

        # отсутствует title
        resp = client.post("/albums", headers={"Authorization": f"Bearer {token}"}, json={"family_id": family.id})
        assert resp.status_code == 422


class TestAlbumAccess:
    def test_album_access_for_admin(self, client, verified_user, test_user_data, db_session):
        """Администратор альбома имеет полный доступ"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)
        album = album_crud.create_album(
            db_session,
            AlbumCreate(title="Album", description=None, family_id=family.id, event_id=None),
            verified_user.id
        )

        login_resp = client.post("/auth/login",
                                 data={"username": test_user_data["email"], "password": test_user_data["password"]})
        token = login_resp.json()["access_token"]

        # может видеть альбом
        resp = client.get(f"/albums/{album.id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

        # может обновить альбом
        resp = client.put(f"/albums/{album.id}", headers={"Authorization": f"Bearer {token}"},
                          json={"title": "Updated"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated"

        # может удалить альбом
        resp = client.delete(f"/albums/{album.id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        album_db = album_crud.get_album_by_id(db_session, album.id, include_deleted=True)
        assert album_db.is_deleted is True

    def test_album_access_for_member(self, client, verified_user, db_session):
        """Обычный участник альбома может просматривать и загружать фото, но не управлять"""
        admin_user = user_crud.register_user(db_session,
                                             UserCreate(email="admin@test.com", password="Test123456", name="Admin"))
        admin_user.is_verified = True
        db_session.commit()

        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), admin_user.id)

        member_user = user_crud.register_user(db_session,
                                              UserCreate(email="member@test.com", password="Test123456", name="Member"))
        member_user.is_verified = True
        db_session.commit()

        from app.crud.family import family_crud as fc
        from app.schemas.family_member import FamilyMemberCreate
        fc.add_member(db_session, family.id,
                      FamilyMemberCreate(first_name="Member", last_name="Test", birth_date=datetime.now(timezone.utc),
                                         user_id=member_user.id), admin_user.id)

        album = album_crud.create_album(
            db_session,
            AlbumCreate(title="Album", description=None, family_id=family.id, event_id=None),
            admin_user.id
        )

        # Добавляем участника в альбом как обычного члена (исправлено - передаем user_id напрямую)
        album_crud.add_member(db_session, album.id, member_user.id, admin_user.id)

        login_resp = client.post("/auth/login", data={"username": "member@test.com", "password": "Test123456"})
        token = login_resp.json()["access_token"]

        # может видеть альбом
        resp = client.get(f"/albums/{album.id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

        # не может обновить альбом
        resp = client.put(f"/albums/{album.id}", headers={"Authorization": f"Bearer {token}"}, json={"title": "Hacked"})
        assert resp.status_code == 403

        # не может удалить альбом
        resp = client.delete(f"/albums/{album.id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_album_access_for_non_member(self, client, verified_user, test_user_data, db_session):
        """Пользователь, не входящий в альбом, не имеет доступа"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)
        album = album_crud.create_album(
            db_session,
            AlbumCreate(title="Album", description=None, family_id=family.id, event_id=None),
            verified_user.id
        )

        other_user = user_crud.register_user(db_session, UserCreate(email="outsider@test.com", password="Test123456",
                                                                    name="Outsider"))
        other_user.is_verified = True
        db_session.commit()

        from app.crud.family import family_crud as fc
        from app.schemas.family_member import FamilyMemberCreate
        fc.add_member(db_session, family.id,
                      FamilyMemberCreate(first_name="Outsider", last_name="Test", birth_date=datetime.now(timezone.utc),
                                         user_id=other_user.id), verified_user.id)

        login_resp = client.post("/auth/login", data={"username": "outsider@test.com", "password": "Test123456"})
        token = login_resp.json()["access_token"]

        resp = client.get(f"/albums/{album.id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_album_access_expired(self, client, verified_user, test_user_data, db_session):
        """Истёкший альбом недоступен"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)
        album = Album(
            title="Expired", family_id=family.id, created_by_user_id=verified_user.id,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        db_session.add(album)
        db_session.commit()

        login_resp = client.post("/auth/login",
                                 data={"username": test_user_data["email"], "password": test_user_data["password"]})
        token = login_resp.json()["access_token"]

        resp = client.get(f"/albums/{album.id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403


class TestAlbumMembersAndAdmins:
    """Тесты управления участниками и администраторами альбома"""

    @pytest.fixture
    def setup_album_with_family(self, db_session: Session, verified_user):
        """Фикстура: семья с альбомом и несколькими членами"""
        family = family_crud.create_family(
            db_session,
            FamilyCreate(name="Admin Test Family"),
            verified_user.id
        )

        album = album_crud.create_album(
            db_session,
            AlbumCreate(family_id=family.id, title="Test Album"),
            verified_user.id
        )

        # Создаем членов семьи
        members = []
        for i in range(3):
            user = user_crud.register_user(db_session, UserCreate(
                email=f"member{i}@test.com",
                password="Test123456",
                name=f"Member {i}"
            ))
            user.is_verified = True
            db_session.commit()

            from app.schemas.family_member import FamilyMemberCreate
            family_crud.add_member(
                db_session,
                family.id,
                FamilyMemberCreate(
                    first_name=f"Member{i}",
                    last_name="Family",
                    birth_date=datetime.now(timezone.utc),
                    user_id=user.id,
                    is_admin=False,
                    approved=True
                ),
                verified_user.id
            )
            members.append(user)

        return {
            "family": family,
            "album": album,
            "admin": verified_user,
            "members": members
        }

    def test_add_family_member_to_album(self, client, setup_album_with_family, db_session):
        """Добавление члена семьи в альбом админом"""
        setup = setup_album_with_family

        # Логинимся админом (исправлено: data= вместо json=)
        login_response = client.post("/auth/login", data={
            "username": "test@example.com",
            "password": "Test123456!"
        })
        token = login_response.json()["access_token"]

        target_user = setup["members"][0]

        # Добавляем в альбом (исправлено: передаем только user_id)
        response = client.post(
            f"/albums/{setup['album'].id}/members",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": target_user.id}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == target_user.id
        assert data["can_edit"] is False
        assert data["can_delete"] is False

    def test_add_non_family_member_to_album(self, client, setup_album_with_family, db_session):
        """Попытка добавить пользователя не из семьи"""
        setup = setup_album_with_family

        # Создаем пользователя из другой семьи
        outsider = user_crud.register_user(db_session, UserCreate(
            email="outsider@test.com",
            password="Test123456",
            name="Outsider"
        ))
        outsider.is_verified = True
        db_session.commit()

        login_response = client.post("/auth/login", data={
            "username": "test@example.com",
            "password": "Test123456!"
        })
        token = login_response.json()["access_token"]

        response = client.post(
            f"/albums/{setup['album'].id}/members",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": outsider.id}
        )

        assert response.status_code == 400
        assert "не является членом семьи" in response.json()["detail"].lower()

    def test_add_member_by_non_admin(self, client, setup_album_with_family, db_session):
        """Попытка добавить участника не-админом"""
        setup = setup_album_with_family

        # Сначала добавляем первого члена в альбом
        album_crud.add_member(db_session, setup['album'].id, setup['members'][0].id, setup['admin'].id)

        # Логинимся обычным членом
        login_response = client.post("/auth/login", data={
            "username": setup["members"][0].email,
            "password": "Test123456"
        })
        token = login_response.json()["access_token"]

        # Пытаемся добавить другого
        response = client.post(
            f"/albums/{setup['album'].id}/members",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": setup["members"][1].id}
        )

        assert response.status_code == 400
        assert "только администратор" in response.json()["detail"].lower()

    def test_add_admin_to_album(self, client, setup_album_with_family, db_session):
        """Назначение администратора"""
        setup = setup_album_with_family

        login_response = client.post("/auth/login", data={
            "username": "test@example.com",
            "password": "Test123456!"
        })
        token = login_response.json()["access_token"]

        target_user = setup["members"][0]

        response = client.post(
            f"/albums/{setup['album'].id}/admins",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": target_user.id}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == target_user.id
        assert data["can_edit"] is True
        assert data["can_delete"] is True

    def test_promote_existing_member_to_admin(self, client, setup_album_with_family, db_session):
        """Повышение существующего участника до админа"""
        setup = setup_album_with_family

        # Сначала добавляем как обычного участника
        album_crud.add_member(db_session, setup['album'].id, setup['members'][0].id, setup['admin'].id)

        login_response = client.post("/auth/login", data={
            "username": "test@example.com",
            "password": "Test123456!"
        })
        token = login_response.json()["access_token"]

        # Повышаем до админа
        response = client.post(
            f"/albums/{setup['album'].id}/admins",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": setup["members"][0].id}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["can_edit"] is True
        assert data["can_delete"] is True

    def test_remove_admin_rights(self, client, setup_album_with_family, db_session):
        """Снятие прав администратора"""
        setup = setup_album_with_family

        # Добавляем админа
        album_crud.add_admin(db_session, setup['album'].id, setup['members'][0].id, setup['admin'].id)

        login_response = client.post("/auth/login", data={
            "username": "test@example.com",
            "password": "Test123456!"
        })
        token = login_response.json()["access_token"]

        # Снимаем права
        response = client.delete(
            f"/albums/{setup['album'].id}/admins/{setup['members'][0].id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["can_edit"] is False
        assert data["can_delete"] is False

    def test_remove_admin_rights_self(self, client, setup_album_with_family, db_session):
        """Попытка снять права с самого себя"""
        setup = setup_album_with_family

        # Добавляем админа
        album_crud.add_admin(db_session, setup['album'].id, setup['members'][0].id, setup['admin'].id)

        # Логинимся этим админом
        login_response = client.post("/auth/login", data={
            "username": setup["members"][0].email,
            "password": "Test123456"
        })
        token = login_response.json()["access_token"]

        # Пытаемся снять права с себя
        response = client.delete(
            f"/albums/{setup['album'].id}/admins/{setup['members'][0].id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 400
        assert "самого себя" in response.json()["detail"].lower()

    def test_cannot_delete_admin_member_directly(self, client, setup_album_with_family, db_session):
        """Нельзя удалить админа напрямую - нужно сначала снять права"""
        setup = setup_album_with_family

        # Добавляем админа
        album_crud.add_admin(db_session, setup['album'].id, setup['members'][0].id, setup['admin'].id)

        login_response = client.post("/auth/login", data={
            "username": "test@example.com",
            "password": "Test123456!"
        })
        token = login_response.json()["access_token"]

        # Пытаемся удалить админа напрямую через endpoint обычных членов
        response = client.delete(
            f"/albums/{setup['album'].id}/members/{setup['members'][0].id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 400
        assert "снимите права" in response.json()["detail"].lower()

    def test_list_admins(self, client, setup_album_with_family, db_session):
        """Получение списка администраторов"""
        setup = setup_album_with_family

        # Добавляем двух админов
        album_crud.add_admin(db_session, setup['album'].id, setup['members'][0].id, setup['admin'].id)
        album_crud.add_admin(db_session, setup['album'].id, setup['members'][1].id, setup['admin'].id)

        login_response = client.post("/auth/login", data={
            "username": "test@example.com",
            "password": "Test123456!"
        })
        token = login_response.json()["access_token"]

        # Получаем список админов
        response = client.get(
            f"/albums/{setup['album'].id}/admins",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3  # Создатель + 2 добавленных


class TestPhotoOperations:
    def test_upload_photo_success(self, client, verified_user, test_user_data, db_session):
        """Загрузка фото в альбом"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)
        album = album_crud.create_album(
            db_session,
            AlbumCreate(title="Album", description=None, family_id=family.id, event_id=None),
            verified_user.id
        )

        login_resp = client.post("/auth/login",
                                 data={"username": test_user_data["email"], "password": test_user_data["password"]})
        token = login_resp.json()["access_token"]

        from PIL import Image
        img_bytes = io.BytesIO()
        img = Image.new('RGB', (100, 100), color='red')
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)

        resp = client.post(
            f"/albums/{album.id}/photos",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.jpg", img_bytes, "image/jpeg")},
            data={"description": "Test photo"}
        )
        # Исправлено: API возвращает 200, а не 201
        assert resp.status_code == 200
        data = resp.json()
        assert data["photo"]["original_filename"] == "test.jpg"
        assert data["photo"]["description"] == "Test photo"

    def test_upload_photo_unauthorized(self, client, db_session):
        """Загрузка фото без прав доступа к альбому"""
        admin_user = user_crud.register_user(db_session,
                                             UserCreate(email="admin@test.com", password="Test123456", name="Admin"))
        admin_user.is_verified = True
        db_session.commit()
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), admin_user.id)
        album = album_crud.create_album(
            db_session,
            AlbumCreate(title="Album", description=None, family_id=family.id, event_id=None),
            admin_user.id
        )

        other_user = user_crud.register_user(db_session, UserCreate(email="outsider@test.com", password="Test123456",
                                                                    name="Outsider"))
        other_user.is_verified = True
        db_session.commit()

        login_resp = client.post("/auth/login", data={"username": "outsider@test.com", "password": "Test123456"})
        token = login_resp.json()["access_token"]

        img_bytes = io.BytesIO(b"fake image")
        resp = client.post(
            f"/albums/{album.id}/photos",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.jpg", img_bytes, "image/jpeg")}
        )
        assert resp.status_code == 403

    def test_upload_duplicate_photo(self, client, verified_user, test_user_data, db_session):
        """Загрузка дубликата фото (по хешу) не должна проходить"""
        family = family_crud.create_family(db_session, FamilyCreate(name="Family"), verified_user.id)
        album = album_crud.create_album(
            db_session,
            AlbumCreate(title="Album", description=None, family_id=family.id, event_id=None),
            verified_user.id
        )

        login_resp = client.post("/auth/login",
                                 data={"username": test_user_data["email"], "password": test_user_data["password"]})
        token = login_resp.json()["access_token"]

        from PIL import Image
        img_bytes = io.BytesIO()
        img = Image.new('RGB', (100, 100), color='red')
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)

        resp1 = client.post(
            f"/albums/{album.id}/photos",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.jpg", img_bytes, "image/jpeg")}
        )
        assert resp1.status_code == 200

        img_bytes.seek(0)
        resp2 = client.post(
            f"/albums/{album.id}/photos",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.jpg", img_bytes, "image/jpeg")}
        )
        assert resp2.status_code == 400
        assert "уже есть" in resp2.json()["detail"].lower()


