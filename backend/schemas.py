"""
Pydantic 数据模型
用于 API 请求和响应的数据验证
"""
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel


# ============ 标签 ============
class TagBase(BaseModel):
    name: str
    color: Optional[str] = "#3B82F6"


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None


class Tag(TagBase):
    id: int
    card_count: Optional[int] = 0

    class Config:
        from_attributes = True


class TagMerge(BaseModel):
    source_tag_ids: List[int]  # 要合并的标签ID
    new_name: str  # 合并后的新名称


# ============ 卡片 ============
class CardBase(BaseModel):
    question: str
    answer: str


class CardCreate(CardBase):
    tag_ids: Optional[List[int]] = []


class CardUpdate(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None
    tag_ids: Optional[List[int]] = None
    is_weak: Optional[bool] = None
    created_at: Optional[str] = None  # 格式: YYYY-MM-DD


class Card(CardBase):
    id: int
    image_path: Optional[str] = None
    audio_path: Optional[str] = None
    created_at: datetime
    is_weak: bool
    current_stage: int
    next_review: Optional[date] = None
    completed: bool
    tags: List[Tag] = []

    class Config:
        from_attributes = True


class CardBrief(BaseModel):
    """卡片简要信息，用于列表展示"""
    id: int
    question: str
    is_weak: bool
    current_stage: int
    next_review: Optional[date] = None
    tags: List[Tag] = []


# ============ 复习 ============
class ReviewAction(BaseModel):
    card_id: int
    mastered: bool  # 是否掌握


class ReviewHistory(BaseModel):
    id: int
    card_id: int
    reviewed_at: datetime
    stage: int
    mastered: bool


class TodayReviewStats(BaseModel):
    total: int  # 今日总复习数
    completed: int  # 已完成数
    remaining: int  # 剩余数


# ============ 批量操作 ============
class BatchMoveCards(BaseModel):
    card_ids: List[int]
    tag_ids: List[int]  # 移动到这些标签


class BatchDeleteCards(BaseModel):
    card_ids: List[int]


# ============ 认证 ============
class LoginRequest(BaseModel):
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ============ 导入导出 ============
class ExportFormat(BaseModel):
    format: str = "csv"  # csv 或 json


class ImportResult(BaseModel):
    success: bool
    cards_imported: int
    tags_imported: int
    errors: List[str] = []
