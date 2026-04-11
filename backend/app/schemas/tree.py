from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List, Dict


class TreeNode(BaseModel):
    id: int
    first_name: str
    last_name: str
    patronymic: Optional[str] = None
    birth_date: Optional[str] = None
    death_date: Optional[str] = None
    gender: Optional[str] = None
    photo_url: Optional[str] = None
    is_active: bool
    is_admin: bool
    depth: int = 0
    user_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class TreeEdge(BaseModel):
    from_id: int = Field(..., alias="from")
    to_id: int = Field(..., alias="to")
    type: str

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TreeResponse(BaseModel):
    nodes: List[TreeNode]
    edges: List[TreeEdge]
    root_id: Optional[int]
    family_id: int

    model_config = ConfigDict(from_attributes=True)


class TreeSettings(BaseModel):
    root_member_id: Optional[int] = None
    include_inactive: bool = False
    max_depth: int = Field(10, ge=1, le=20)
    show_dates: bool = True
    show_photos: bool = True

    model_config = ConfigDict(from_attributes=True)


class TreeSearchQuery(BaseModel):
    query: Optional[str] = Field(None, description="Поиск по имени/фамилии")
    search_inactive: bool = False
    birth_date_from: Optional[datetime] = None
    birth_date_to: Optional[datetime] = None


class TreeSearchResult(BaseModel):
    id: int
    first_name: str
    last_name: str
    patronymic: Optional[str] = None
    birth_date: Optional[str] = None
    death_date: Optional[str] = None
    gender: Optional[str] = None
    is_active: bool
    user_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class SubtreeRequest(BaseModel):
    member_id: int
    direction: str = Field("both", pattern="^(up|down|both)$")
    generations: int = Field(3, ge=1, le=10)


class RootInfo(BaseModel):
    id: int
    name: str
    birth_date: Optional[str] = None
    is_admin: bool

    model_config = ConfigDict(from_attributes=True)



class PDFMetadata(BaseModel):
    family_name: str
    generated_at: str
    total_members: int
    root_person: Optional[TreeNode] = None
    include_contacts: bool = False


class TreeStatistics(BaseModel):
    total_members: int
    active_members: int
    inactive_members: int
    by_gender: Dict[str, int]
    oldest_member_id: Optional[int] = None
    youngest_member_id: Optional[int] = None


class GenerationGroup(BaseModel):
    level: int
    title: str
    members: List[TreeNode]


class PDFExportData(BaseModel):
    """Данные для генерации PDF на фронтенде"""
    meta: PDFMetadata
    statistics: TreeStatistics
    generations: List[GenerationGroup]
    members_flat: List[TreeNode]
    relationships: List[TreeEdge]

    model_config = ConfigDict(from_attributes=True)


class ExportFormat(BaseModel):
    """Параметры экспорта"""
    format: str = Field("pdf", pattern="^(pdf|json|gedcom)$")
    root_member_id: Optional[int] = None
    include_inactive: bool = False
    include_contacts: bool = Field(False, description="Включить контактные данные (только для PDF)")
    include_statistics: bool = True