from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.services.album_cleanup import album_cleanup_service
from app.crud.event import event_crud
import logging

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def cleanup_expired_albums_job():
    """Job для очистки истёкших альбомов"""
    db = SessionLocal()
    try:
        count = album_cleanup_service.process_expired_albums(db)
        logger.info(f"Очищено истёкших альбомов: {count}")
    finally:
        db.close()


def send_deletion_warnings_job():
    """Job для отправки предупреждений об удалении альбомов"""
    db = SessionLocal()
    try:
        count = album_cleanup_service.send_deletion_warnings(db)
        logger.info(f"Отправлено предупреждений: {count}")
    finally:
        db.close()


def cleanup_expired_event_chats_job():
    """Job для удаления чатов событий через 7 дней после окончания"""
    db = SessionLocal()
    try:
        expired_events = event_crud.get_expired_events_with_chats(db, days_after_end=7)
        deleted_count = 0

        for event in expired_events:
            try:
                if event.chat:
                    # Удаляем чат (каскадно удалятся сообщения и участники)
                    db.delete(event.chat)
                    deleted_count += 1
                    logger.info(f"Удален чат события {event.id} (событие закончилось {event.end_datetime})")
            except Exception as e:
                logger.error(f"Ошибка удаления чата события {event.id}: {e}")

        db.commit()
        logger.info(f"Удалено чатов событий: {deleted_count}")
    except Exception as e:
        logger.error(f"Ошибка очистки чатов событий: {e}")
    finally:
        db.close()


def start_scheduler():
    """Запустить планировщик задач"""
    # Очистка истёкших альбомов каждый час
    scheduler.add_job(
        cleanup_expired_albums_job,
        trigger=CronTrigger(minute=0),
        id="cleanup_expired_albums",
        name="Очистка истёкших альбомов",
        replace_existing=True
    )

    # Проверка уведомлений альбомов каждые 30 минут
    scheduler.add_job(
        send_deletion_warnings_job,
        trigger=CronTrigger(minute="0,30"),
        id="send_deletion_warnings",
        name="Отправка предупреждений об удалении",
        replace_existing=True
    )

    # Очистка чатов событий раз в день в 3 ночи
    scheduler.add_job(
        cleanup_expired_event_chats_job,
        trigger=CronTrigger(hour=3, minute=0),
        id="cleanup_event_chats",
        name="Удаление чатов завершенных событий",
        replace_existing=True
    )

    scheduler.start()
    logger.info("Планировщик задач запущен")


def shutdown_scheduler():
    """Остановить планировщик"""
    scheduler.shutdown()
    logger.info("Планировщик задач остановлен")