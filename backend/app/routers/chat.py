from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.dependencies.auth import get_current_active_user
from backend.app.crud import chat_crud, family_crud, user_crud
from backend.app.schemas.chat import (
    ChatCreate, ChatUpdate, ChatResponse, ChatDetailResponse,
    ChatListResponse, ChatMemberAdd, ChatMemberResponse, TransferAdminRequest
)
from backend.app.schemas.message import MessageCreate, MessageResponse, MessageListResponse, MessageUpdate
from backend.app.models.user import User
from backend.app.crud.message import message_crud
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chats", tags=["chats"])


@router.post("", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(
        chat_data: ChatCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    if not family_crud.is_family_member(db, current_user.id, chat_data.family_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы не являетесь членом этой семьи"
        )

    if chat_data.event_id:
        from backend.app.crud.event import event_crud
        if not event_crud.is_event_admin(db, current_user.id, chat_data.event_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Только создатель события может создать чат"
            )

    try:
        chat = chat_crud.create_chat(db, chat_data, current_user.id)
        response = ChatResponse.model_validate(chat)
        response.is_admin = True
        return response
    except Exception as e:
        logger.error(f"Ошибка создания чата: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при создании чата"
        )


@router.get("", response_model=ChatListResponse)
async def list_chats(
        family_id: Optional[int] = Query(None, description="Фильтр по семье"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    chats = chat_crud.get_user_chats(db, current_user.id, family_id)

    result = []
    for chat in chats:
        chat.members_count = len(chat.members) if hasattr(chat, 'members') else 0
        chat.is_admin = chat_crud.is_chat_admin(db, current_user.id, chat.id)
        result.append(chat)

    return ChatListResponse(chats=result, total=len(result))


@router.get("/{chat_id}", response_model=ChatDetailResponse)
async def get_chat(
        chat_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    chat = chat_crud.get_chat_by_id(db, chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Чат не найден"
        )

    if not chat_crud.is_chat_member(db, current_user.id, chat_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этому чату"
        )

    chat = chat_crud.get_chat_with_members(db, chat_id)
    is_admin = chat_crud.is_chat_admin(db, current_user.id, chat_id)
    response_data = ChatDetailResponse.model_validate(chat)
    response_data.is_admin = is_admin
    response_data.members_count = len(chat.members)
    return response_data


@router.put("/{chat_id}", response_model=ChatResponse)
async def update_chat(
        chat_id: int,
        update_data: ChatUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    if not chat_crud.is_chat_admin(db, current_user.id, chat_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администратор может редактировать чат"
        )

    chat = chat_crud.update_chat(db, chat_id, update_data)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Чат не найден"
        )

    return chat


@router.delete("/{chat_id}")
async def delete_chat(
        chat_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    if not chat_crud.is_chat_admin(db, current_user.id, chat_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администратор может удалять чат"
        )

    success = chat_crud.delete_chat(db, chat_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Чат не найден"
        )

    return {"message": "Чат удален"}


@router.post("/{chat_id}/leave")
async def leave_chat(
        chat_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    try:
        chat_crud.leave_chat(db, chat_id, current_user.id)
        return {"message": "Вы покинули чат"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{chat_id}/admins", response_model=ChatMemberResponse)
async def add_admin(
        chat_id: int,
        user_id: int = Body(..., embed=True),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    try:
        member = chat_crud.add_admin(db, chat_id, user_id, current_user.id)
        user = user_crud.get_user_by_id(db, user_id)

        response = ChatMemberResponse.model_validate(member)
        if user:
            response.user_name = user.name
        return response

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{chat_id}/admins/{user_id}")
async def remove_admin(
        chat_id: int,
        user_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    try:
        chat_crud.remove_admin(db, chat_id, user_id, current_user.id)
        return {"message": "Права администратора сняты"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{chat_id}/members", response_model=ChatMemberResponse)
async def add_member(
        chat_id: int,
        member_data: ChatMemberAdd,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    try:
        member = chat_crud.add_member(db, chat_id, member_data.user_id, current_user.id)
        user = user_crud.get_user_by_id(db, member_data.user_id)

        response = ChatMemberResponse.model_validate(member)
        if user:
            response.user_name = user.name
        return response

    except ValueError as e:
        if "не является членом" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{chat_id}/members/{user_id}")
async def remove_member(
        chat_id: int,
        user_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    if not chat_crud.is_chat_admin(db, current_user.id, chat_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администратор может удалять участников"
        )

    success = chat_crud.remove_member(db, chat_id, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Участник не найден"
        )

    return {"message": "Участник удален из чата"}


@router.post("/{chat_id}/transfer-admin")
async def transfer_admin(
        chat_id: int,
        transfer_data: TransferAdminRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    try:
        chat_crud.transfer_admin_rights(
            db, chat_id, current_user.id, transfer_data.new_admin_user_id
        )
        return {"message": "Права администратора переданы"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{chat_id}/members", response_model=List[ChatMemberResponse])
async def list_members(
        chat_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    if not chat_crud.is_chat_member(db, current_user.id, chat_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этому чату"
        )

    members = chat_crud.get_chat_members(db, chat_id)
    result = []
    for member in members:
        response = ChatMemberResponse.model_validate(member)
        if member.user:
            response.user_name = member.user.name
        result.append(response)

    return result


@router.post("/{chat_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
        chat_id: int,
        message_data: MessageCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    if not chat_crud.is_chat_member(db, current_user.id, chat_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этому чату"
        )

    try:
        message = message_crud.create_message(
            db, chat_id, current_user.id, message_data.content
        )

        response = MessageResponse.model_validate(message)
        response.sender_name = current_user.name
        return response

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{chat_id}/messages", response_model=MessageListResponse)
async def get_messages(
        chat_id: int,
        limit: int = Query(50, ge=1, le=100),
        offset: int = Query(0, ge=0),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    if not chat_crud.is_chat_member(db, current_user.id, chat_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этому чату"
        )

    messages, total = message_crud.get_chat_messages(db, chat_id, limit, offset)

    result = []
    for msg in messages:
        response = MessageResponse.model_validate(msg)
        if msg.sender:
            response.sender_name = msg.sender.name
        result.append(response)

    return MessageListResponse(messages=result, total=total, chat_id=chat_id)


@router.put("/{chat_id}/messages/{message_id}", response_model=MessageResponse)
async def update_message(
        chat_id: int,
        message_id: int,
        update_data: MessageUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    if not chat_crud.is_chat_member(db, current_user.id, chat_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этому чату"
        )

    try:
        message = message_crud.update_message(db, message_id, current_user.id, update_data.content)
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Сообщение не найдено"
            )

        response = MessageResponse.model_validate(message)
        response.sender_name = current_user.name
        return response

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.delete("/{chat_id}/messages/{message_id}")
async def delete_message(
        chat_id: int,
        message_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    if not chat_crud.is_chat_member(db, current_user.id, chat_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этому чату"
        )

    is_admin = chat_crud.is_chat_admin(db, current_user.id, chat_id)

    try:
        success = message_crud.delete_message(db, message_id, current_user.id, is_admin)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Сообщение не найдено"
            )
        return {"message": "Сообщение удалено"}

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )