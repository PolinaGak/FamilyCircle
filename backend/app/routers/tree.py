from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime

from backend.app.database import get_db
from backend.app.dependencies.family_access import (
    check_family_access
)
from backend.app.crud.tree import tree_crud
from backend.app.crud.family import family_crud
from backend.app.schemas.tree import (
    TreeResponse, TreeSettings, TreeSearchResult,
    SubtreeRequest, RootInfo, RelativesGroup,
    PDFExportData, ExportFormat
)
from backend.app.services.tree_export import tree_export_service
from backend.app.models.user import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/family/{family_id}/tree", tags=["family-tree"])


@router.get("", response_model=TreeResponse)
async def get_family_tree(
        family_id: int,
        root_member_id: Optional[int] = Query(None, description="ID корневого члена (точка отсчета)"),
        include_inactive: bool = Query(False, description="Показывать неактивных участников"),
        max_depth: int = Query(10, ge=1, le=20, description="Глубина дерева"),
        db: Session = Depends(get_db),
        current_user: User = Depends(check_family_access)
):
    """
    Получить полное семейное дерево или поддерево от выбранного корня.
    Если root_member_id не указан, выбирается старший администратор.
    """
    try:
        tree_data = tree_crud.build_tree(
            db,
            family_id,
            root_member_id=root_member_id,
            include_inactive=include_inactive,
            max_depth=max_depth,
            current_user_id=current_user.id,
        )
        return tree_data
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка построения дерева: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при построении семейного дерева"
        )


@router.get("/roots", response_model=List[RootInfo])
async def get_available_roots(
        family_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_family_access)
):
    """Получить список доступных точек отсчета (корней) для переключения"""
    return tree_crud.get_available_roots(db, family_id)


@router.get("/member/{member_id}/subtree", response_model=TreeResponse)
async def get_member_subtree(
        family_id: int,
        member_id: int,
        direction: str = Query("both", regex="^(up|down|both)$", description="up - предки, down - потомки, both - все"),
        generations: int = Query(3, ge=1, le=10, description="Количество поколений"),
        db: Session = Depends(get_db),
        current_user: User = Depends(check_family_access)
):
    """Получить поддерево от конкретного участника (его предков и/или потомков)"""
    member = family_crud.get_member_by_id(db, member_id)
    if not member or member.family_id != family_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Член семьи не найден в этой семье"
        )

    try:
        subtree = tree_crud.get_member_subtree(
            db, member_id, direction=direction, generations=generations
        )
        return subtree
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/member/{member_id}/relatives", response_model=RelativesGroup)
async def get_member_relatives(
        family_id: int,
        member_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_family_access)
):
    """Получить ближайших родственников по категориям"""
    member = family_crud.get_member_by_id(db, member_id)
    if not member or member.family_id != family_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Член семьи не найден")

    try:
        return tree_crud.get_member_relatives(db, member_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/search", response_model=List[TreeSearchResult])
async def search_tree_members(
        family_id: int,
        query: Optional[str] = Query(None, description="Поиск по ФИО"),
        search_inactive: bool = Query(False, description="Искать среди неактивных"),
        birth_date_from: Optional[datetime] = Query(None, description="Дата рождения от (YYYY-MM-DD)"),
        birth_date_to: Optional[datetime] = Query(None, description="Дата рождения до"),
        db: Session = Depends(get_db),
        current_user: User = Depends(check_family_access)
):
    """Поиск по семейному древу"""
    results = tree_crud.search_members(
        db,
        family_id,
        query=query,
        search_inactive=search_inactive,
        birth_date_from=birth_date_from,
        birth_date_to=birth_date_to
    )
    return results


@router.delete("/relationship/{relationship_id}")
async def delete_relationship(
        family_id: int,
        relationship_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_family_access)
):
    """
    Удалить связь между членами семьи.
    Проверка прав внутри crud (админ или владелец карточки).
    """
    try:
        success = tree_crud.delete_relationship(db, relationship_id, current_user.id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Связь не найдена"
            )
        return {"message": "Связь успешно удалена"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка удаления связи: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при удалении связи")


@router.get("/export/pdf-data", response_model=PDFExportData)
async def export_tree_pdf_data(
        family_id: int,
        root_member_id: Optional[int] = Query(None),
        include_inactive: bool = Query(False),
        include_contacts: bool = Query(False),
        db: Session = Depends(get_db),
        current_user: User = Depends(check_family_access)
):
    """
    Получить данные семейного древа в формате, готовом для генерации PDF.
    """
    try:
        data = tree_export_service.prepare_pdf_data(
            db, family_id, current_user.id,  root_member_id, include_inactive, include_contacts
        )
        return data
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка подготовки PDF данных: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при подготовке данных для экспорта"
        )


@router.get("/export/gedcom")
async def export_tree_gedcom(
        family_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_family_access)
):
    """
    Экспорт семейного древа в формат GEDCOM 5.5.
    """
    try:
        from fastapi.responses import PlainTextResponse
        gedcom_content = tree_export_service.export_to_gedcom(db, family_id)
        filename = f"family_tree_{family_id}_{datetime.now().strftime('%Y%m%d')}.ged"

        return PlainTextResponse(
            content=gedcom_content,
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Ошибка GEDCOM экспорта: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при экспорте в GEDCOM"
        )


@router.post("/export")
async def export_tree_generic(
        family_id: int,
        params: ExportFormat,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_family_access)
):
    """
    Универсальный endpoint для экспорта в различные форматы.
    """
    from fastapi.responses import JSONResponse, PlainTextResponse

    if params.format == "pdf" or params.format == "json":
        data = tree_export_service.prepare_pdf_data(
            db, family_id, current_user.id,
            params.root_member_id,
            params.include_inactive,
            params.include_contacts
        )
        return JSONResponse(content=data)

    elif params.format == "gedcom":
        gedcom = tree_export_service.export_to_gedcom(db, family_id)
        return PlainTextResponse(
            content=gedcom,
            media_type="text/plain",
            headers={"Content-Disposition": "attachment; filename=family_tree.ged"}
        )

    else:
        raise HTTPException(status_code=400, detail="Неподдерживаемый формат")