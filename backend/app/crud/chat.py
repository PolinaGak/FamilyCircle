from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from datetime import datetime, timezone

from backend.app.models.chat import Chat
from backend.app.models.chat_member import ChatMember
from backend.app.models.message import Message
from backend.app.models.enums import InvitationStatus
from backend.app.schemas.chat import ChatCreate, ChatUpdate
import logging

logger = logging.getLogger(__name__)


class ChatCRUD:

    @staticmethod
    def create_chat(db: Session, chat_data: ChatCreate, created_by_user_id: int) -> Chat:
        try:
            chat = Chat(
                family_id=chat_data.family_id,
                is_event=chat_data.is_event,
                event_id=chat_data.event_id,
                created_by_user_id=created_by_user_id,
                title=chat_data.title.strip() if chat_data.title else None
            )

            db.add(chat)
            db.flush()

            admin_member = ChatMember(
                chat_id=chat.id,
                user_id=created_by_user_id,
                is_admin=True,
                status=InvitationStatus.accepted,
                added_by_user_id=created_by_user_id
            )
            db.add(admin_member)

            db.commit()
            db.refresh(chat)
            logger.info(f"Чат {chat.id} создан пользователем {created_by_user_id}")
            return chat

        except Exception as e:
            logger.error(f"Ошибка при создании чата: {str(e)}")
            db.rollback()
            raise

    @staticmethod
    def get_chat_by_id(db: Session, chat_id: int) -> Optional[Chat]:
        return db.query(Chat).filter(Chat.id == chat_id).first()

    @staticmethod
    def get_chat_with_members(db: Session, chat_id: int) -> Optional[Chat]:
        return db.query(Chat).options(
            joinedload(Chat.members).joinedload(ChatMember.user),
            joinedload(Chat.created_by)
        ).filter(Chat.id == chat_id).first()

    @staticmethod
    def get_user_chats(db: Session, user_id: int, family_id: Optional[int] = None) -> List[Chat]:
        query = db.query(Chat).join(
            ChatMember, Chat.id == ChatMember.chat_id
        ).filter(
            ChatMember.user_id == user_id,
            ChatMember.status == InvitationStatus.accepted
        )

        if family_id:
            query = query.filter(Chat.family_id == family_id)

        return query.order_by(Chat.created_at.desc()).all()

    @staticmethod
    def update_chat(db: Session, chat_id: int, update_data: ChatUpdate) -> Optional[Chat]:
        chat = ChatCRUD.get_chat_by_id(db, chat_id)
        if not chat:
            return None

        if update_data.title is not None:
            chat.title = update_data.title.strip()

        db.commit()
        db.refresh(chat)
        return chat

    @staticmethod
    def delete_chat(db: Session, chat_id: int) -> bool:
        try:
            chat = ChatCRUD.get_chat_by_id(db, chat_id)
            if not chat:
                return False

            db.delete(chat)
            db.commit()
            logger.info(f"Чат {chat_id} удален")
            return True

        except Exception as e:
            logger.error(f"Ошибка при удалении чата {chat_id}: {str(e)}")
            db.rollback()
            return False

    @staticmethod
    def add_member(db: Session, chat_id: int, user_id: int, added_by_user_id: int) -> ChatMember:
        if not ChatCRUD.is_chat_admin(db, added_by_user_id, chat_id):
            raise ValueError("Только администратор может добавлять участников")

        chat = ChatCRUD.get_chat_by_id(db, chat_id)
        if not chat:
            raise ValueError("Чат не найден")

        from backend.app.crud.family import family_crud
        if not family_crud.is_family_member(db, user_id, chat.family_id):
            raise ValueError("Пользователь не является членом этой семьи")

        existing = db.query(ChatMember).filter(
            ChatMember.chat_id == chat_id,
            ChatMember.user_id == user_id
        ).first()

        if existing:
            raise ValueError("Пользователь уже является участником чата")

        member = ChatMember(
            chat_id=chat_id,
            user_id=user_id,
            is_admin=False,
            status=InvitationStatus.accepted,
            added_by_user_id=added_by_user_id
        )

        db.add(member)
        db.commit()
        db.refresh(member)
        logger.info(f"Пользователь {user_id} добавлен в чат {chat_id}")
        return member

    @staticmethod
    def remove_member(db: Session, chat_id: int, user_id: int) -> bool:
        try:
            member = db.query(ChatMember).filter(
                ChatMember.chat_id == chat_id,
                ChatMember.user_id == user_id
            ).first()

            if not member:
                return False

            db.delete(member)
            db.commit()
            logger.info(f"Пользователь {user_id} удален из чата {chat_id}")
            return True

        except Exception as e:
            logger.error(f"Ошибка при удалении участника: {str(e)}")
            db.rollback()
            return False

    @staticmethod
    def add_admin(db: Session, chat_id: int, user_id: int, added_by_user_id: int) -> ChatMember:
        if not ChatCRUD.is_chat_admin(db, added_by_user_id, chat_id):
            raise ValueError("Только администратор может назначать администраторов")

        chat = ChatCRUD.get_chat_by_id(db, chat_id)
        if not chat:
            raise ValueError("Чат не найден")

        from backend.app.crud.family import family_crud
        if not family_crud.is_family_member(db, user_id, chat.family_id):
            raise ValueError("Пользователь не является членом этой семьи")

        existing = db.query(ChatMember).filter(
            ChatMember.chat_id == chat_id,
            ChatMember.user_id == user_id
        ).first()

        if existing:
            if existing.is_admin:
                raise ValueError("Пользователь уже является администратором")
            existing.is_admin = True
            db.commit()
            db.refresh(existing)
            logger.info(f"Пользователь {user_id} повышен до админа в чате {chat_id}")
            return existing
        else:
            member = ChatMember(
                chat_id=chat_id,
                user_id=user_id,
                is_admin=True,
                status=InvitationStatus.accepted,
                added_by_user_id=added_by_user_id
            )
            db.add(member)
            db.commit()
            db.refresh(member)
            logger.info(f"Пользователь {user_id} добавлен как админ в чат {chat_id}")
            return member

    @staticmethod
    def remove_admin(db: Session, chat_id: int, user_id: int, removed_by_user_id: int) -> bool:
        if not ChatCRUD.is_chat_admin(db, removed_by_user_id, chat_id):
            raise ValueError("Только администратор может снимать права")

        if user_id == removed_by_user_id:
            raise ValueError("Используйте 'transfer-admin' для передачи прав")

        member = db.query(ChatMember).filter(
            ChatMember.chat_id == chat_id,
            ChatMember.user_id == user_id,
            ChatMember.is_admin == True
        ).first()

        if not member:
            raise ValueError("Пользователь не является администратором")

        member.is_admin = False
        db.commit()
        logger.info(f"Пользователь {user_id} лишен прав админа в чате {chat_id}")
        return True

    @staticmethod
    def transfer_admin_rights(db: Session, chat_id: int, current_admin_id: int, new_admin_id: int) -> bool:
        current_admin = db.query(ChatMember).filter(
            ChatMember.chat_id == chat_id,
            ChatMember.user_id == current_admin_id,
            ChatMember.is_admin == True
        ).first()

        if not current_admin:
            raise ValueError("Вы не являетесь администратором чата")

        new_admin = db.query(ChatMember).filter(
            ChatMember.chat_id == chat_id,
            ChatMember.user_id == new_admin_id,
            ChatMember.status == InvitationStatus.accepted
        ).first()

        if not new_admin:
            raise ValueError("Новый администратор не найден в чате")

        current_admin.is_admin = False
        new_admin.is_admin = True

        chat = ChatCRUD.get_chat_by_id(db, chat_id)
        chat.created_by_user_id = new_admin_id

        db.commit()
        logger.info(f"Права администратора переданы пользователю {new_admin_id} в чате {chat_id}")
        return True

    @staticmethod
    def leave_chat(db: Session, chat_id: int, user_id: int) -> bool:
        member = db.query(ChatMember).filter(
            ChatMember.chat_id == chat_id,
            ChatMember.user_id == user_id
        ).first()

        if not member:
            raise ValueError("Вы не являетесь участником этого чата")

        if member.is_admin:
            admin_count = db.query(ChatMember).filter(
                ChatMember.chat_id == chat_id,
                ChatMember.is_admin == True
            ).count()

            if admin_count <= 1:
                raise ValueError("Вы единственный администратор. Сначала передайте права другому участнику.")

        db.delete(member)
        db.commit()
        logger.info(f"Пользователь {user_id} покинул чат {chat_id}")
        return True

    @staticmethod
    def is_chat_admin(db: Session, user_id: int, chat_id: int) -> bool:
        chat = ChatCRUD.get_chat_by_id(db, chat_id)
        if not chat:
            return False
        member = db.query(ChatMember).filter(
            ChatMember.chat_id == chat_id,
            ChatMember.user_id == user_id,
            ChatMember.is_admin == True,
            ChatMember.status == InvitationStatus.accepted
        ).first()
        return member is not None

    @staticmethod
    def is_chat_member(db: Session, user_id: int, chat_id: int) -> bool:
        chat = ChatCRUD.get_chat_by_id(db, chat_id)
        if not chat:
            return False
        member = db.query(ChatMember).filter(
            ChatMember.chat_id == chat_id,
            ChatMember.user_id == user_id,
            ChatMember.status == InvitationStatus.accepted
        ).first()
        return member is not None

    @staticmethod
    def get_chat_members(db: Session, chat_id: int) -> List[ChatMember]:
        return db.query(ChatMember).options(
            joinedload(ChatMember.user)
        ).filter(ChatMember.chat_id == chat_id).all()


chat_crud = ChatCRUD()