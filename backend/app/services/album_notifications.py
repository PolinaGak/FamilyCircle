from typing import List
import logging

from backend.app.models.album import Album
from backend.app.models.photo import Photo
from backend.app.models.user import User
from backend.app.core.email_utils import email_service

logger = logging.getLogger(__name__)


class AlbumNotificationService:
    """Сервис уведомлений о событиях в альбомах"""

    @staticmethod
    def notify_new_album(album: Album, creator: User):
        """Уведомить участников семьи о создании нового альбома"""
        try:
            from backend.app.crud.family import family_crud

            family_members = family_crud.get_family_members(album.family_id)
            recipient_emails = []

            for member in family_members:
                if member.user and member.user.email and member.user.id != creator.id:
                    recipient_emails.append(member.user.email)

            if not recipient_emails:
                return

            subject = f"📸 Новый альбом в Family Circle: {album.title}"

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .album-info {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h2>📸 Новый альбом</h2>

                    <p><strong>{creator.name}</strong> создал новый альбом 
                    в семейном круге:</p>

                    <div class="album-info">
                        <h3>{album.title}</h3>
                        <p>{album.description or ''}</p>
                        <p><small>Альбом будет доступен 7 дней</small></p>
                    </div>

                    <p>С уважением,<br>Команда Family Circle</p>
                </div>
            </body>
            </html>
            """

            for email in recipient_emails:
                email_service.send_email(email, subject, html_content)

            logger.info(f"Уведомление о новом альбоме {album.id} отправлено")

        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о новом альбоме: {str(e)}")

    @staticmethod
    def notify_new_photos(album: Album, photos: List[Photo], uploader: User):
        """Уведомить участников альбома о новых фото"""
        try:
            recipient_emails = []
            for member in album.members:
                if member.user and member.user.email and member.user.id != uploader.id:
                    recipient_emails.append(member.user.email)

            if not recipient_emails or not photos:
                return

            photo_count = len(photos)
            subject = f"📷 {uploader.name} добавил {photo_count} фото в альбом '{album.title}'"

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h2>📷 Новые фотографии</h2>

                    <p><strong>{uploader.name}</strong> добавил {photo_count} 
                    новых фотографий в альбом "{album.title}":</p>

                    <p>С уважением,<br>Команда Family Circle</p>
                </div>
            </body>
            </html>
            """

            for email in recipient_emails:
                email_service.send_email(email, subject, html_content)

            logger.info(f"Уведомление о новых фото отправлено для альбома {album.id}")

        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о новых фото: {str(e)}")


album_notification_service = AlbumNotificationService()