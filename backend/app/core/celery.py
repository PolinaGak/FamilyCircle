from celery import Celery
from celery.schedules import crontab
from backend.app.core.config import settings

celery_app = Celery(
    "family_circle",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["backend.app.tasks.scheduled_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Moscow",
    enable_utc=True,
    beat_schedule={
        'cleanup-expired-albums': {
            'task': 'backend.app.tasks.scheduled_tasks.cleanup_expired_albums',
            'schedule': 3600.0,
        },
        'send-album-warnings': {
            'task': 'backend.app.tasks.scheduled_tasks.send_album_warnings',
            'schedule': 1800.0,
        },
        'cleanup-event-chats': {
            'task': 'backend.app.tasks.scheduled_tasks.cleanup_expired_event_chats',
            'schedule': crontab(hour=3, minute=0),
        },
        'send-event-reminders': {
            'task': 'backend.app.tasks.scheduled_tasks.send_event_reminders',
            'schedule': 900.0,
        },
    }
)