from typing import Optional, List, Dict, Set
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, func
from datetime import datetime

from app.models.family_member import FamilyMember
from app.models.relationship import Relationship
from app.models.enums import RelationshipType, Gender
from app.crud.family import family_crud
import logging

logger = logging.getLogger(__name__)


class TreeCRUD:
    """CRUD операции для семейного древа"""

    @staticmethod
    def _get_reverse_relationship(rel_type: RelationshipType, gender: Gender) -> Optional[RelationshipType]:
        """Получить обратный тип связи с учетом пола"""
        reverse_map = {
            (RelationshipType.son, Gender.male): RelationshipType.father,
            (RelationshipType.son, Gender.female): RelationshipType.mother,
            (RelationshipType.daughter, Gender.male): RelationshipType.father,
            (RelationshipType.daughter, Gender.female): RelationshipType.mother,
            (RelationshipType.father, Gender.male): RelationshipType.son,
            (RelationshipType.father, Gender.female): RelationshipType.daughter,
            (RelationshipType.mother, Gender.male): RelationshipType.son,
            (RelationshipType.mother, Gender.female): RelationshipType.daughter,
            (RelationshipType.spouse, Gender.male): RelationshipType.spouse,
            (RelationshipType.spouse, Gender.female): RelationshipType.spouse,
            (RelationshipType.partner, Gender.male): RelationshipType.partner,
            (RelationshipType.partner, Gender.female): RelationshipType.partner,
            (RelationshipType.brother, Gender.male): RelationshipType.brother,
            (RelationshipType.brother, Gender.female): RelationshipType.sister,
            (RelationshipType.sister, Gender.male): RelationshipType.brother,
            (RelationshipType.sister, Gender.female): RelationshipType.sister,
        }
        return reverse_map.get((rel_type, gender))

    @staticmethod
    def build_tree(
            db: Session,
            family_id: int,
            root_member_id: Optional[int] = None,
            include_inactive: bool = False,
            max_depth: int = 10
    ) -> Dict:
        """
        Построить семейное дерево в формате nodes и edges
        """
        # Проверяем существование семьи
        if not family_crud.get_family_by_id(db, family_id):
            raise ValueError("Семья не найдена")

        # Базовый запрос для членов семьи
        query = db.query(FamilyMember).filter(FamilyMember.family_id == family_id)

        if not include_inactive:
            query = query.filter(FamilyMember.is_active == True)

        members = query.all()

        if not members:
            return {"nodes": [], "edges": [], "root_id": None}

        # Если корень не указан, берем первого активного члена или первого в списке
        if root_member_id:
            root = next((m for m in members if m.id == root_member_id), None)
            if not root:
                raise ValueError("Корневой член семьи не найден")
        else:
            root = next((m for m in members if m.is_active), members[0])

        # Строим граф связей
        member_ids = {m.id for m in members}

        # Получаем все связи между членами семьи
        relationships = db.query(Relationship).filter(
            Relationship.from_member_id.in_(member_ids),
            Relationship.to_member_id.in_(member_ids)
        ).all()

        # Формируем структуру
        nodes = []
        edges = []
        visited = set()

        # BFS для построения дерева
        queue = [(root.id, 0)]  # (member_id, depth)

        while queue:
            current_id, depth = queue.pop(0)

            if current_id in visited or depth > max_depth:
                continue

            visited.add(current_id)

            member = next((m for m in members if m.id == current_id), None)
            if not member:
                continue

            # Добавляем узел
            node_data = {
                "id": member.id,
                "first_name": member.first_name,
                "last_name": member.last_name,
                "patronymic": member.patronymic,
                "birth_date": member.birth_date.isoformat() if member.birth_date else None,
                "death_date": member.death_date.isoformat() if member.death_date else None,
                "gender": member.gender.value if member.gender else None,
                "photo_url": None,  # TODO: добавить фото если есть
                "is_active": member.is_active,
                "is_admin": member.is_admin,
                "depth": depth,
                "user_id": member.user_id
            }
            nodes.append(node_data)

            # Находим связанных членов
            related_ids = set()
            for rel in relationships:
                if rel.from_member_id == current_id:
                    related_ids.add((rel.to_member_id, rel.relationship_type.value))
                    if rel.to_member_id not in visited:
                        queue.append((rel.to_member_id, depth + 1))
                elif rel.to_member_id == current_id:
                    # Обратная связь (для полноты картины)
                    pass

        # Формируем edges на основе relationships
        for rel in relationships:
            if rel.from_member_id in visited and rel.to_member_id in visited:
                edges.append({
                    "from": rel.from_member_id,
                    "to": rel.to_member_id,
                    "type": rel.relationship_type.value
                })

        return {
            "nodes": nodes,
            "edges": edges,
            "root_id": root.id,
            "family_id": family_id
        }

    @staticmethod
    def get_member_subtree(
            db: Session,
            member_id: int,
            direction: str = "both",  # 'up' (предки), 'down' (потомки), 'both'
            generations: int = 3
    ) -> Dict:
        """Получить поддерево для конкретного члена семьи"""
        member = db.query(FamilyMember).filter(FamilyMember.id == member_id).first()
        if not member:
            raise ValueError("Член семьи не найден")

        visited = set()
        nodes = []
        edges = []

        def traverse(current_id: int, current_gen: int, dir_flag: str):
            if current_id in visited or abs(current_gen) > generations:
                return

            visited.add(current_id)
            current = db.query(FamilyMember).filter(FamilyMember.id == current_id).first()
            if not current:
                return

            nodes.append({
                "id": current.id,
                "first_name": current.first_name,
                "last_name": current.last_name,
                "birth_date": current.birth_date.isoformat() if current.birth_date else None,
                "gender": current.gender.value if current.gender else None,
                "generation": current_gen
            })

            # Получаем связи
            if dir_flag in ['down', 'both']:
                # Дети (исходящие связи типа father/mother ведут к детям?
                # Нужно смотреть на логику: from_member -> to_member с типом son/daughter означает,
                # что to_member является сыном/дочерью from_member)
                children_rels = db.query(Relationship).filter(
                    Relationship.from_member_id == current_id,
                    Relationship.relationship_type.in_([RelationshipType.son, RelationshipType.daughter])
                ).all()

                for rel in children_rels:
                    edges.append({"from": current_id, "to": rel.to_member_id, "type": rel.relationship_type.value})
                    traverse(rel.to_member_id, current_gen + 1, dir_flag)

            if dir_flag in ['up', 'both']:
                # Родители (входящие связи типа son/daughter означают, что from_member - ребенок current)
                # или исходящие father/mother
                parent_rels_out = db.query(Relationship).filter(
                    Relationship.from_member_id == current_id,
                    Relationship.relationship_type.in_([RelationshipType.father, RelationshipType.mother])
                ).all()

                for rel in parent_rels_out:
                    edges.append({"from": current_id, "to": rel.to_member_id, "type": rel.relationship_type.value})
                    traverse(rel.to_member_id, current_gen - 1, dir_flag)

                # Также ищем входящие связи как ребенок
                parent_rels_in = db.query(Relationship).filter(
                    Relationship.to_member_id == current_id,
                    Relationship.relationship_type.in_([RelationshipType.son, RelationshipType.daughter])
                ).all()

                for rel in parent_rels_in:
                    if rel.from_member_id not in visited:
                        edges.append(
                            {"from": rel.from_member_id, "to": current_id, "type": rel.relationship_type.value})
                        traverse(rel.from_member_id, current_gen - 1, dir_flag)

        traverse(member_id, 0, direction)

        return {
            "nodes": nodes,
            "edges": edges,
            "center_id": member_id
        }

    @staticmethod
    def search_members(
            db: Session,
            family_id: int,
            query: str,
            search_inactive: bool = False,
            birth_date_from: Optional[datetime] = None,
            birth_date_to: Optional[datetime] = None
    ) -> List[Dict]:
        """Поиск членов семьи по критериям"""
        db_query = db.query(FamilyMember).filter(FamilyMember.family_id == family_id)

        if not search_inactive:
            db_query = db_query.filter(FamilyMember.is_active == True)

        # Поиск по имени/фамилии/отчеству
        if query:
            search_filter = or_(
                FamilyMember.first_name.ilike(f"%{query}%"),
                FamilyMember.last_name.ilike(f"%{query}%"),
                FamilyMember.patronymic.ilike(f"%{query}%")
            )
            db_query = db_query.filter(search_filter)

        # Фильтр по датам рождения
        if birth_date_from:
            db_query = db_query.filter(FamilyMember.birth_date >= birth_date_from)
        if birth_date_to:
            db_query = db_query.filter(FamilyMember.birth_date <= birth_date_to)

        members = db_query.all()

        result = []
        for member in members:
            result.append({
                "id": member.id,
                "first_name": member.first_name,
                "last_name": member.last_name,
                "patronymic": member.patronymic,
                "birth_date": member.birth_date.isoformat() if member.birth_date else None,
                "death_date": member.death_date.isoformat() if member.death_date else None,
                "gender": member.gender.value if member.gender else None,
                "is_active": member.is_active,
                "user_id": member.user_id
            })

        return result

    @staticmethod
    def get_available_roots(db: Session, family_id: int) -> List[Dict]:
        """Получить список доступных корней (основ) для дерева"""
        members = db.query(FamilyMember).filter(
            FamilyMember.family_id == family_id,
            FamilyMember.is_active == True
        ).all()

        # Сортируем: сначала админы, потом по фамилии
        sorted_members = sorted(
            members,
            key=lambda x: (not x.is_admin, x.last_name, x.first_name)
        )

        return [
            {
                "id": m.id,
                "name": f"{m.last_name} {m.first_name} {m.patronymic or ''}".strip(),
                "birth_date": m.birth_date.isoformat() if m.birth_date else None,
                "is_admin": m.is_admin
            }
            for m in sorted_members
        ]

    @staticmethod
    def delete_relationship(db: Session, relationship_id: int, user_id: int) -> bool:
        """Удалить связь между членами семьи"""
        rel = db.query(Relationship).filter(Relationship.id == relationship_id).first()
        if not rel:
            return False

        # Проверяем права (админ семьи или создатель связи - если будем хранить created_by)
        # Пока просто проверяем, что пользователь - член семьи
        from_member = db.query(FamilyMember).filter(FamilyMember.id == rel.from_member_id).first()
        if not from_member:
            return False

        # Проверка прав: админ семьи или связанный пользователь
        is_admin = family_crud.is_family_admin(db, user_id, from_member.family_id)
        is_self = from_member.user_id == user_id

        if not (is_admin or is_self):
            raise ValueError("Нет прав на удаление связи")

        db.delete(rel)
        db.commit()
        return True


tree_crud = TreeCRUD()