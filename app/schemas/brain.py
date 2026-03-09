from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.schemas.tag import TagOut

# =====================================================================
# СХЕМЫ ДЛЯ "SECOND BRAIN" (ЗАМЕТОК)
# Эти классы используют Pydantic для строгой проверки данных (валидации).
# Если пользователь пришлет текст вместо числа или забудет обязательное
# поле - Pydantic сам выдаст красивую ошибку 422 Unprocessable Entity.
# =====================================================================

class BrainEntryBase(BaseModel):
    """
    Базовая схема, содержащая общие поля для создания и чтения заметки.
    """
    # Заголовок заметки. Максимум 255 символов.
    title: Optional[str] = Field(None, max_length=255, description="Заголовок мысли/заметки (опционально)")
    
    # Текст самой заметки. Это обязательное поле (нет None).
    content: str = Field(..., description="Основной текст мысли или идея")
    
    # Категория, например 'Work', 'Life', 'Ideas'
    category: Optional[str] = Field(None, max_length=100, description="Категория заметки (опционально)")
    
    # Краткая выжимка (в будущем её может генерировать ИИ-дворецкий)
    summary: Optional[str] = Field(None, description="Краткое содержание (сгенерированное ИИ или вручную)")


class BrainEntryCreate(BrainEntryBase):
    """
    Схема для СОЗДАНИЯ новой заметки (POST запрос).
    Мы наследуем всё из BrainEntryBase (title, content, category, summary).
    Дополнительных полей при создании от пользователя нам не нужно
    (ID и дата создадутся в базе данных автоматически).
    """
    pass


class BrainEntryUpdate(BaseModel):
    """
    Схема для ОБНОВЛЕНИЯ заметки (PUT запрос).
    В отличие от базовой схемы, при редактировании пользователь 
    может обновить только часть полей, поэтому все поля опциональны (Optional).
    """
    title: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    summary: Optional[str] = None


class BrainEntryOut(BrainEntryBase):
    """
    Схема для ВОЗВРАТА заметки пользователю в ответ (Output).
    Здесь уже появляются поля, которые сгенерировала наша база данных (id, created_at, user_id).
    """
    id: int = Field(..., description="Уникальный номер заметки в базе данных")
    created_at: datetime = Field(..., description="Время создания")
    user_id: int = Field(..., description="ID пользователя - владельца заметки")
    
    # Список тегов, прикрепленных к этой заметке
    tags: List[TagOut] = Field(default=[], description="Список прикрепленных тегов")

    class Config:
        # Это очень важная настройка! 
        # Она говорит Pydantic'у: "Ты можешь читать данные прямо из
        # объектов базы данных SQLAlchemy (ORM), а не только из обычных словарей".
        from_attributes = True
