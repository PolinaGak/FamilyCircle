from sqlalchemy.orm import Session
from typing import List
import logging

from app.models.event import Event
from app.models.event_participant import EventParticipant
from app.models.user import User
from app.core.email_utils import email_service
from app.core.config import settings

logger = logging.getLogger(__name__)


class EventNotificationService:
    """Сервис уведомлений о событиях"""

    @staticmethod
    def notify_invitation(db: Session, event: Event, invited_user: User, invited_by: User):
        """Отправить приглашение на событие"""
        try:
            subject = f"📅 Приглашение на событие: {event.title}"

            accept_url = f"{settings.FRONTEND_URL}/events/{event.id}/respond?action=accept"
            decline_url = f"{settings.FRONTEND_URL}/events/{event.id}/respond?action=decline"

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                           line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f5f5f5; }}
                    .container {{ max-width: 600px; margin: 0 auto; background-color: white; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; 
                              padding: 40px 20px; text-align: center; }}
                    .content {{ padding: 40px 30px; }}
                    .event-details {{ background-color: #f8f9fa; border-left: 4px solid #667eea; 
                                    padding: 20px; margin: 20px 0; }}
                    .button-group {{ text-align: center; margin: 30px 0; }}
                    .button {{ display: inline-block; padding: 12px 30px; margin: 0 10px; text-decoration: none; 
                             border-radius: 6px; font-weight: 600; }}
                    .accept {{ background-color: #28a745; color: white; }}
                    .decline {{ background-color: #dc3545; color: white; }}
                    .footer {{ text-align: center; margin-top: 40px; padding-top: 20px;
                              border-top: 1px solid #eaeaea; font-size: 12px; color: #666; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1 style="margin: 0;">📅 Приглашение на событие</h1>
                    </div>
                    <div class="content">
                        <p>Здравствуйте, <strong>{invited_user.name}</strong>!</p>

                        <p><strong>{invited_by.name}</strong> приглашает вас на событие в Family Circle:</p>

                        <div class="event-details">
                            <h3 style="margin-top: 0;">{event.title}</h3>
                            <p><strong>📅 Дата начала:</strong> {event.start_datetime.strftime('%d.%m.%Y %H:%M')}</p>
                            <p><strong>📅 Дата окончания:</strong> {event.end_datetime.strftime('%d.%m.%Y %H:%M')}</p>
                            {'<p><strong>📝 Описание:</strong> ' + event.description + '</p>' if event.description else ''}
                        </div>

                        <p>Пожалуйста, подтвердите ваше участие:</p>

                        <div class="button-group">
                            <a href="{accept_url}" class="button accept">✅ Принять</a>
                            <a href="{decline_url}" class="button decline">❌ Отклонить</a>
                        </div>

                        <p style="color: #666; font-size: 14px;">
                            Если вы не хотите получать такие уведомления, вы можете отключить их в настройках профиля.
                        </p>
                    </div>
                    <div class="footer">
                        <p>© 2026 Family Circle. Все права защищены.</p>
                    </div>
                </div>
            </body>
            </html>
            """

            text_content = f"""
            Здравствуйте, {invited_user.name}!

            {invited_by.name} приглашает вас на событие: {event.title}

            Дата: {event.start_datetime.strftime('%d.%m.%Y %H:%M')} - {event.end_datetime.strftime('%d.%m.%Y %H:%M')}

            Для ответа перейдите по ссылке:
            Принять: {accept_url}
            Отклонить: {decline_url}
            """

            success = email_service.send_email(
                invited_user.email,
                subject,
                html_content,
                text_content
            )

            if success:
                logger.info(f"Приглашение на событие {event.id} отправлено пользователю {invited_user.id}")
            return success

        except Exception as e:
            logger.error(f"Ошибка отправки приглашения: {str(e)}")
            return False

    @staticmethod
    def notify_event_update(db: Session, event: Event, updated_by: User):
        """Уведомить участников об изменении события"""
        try:
            from app.crud.event import event_crud

            participants = event_crud.get_event_participants(db, event.id)
            recipient_emails = []

            for p in participants:
                if p.user and p.user.email and p.user_id != updated_by.id:
                    recipient_emails.append(p.user.email)

            if not recipient_emails:
                return

            subject = f"📝 Обновление события: {event.title}"

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto;">
                    <h2>📝 Событие обновлено</h2>
                    <p><strong>{updated_by.name}</strong> внес изменения в событие:</p>
                    <h3>{event.title}</h3>
                    <p><strong>Новое время:</strong> {event.start_datetime.strftime('%d.%m.%Y %H:%M')} - 
                       {event.end_datetime.strftime('%d.%m.%Y %H:%M')}</p>
                    <p>С уважением,<br>Family Circle</p>
                </div>
            </body>
            </html>
            """

            for email in recipient_emails:
                email_service.send_email(email, subject, html_content)

            logger.info(f"Уведомление об обновлении события {event.id} отправлено")

        except Exception as e:
            logger.error(f"Ошибка отправки уведомления об обновлении: {str(e)}")

    @staticmethod
    def notify_event_cancellation(db: Session, event: Event, cancelled_by: User):
        """Уведомить участников об отмене события"""
        try:
            from app.crud.event import event_crud

            participants = event_crud.get_event_participants(db, event.id)
            recipient_emails = []

            for p in participants:
                if p.user and p.user.email and p.user_id != cancelled_by.id:
                    recipient_emails.append(p.user.email)

            if not recipient_emails:
                return

            subject = f"❌ Событие отменено: {event.title}"

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #dc3545;">❌ Событие отменено</h2>
                    <p><strong>{cancelled_by.name}</strong> отменил событие:</p>
                    <h3>{event.title}</h3>
                    <p><strong>Было запланировано на:</strong> {event.start_datetime.strftime('%d.%m.%Y %H:%M')}</p>
                    <p>С уважением,<br>Family Circle</p>
                </div>
            </body>
            </html>
            """

            for email in recipient_emails:
                email_service.send_email(email, subject, html_content)

            logger.info(f"Уведомление об отмене события {event.id} отправлено")

        except Exception as e:
            logger.error(f"Ошибка отправки уведомления об отмене: {str(e)}")


event_notification_service = EventNotificationService()