# app/services/album_cleanup.py
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List
import logging

from backend.app.models.album import Album
from backend.app.crud.album import album_crud
from backend.app.core.email_utils import email_service

logger = logging.getLogger(__name__)


class AlbumCleanupService:
    """Сервис очистки истёкших альбомов и отправки уведомлений"""

    @staticmethod
    def process_expired_albums(db: Session):
        """
        Обработать истёкшие альбомы (удалить).
        Вызывать по cron/job scheduler.
        """
        expired_albums = album_crud.get_expired_albums(db)
        deleted_count = 0

        for album in expired_albums:
            try:
                # Отправляем уведомление о удалении если ещё не отправлено
                if not album.deletion_notified_at:
                    AlbumCleanupService._send_deletion_notification(album)

                # Жёсткое удаление
                album_crud.delete_album(db, album.id, permanent=True)
                deleted_count += 1
                logger.info(f"Истёкший альбом {album.id} удалён")

            except Exception as e:
                logger.error(f"Ошибка удаления альбома {album.id}: {str(e)}")

        return deleted_count

    @staticmethod
    def send_deletion_warnings(db: Session):
        """
        Отправить уведомления об удалении (за 24 часа).
        Вызывать по cron/job scheduler.
        """
        albums_to_notify = album_crud.get_albums_for_deletion_notification(db, hours_before=24)
        notified_count = 0

        for album in albums_to_notify:
            try:
                if AlbumCleanupService._send_deletion_notification(album):
                    album_crud.mark_deletion_notified(db, album.id)
                    notified_count += 1
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления для альбома {album.id}: {str(e)}")

        return notified_count

    @staticmethod
    def _send_deletion_notification(album: Album) -> bool:
        """Отправить email уведомление о скором удалении альбома"""
        try:
            # Собираем email всех участников
            member_emails = []
            for member in album.members:
                if member.user and member.user.email:
                    member_emails.append(member.user.email)

            if not member_emails:
                return False

            subject = f"⏰ Альбом '{album.title}' будет удалён через 24 часа"

            hours_left = int(album.hours_until_deletion)

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .warning {{ background: #fff3cd; border: 1px solid #ffeeba; padding: 15px; 
                               border-radius: 8px; margin: 20px 0; }}
                    .button {{ display: inline-block; padding: 12px 24px; background: #007bff; 
                              color: white; text-decoration: none; border-radius: 6px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h2>⏰ Напоминание об удалении альбома</h2>

                    <div class="warning">
                        <strong>Альбом "{album.title}" будет автоматически удалён 
                        через {hours_left} часов.</strong>
                    </div>

                    <p>Чтобы сохранить фотографии, пожалуйста, скачайте их или 
                    попросите администратора продлить срок хранения альбома.</p>

                    <p>Срок хранения истекает: {album.expires_at.strftime('%d.%m.%Y %H:%M')}</p>

                    <p>С уважением,<br>Команда Family Circle</p>
                </div>
            </body>
            </html>
            """

            # Отправляем всем участникам
            for email in member_emails:
                email_service.send_email(email, subject, html_content)

            logger.info(f"Уведомление об удалении отправлено для альбома {album.id}")
            return True

        except Exception as e:
            logger.error(f"Ошибка отправки уведомления: {str(e)}")
            return False


# Экземпляр для использования
album_cleanup_service = AlbumCleanupService()