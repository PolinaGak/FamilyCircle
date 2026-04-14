from celery import shared_task
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import logging

from app.database import SessionLocal
from app.services.album_cleanup import album_cleanup_service
from app.crud.event import event_crud
from app.services.event_notifications import event_notification_service
from app.models.event import Event
from app.models.event_participant import EventParticipant
from app.models.enums import InvitationStatus

logger = logging.getLogger(__name__)


@shared_task
def cleanup_expired_albums():
    """Очистка истёкших альбомов"""
    db = SessionLocal()
    try:
        count = album_cleanup_service.process_expired_albums(db)
        logger.info(f"Очищено истёкших альбомов: {count}")
        return f"Cleaned {count} albums"
    finally:
        db.close()


@shared_task
def send_album_warnings():
    """Отправка предупреждений об удалении альбомов"""
    db = SessionLocal()
    try:
        count = album_cleanup_service.send_deletion_warnings(db)
        logger.info(f"Отправлено предупреждений: {count}")
        return f"Sent {count} warnings"
    finally:
        db.close()


@shared_task
def cleanup_expired_event_chats():
    """Удаление чатов завершённых событий"""
    db = SessionLocal()
    try:
        expired_events = event_crud.get_expired_events_with_chats(db, days_after_end=7)
        deleted_count = 0

        for event in expired_events:
            try:
                if event.chat:
                    db.delete(event.chat)
                    deleted_count += 1
                    logger.info(f"Удален чат события {event.id}")
            except Exception as e:
                logger.error(f"Ошибка удаления чата {event.id}: {e}")

        db.commit()
        return f"Deleted {deleted_count} chats"
    except Exception as e:
        logger.error(f"Ошибка очистки чатов: {e}")
        db.rollback()
        return f"Error: {str(e)}"
    finally:
        db.close()


@shared_task
def send_event_reminders():
    """
    Отправка напоминаний о событиях, которые начнутся через 24 часа.
    Проверяем каждые 15 минут окно +/- 15 минут от целевого времени.
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        target_time = now + timedelta(hours=24)
        window = timedelta(minutes=15)

        # Ищем события, которые начнутся примерно через 24 часа
        # и ещё не было напоминания (или проверяем флаг)
        events = db.query(Event).filter(
            Event.start_datetime >= target_time - window,
            Event.start_datetime <= target_time + window,
            Event.is_active == True
        ).all()

        sent_count = 0
        for event in events:
            # Получаем подтверждённых участников
            participants = event_crud.get_event_participants(
                db, event.id, status=InvitationStatus.accepted
            )

            for participant in participants:
                if participant.user and participant.user.email:
                    try:
                        event_notification_service.send_event_reminder(
                            db, event, participant.user
                        )
                        sent_count += 1
                    except Exception as e:
                        logger.error(f"Failed to send reminder to {participant.user_id}: {e}")

        logger.info(f"Отправлено напоминаний о событиях: {sent_count}")
        return f"Sent {sent_count} reminders"

    except Exception as e:
        logger.error(f"Error in event reminders: {e}")
        return f"Error: {str(e)}"
    finally:
        db.close()