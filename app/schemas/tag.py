from pydantic import BaseModel, Field
from typing import Optional

# =====================================================================
# СХЕМЫ ДЛЯ "TAG" (ТЕГОВ)
# Теги прикрепляются к заметкам (BrainEntry).
# =====================================================================

class TagBase(BaseModel):
    """
    Базовая схема тега.
    Параметры min_length и max_length защищают от пустых или слишком длинных тегов.
    """
    name: str = Field(..., min_length=1, max_length=50, description="Название тега (например: Идея, Работа)")


class TagCreate(TagBase):
    """
    Схема для СОЗДАНИЯ нового тега.
    """
    pass


class TagUpdate(TagBase):
    """
    Схема для ОБНОВЛЕНИЯ тега.
    Все поля делаем опциональными на будущее.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=50)


class TagOut(TagBase):
    """
    Схема для ВОЗВРАТА тега пользователю.
    Содержит ID тега и ID владельца.
    """
    id: int = Field(..., description="Уникальный номер тега")
    user_id: int = Field(..., description="ID владельца тега")

    # entry_count можно будет добавить позже для аналитики
    # entry_count: Optional[int] = None

    class Config:
        from_attributes = True
