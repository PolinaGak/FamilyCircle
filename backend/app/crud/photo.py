from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import os
import hashlib
import shutil
from pathlib import Path

from backend.app.models.photo import Photo
from backend.app.schemas.photo import PhotoUpdate
import logging

logger = logging.getLogger(__name__)


class PhotoCRUD:

    UPLOAD_DIR = Path("uploads/photos")
    ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/webp']
    MAX_FILE_SIZE = 20 * 1024 * 1024

    def __init__(self):
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    def _generate_file_path(self, album_id: int, file_hash: str, extension: str) -> str:
        album_dir = self.UPLOAD_DIR / str(album_id)
        album_dir.mkdir(exist_ok=True)
        filename = f"{file_hash}{extension}"
        return str(album_dir / filename)

    def _calculate_file_hash(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def _save_uploaded_file(self, content: bytes, file_path: str) -> bool:
        try:
            with open(file_path, 'wb') as f:
                f.write(content)
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения файла: {str(e)}")
            return False

    def create_photo(
            self,
            db: Session,
            album_id: int,
            uploaded_by_user_id: int,
            file_content: bytes,
            original_filename: str,
            mime_type: str,
            description: Optional[str] = None
    ) -> Photo:

        if mime_type.lower() not in self.ALLOWED_MIME_TYPES:
            raise ValueError(f"Неподдерживаемый формат файла: {mime_type}")

        if len(file_content) > self.MAX_FILE_SIZE:
            raise ValueError(f"Файл слишком большой. Максимум {self.MAX_FILE_SIZE // (1024 * 1024)} MB")

        file_hash = self._calculate_file_hash(file_content)

        existing = db.query(Photo).filter(
            Photo.album_id == album_id,
            Photo.file_hash == file_hash
        ).first()

        if existing:
            raise ValueError("Такое фото уже есть в альбоме")

        extension = Photo.ALLOWED_MIME_TYPES.get(mime_type.lower(), ['.jpg'])[0]

        file_path = self._generate_file_path(album_id, file_hash, extension)

        if not self._save_uploaded_file(file_content, file_path):
            raise ValueError("Не удалось сохранить файл")

        width, height = self._get_image_dimensions(file_content, mime_type)

        photo = Photo(
            album_id=album_id,
            uploaded_by_user_id=uploaded_by_user_id,
            file_path=file_path,
            original_filename=original_filename,
            file_size=len(file_content),
            mime_type=mime_type.lower(),
            file_hash=file_hash,
            width=width,
            height=height,
            description=description
        )

        db.add(photo)
        db.commit()
        db.refresh(photo)

        logger.info(f"Фото {photo.id} загружено в альбом {album_id}")
        return photo

    def _get_image_dimensions(self, content: bytes, mime_type: str) -> tuple[Optional[int], Optional[int]]:
        try:
            from PIL import Image
            import io

            image = Image.open(io.BytesIO(content))
            return image.size
        except Exception as e:
            logger.warning(f"Не удалось получить размеры изображения: {str(e)}")
            return None, None

    def get_photo_by_id(self, db: Session, photo_id: int) -> Optional[Photo]:
        return db.query(Photo).filter(Photo.id == photo_id).first()

    def get_album_photos(
            self,
            db: Session,
            album_id: int,
            limit: int = 50,
            offset: int = 0
    ) -> tuple[List[Photo], int]:
        query = db.query(Photo).filter(Photo.album_id == album_id)
        total = query.count()
        photos = query.order_by(Photo.uploaded_at.desc()).offset(offset).limit(limit).all()
        return photos, total

    def update_photo(
            self,
            db: Session,
            photo_id: int,
            update_data: PhotoUpdate,
            user_id: int
    ) -> Optional[Photo]:
        photo = self.get_photo_by_id(db, photo_id)
        if not photo:
            return None

        from backend.app.crud.album import album_crud
        is_admin = album_crud.is_album_admin(db, user_id, photo.album_id)
        is_uploader = photo.uploaded_by_user_id == user_id

        if not (is_admin or is_uploader):
            raise ValueError("Нет прав на редактирование фото")

        if update_data.description is not None:
            photo.description = update_data.description

        db.commit()
        db.refresh(photo)
        return photo

    def delete_photo(self, db: Session, photo_id: int, user_id: int) -> bool:
        photo = self.get_photo_by_id(db, photo_id)
        if not photo:
            return False

        from backend.app.crud.album import album_crud
        is_admin = album_crud.is_album_admin(db, user_id, photo.album_id)
        is_uploader = photo.uploaded_by_user_id == user_id

        if not (is_admin or is_uploader):
            raise ValueError("Нет прав на удаление фото")

        try:
            if os.path.exists(photo.file_path):
                os.remove(photo.file_path)
        except Exception as e:
            logger.error(f"Ошибка удаления файла: {str(e)}")

        db.delete(photo)
        db.commit()
        logger.info(f"Фото {photo_id} удалено")
        return True

    def delete_album_photos(self, db: Session, album_id: int):
        photos = db.query(Photo).filter(Photo.album_id == album_id).all()

        for photo in photos:
            try:
                if os.path.exists(photo.file_path):
                    os.remove(photo.file_path)
            except Exception as e:
                logger.error(f"Ошибка удаления файла {photo.file_path}: {str(e)}")

            db.delete(photo)

        album_dir = self.UPLOAD_DIR / str(album_id)
        try:
            if album_dir.exists():
                shutil.rmtree(album_dir)
        except Exception as e:
            logger.error(f"Ошибка удаления директории {album_dir}: {str(e)}")

    def get_photo_file(self, photo: Photo) -> Optional[bytes]:
        try:
            with open(photo.file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Ошибка чтения файла {photo.file_path}: {str(e)}")
            return None


photo_crud = PhotoCRUD()