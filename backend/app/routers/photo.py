from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse
import io

from app.database import get_db
from app.dependencies.auth import get_current_active_user
from app.crud import photo_crud, album_crud
from app.schemas.photo import PhotoResponse, PhotoUpdate
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/photos", tags=["photos"])


@router.get("/{photo_id}", response_model=PhotoResponse)
async def get_photo_info(
        photo_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Получить информацию о фотографии.
    """
    photo = photo_crud.get_photo_by_id(db, photo_id)
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Фотография не найдена"
        )

    if not album_crud.can_view_album(db, current_user.id, photo.album_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этой фотографии"
        )

    return photo


@router.get("/{photo_id}/file")
async def get_photo_file(
        photo_id: int,
        size: Optional[str] = Query(None, regex="^(small|medium|large)$"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Получить файл фотографии.
    Поддерживает размеры: small (300px), medium (800px), large (1600px), original.
    """
    photo = photo_crud.get_photo_by_id(db, photo_id)
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Фотография не найдена"
        )

    if not album_crud.can_view_album(db, current_user.id, photo.album_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этой фотографии"
        )

    file_content = photo_crud.get_photo_file(photo)
    if not file_content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл не найден на диске"
        )


    return StreamingResponse(
        io.BytesIO(file_content),
        media_type=photo.mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{photo.original_filename}"',
            "Cache-Control": "public, max-age=86400"
        }
    )


@router.put("/{photo_id}", response_model=PhotoResponse)
async def update_photo(
        photo_id: int,
        update_data: PhotoUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Обновить описание фотографии.
    Может загрузивший или админ альбома.
    """
    try:
        photo = photo_crud.update_photo(db, photo_id, update_data, current_user.id)
        if not photo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Фотография не найдена"
            )
        return photo
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.delete("/{photo_id}")
async def delete_photo(
        photo_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Удалить фотографию.
    Может загрузивший или админ альбома.
    """
    try:
        success = photo_crud.delete_photo(db, photo_id, current_user.id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Фотография не найдена"
            )
        return {"message": "Фотография удалена"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )