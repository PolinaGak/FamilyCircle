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
            current_user_id: int,
            root_member_id: Optional[int] = None,
            include_inactive: bool = False,
            max_depth: int = 10,
    ) -> Dict:
        """
        Построить семейное дерево с правильным расчетом поколений (generation)
        """
        if not family_crud.get_family_by_id(db, family_id):
            raise ValueError("Семья не найдена")

        query = db.query(FamilyMember).filter(FamilyMember.family_id == family_id)
        if not include_inactive:
            query = query.filter(FamilyMember.is_active == True)

        members_list = query.all()
        members = {m.id: m for m in members_list}

        if not members:
            return {"nodes": [], "edges": [], "family_units": [], "root_id": None, "family_id": family_id}

        # Определяем корень
        if root_member_id:
            root = members.get(root_member_id)
            if not root:
                raise ValueError("Корневой член семьи не найден")
        else:
            root = next((m for m in members.values() if m.user_id == current_user_id), None)
            if not root:
                root = next((m for m in members.values() if m.is_active), None)
            if not root:
                root = next(iter(members.values()), None)

        # Получаем все связи
        member_ids = set(members.keys())
        relationships = db.query(Relationship).filter(
            Relationship.from_member_id.in_(member_ids),
            Relationship.to_member_id.in_(member_ids)
        ).all()

        # Строим карты связей
        partners_map = {m_id: set() for m_id in member_ids}  # партнеры
        child_to_parents = {m_id: [] for m_id in member_ids}  # ребенок -> родители
        parent_to_children = {m_id: [] for m_id in member_ids}  # родитель -> дети

        for rel in relationships:
            if rel.relationship_type in [RelationshipType.spouse, RelationshipType.partner]:
                partners_map[rel.from_member_id].add(rel.to_member_id)
                partners_map[rel.to_member_id].add(rel.from_member_id)  # двусторонняя связь

            elif rel.relationship_type in [RelationshipType.son, RelationshipType.daughter]:
                # from = parent, to = child
                child_to_parents[rel.to_member_id].append(rel.from_member_id)
                parent_to_children[rel.from_member_id].append(rel.to_member_id)

            elif rel.relationship_type in [RelationshipType.father, RelationshipType.mother]:
                # from = child, to = parent
                child_to_parents[rel.from_member_id].append(rel.to_member_id)
                parent_to_children[rel.to_member_id].append(rel.from_member_id)

        # Расчет generation (поколения) относительно корня
        generation_map = {}

        # BFS очередь: (member_id, generation)
        from collections import deque
        queue = deque()

        # Начинаем с корня
        generation_map[root.id] = 0
        queue.append((root.id, 0))

        # Обрабатываем очередь
        while queue:
            current_id, current_gen = queue.popleft()

            # 1. Обрабатываем партнеров (они того же поколения)
            for partner_id in partners_map[current_id]:
                if partner_id not in generation_map:
                    generation_map[partner_id] = current_gen
                    queue.append((partner_id, current_gen))
                elif generation_map[partner_id] != current_gen:
                    # Если уже есть другое значение, синхронизируем (берем минимум по модулю или текущее)
                    # Для семейного дерева партнеры всегда одного поколения
                    pass

            # 2. Обрабатываем родителей (поколение -1)
            for parent_id in child_to_parents[current_id]:
                if parent_id not in generation_map:
                    generation_map[parent_id] = current_gen - 1
                    queue.append((parent_id, current_gen - 1))

            # 3. Обрабатываем детей (поколение +1)
            for child_id in parent_to_children[current_id]:
                if child_id not in generation_map:
                    generation_map[child_id] = current_gen + 1
                    queue.append((child_id, current_gen + 1))

            # 4. Обрабатываем братьев/сестер (те же родители = то же поколение)
            # Находим всех детей наших родителей
            for parent_id in child_to_parents[current_id]:
                for sibling_id in parent_to_children[parent_id]:
                    if sibling_id not in generation_map:
                        generation_map[sibling_id] = current_gen
                        queue.append((sibling_id, current_gen))

        # Если остались несвязанные члены (нет пути от корня), назначаем им поколение 0 или пропускаем
        for m_id in members:
            if m_id not in generation_map:
                generation_map[m_id] = 0  # или можно не включать в дерево

        # Формируем family_units (семейные ячейки)
        family_units = []
        processed_pairs = set()

        # Создаем ячейки для родительских пар
        for child_id, parent_ids in child_to_parents.items():
            # КРИТИЧНО: пропускаем тех, у кого нет родителей в базе
            if not parent_ids:
                continue

            # Находим всех родителей и их партнеров
            all_parents = set(parent_ids)
            for pid in parent_ids:
                all_parents.update(partners_map[pid])

            # Проверяем, что это реальная пара (есть связь spouse/partner или общие дети)
            parents_list = sorted(all_parents)
            pair_key = tuple(parents_list)

            if pair_key not in processed_pairs:
                processed_pairs.add(pair_key)

                # Находим детей этой пары (все, у кого оба родителя в списке, или один если одиночка)
                children_of_pair = []
                for cid, c_parents in child_to_parents.items():
                    # КРИТИЧНО: пропускаем тех, у кого нет родителей в базе
                    if not c_parents:
                        continue

                    # Проверяем, что все родители ребенка входят в текущую группу all_parents
                    if all(p in all_parents for p in c_parents):
                        children_of_pair.append(cid)

                family_units.append({
                    "id": f"FU_{'_'.join(map(str, parents_list))}",
                    "parents": list(parents_list),
                    "children": sorted(children_of_pair),
                    "type": "nuclear_family" if len(parents_list) == 2 else "single_parent"
                })

        # Формируем nodes
        nodes = []
        for m_id, member in members.items():
            gen = generation_map.get(m_id, 0)
            nodes.append({
                "id": member.id,
                "first_name": member.first_name,
                "last_name": member.last_name,
                "patronymic": member.patronymic,
                "birth_date": member.birth_date.isoformat() if member.birth_date else None,
                "death_date": member.death_date.isoformat() if member.death_date else None,
                "gender": member.gender.value if member.gender else None,
                "is_active": member.is_active,
                "is_admin": member.is_admin,
                "generation": gen,
                "partners": list(partners_map.get(m_id, [])),
                "user_id": member.user_id
            })

        # Формируем edges для фронта (можно оставить как есть)
        edges = [{"from": r.from_member_id, "to": r.to_member_id, "type": r.relationship_type.value}
                 for r in relationships]

        return {
            "nodes": nodes,
            "edges": edges,
            "family_units": family_units,
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

    @staticmethod
    def get_member_relatives(db: Session, member_id: int) -> Dict:
        """
        Получить ближайших родственников по категориям (родители, дети, супруги, братья/сестры).
        Используется для получения списка родителей при добавлении братьев/сестер.
        """
        member = db.query(FamilyMember).filter(FamilyMember.id == member_id).first()
        if not member:
            raise ValueError("Член семьи не найден")

        parents = []
        children = []
        spouses = []
        siblings = []

        # Исходящие связи (member -> other)
        outgoing = db.query(Relationship).filter(Relationship.from_member_id == member_id).all()

        # Входящие связи (other -> member)
        incoming = db.query(Relationship).filter(Relationship.to_member_id == member_id).all()

        # Обрабатываем исходящие связи
        for rel in outgoing:
            target = db.query(FamilyMember).filter(FamilyMember.id == rel.to_member_id).first()
            if not target:
                continue

            if rel.relationship_type in [RelationshipType.father, RelationshipType.mother]:
                # member указывает на father/mother (значит target - родитель)
                parents.append({
                    "id": target.id,
                    "first_name": target.first_name,
                    "last_name": target.last_name,
                    "patronymic": target.patronymic,
                    "gender": target.gender.value if target.gender else None,
                    "relationship_type": rel.relationship_type.value
                })
            elif rel.relationship_type in [RelationshipType.son, RelationshipType.daughter]:
                # member указывает на son/daughter (значит target - ребенок)
                children.append({
                    "id": target.id,
                    "first_name": target.first_name,
                    "last_name": target.last_name,
                    "patronymic": target.patronymic,
                    "gender": target.gender.value if target.gender else None,
                })
            elif rel.relationship_type in [RelationshipType.spouse, RelationshipType.partner]:
                spouses.append({
                    "id": target.id,
                    "first_name": target.first_name,
                    "last_name": target.last_name,
                })
            elif rel.relationship_type in [RelationshipType.brother, RelationshipType.sister]:
                siblings.append({
                    "id": target.id,
                    "first_name": target.first_name,
                    "last_name": target.last_name,
                })

        # Обрабатываем входящие связи (для случаев, когда связь хранится как parent -> child)
        for rel in incoming:
            source = db.query(FamilyMember).filter(FamilyMember.id == rel.from_member_id).first()
            if not source:
                continue

            # source -> member с типом son/daughter означает, что source - родитель для member
            if rel.relationship_type in [RelationshipType.son, RelationshipType.daughter]:
                if not any(p["id"] == source.id for p in parents):
                    parent_type = RelationshipType.father if source.gender == Gender.male else RelationshipType.mother
                    parents.append({
                        "id": source.id,
                        "first_name": source.first_name,
                        "last_name": source.last_name,
                        "patronymic": source.patronymic,
                        "gender": source.gender.value if source.gender else None,
                        "relationship_type": parent_type.value
                    })

            # source -> member с типом father/mother означает, что source - ребенок для member
            elif rel.relationship_type in [RelationshipType.father, RelationshipType.mother]:
                if not any(c["id"] == source.id for c in children):
                    children.append({
                        "id": source.id,
                        "first_name": source.first_name,
                        "last_name": source.last_name,
                    })

        return {
            "parents": parents,
            "children": children,
            "spouses": spouses,
            "siblings": siblings
        }


tree_crud = TreeCRUD()