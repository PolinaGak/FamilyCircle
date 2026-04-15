from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
import magic

from backend.app.database import get_db
from backend.app.dependencies.auth import get_current_active_user
from backend.app.crud import album_crud, photo_crud
from backend.app.schemas.album import (
    AlbumCreate, AlbumUpdate, AlbumResponse, AlbumDetailResponse,
    AlbumListResponse
)
from backend.app.schemas.album_member import (
    AlbumMemberAdd, AlbumAdminAdd,
    AlbumMemberResponse, AlbumAdminResponse
)
from backend.app.schemas.photo import PhotoResponse, PhotoUploadResponse, PhotoListResponse
from backend.app.models.user import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/albums", tags=["albums"])


@router.post("", response_model=AlbumResponse, status_code=status.HTTP_201_CREATED)
async def create_album(
        album_data: AlbumCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    if album_data.event_id:
        from backend.app.models.event_participant import EventParticipant
        from backend.app.models.enums import InvitationStatus

        has_access = db.query(EventParticipant).filter(
            EventParticipant.event_id == album_data.event_id,
            EventParticipant.user_id == current_user.id,
            EventParticipant.status == InvitationStatus.accepted
        ).first()

        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="У вас нет доступа к этому событию"
            )

    try:
        album = album_crud.create_album(db, album_data, current_user.id)
        return album
    except ValueError as e:
        if "не являетесь членом" in str(e):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка создания альбома: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при создании альбома"
        )


@router.get("", response_model=AlbumListResponse)
async def list_albums(
        family_id: Optional[int] = Query(None, description="Фильтр по семье"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    albums = album_crud.get_user_albums(db, current_user.id, family_id)

    result = []
    for album in albums:
        album.photos_count = len(album.photos) if hasattr(album, 'photos') else 0
        album.members_count = len(album.members) if hasattr(album, 'members') else 0
        result.append(album)

    return AlbumListResponse(albums=result, total=len(result))


@router.get("/{album_id}", response_model=AlbumDetailResponse)
async def get_album(
        album_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    if not album_crud.can_view_album(db, current_user.id, album_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этому альбому или срок его действия истёк"
        )

    album = album_crud.get_album_with_details(db, album_id)
    if not album:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Альбом не найден"
        )

    is_admin = album_crud.is_album_admin(db, current_user.id, album_id)

    response_data = AlbumDetailResponse.model_validate(album)
    response_data.is_admin = is_admin
    response_data.photos_count = len(album.photos)
    response_data.members_count = len(album.members)

    return response_data


@router.put("/{album_id}", response_model=AlbumResponse)
async def update_album(
        album_id: int,
        update_data: AlbumUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    if not album_crud.is_album_admin(db, current_user.id, album_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администратор может редактировать альбом"
        )

    album = album_crud.update_album(db, album_id, update_data)
    if not album:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Альбом не найден"
        )

    return album


@router.delete("/{album_id}")
async def delete_album(
        album_id: int,
        permanent: bool = Query(False, description="Полное удаление (иначе мягкое)"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    if not album_crud.is_album_admin(db, current_user.id, album_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администратор может удалять альбом"
        )

    success = album_crud.delete_album(db, album_id, permanent)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Альбом не найден"
        )

    return {"message": "Альбом удалён"}


@router.post("/{album_id}/members", response_model=AlbumMemberResponse)
async def add_album_member(
        album_id: int,
        member_data: AlbumMemberAdd,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    try:
        member = album_crud.add_member(
            db, album_id, member_data.user_id, current_user.id
        )
        return member
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{album_id}/members/{user_id}")
async def remove_album_member(
        album_id: int,
        user_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    try:
        success = album_crud.remove_member(db, album_id, user_id, current_user.id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Участник не найден"
            )
        return {"message": "Участник удалён"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{album_id}/admins", response_model=AlbumAdminResponse)
async def add_album_admin(
        album_id: int,
        admin_data: AlbumAdminAdd,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    try:
        admin = album_crud.add_admin(
            db, album_id, admin_data.user_id, current_user.id
        )
        return admin
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{album_id}/admins/{user_id}", response_model=AlbumAdminResponse)
async def remove_admin_rights(
        album_id: int,
        user_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    try:
        member = album_crud.remove_admin_rights(
            db, album_id, user_id, current_user.id
        )
        return member
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{album_id}/admins", response_model=List[AlbumMemberResponse])
async def list_album_admins(
        album_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    if not album_crud.is_album_member(db, current_user.id, album_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этому альбому"
        )

    admins = album_crud.get_album_admins(db, album_id)
    return admins


@router.post("/{album_id}/photos", response_model=PhotoUploadResponse)
async def upload_photo(
        album_id: int,
        file: UploadFile = File(...),
        description: Optional[str] = Form(None, max_length=500),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    if not album_crud.can_upload_photos(db, current_user.id, album_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет прав на загрузку в этот альбом или срок действия истёк"
        )

    content = await file.read()

    mime_type = magic.from_buffer(content, mime=True)

    try:
        photo = photo_crud.create_photo(
            db=db,
            album_id=album_id,
            uploaded_by_user_id=current_user.id,
            file_content=content,
            original_filename=file.filename,
            mime_type=mime_type,
            description=description
        )

        return PhotoUploadResponse(
            success=True,
            photo=PhotoResponse.model_validate(photo),
            message="Фотография успешно загружена"
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Ошибка загрузки фото: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при сохранении фотографии"
        )


@router.get("/{album_id}/photos", response_model=PhotoListResponse)
async def list_photos(
        album_id: int,
        limit: int = Query(50, ge=1, le=100),
        offset: int = Query(0, ge=0),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    if not album_crud.can_view_album(db, current_user.id, album_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этому альбому"
        )

    photos, total = photo_crud.get_album_photos(db, album_id, limit, offset)
    return PhotoListResponse(photos=photos, total=total, album_id=album_id)