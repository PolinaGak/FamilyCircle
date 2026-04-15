from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.dependencies.auth import get_current_active_user
from backend.app.crud import event_crud, family_crud, user_crud
from backend.app.services.event_notifications import event_notification_service
from backend.app.schemas.event import (
    EventCreate, EventUpdate, EventResponse, EventDetailResponse,
    EventListResponse, InviteParticipantRequest, RespondToInvitationRequest,
    CalendarEventResponse
)
from backend.app.models.user import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
        event_data: EventCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Создать новое событие в семье.
    Опционально создаётся чат (по умолчанию True).
    """
    if not family_crud.is_family_member(db, current_user.id, event_data.family_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы не являетесь членом этой семьи"
        )

    if event_data.end_datetime <= event_data.start_datetime:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Дата окончания должна быть позже даты начала"
        )

    try:
        event = event_crud.create_event(db, event_data, current_user.id)

        if event_data.invite_members:
            for user_id in event_data.invite_members:
                if family_crud.is_family_member(db, user_id, event_data.family_id):
                    try:
                        participant = event_crud.invite_participant(db, event.id, user_id)
                        invited_user = user_crud.get_user_by_id(db, user_id)
                        if invited_user:
                            event_notification_service.notify_invitation(
                                db, event, invited_user, current_user
                            )
                    except ValueError as e:
                        logger.warning(f"Не удалось пригласить пользователя {user_id}: {e}")

        event_crud.invite_participant(db, event.id, current_user.id)
        event_crud.respond_to_invitation(db, event.id, current_user.id, accept=True)

        return event

    except Exception as e:
        logger.error(f"Ошибка создания события: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при создании события"
        )


@router.get("/my/calendar", response_model=List[CalendarEventResponse])
async def get_my_calendar(
        family_id: Optional[int] = Query(None, description="Фильтр по семье"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Получить события для календаря текущего пользователя.
    Показываются только принятые (accepted) события.
    """
    events = event_crud.get_user_calendar_events(db, current_user.id, family_id)
    return events


@router.get("/family/{family_id}", response_model=EventListResponse)
async def get_family_events(
        family_id: int,
        include_past: bool = Query(False, description="Включить прошедшие события"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Получить все события семьи (для администрирования).
    """
    if not family_crud.is_family_member(db, current_user.id, family_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этой семье"
        )

    events = event_crud.get_family_events(db, family_id, include_inactive=False)

    if not include_past:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        events = [e for e in events if e.end_datetime > now]

    return EventListResponse(events=events, total=len(events))


@router.get("/{event_id}", response_model=EventDetailResponse)
async def get_event(
        event_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Получить детальную информацию о событии.
    """
    event = event_crud.get_event_with_participants(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Событие не найдено"
        )

    is_family_member = family_crud.is_family_member(db, current_user.id, event.family_id)
    is_participant = any(p.user_id == current_user.id for p in event.participants)

    if not (is_family_member or is_participant):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этому событию"
        )

    response = EventDetailResponse.model_validate(event)
    response.is_admin = event.created_by_user_id == current_user.id
    response.chat_exists = event.chat is not None

    return response


@router.put("/{event_id}", response_model=EventResponse)
async def update_event(
        event_id: int,
        update_data: EventUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Обновить событие (только создатель).
    """
    if not event_crud.is_event_admin(db, current_user.id, event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только создатель может редактировать событие"
        )

    if update_data.start_datetime and update_data.end_datetime:
        if update_data.end_datetime <= update_data.start_datetime:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Дата окончания должна быть позже даты начала"
            )

    event = event_crud.update_event(db, event_id, update_data)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Событие не найдено"
        )

    event_notification_service.notify_event_update(db, event, current_user)

    return event


@router.delete("/{event_id}")
async def delete_event(
        event_id: int,
        permanent: bool = Query(False, description="Полное удаление"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Удалить/отменить событие (только создатель).
    """
    event = event_crud.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Событие не найдено"
        )

    if not event_crud.is_event_admin(db, current_user.id, event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только создатель может удалять событие"
        )

    event_notification_service.notify_event_cancellation(db, event, current_user)

    success = event_crud.delete_event(db, event_id, permanent)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось удалить событие"
        )

    return {"message": "Событие удалено"}


@router.post("/{event_id}/invite", status_code=status.HTTP_201_CREATED)
async def invite_participant(
        event_id: int,
        invite_data: InviteParticipantRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Пригласить участника на событие (только создатель).
    """
    if not event_crud.is_event_admin(db, current_user.id, event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только создатель может приглашать участников"
        )

    event = event_crud.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Событие не найдено"
        )

    if not family_crud.is_family_member(db, invite_data.user_id, event.family_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь не является членом семьи"
        )

    try:
        participant = event_crud.invite_participant(db, event_id, invite_data.user_id)

        invited_user = user_crud.get_user_by_id(db, invite_data.user_id)
        if invited_user:
            event_notification_service.notify_invitation(db, event, invited_user, current_user)

        return {"success": True, "message": "Приглашение отправлено"}

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{event_id}/respond")
async def respond_to_invitation(
        event_id: int,
        response_data: RespondToInvitationRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Ответить на приглашение (принять/отклонить).
    При принятии пользователь добавляется в чат события (если есть).
    """
    try:
        participant = event_crud.respond_to_invitation(
            db, event_id, current_user.id, response_data.accept
        )

        action_text = "принято" if response_data.accept else "отклонено"
        return {
            "success": True,
            "message": f"Приглашение {action_text}",
            "status": participant.status.value
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/my/invitations/pending")
async def get_pending_invitations(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Получить список ожидающих приглашений на события.
    """
    invitations = event_crud.get_pending_invitations(db, current_user.id)

    result = []
    for inv in invitations:
        result.append({
            "event_id": inv.event_id,
            "event_title": inv.event.title if inv.event else None,
            "start_datetime": inv.event.start_datetime if inv.event else None,
            "end_datetime": inv.event.end_datetime if inv.event else None,
            "invited_at": inv.invited_at,
            "family_name": inv.event.family.name if inv.event and inv.event.family else None
        })

    return result


@router.delete("/{event_id}/participants/{user_id}")
async def remove_participant(
        event_id: int,
        user_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Удалить участника из события (только создатель).
    """
    if not event_crud.is_event_admin(db, current_user.id, event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только создатель может удалять участников"
        )

    success = event_crud.remove_participant(db, event_id, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Участник не найден"
        )

    return {"message": "Участник удален"}


@router.post("/{event_id}/create-chat")
async def create_event_chat(
        event_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Создать чат для события (только создатель, если чат не создан автоматически).
    """
    try:
        chat = event_crud.create_event_chat(db, event_id, current_user.id)
        return {
            "success": True,
            "chat_id": chat.id,
            "message": "Чат события создан"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )