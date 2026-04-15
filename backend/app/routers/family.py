from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import exc
from sqlalchemy.orm import Session
from fastapi import Query
from sqlalchemy import func
from app.models import FamilyMember
from app.database import get_db
from app.dependencies.auth import get_current_active_user
from app.crud import family_crud
from app.schemas.family import (
    FamilyCreate, FamilyResponse, FamilyDetailResponse
)
from app.schemas.family_member import (
    FamilyMemberCreate, FamilyMemberResponse,
    FamilyMemberUpdate, FamilyMemberApprove, SiblingCreate, ParentCreate
)

from app.models.user import User
import logging

from app.models import FamilyMember

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/family", tags=["family"])


@router.post("/create", response_model=FamilyResponse)
async def create_family(
        family_data: FamilyCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    MAX_FAMILIES_PER_USER = 3
    families_count = db.query(func.count(FamilyMember.id)).filter(
        FamilyMember.user_id == current_user.id,
        FamilyMember.is_admin == True
    ).scalar()
    
    if families_count >= MAX_FAMILIES_PER_USER:
        logger.warning(f"Пользователь {current_user.id} пытается создать {families_count + 1}-ю семью (лимит {MAX_FAMILIES_PER_USER})")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Вы не можете создать более {MAX_FAMILIES_PER_USER} семей. Достигнут лимит."
        )
    
    try:
        family = family_crud.create_family(db, family_data, current_user.id)
        logger.info(f"Семья '{family.name}' создана пользователем {current_user.id}")
        return family
    except Exception as e:
        logger.error(f"Ошибка при создании семьи: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при создании семьи"
        )


