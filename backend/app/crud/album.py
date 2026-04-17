from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timezone, timedelta

from backend.app.models import (Album, AlbumMember, Photo, Event, EventParticipant,
                                FamilyMember, InvitationStatus)

from backend.app.schemas.album import AlbumCreate, AlbumUpdate
import logging
import os

logger = logging.getLogger(__name__)

class AlbumCRUD:

    @staticmethod
    def create_album(db: Session, album_data: AlbumCreate, created_by_user_id: int) -> Album:
        try:
            from backend.app.crud.family import family_crud
            if not family_crud.is_family_member(db, created_by_user_id, album_data.family_id):
                raise ValueError("Вы не являетесь членом этой семьи")
            album = Album(
                title=album_data.title.strip(),
                description=album_data.description.strip() if album_data.description else None,
                family_id=album_data.family_id,
                created_by_user_id=created_by_user_id,
                event_id=album_data.event_id,
                expires_at=datetime.now(timezone.utc) + timedelta(days=7)
            )
            db.add(album)
            db.flush()
            admin_member = AlbumMember(
                album_id=album.id,
                user_id=created_by_user_id,
                can_edit=True,
                can_delete=True,
                status=InvitationStatus.accepted,
                added_by_user_id=created_by_user_id
            )
            db.add(admin_member)
            db.commit()
            db.refresh(album)
            logger.info(f"Альбом '{album.title}' создан пользователем {created_by_user_id}")
            return album
        except Exception as e:
            logger.error(f"Ошибка при создании альбома: {str(e)}")
            db.rollback()
            raise

    @staticmethod
    def get_album_by_id(db: Session, album_id: int, include_deleted: bool = False) -> Optional[Album]:
        query = db.query(Album).filter(Album.id == album_id)
        if not include_deleted:
            query = query.filter(Album.is_deleted == False)
        return query.first()

    @staticmethod
    def get_album_with_details(db: Session, album_id: int) -> Optional[Album]:
        return db.query(Album) \
            .options(
            joinedload(Album.members).joinedload(AlbumMember.user),
            joinedload(Album.photos),
            joinedload(Album.created_by)
        ) \
            .filter(Album.id == album_id, Album.is_deleted == False) \
            .first()

    @staticmethod
    def get_user_albums(db: Session, user_id: int, family_id: Optional[int] = None) -> List[Album]:
        member_albums = db.query(Album).join(
            AlbumMember, Album.id == AlbumMember.album_id
        ).filter(
            AlbumMember.user_id == user_id,
            Album.is_deleted == False,
            AlbumMember.status == InvitationStatus.accepted
        )
        event_albums = db.query(Album).join(
            Event, Album.event_id == Event.id
        ).join(
            EventParticipant, Event.id == EventParticipant.event_id
        ).filter(
            EventParticipant.user_id == user_id,
            Album.is_deleted == False
        )
        query = member_albums.union(event_albums)
        if family_id:
            query = query.filter(Album.family_id == family_id)
        now = datetime.now(timezone.utc)
        return query.filter(Album.expires_at > now).order_by(Album.created_at.desc()).all()

    @staticmethod
    def get_family_albums(db: Session, family_id: int, user_id: int) -> List[Album]:
        return AlbumCRUD.get_user_albums(db, user_id, family_id)

    @staticmethod
    def update_album(db: Session, album_id: int, update_data: AlbumUpdate) -> Optional[Album]:
        album = AlbumCRUD.get_album_by_id(db, album_id)
        if not album:
            return None
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            if value is not None:
                if key in ['title', 'description'] and isinstance(value, str):
                    value = value.strip()
                setattr(album, key, value)
        db.commit()
        db.refresh(album)
        return album

    @staticmethod
    def delete_album(db: Session, album_id: int, permanent: bool = False) -> bool:
        try:
            album = AlbumCRUD.get_album_by_id(db, album_id, include_deleted=True)
            if not album:
                return False
            if permanent:
                for photo in album.photos:
                    AlbumCRUD._delete_photo_file(photo.file_path)
                db.delete(album)
            else:
                album.is_deleted = True
            db.commit()
            logger.info(f"Альбом {album_id} удален (permanent={permanent})")
            return True
        except Exception as e:
            logger.error(f"Ошибка при удалении альбома {album_id}: {str(e)}")
            db.rollback()
            return False

    @staticmethod
    def _delete_photo_file(file_path: str):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Файл удален: {file_path}")
        except Exception as e:
            logger.error(f"Ошибка при удалении файла {file_path}: {str(e)}")

    @staticmethod
    def is_album_admin(db: Session, user_id: int, album_id: int) -> bool:
        member = db.query(AlbumMember).filter(
            AlbumMember.album_id == album_id,
            AlbumMember.user_id == user_id,
            AlbumMember.can_edit == True,
            AlbumMember.can_delete == True,
            AlbumMember.status == InvitationStatus.accepted
        ).first()
        return member is not None

    @staticmethod
    def is_album_member(db: Session, user_id: int, album_id: int) -> bool:
        member = db.query(AlbumMember).filter(
            AlbumMember.album_id == album_id,
            AlbumMember.user_id == user_id,
            AlbumMember.status == InvitationStatus.accepted
        ).first()
        if member:
            return True
        album = AlbumCRUD.get_album_by_id(db, album_id)
        if album and album.event_id:
            event_access = db.query(EventParticipant).filter(
                EventParticipant.event_id == album.event_id,
                EventParticipant.user_id == user_id,
                EventParticipant.status == InvitationStatus.accepted
            ).first()
            return event_access is not None
        return False

    @staticmethod
    def can_upload_photos(db: Session, user_id: int, album_id: int) -> bool:
        album = AlbumCRUD.get_album_by_id(db, album_id)
        if not album or album.is_expired or album.is_deleted:
            return False
        return AlbumCRUD.is_album_member(db, user_id, album_id)

    @staticmethod
    def can_view_album(db: Session, user_id: int, album_id: int) -> bool:
        album = AlbumCRUD.get_album_by_id(db, album_id)
        if not album or album.is_deleted:
            return False
        if album.is_expired:
            return False
        return AlbumCRUD.is_album_member(db, user_id, album_id)

    @staticmethod
    def _is_family_member(db: Session, user_id: int, family_id: int) -> bool:
        from backend.app.crud.family import family_crud
        return family_crud.is_family_member(db, user_id, family_id)

    @staticmethod
    def add_member(db: Session, album_id: int, user_id: int, added_by_user_id: int) -> AlbumMember:
        if not AlbumCRUD.is_album_admin(db, added_by_user_id, album_id):
            raise ValueError("Только администратор может добавлять участников")
        album = AlbumCRUD.get_album_by_id(db, album_id)
        if not album:
            raise ValueError("Альбом не найден")
        if not AlbumCRUD._is_family_member(db, user_id, album.family_id):
            raise ValueError("Пользователь не является членом семьи")
        existing = db.query(AlbumMember).filter(
            AlbumMember.album_id == album_id,
            AlbumMember.user_id == user_id
        ).first()
        if existing:
            raise ValueError("Пользователь уже является участником альбома")
        member = AlbumMember(
            album_id=album_id,
            user_id=user_id,
            can_edit=False,
            can_delete=False,
            status=InvitationStatus.accepted,
            added_by_user_id=added_by_user_id
        )
        db.add(member)
        db.commit()
        db.refresh(member)
        logger.info(f"Пользователь {user_id} добавлен в альбом {album_id}")
        return member

    @staticmethod
    def add_admin(db: Session, album_id: int, user_id: int, added_by_user_id: int) -> AlbumMember:
        if not AlbumCRUD.is_album_admin(db, added_by_user_id, album_id):
            raise ValueError("Только администратор может добавлять администраторов")
        album = AlbumCRUD.get_album_by_id(db, album_id)
        if not album:
            raise ValueError("Альбом не найден")
        if not AlbumCRUD._is_family_member(db, user_id, album.family_id):
            raise ValueError("Пользователь не является членом семьи")
        existing = db.query(AlbumMember).filter(
            AlbumMember.album_id == album_id,
            AlbumMember.user_id == user_id
        ).first()
        if existing:
            if existing.can_edit and existing.can_delete:
                raise ValueError("Пользователь уже является администратором")
            existing.can_edit = True
            existing.can_delete = True
            db.commit()
            db.refresh(existing)
            logger.info(f"Пользователь {user_id} повышен до админа в альбоме {album_id}")
            return existing
        member = AlbumMember(
            album_id=album_id,
            user_id=user_id,
            can_edit=True,
            can_delete=True,
            status=InvitationStatus.accepted,
            added_by_user_id=added_by_user_id
        )
        db.add(member)
        db.commit()
        db.refresh(member)
        logger.info(f"Администратор {user_id} добавлен в альбом {album_id}")
        return member

    @staticmethod
    def remove_admin_rights(db: Session, album_id: int, user_id: int, removed_by_user_id: int) -> AlbumMember:
        if not AlbumCRUD.is_album_admin(db, removed_by_user_id, album_id):
            raise ValueError("Только администратор может снимать права администраторов")
        if user_id == removed_by_user_id:
            raise ValueError("Нельзя снять права с самого себя")
        member = db.query(AlbumMember).filter(
            AlbumMember.album_id == album_id,
            AlbumMember.user_id == user_id,
            AlbumMember.can_edit == True,
            AlbumMember.can_delete == True,
            AlbumMember.status == InvitationStatus.accepted
        ).first()
        if not member:
            raise ValueError("Пользователь не является администратором этого альбома")
        admin_count = db.query(AlbumMember).filter(
            AlbumMember.album_id == album_id,
            AlbumMember.can_edit == True,
            AlbumMember.can_delete == True,
            AlbumMember.status == InvitationStatus.accepted
        ).count()
        if admin_count <= 1:
            raise ValueError("Нельзя снять права с последнего администратора")
        member.can_edit = False
        member.can_delete = False
        db.commit()
        db.refresh(member)
        logger.info(f"Права администратора сняты с пользователя {user_id} в альбоме {album_id}")
        return member

    @staticmethod
    def remove_member(db: Session, album_id: int, user_id: int, removed_by_user_id: int) -> bool:
        is_admin = AlbumCRUD.is_album_admin(db, removed_by_user_id, album_id)
        is_self = user_id == removed_by_user_id
        if not (is_admin or is_self):
            raise ValueError("Нет прав на удаление участника")
        member = db.query(AlbumMember).filter(
            AlbumMember.album_id == album_id,
            AlbumMember.user_id == user_id
        ).first()
        if not member:
            return False
        if member.can_delete and not is_self:
            raise ValueError("Сначала снимите права администратора")
        if is_self and member.can_delete:
            admin_count = db.query(AlbumMember).filter(
                AlbumMember.album_id == album_id,
                AlbumMember.can_delete == True,
                AlbumMember.status == InvitationStatus.accepted
            ).count()
            if admin_count <= 1:
                raise ValueError("Нельзя удалить единственного администратора")
        db.delete(member)
        db.commit()
        logger.info(f"Пользователь {user_id} удален из альбома {album_id}")
        return True

    @staticmethod
    def get_album_members(db: Session, album_id: int) -> List[AlbumMember]:
        return db.query(AlbumMember) \
            .filter(AlbumMember.album_id == album_id) \
            .order_by(AlbumMember.added_at) \
            .all()

    @staticmethod
    def get_album_admins(db: Session, album_id: int) -> List[AlbumMember]:
        return db.query(AlbumMember) \
            .filter(
            AlbumMember.album_id == album_id,
            AlbumMember.can_edit == True,
            AlbumMember.can_delete == True,
            AlbumMember.status == InvitationStatus.accepted
        ) \
            .all()

    @staticmethod
    def get_expired_albums(db: Session) -> List[Album]:
        now = datetime.now(timezone.utc)
        return db.query(Album).filter(
            Album.expires_at <= now,
            Album.is_deleted == False
        ).all()

    @staticmethod
    def get_albums_for_deletion_notification(db: Session, hours_before: int = 24) -> List[Album]:
        now = datetime.now(timezone.utc)
        notification_time = now + timedelta(hours=hours_before)
        return db.query(Album).filter(
            Album.expires_at <= notification_time,
            Album.expires_at > now,
            Album.is_deleted == False,
            Album.deletion_notified_at == None
        ).all()

    @staticmethod
    def mark_deletion_notified(db: Session, album_id: int):
        album = AlbumCRUD.get_album_by_id(db, album_id)
        if album:
            album.deletion_notified_at = datetime.now(timezone.utc)
            db.commit()

album_crud = AlbumCRUD()