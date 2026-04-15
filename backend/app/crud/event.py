from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from datetime import datetime, timezone, timedelta

from backend.app.models.event import Event
from backend.app.models.event_participant import EventParticipant
from backend.app.models.chat import Chat
from backend.app.models.chat_member import ChatMember
from backend.app.models.enums import InvitationStatus
from backend.app.schemas.event import EventCreate, EventUpdate
import logging

logger = logging.getLogger(__name__)


class EventCRUD:
    """CRUD операции для событий"""

    @staticmethod
    def create_event(db: Session, event_data: EventCreate, created_by_user_id: int) -> Event:
        """Создать событие. Если create_chat=True, создаётся чат."""
        try:
            event = Event(
                title=event_data.title.strip(),
                description=event_data.description.strip() if event_data.description else None,
                family_id=event_data.family_id,
                created_by_user_id=created_by_user_id,
                start_datetime=event_data.start_datetime,
                end_datetime=event_data.end_datetime,
                is_active=True
            )

            db.add(event)
            db.flush()

            if event_data.create_chat:
                chat = Chat(
                    title=event_data.title.strip(),
                    family_id=event_data.family_id,
                    is_event=True,
                    event_id=event.id,
                    created_by_user_id=created_by_user_id
                )
                db.add(chat)
                db.flush()

                chat_member = ChatMember(
                    chat_id=chat.id,
                    user_id=created_by_user_id,
                    is_admin=True,
                    status=InvitationStatus.accepted
                )
                db.add(chat_member)

            db.commit()
            db.refresh(event)
            logger.info(f"Событие '{event.title}' создано пользователем {created_by_user_id}")
            return event

        except Exception as e:
            logger.error(f"Ошибка при создании события: {str(e)}")
            db.rollback()
            raise

    @staticmethod
    def get_event_by_id(db: Session, event_id: int) -> Optional[Event]:
        """Получить событие по ID"""
        return db.query(Event).filter(Event.id == event_id, Event.is_active == True).first()

    @staticmethod
    def get_event_with_participants(db: Session, event_id: int) -> Optional[Event]:
        """Получить событие с участниками"""
        return db.query(Event).options(
            joinedload(Event.participants).joinedload(EventParticipant.user),
            joinedload(Event.chat)
        ).filter(Event.id == event_id, Event.is_active == True).first()

    @staticmethod
    def get_family_events(db: Session, family_id: int, include_inactive: bool = False) -> List[Event]:
        """Получить все события семьи"""
        query = db.query(Event).filter(Event.family_id == family_id)
        if not include_inactive:
            query = query.filter(Event.is_active == True)
        return query.order_by(Event.start_datetime.desc()).all()

    @staticmethod
    def get_user_calendar_events(db: Session, user_id: int, family_id: Optional[int] = None) -> List[Event]:
        """Получить события для календаря пользователя (только accepted)"""
        query = db.query(Event).join(
            EventParticipant, Event.id == EventParticipant.event_id
        ).filter(
            EventParticipant.user_id == user_id,
            EventParticipant.status == InvitationStatus.accepted,
            Event.is_active == True
        )

        if family_id:
            query = query.filter(Event.family_id == family_id)

        return query.order_by(Event.start_datetime).all()

    @staticmethod
    def update_event(db: Session, event_id: int, update_data: EventUpdate) -> Optional[Event]:
        """Обновить событие"""
        event = EventCRUD.get_event_by_id(db, event_id)
        if not event:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            if value is not None:
                if key in ['title', 'description'] and isinstance(value, str):
                    value = value.strip()
                setattr(event, key, value)

        db.commit()
        db.refresh(event)
        logger.info(f"Событие {event_id} обновлено")
        return event

    @staticmethod
    def delete_event(db: Session, event_id: int, permanent: bool = False) -> bool:
        """Удалить событие (мягкое или жёсткое)"""
        try:
            event = EventCRUD.get_event_by_id(db, event_id)
            if not event:
                return False

            if permanent:
                db.delete(event)
            else:
                event.is_active = False

            db.commit()
            logger.info(f"Событие {event_id} удалено (permanent={permanent})")
            return True

        except Exception as e:
            logger.error(f"Ошибка при удалении события {event_id}: {str(e)}")
            db.rollback()
            return False

    @staticmethod
    def is_event_admin(db: Session, user_id: int, event_id: int) -> bool:
        """Проверить, является ли пользователь создателем события"""
        event = EventCRUD.get_event_by_id(db, event_id)
        return event is not None and event.created_by_user_id == user_id

    @staticmethod
    def invite_participant(db: Session, event_id: int, user_id: int) -> EventParticipant:
        """Пригласить участника на событие"""
        existing = db.query(EventParticipant).filter(
            EventParticipant.event_id == event_id,
            EventParticipant.user_id == user_id
        ).first()

        if existing:
            raise ValueError("Пользователь уже приглашен на это событие")

        participant = EventParticipant(
            event_id=event_id,
            user_id=user_id,
            status=InvitationStatus.invited,
            invited_at=datetime.now(timezone.utc)
        )

        db.add(participant)
        db.commit()
        db.refresh(participant)

        logger.info(f"Пользователь {user_id} приглашен на событие {event_id}")
        return participant

    @staticmethod
    def respond_to_invitation(db: Session, event_id: int, user_id: int, accept: bool) -> EventParticipant:
        """Ответить на приглашение (принять/отклонить)"""
        participant = db.query(EventParticipant).filter(
            EventParticipant.event_id == event_id,
            EventParticipant.user_id == user_id
        ).first()

        if not participant:
            raise ValueError("Приглашение не найдено")

        if participant.status != InvitationStatus.invited:
            raise ValueError("Вы уже ответили на это приглашение")

        participant.status = InvitationStatus.accepted if accept else InvitationStatus.declined
        participant.responded_at = datetime.now(timezone.utc)

        if accept:
            event = EventCRUD.get_event_by_id(db, event_id)
            if event and event.chat:
                existing_member = db.query(ChatMember).filter(
                    ChatMember.chat_id == event.chat.id,
                    ChatMember.user_id == user_id
                ).first()

                if not existing_member:
                    chat_member = ChatMember(
                        chat_id=event.chat.id,
                        user_id=user_id,
                        is_admin=False,
                        status=InvitationStatus.accepted
                    )
                    db.add(chat_member)
                    logger.info(f"Пользователь {user_id} добавлен в чат события {event_id}")

        db.commit()
        db.refresh(participant)
        return participant

    @staticmethod
    def get_pending_invitations(db: Session, user_id: int) -> List[EventParticipant]:
        """Получить ожидающие приглашения для пользователя"""
        return db.query(EventParticipant).options(
            joinedload(EventParticipant.event)
        ).filter(
            EventParticipant.user_id == user_id,
            EventParticipant.status == InvitationStatus.invited
        ).all()

    @staticmethod
    def get_event_participants(db: Session, event_id: int, status: Optional[InvitationStatus] = None) -> List[
        EventParticipant]:
        """Получить участников события"""
        query = db.query(EventParticipant).filter(EventParticipant.event_id == event_id)
        if status:
            query = query.filter(EventParticipant.status == status)
        return query.all()

    @staticmethod
    def remove_participant(db: Session, event_id: int, user_id: int) -> bool:
        """Удалить участника из события"""
        try:
            participant = db.query(EventParticipant).filter(
                EventParticipant.event_id == event_id,
                EventParticipant.user_id == user_id
            ).first()

            if not participant:
                return False

            event = EventCRUD.get_event_by_id(db, event_id)
            if event and event.chat:
                db.query(ChatMember).filter(
                    ChatMember.chat_id == event.chat.id,
                    ChatMember.user_id == user_id
                ).delete()

            db.delete(participant)
            db.commit()
            logger.info(f"Пользователь {user_id} удален из события {event_id}")
            return True

        except Exception as e:
            logger.error(f"Ошибка при удалении участника: {str(e)}")
            db.rollback()
            return False

    @staticmethod
    def create_event_chat(db: Session, event_id: int, user_id: int) -> Chat:
        """Создать чат для существующего события (если не создан при создании события)"""
        event = EventCRUD.get_event_by_id(db, event_id)
        if not event:
            raise ValueError("Событие не найдено")

        if event.chat:
            raise ValueError("Чат для этого события уже существует")

        if event.created_by_user_id != user_id:
            raise ValueError("Только создатель события может создать чат")

        chat = Chat(
            family_id=event.family_id,
            is_event=True,
            event_id=event.id,
            created_by_user_id=user_id
        )
        db.add(chat)
        db.flush()

        chat_member = ChatMember(
            chat_id=chat.id,
            user_id=user_id,
            is_admin=True,
            status=InvitationStatus.accepted
        )
        db.add(chat_member)

        participants = EventCRUD.get_event_participants(db, event_id, InvitationStatus.accepted)
        for p in participants:
            if p.user_id != user_id:
                member = ChatMember(
                    chat_id=chat.id,
                    user_id=p.user_id,
                    is_admin=False,
                    status=InvitationStatus.accepted
                )
                db.add(member)

        db.commit()
        db.refresh(chat)
        return chat

    @staticmethod
    def get_expired_events_with_chats(db: Session, days_after_end: int = 7) -> List[Event]:
        """Получить события, закончившиеся более чем days_after_end дней назад, с чатами"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_after_end)

        return db.query(Event).join(
            Chat, Event.id == Chat.event_id
        ).filter(
            Event.end_datetime < cutoff_date,
            Event.is_active == True,
            Chat.is_event == True
        ).all()


event_crud = EventCRUD()