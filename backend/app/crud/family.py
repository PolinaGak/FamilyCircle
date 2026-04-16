from typing import Optional, List, Dict
from sqlalchemy.orm import Session, joinedload

from backend.app.models import RelationshipType
from backend.app.models import Relationship
from backend.app.models.family import Family
from backend.app.models.family_member import FamilyMember
from backend.app.models.enums import Gender
from backend.app.schemas.family import FamilyCreate
from backend.app.schemas.family_member import FamilyMemberCreate, FamilyMemberUpdate
import logging

logger = logging.getLogger(__name__)


class FamilyCRUD:

    @staticmethod
    def _validate_gender_consistency(member: FamilyMember, rel_type: RelationshipType):
        """
        Проверяет соответствие пола члена семьи типу связи.
        Вызывает ValueError при несоответствии.
        """
        if rel_type == RelationshipType.father and member.gender != Gender.male:
            raise ValueError(
                f"Член семьи '{member.first_name} {member.last_name}' не может быть отцом: указан не мужской пол")
        if rel_type == RelationshipType.mother and member.gender != Gender.female:
            raise ValueError(
                f"Член семьи '{member.first_name} {member.last_name}' не может быть матерью: указан не женский пол")
        if rel_type == RelationshipType.brother and member.gender != Gender.male:
            raise ValueError(
                f"Член семьи '{member.first_name} {member.last_name}' не может быть братом: указан не мужской пол")
        if rel_type == RelationshipType.sister and member.gender != Gender.female:
            raise ValueError(
                f"Член семьи '{member.first_name} {member.last_name}' не может быть сестрой: указан не женский пол")

    @staticmethod
    def _would_create_ancestor_cycle(db: Session, parent_id: int, child_id: int) -> bool:
        """
        Проверяет, создаст ли связь parent_id -> child_id цикл в родословной.
        Цикл возможен, если child_id уже является предком (родителем, дедом и т.д.) parent_id.
        """
        if parent_id == child_id:
            return True

        visited = set()
        queue = [child_id]

        while queue:
            current_id = queue.pop(0)
            if current_id == parent_id:
                return True

            if current_id in visited:
                continue
            visited.add(current_id)

            parent_rels = db.query(Relationship).filter(
                Relationship.to_member_id == current_id,
                Relationship.relationship_type.in_([RelationshipType.son, RelationshipType.daughter])
            ).all()

            for rel in parent_rels:
                if rel.from_member_id not in visited:
                    queue.append(rel.from_member_id)

            ancestor_rels = db.query(Relationship).filter(
                Relationship.from_member_id == current_id,
                Relationship.relationship_type.in_([RelationshipType.father, RelationshipType.mother])
            ).all()

            for rel in ancestor_rels:
                if rel.to_member_id not in visited:
                    queue.append(rel.to_member_id)

        return False

    @staticmethod
    def create_family(db: Session, family_data: FamilyCreate, admin_user_id: int) -> Family:
        try:
            family = Family(
                name=family_data.name.strip(),
                admin_user_id=admin_user_id
            )

            db.add(family)
            db.flush()

            from datetime import datetime

            admin_member = FamilyMember(
                family_id=family.id,
                user_id=admin_user_id,
                first_name="Администратор",
                last_name="Семьи",
                birth_date=datetime.now(),
                gender=Gender.male,
                is_admin=True,
                approved=True,
                is_active=True,
                created_by_user_id=admin_user_id
            )
            db.add(admin_member)

            db.commit()
            db.refresh(family)

            logger.info(f"Семья '{family.name}' создана пользователем {admin_user_id}")
            return family

        except Exception as e:
            logger.error(f"Ошибка при создании семьи: {str(e)}")
            db.rollback()
            raise

    @staticmethod
    def get_family_by_id(db: Session, family_id: int) -> Optional[Family]:
        return db.query(Family).filter(Family.id == family_id).first()

    @staticmethod
    def get_family_with_members(db: Session, family_id: int) -> Optional[Family]:
        return db.query(Family) \
            .options(joinedload(Family.members)) \
            .filter(Family.id == family_id) \
            .first()

    @staticmethod
    def get_user_families(db: Session, user_id: int) -> List[Family]:
        return db.query(Family) \
            .join(FamilyMember, Family.id == FamilyMember.family_id) \
            .filter(FamilyMember.user_id == user_id) \
            .all()

    @staticmethod
    def update_family(db: Session, family_id: int, name: str) -> Optional[Family]:
        family = FamilyCRUD.get_family_by_id(db, family_id)
        if not family:
            return None

        family.name = name.strip()
        db.commit()
        db.refresh(family)
        return family

    @staticmethod
    def delete_family(db: Session, family_id: int) -> bool:
        try:
            family = FamilyCRUD.get_family_by_id(db, family_id)
            if not family:
                return False

            db.query(FamilyMember).filter(FamilyMember.family_id == family_id).delete()
            db.delete(family)
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка при удалении семьи {family_id}: {str(e)}")
            db.rollback()
            return False

    def add_member(
            self,
            db: Session,
            family_id: int,
            member_data: FamilyMemberCreate,
            created_by_user_id: int
    ) -> FamilyMember:
        try:
            related_member = None
            if member_data.related_member_id:
                from backend.app.models.relationship import Relationship

                related_member = db.query(FamilyMember).filter(
                    FamilyMember.id == member_data.related_member_id,
                    FamilyMember.family_id == family_id
                ).first()

                if not related_member:
                    raise ValueError("Указанный связанный член семьи не найден или принадлежит другой семье")

                if member_data.relationship_type:
                    self._validate_gender_consistency(related_member, member_data.relationship_type)

            member = FamilyMember(
                family_id=family_id,
                user_id=member_data.user_id,
                first_name=member_data.first_name.strip(),
                last_name=member_data.last_name.strip(),
                patronymic=member_data.patronymic.strip() if member_data.patronymic else None,
                gender=member_data.gender,
                birth_date=member_data.birth_date,
                death_date=member_data.death_date,
                phone=member_data.phone,
                workplace=member_data.workplace,
                residence=member_data.residence,
                is_admin=member_data.is_admin,
                created_by_user_id=created_by_user_id,
                approved=member_data.approved,
                is_active=False
            )

            db.add(member)
            db.flush()

            if member_data.related_member_id and member_data.relationship_type:
                from backend.app.models.relationship import Relationship
                from backend.app.crud.tree import tree_crud

                if member_data.relationship_type in [RelationshipType.father, RelationshipType.mother]:
                    if self._would_create_ancestor_cycle(db, member_data.related_member_id, member.id):
                        raise ValueError(
                            "Невозможно установить связь: образуется цикл в родословной (предок не может быть потомком)")

                existing_rel = db.query(Relationship).filter(
                    Relationship.from_member_id == member_data.related_member_id,
                    Relationship.to_member_id == member.id,
                    Relationship.relationship_type == member_data.relationship_type
                ).first()

                if existing_rel:
                    raise ValueError("Такая связь уже существует")

                rel = Relationship(
                    from_member_id=member_data.related_member_id,
                    to_member_id=member.id,
                    relationship_type=member_data.relationship_type
                )
                db.add(rel)

                if member_data.relationship_type in [RelationshipType.son, RelationshipType.daughter]:
                    reverse_type = tree_crud._get_reverse_relationship(
                        member_data.relationship_type,
                        related_member.gender
                    )
                else:
                    reverse_type = tree_crud._get_reverse_relationship(
                        member_data.relationship_type,
                        member.gender
                    )

                if reverse_type:
                    self._validate_gender_consistency(member, reverse_type)

                    existing_reverse = db.query(Relationship).filter(
                        Relationship.from_member_id == member.id,
                        Relationship.to_member_id == member_data.related_member_id,
                        Relationship.relationship_type == reverse_type
                    ).first()

                    if not existing_reverse:
                        reverse = Relationship(
                            from_member_id=member.id,
                            to_member_id=member_data.related_member_id,
                            relationship_type=reverse_type
                        )
                        db.add(reverse)

            db.commit()
            db.refresh(member)

            logger.info(f"Член семьи {member.id} добавлен в семью {family_id}" +
                        (f" со связью к {member_data.related_member_id}" if member_data.related_member_id else ""))
            return member

        except Exception as e:
            logger.error(f"Ошибка при добавлении члена семьи: {str(e)}")
            db.rollback()
            raise

    @staticmethod
    def add_sibling(
            db: Session,
            family_id: int,
            existing_member_id: int,
            sibling_data: Dict,
            mother_id: Optional[int],
            father_id: Optional[int],
            created_by_user_id: int
    ) -> FamilyMember:
        """
        Добавляет брата или сестру к существующему члену семьи.
        Позволяет отдельно указать мать и/или отца.
        Если родители указаны, создаются соответствующие родительские связи.
        """
        from backend.app.models.relationship import Relationship
        from backend.app.crud.tree import tree_crud
        existing = db.query(FamilyMember).filter(
            FamilyMember.id == existing_member_id,
            FamilyMember.family_id == family_id
        ).first()

        if not existing:
            raise ValueError("Базовый член семьи не найден в указанной семье")

        gender = sibling_data.get('gender')
        if not gender:
            raise ValueError("Не указан пол нового члена семьи")

        if gender == Gender.male:
            sibling_rel_type = RelationshipType.brother
        else:
            sibling_rel_type = RelationshipType.sister

        member = FamilyMember(
            family_id=family_id,
            user_id=sibling_data.get('user_id'),
            first_name=sibling_data['first_name'].strip(),
            last_name=sibling_data['last_name'].strip(),
            patronymic=sibling_data.get('patronymic', '').strip() if sibling_data.get('patronymic') else None,
            gender=gender,
            birth_date=sibling_data['birth_date'],
            death_date=sibling_data.get('death_date'),
            phone=sibling_data.get('phone'),
            workplace=sibling_data.get('workplace'),
            residence=sibling_data.get('residence'),
            is_admin=sibling_data.get('is_admin', False),
            created_by_user_id=created_by_user_id,
            approved=sibling_data.get('approved', False),
            is_active=False
        )

        db.add(member)
        db.flush()

        existing_rel_type = RelationshipType.brother if existing.gender == Gender.male else RelationshipType.sister

        rel1 = Relationship(
            from_member_id=existing_member_id,
            to_member_id=member.id,
            relationship_type=sibling_rel_type
        )
        db.add(rel1)

        rel2 = Relationship(
            from_member_id=member.id,
            to_member_id=existing_member_id,
            relationship_type=existing_rel_type
        )
        db.add(rel2)

        if mother_id:
            mother = db.query(FamilyMember).filter(
                FamilyMember.id == mother_id,
                FamilyMember.family_id == family_id
            ).first()

            if not mother:
                raise ValueError(f"Мать с ID {mother_id} не найдена в этой семье")

            FamilyCRUD._validate_gender_consistency(mother, RelationshipType.mother)

            if FamilyCRUD._would_create_ancestor_cycle(db, mother.id, member.id):
                raise ValueError("Невозможно установить мать: образуется цикл в родословной")

            existing_child_rel = db.query(Relationship).filter(
                Relationship.from_member_id == mother_id,
                Relationship.to_member_id == member.id,
                Relationship.relationship_type.in_([RelationshipType.son, RelationshipType.daughter])
            ).first()

            if not existing_child_rel:
                child_type = RelationshipType.daughter if gender == Gender.female else RelationshipType.son
                rel_m = Relationship(
                    from_member_id=mother_id,
                    to_member_id=member.id,
                    relationship_type=child_type
                )
                db.add(rel_m)

                rel_m_rev = Relationship(
                    from_member_id=member.id,
                    to_member_id=mother_id,
                    relationship_type=RelationshipType.mother
                )
                db.add(rel_m_rev)

        if father_id:
            father = db.query(FamilyMember).filter(
                FamilyMember.id == father_id,
                FamilyMember.family_id == family_id
            ).first()

            if not father:
                raise ValueError(f"Отец с ID {father_id} не найден в этой семье")

            FamilyCRUD._validate_gender_consistency(father, RelationshipType.father)

            if FamilyCRUD._would_create_ancestor_cycle(db, father.id, member.id):
                raise ValueError("Невозможно установить отца: образуется цикл в родословной")

            existing_child_rel = db.query(Relationship).filter(
                Relationship.from_member_id == father_id,
                Relationship.to_member_id == member.id,
                Relationship.relationship_type.in_([RelationshipType.son, RelationshipType.daughter])
            ).first()

            if not existing_child_rel:
                child_type = RelationshipType.daughter if gender == Gender.female else RelationshipType.son
                rel_f = Relationship(
                    from_member_id=father_id,
                    to_member_id=member.id,
                    relationship_type=child_type
                )
                db.add(rel_f)

                rel_f_rev = Relationship(
                    from_member_id=member.id,
                    to_member_id=father_id,
                    relationship_type=RelationshipType.father
                )
                db.add(rel_f_rev)

        db.commit()
        db.refresh(member)

        logger.info(
            f"Добавлен {'брат' if gender == Gender.male else 'сестра'} {member.id} к члену {existing_member_id}" +
            (f", мать: {mother_id}" if mother_id else "") +
            (f", отец: {father_id}" if father_id else ""))

        return member

    def add_parent(
            self,
            db: Session,
            family_id: int,
            parent_data: Dict,
            children_ids: List[int],
            created_by_user_id: int,
            spouse_id: Optional[int] = None
    ) -> FamilyMember:
        """
        Добавляет родителя (маму или папу) и связывает его с несколькими детьми.

        Args:
            parent_data: Данные родителя (first_name, last_name, gender и т.д.)
            children_ids: Список ID детей, для которых создается родитель
            spouse_id: Опционально - ID супруга/супруги для создания связи spouse
        """
        from backend.app.models.relationship import Relationship
        from backend.app.crud.tree import tree_crud

        if parent_data.get('gender') == Gender.male:
            parent_rel_type = RelationshipType.father
        elif parent_data.get('gender') == Gender.female:
            parent_rel_type = RelationshipType.mother
        else:
            raise ValueError("Необходимо указать пол родителя (male/female)")

        children = []
        for child_id in children_ids:
            child = db.query(FamilyMember).filter(
                FamilyMember.id == child_id,
                FamilyMember.family_id == family_id
            ).first()
            if not child:
                raise ValueError(f"Ребенок с ID {child_id} не найден в этой семье")
            children.append(child)

        spouse = None
        if spouse_id:
            spouse = db.query(FamilyMember).filter(
                FamilyMember.id == spouse_id,
                FamilyMember.family_id == family_id
            ).first()
            if not spouse:
                raise ValueError("Указанный супруг/супруга не найден в этой семье")

            if spouse.gender == parent_data.get('gender'):
                raise ValueError("Супруги должны быть разного пола")

        parent = FamilyMember(
            family_id=family_id,
            user_id=parent_data.get('user_id'),
            first_name=parent_data['first_name'].strip(),
            last_name=parent_data['last_name'].strip(),
            patronymic=parent_data.get('patronymic', '').strip() if parent_data.get('patronymic') else None,
            gender=parent_data['gender'],
            birth_date=parent_data['birth_date'],
            death_date=parent_data.get('death_date'),
            phone=parent_data.get('phone'),
            workplace=parent_data.get('workplace'),
            residence=parent_data.get('residence'),
            is_admin=parent_data.get('is_admin', False),
            created_by_user_id=created_by_user_id,
            approved=parent_data.get('approved', False),
            is_active=False
        )

        db.add(parent)
        db.flush()

        for child in children:
            if self._would_create_ancestor_cycle(db, parent.id, child.id):
                raise ValueError(f"Невозможно установить связь с ребенком {child.id}: образуется цикл в родословной")

            if child.gender == Gender.male:
                child_rel_type = RelationshipType.son
            else:
                child_rel_type = RelationshipType.daughter

            existing = db.query(Relationship).filter(
                Relationship.from_member_id == parent.id,
                Relationship.to_member_id == child.id,
                Relationship.relationship_type.in_([RelationshipType.son, RelationshipType.daughter])
            ).first()

            if not existing:
                rel = Relationship(
                    from_member_id=parent.id,
                    to_member_id=child.id,
                    relationship_type=child_rel_type
                )
                db.add(rel)

            existing_reverse = db.query(Relationship).filter(
                Relationship.from_member_id == child.id,
                Relationship.to_member_id == parent.id,
                Relationship.relationship_type == parent_rel_type
            ).first()

            if not existing_reverse:
                reverse_rel = Relationship(
                    from_member_id=child.id,
                    to_member_id=parent.id,
                    relationship_type=parent_rel_type
                )
                db.add(reverse_rel)

        if spouse:
            existing_spouse = db.query(Relationship).filter(
                Relationship.from_member_id == parent.id,
                Relationship.to_member_id == spouse.id,
                Relationship.relationship_type == RelationshipType.spouse
            ).first()

            if not existing_spouse:
                rel1 = Relationship(
                    from_member_id=parent.id,
                    to_member_id=spouse.id,
                    relationship_type=RelationshipType.spouse
                )
                rel2 = Relationship(
                    from_member_id=spouse.id,
                    to_member_id=parent.id,
                    relationship_type=RelationshipType.spouse
                )
                db.add(rel1)
                db.add(rel2)

        db.commit()
        db.refresh(parent)

        logger.info(f"Добавлен родитель {parent.id} ({parent_rel_type.value}) для детей: {children_ids}")
        return parent

    @staticmethod
    def get_member_by_id(db: Session, member_id: int) -> Optional[FamilyMember]:
        return db.query(FamilyMember).filter(FamilyMember.id == member_id).first()

    @staticmethod
    def get_family_members(db: Session, family_id: int) -> List[FamilyMember]:
        return db.query(FamilyMember) \
            .filter(FamilyMember.family_id == family_id) \
            .order_by(FamilyMember.last_name, FamilyMember.first_name) \
            .all()

    @staticmethod
    def update_member(
            db: Session,
            member_id: int,
            update_data: FamilyMemberUpdate
    ) -> Optional[FamilyMember]:
        from backend.app.models.relationship import Relationship
        from backend.app.crud.tree import tree_crud

        member = FamilyCRUD.get_member_by_id(db, member_id)
        if not member:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)

        if (update_data.related_member_id and update_data.relationship_type):
            existing = db.query(Relationship).filter(
                Relationship.from_member_id == update_data.related_member_id,
                Relationship.to_member_id == member_id
            ).first()

            if not existing:
                related = db.get(FamilyMember, update_data.related_member_id)
                if related and related.family_id == member.family_id:

                    FamilyCRUD._validate_gender_consistency(related, update_data.relationship_type)

                    if update_data.relationship_type in [RelationshipType.father, RelationshipType.mother]:
                        if FamilyCRUD._would_create_ancestor_cycle(db, related.id, member_id):
                            raise ValueError("Невозможно установить связь: образуется цикл в родословной")

                    rel = Relationship(
                        from_member_id=update_data.related_member_id,
                        to_member_id=member_id,
                        relationship_type=update_data.relationship_type
                    )
                    db.add(rel)

                    if update_data.relationship_type in [RelationshipType.son, RelationshipType.daughter]:
                        reverse_type = tree_crud._get_reverse_relationship(
                            update_data.relationship_type, related.gender
                        )
                    elif update_data.relationship_type in [RelationshipType.brother, RelationshipType.sister]:
                        reverse_type = tree_crud._get_reverse_relationship(
                            update_data.relationship_type, related.gender
                        )
                    else:
                        reverse_type = tree_crud._get_reverse_relationship(
                            update_data.relationship_type, member.gender
                        )

                    if reverse_type:
                        FamilyCRUD._validate_gender_consistency(member, reverse_type)

                        reverse = Relationship(
                            from_member_id=member_id,
                            to_member_id=update_data.related_member_id,
                            relationship_type=reverse_type
                        )
                        db.add(reverse)

        for key, value in update_dict.items():
            if key not in ['related_member_id', 'relationship_type'] and value is not None:
                setattr(member, key, value)

        db.commit()
        db.refresh(member)
        return member

    @staticmethod
    def approve_member(db: Session, member_id: int, approved: bool = True) -> Optional[FamilyMember]:
        member = FamilyCRUD.get_member_by_id(db, member_id)
        if not member:
            return None

        member.approved = approved
        db.commit()
        db.refresh(member)
        return member

    @staticmethod
    def remove_member(db: Session, member_id: int) -> bool:
        try:
            member = FamilyCRUD.get_member_by_id(db, member_id)
            if not member:
                return False

            from backend.app.models.invitation import Invitation
            db.query(Invitation).filter(Invitation.target_member_id == member_id).update(
                {"target_member_id": None}, synchronize_session=False
            )

            db.delete(member)
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка при удалении члена семьи {member_id}: {str(e)}")
            db.rollback()
            return False

    @staticmethod
    def is_family_admin(db: Session, user_id: int, family_id: int) -> bool:
        return db.query(FamilyMember).filter(
            FamilyMember.family_id == family_id,
            FamilyMember.user_id == user_id,
            FamilyMember.is_admin == True
        ).first() is not None

    @staticmethod
    def is_family_member(db: Session, user_id: int, family_id: int) -> bool:
        return db.query(FamilyMember).filter(
            FamilyMember.family_id == family_id,
            FamilyMember.user_id == user_id
        ).first() is not None

    @staticmethod
    def leave_family(db: Session, user_id: int, family_id: int) -> FamilyMember:
        member = db.query(FamilyMember).filter(
            FamilyMember.family_id == family_id,
            FamilyMember.user_id == user_id,
            FamilyMember.is_active == True
        ).first()

        if not member:
            raise ValueError("Вы не являетесь активным членом этой семьи")

        if member.is_admin:
            admin_count = db.query(FamilyMember).filter(
                FamilyMember.family_id == family_id,
                FamilyMember.is_admin == True,
                FamilyMember.is_active == True
            ).count()

            if admin_count <= 1:
                raise ValueError(
                    "Вы последний администратор. Невозможно покинуть семью. Назначьте другого администратора или удалите семью.")

        member.user_id = None
        if member.is_admin:
            member.is_admin = False

        db.commit()
        db.refresh(member)

        logger.info(f"Пользователь {user_id} покинул семью {family_id}, карточка {member.id} отвязана")
        return member

    @staticmethod
    def transfer_admin_rights(db: Session, current_user_id: int, family_id: int, target_member_id: int) -> FamilyMember:
        current_member = db.query(FamilyMember).filter(
            FamilyMember.family_id == family_id,
            FamilyMember.user_id == current_user_id,
            FamilyMember.is_active == True
        ).first()

        if not current_member or not current_member.is_admin:
            raise ValueError("Только администратор может передавать права")

        target_member = db.query(FamilyMember).filter(
            FamilyMember.id == target_member_id,
            FamilyMember.family_id == family_id,
            FamilyMember.is_active == True
        ).first()

        if not target_member:
            raise ValueError("Целевой член семьи не найден или неактивен")

        if target_member.is_admin:
            raise ValueError("Целевой член уже является администратором")

        current_member.is_admin = False
        target_member.is_approved = True
        target_member.is_admin = True

        db.commit()
        db.refresh(target_member)

        logger.info(
            f"Права администратора переданы от пользователя {current_user_id} к члену {target_member_id} в семье {family_id}")
        return target_member

    @staticmethod
    def get_parent_candidates(db: Session, family_id: int, gender: Gender) -> List[FamilyMember]:
        """
        Получить членов семьи подходящего пола для роли родителя.
        Исключает детей (тех, у кого есть родители в этой семье - опционально).
        """
        query = db.query(FamilyMember).filter(
            FamilyMember.family_id == family_id,
            FamilyMember.gender == gender,
            FamilyMember.is_active == True
        ).order_by(FamilyMember.last_name, FamilyMember.first_name)

        return query.all()


family_crud = FamilyCRUD()