@router.get("/my", response_model=List[FamilyResponse])
async def get_my_families(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    families = family_crud.get_user_families(db, current_user.id)
    return families


@router.get("/{family_id}", response_model=FamilyDetailResponse)
async def get_family_detail(
        family_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    if not family_crud.is_family_member(db, current_user.id, family_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этой семье"
        )

    family = family_crud.get_family_with_members(db, family_id)
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Семья не найдена"
        )

    return family


@router.put("/{family_id}", response_model=FamilyResponse)
async def update_family(
        family_id: int,
        family_data: FamilyCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    if not family_crud.is_family_admin(db, current_user.id, family_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администратор может изменять семью"
        )

    family = family_crud.update_family(db, family_id, family_data.name)
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Семья не найдена"
        )

    return family


@router.delete("/{family_id}")
async def delete_family(
        family_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    if not family_crud.is_family_admin(db, current_user.id, family_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администратор может удалить семью"
        )

    success = family_crud.delete_family(db, family_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Семья не найдена"
        )

    return {"message": "Семья успешно удалена"}


@router.post("/{family_id}/member", response_model=FamilyMemberResponse)
async def add_family_member(
        family_id: int,
        member_data: FamilyMemberCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    is_admin = family_crud.is_family_admin(db, current_user.id, family_id)
    is_member = family_crud.is_family_member(db, current_user.id, family_id)

    if not (is_admin or is_member):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет прав добавлять членов в эту семью"
        )

    if is_admin:
        member_data.approved = True

    try:
        member = family_crud.add_member(db, family_id, member_data, current_user.id)
        return member
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка при добавлении члена семьи: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при добавлении члена семьи"
        )


@router.post("/{family_id}/sibling", response_model=FamilyMemberResponse)
async def add_sibling(
        family_id: int,
        sibling_data: SiblingCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Добавить брата или сестру к существующему члену семьи.

    Позволяет отдельно указать общих родителей (мать и/или отца).
    Если родители указаны, будут созданы соответствующие родительские связи (son/daughter),
    что автоматически поместит нового члена в ту же family_unit.

    - existing_member_id: ID члена семьи, к которому добавляем брата/сестру
    - mother_id: ID матери в семье (опционально, но рекомендуется)
    - father_id: ID отца в семье (опционально, но рекомендуется)
    """
    # Проверка доступа к семье
    if not family_crud.is_family_member(db, current_user.id, family_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этой семье"
        )

    try:
        # Подготавливаем данные для CRUD
        member_dict = {
            "first_name": sibling_data.first_name,
            "last_name": sibling_data.last_name,
            "patronymic": sibling_data.patronymic,
            "gender": sibling_data.gender,
            "birth_date": sibling_data.birth_date,
            "death_date": sibling_data.death_date,
            "phone": sibling_data.phone,
            "workplace": sibling_data.workplace,
            "residence": sibling_data.residence,
            "is_admin": sibling_data.is_admin,
            "user_id": sibling_data.user_id,
            "approved": family_crud.is_family_admin(db, current_user.id, family_id)
        }

        member = family_crud.add_sibling(
            db=db,
            family_id=family_id,
            existing_member_id=sibling_data.existing_member_id,
            sibling_data=member_dict,
            mother_id=sibling_data.mother_id,
            father_id=sibling_data.father_id,
            created_by_user_id=current_user.id
        )
        return member
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка при добавлении брата/сестры: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при добавлении члена семьи"

        )


@router.post("/{family_id}/parent", response_model=FamilyMemberResponse)
async def add_parent(
        family_id: int,
        parent_data: ParentCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Добавить родителя (маму или папу) с привязкой к нескольким детям.

    - Выбирается пол (male=отец, female=мать)
    - Указывается список детей (children_ids), к которым привязывается родитель
    - Опционально можно сразу привязать к супругу/супруге (spouse_id)
    """
    # Проверка доступа к семье
    if not family_crud.is_family_member(db, current_user.id, family_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этой семье"
        )

    is_admin = family_crud.is_family_admin(db, current_user.id, family_id)

    try:
        # Подготавливаем данные родителя
        parent_dict = {
            "first_name": parent_data.first_name,
            "last_name": parent_data.last_name,
            "patronymic": parent_data.patronymic,
            "gender": parent_data.gender,
            "birth_date": parent_data.birth_date,
            "death_date": parent_data.death_date,
            "phone": parent_data.phone,
            "workplace": parent_data.workplace,
            "residence": parent_data.residence,
            "is_admin": False,  # Родитель по умолчанию не админ
            "user_id": None,  # Можно добавить поле в схему, если нужно
            "approved": is_admin  # Если создатель админ - сразу подтверждаем
        }

        member = family_crud.add_parent(
            db=db,
            family_id=family_id,
            parent_data=parent_dict,
            children_ids=parent_data.children_ids,
            created_by_user_id=current_user.id,
            spouse_id=parent_data.spouse_id
        )
        return member

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка при добавлении родителя: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при добавлении родителя"
        )


@router.get("/{family_id}/members", response_model=List[FamilyMemberResponse])
async def get_family_members(
        family_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    if not family_crud.is_family_member(db, current_user.id, family_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этой семье"
        )

    members = family_crud.get_family_members(db, family_id)
    return members


@router.put("/member/{member_id}", response_model=FamilyMemberResponse)
async def update_family_member(
        member_id: int,
        update_data: FamilyMemberUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    member = family_crud.get_member_by_id(db, member_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Член семьи не найден"
        )

    is_admin = family_crud.is_family_admin(db, current_user.id, member.family_id)
    is_self = member.user_id == current_user.id

    if not (is_admin or is_self):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав на редактирование"
        )

    try:
        updated = family_crud.update_member(db, member_id, update_data)
        return updated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/member/{member_id}/approve", response_model=FamilyMemberResponse)
async def approve_family_member(
        member_id: int,
        approve_data: FamilyMemberApprove,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    member = family_crud.get_member_by_id(db, member_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Член семьи не найден"
        )

    if not family_crud.is_family_admin(db, current_user.id, member.family_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администратор может подтверждать членов семьи"
        )

    updated = family_crud.approve_member(db, member_id, approve_data.approved)
    return updated


@router.delete("/member/{member_id}")
async def remove_family_member(
        member_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    member = family_crud.get_member_by_id(db, member_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Член семьи не найден"
        )

    is_admin = family_crud.is_family_admin(db, current_user.id, member.family_id)
    is_self = member.user_id == current_user.id

    if not (is_admin or is_self):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав на удаление"
        )

    if is_self and member.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Администратор не может удалить себя. Сначала передайте права другому."
        )

    try:
        success = family_crud.remove_member(db, member_id)
        if not success:
            raise HTTPException(status_code=404, detail="Член семьи не найден")
        return {"message": "Член семьи успешно удален"}
    except exc.IntegrityError as e:
        logger.error(f"Ошибка целостности при удалении: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Невозможно удалить, так как есть связанные данные"
        )
    except Exception as e:
        logger.error(f"Ошибка при удалении: {str(e)}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/{family_id}/transfer-admin")
async def transfer_admin_rights(
        family_id: int,
        target_member_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    try:
        family_crud.transfer_admin_rights(db, current_user.id, family_id, target_member_id)
        return {"success": True, "message": "Права администратора переданы"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{family_id}/leave")
async def leave_family(
        family_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    try:
        family_crud.leave_family(db, current_user.id, family_id)
        return {"success": True, "message": "Вы успешно покинули семью"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/{family_id}/members/without-parent/{gender}")
async def get_members_without_parent(
        family_id: int,
        gender: str,  # 'mother' или 'father'
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Получить список членов семьи, у которых нет указанного родителя.
    Используется при добавлении мамы/папы - показывает, кого можно выбрать в дети.
    """
    if not family_crud.is_family_member(db, current_user.id, family_id):
        raise HTTPException(status_code=403, detail="Нет доступа")

    from app.models.relationship import Relationship
    from app.models.enums import RelationshipType, Gender

    # Определяем тип связи, которой не должно быть
    if gender == 'mother':
        exclude_rel = RelationshipType.mother
        expected_gender = Gender.female
    elif gender == 'father':
        exclude_rel = RelationshipType.father
        expected_gender = Gender.male
    else:
        raise HTTPException(status_code=400, detail="gender должен быть 'mother' или 'father'")

    # Получаем всех членов семьи, у которых нет такой связи
    subquery = db.query(Relationship.from_member_id).filter(
        Relationship.relationship_type == exclude_rel,
        Relationship.from_member_id.in_(
            db.query(FamilyMember.id).filter(FamilyMember.family_id == family_id)
        )
    )

    members = db.query(FamilyMember).filter(
        FamilyMember.family_id == family_id,
        ~FamilyMember.id.in_(subquery)
    ).all()

    return [
        {
            "id": m.id,
            "full_name": f"{m.last_name} {m.first_name} {m.patronymic or ''}".strip(),
            "birth_date": m.birth_date,
            "gender": m.gender.value if m.gender else None
        }
        for m in members
    ]


@router.get("/{family_id}/parent-candidates")
async def get_parent_candidates(
        family_id: int,
        gender: str,
        existing_member_id: Optional[int] = Query(None,
                                                  description="ID существующего члена (для приоритета его родителей)"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Получить список кандидатов в родители указанного пола.
    """
    if not family_crud.is_family_member(db, current_user.id, family_id):
        raise HTTPException(status_code=403, detail="Нет доступа")

    from app.models.enums import Gender

    try:
        gender_enum = Gender(gender)
    except ValueError:
        raise HTTPException(status_code=400, detail="gender должен быть 'male' или 'female'")

    # Получаем всех членов семьи нужного пола
    candidates = family_crud.get_parent_candidates(db, family_id, gender_enum)

    # Инициализируем пустое множество для случая, когда existing_member_id не передан
    parent_ids = set()

    # Если указан existing_member_id, поднимаем его родителей в начало списка
    if existing_member_id:
        from app.crud.tree import tree_crud

        try:
            existing_parents = tree_crud.get_member_relatives(db, existing_member_id)
            parent_ids = {p["id"] for p in existing_parents.get("parents", [])}

            # Сортируем: сначала родители (False < True), потом по фамилии
            candidates.sort(key=lambda x: (x.id not in parent_ids, x.last_name))
        except ValueError:
            # Если member не найден, просто возвращаем как есть
            pass

    return [
        {
            "id": c.id,
            "first_name": c.first_name,
            "last_name": c.last_name,
            "patronymic": c.patronymic,
            "birth_date": c.birth_date.isoformat() if c.birth_date else None,
            "is_already_parent": c.id in parent_ids if existing_member_id else False
        }
        for c in candidates
    ]