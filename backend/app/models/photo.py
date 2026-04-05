from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class Photo(Base):
    __tablename__ = "photo"

    id = Column(Integer, primary_key=True, index=True)
    album_id = Column(Integer, ForeignKey("album.id"), nullable=False)
    uploaded_by_user_id = Column(Integer, ForeignKey("user.id"), nullable=False)

    file_path = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String, nullable=False)
    file_hash = Column(String(64), nullable=False)

    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    description = Column(String(500), nullable=True)

    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_photo_album_id', 'album_id'),
        Index('ix_photo_uploaded_by', 'uploaded_by_user_id'),
        Index('ix_photo_file_hash', 'file_hash'),
    )

    album = relationship("Album", back_populates="photos")
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_user_id])

    ALLOWED_MIME_TYPES = {
        'image/jpeg': ['.jpg', '.jpeg'],
        'image/png': ['.png'],
        'image/webp': ['.webp']
    }

    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB

    @classmethod
    def is_valid_mime_type(cls, mime_type: str) -> bool:
        return mime_type.lower() in cls.ALLOWED_MIME_TYPES

    @classmethod
    def is_valid_size(cls, size_bytes: int) -> bool:
        return 0 < size_bytes <= cls.MAX_FILE_SIZE

    @property
    def file_extension(self) -> str:
        """Получить расширение файла по MIME типу"""
        return self.ALLOWED_MIME_TYPES.get(self.mime_type, ['.jpg'])[0]