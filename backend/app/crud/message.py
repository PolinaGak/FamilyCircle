from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timezone

from app.models.message import Message
from app.models.chat_member import ChatMember
from app.models.enums import InvitationStatus
from app.schemas.message import MessageCreate, MessageUpdate
import logging

logger = logging.getLogger(__name__)


class MessageCRUD:

    @staticmethod
    def create_message(db: Session, chat_id: int, sender_user_id: int, content: str) -> Message:
        member = db.query(ChatMember).filter(
            ChatMember.chat_id == chat_id,
            ChatMember.user_id == sender_user_id,
            ChatMember.status == InvitationStatus.accepted
        ).first()

        if not member:
            raise ValueError("Вы не являетесь участником этого чата")

        message = Message(
            chat_id=chat_id,
            sender_user_id=sender_user_id,
            content=content.strip()
        )

        db.add(message)
        db.commit()
        db.refresh(message)
        logger.info(f"Сообщение {message.id} создано в чате {chat_id}")
        return message

    @staticmethod
    def get_message_by_id(db: Session, message_id: int) -> Optional[Message]:
        return db.query(Message).filter(Message.id == message_id).first()

    @staticmethod
    def get_chat_messages(
            db: Session,
            chat_id: int,
            limit: int = 50,
            offset: int = 0
    ) -> tuple[List[Message], int]:
        query = db.query(Message).filter(Message.chat_id == chat_id)
        total = query.count()

        messages = query.options(
            joinedload(Message.sender)
        ).order_by(Message.sent_at.desc()).offset(offset).limit(limit).all()

        return messages, total

    @staticmethod
    def update_message(db: Session, message_id: int, user_id: int, new_content: str) -> Optional[Message]:
        message = MessageCRUD.get_message_by_id(db, message_id)
        if not message:
            return None

        if message.sender_user_id != user_id:
            raise ValueError("Вы можете редактировать только свои сообщения")

        message.content = new_content.strip()
        message.is_edited = True
        message.edited_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(message)
        logger.info(f"Сообщение {message_id} отредактировано")
        return message

    @staticmethod
    def delete_message(db: Session, message_id: int, user_id: int, is_admin: bool = False) -> bool:
        message = MessageCRUD.get_message_by_id(db, message_id)
        if not message:
            return False

        if message.sender_user_id != user_id and not is_admin:
            raise ValueError("Нет прав на удаление сообщения")

        db.delete(message)
        db.commit()
        logger.info(f"Сообщение {message_id} удалено")
        return True


message_crud = MessageCRUD()