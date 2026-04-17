from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime
from backend.app.crud.tree import tree_crud
from backend.app.crud.family import family_crud
import logging

logger = logging.getLogger(__name__)


class TreeExportService:
    """Сервис для экспорта семейного древа в различные форматы"""

    @staticmethod
    def prepare_pdf_data(
            db: Session,
            family_id: int,
            current_user_id: int,
            root_member_id: Optional[int] = None,
            include_inactive: bool = False,
            include_contacts: bool = False
    ) -> Dict[str, Any]:
        """
        Подготовить данные для генерации PDF на фронтенде.
        Возвращает иерархическую структуру с метаданными.
        """
        family = family_crud.get_family_by_id(db, family_id)
        if not family:
            raise ValueError("Семья не найдена")

        tree_data = tree_crud.build_tree(
            db, family_id, current_user_id, root_member_id, include_inactive, max_depth=15
        )

        generations = TreeExportService._organize_by_generations(tree_data)

        stats = TreeExportService._calculate_stats(tree_data)

        pdf_data = {
            "meta": {
                "family_name": family.name,
                "generated_at": datetime.now().isoformat(),
                "total_members": len(tree_data["nodes"]),
                "root_person": next(
                    (n for n in tree_data["nodes"] if n["id"] == tree_data["root_id"]),
                    None
                ),
                "include_contacts": include_contacts
            },
            "statistics": stats,
            "generations": generations,
            "members_flat": tree_data["nodes"],
            "relationships": tree_data["edges"]
        }

        return pdf_data

    @staticmethod
    def _organize_by_generations(tree_data: Dict) -> List[Dict]:
        """
        Организовать членов семьи по поколениям для иерархического отображения.
        Возвращает список поколений (0 - корневое, 1 - дети, -1 - родители и т.д.)
        """
        nodes_by_id = {n["id"]: n for n in tree_data["nodes"]}
        edges = tree_data["edges"]

        parent_to_children = {}
        child_to_parents = {}

        for edge in edges:
            rel_type = edge["type"]
            from_id = edge["from"]
            to_id = edge["to"]

            if rel_type in ["son", "daughter"]:
                if from_id not in parent_to_children:
                    parent_to_children[from_id] = []
                parent_to_children[from_id].append(to_id)

                if to_id not in child_to_parents:
                    child_to_parents[to_id] = []
                child_to_parents[to_id].append(from_id)

        generations_map = {}
        root_id = tree_data["root_id"]

        if root_id:
            generations_map[root_id] = 0
            TreeExportService._assign_generations_bfs(
                root_id, 0, parent_to_children, child_to_parents, generations_map, set()
            )

        gen_groups = {}
        for member_id, gen in generations_map.items():
            if gen not in gen_groups:
                gen_groups[gen] = []
            member = nodes_by_id.get(member_id)
            if member:
                gen_groups[gen].append(member)

        sorted_gens = sorted(gen_groups.keys(), reverse=True)
        result = []
        for gen_num in sorted_gens:
            result.append({
                "level": gen_num,
                "title": TreeExportService._generation_title(gen_num),
                "members": gen_groups[gen_num]
            })

        return result

    @staticmethod
    def _assign_generations_bfs(
            start_id: int,
            start_gen: int,
            parent_to_children: Dict,
            child_to_parents: Dict,
            generations_map: Dict,
            visited: set
    ):
        """BFS для назначения поколений"""
        from collections import deque
        queue = deque([(start_id, start_gen)])
        visited.add(start_id)

        while queue:
            current_id, current_gen = queue.popleft()

            if current_id in parent_to_children:
                for child_id in parent_to_children[current_id]:
                    if child_id not in visited:
                        generations_map[child_id] = current_gen + 1
                        visited.add(child_id)
                        queue.append((child_id, current_gen + 1))

            if current_id in child_to_parents:
                for parent_id in child_to_parents[current_id]:
                    if parent_id not in visited:
                        generations_map[parent_id] = current_gen - 1
                        visited.add(parent_id)
                        queue.append((parent_id, current_gen - 1))

    @staticmethod
    def _generation_title(level: int) -> str:
        """Название поколения"""
        titles = {
            -3: "Прадеды/Прабабки",
            -2: "Деды/Бабушки",
            -1: "Родители",
            0: "Корневое поколение",
            1: "Дети",
            2: "Внуки/Внучки",
            3: "Правнуки/Правнучки"
        }
        return titles.get(level, f"Поколение {level:+d}")

    @staticmethod
    def _calculate_stats(tree_data: Dict) -> Dict:
        """Статистика по древу"""
        nodes = tree_data["nodes"]
        total = len(nodes)
        if total == 0:
            return {}

        active = sum(1 for n in nodes if n.get("is_active"))
        by_gender = {}
        for n in nodes:
            g = n.get("gender") or "unknown"
            by_gender[g] = by_gender.get(g, 0) + 1

        dates = [(n["id"], n.get("birth_date")) for n in nodes if n.get("birth_date")]
        oldest = min(dates, key=lambda x: x[1]) if dates else None
        youngest = max(dates, key=lambda x: x[1]) if dates else None

        return {
            "total_members": total,
            "active_members": active,
            "inactive_members": total - active,
            "by_gender": by_gender,
            "oldest_member_id": oldest[0] if oldest else None,
            "youngest_member_id": youngest[0] if youngest else None
        }

    @staticmethod
    def export_to_gedcom(db: Session, family_id: int) -> str:
        """
        Экспорт в формат GEDCOM 5.5 (генеалогический стандарт).
        Возвращает строку в формате GEDCOM.
        """
        family = family_crud.get_family_by_id(db, family_id)
        if not family:
            raise ValueError("Семья не найдена")

        members = family_crud.get_family_members(db, family_id)
        lines = [
            "0 HEAD",
            "1 SOUR FamilyCircle",
            "2 VERS 1.0",
            "1 DATE " + datetime.now().strftime("%d %b %Y").upper(),
            "1 GEDC",
            "2 VERS 5.5.1",
            "2 FORM LINEAGE-LINKED",
            "1 CHAR UTF-8",
            "0 @F1@ FAM",
            f"1 NAME {family.name}",
        ]

        for member in members:
            indi_id = f"@I{member.id}@"
            lines.append(f"0 {indi_id} INDI")
            lines.append(f"1 NAME {member.first_name} /{member.last_name}/")
            if member.patronymic:
                lines.append(f"2 GIVN {member.first_name} {member.patronymic}")
            else:
                lines.append(f"2 GIVN {member.first_name}")
            lines.append(f"2 SURN {member.last_name}")

            if member.gender:
                sex = "M" if member.gender.value == "male" else "F"
                lines.append(f"1 SEX {sex}")

            if member.birth_date:
                lines.append(f"1 BIRT")
                lines.append(f"2 DATE {member.birth_date.strftime('%d %b %Y').upper()}")

            if member.death_date:
                lines.append(f"1 DEAT")
                lines.append(f"2 DATE {member.death_date.strftime('%d %b %Y').upper()}")

            lines.append(f"1 FAMS @F1@")

        lines.append("0 TRLR")
        return "\n".join(lines)


tree_export_service = TreeExportService()