from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime

# ==========================================
# Базовые классы для OptionScore (Оценки)
# ==========================================
class OptionScoreBase(BaseModel):
    score: int = Field(..., ge=1, le=10, description="Оценка от 1 до 10")

class OptionScoreCreate(OptionScoreBase):
    option_id: int
    criterion_id: int

class OptionScoreOut(OptionScoreBase):
    id: int
    option_id: int
    criterion_id: int
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Базовые классы для Option (Варианты выбора)
# ==========================================
class OptionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)

class OptionCreate(OptionBase):
    pass

class OptionOut(OptionBase):
    id: int
    decision_id: int
    scores: List[OptionScoreOut] = []
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Базовые классы для Criterion (Критерии качества)
# ==========================================
class CriterionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    weight: int = Field(5, ge=1, le=10, description="Важность критерия от 1 до 10")

class CriterionCreate(CriterionBase):
    pass

class CriterionOut(CriterionBase):
    id: int
    decision_id: int
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Базовые классы для Decision (Сам вопрос/Решение)
# ==========================================
class DecisionBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None

class DecisionCreate(DecisionBase):
    # Позволяет клиенту передать сразу критерии и опции при создании (Batch Creation)
    criteria: Optional[List[CriterionCreate]] = []
    options: Optional[List[OptionCreate]] = []

class DecisionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None

class DecisionOut(DecisionBase):
    id: int
    user_id: int
    created_at: datetime
    # При возврате тянем за собой все зависимые данные
    criteria: List[CriterionOut] = []
    options: List[OptionOut] = []
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Формат вывода для Расчета Результатов
# ==========================================
class OptionResult(BaseModel):
    option_id: int
    option_name: str
    total_score: int
    breakdown: dict[str, int] # Как сложился балл: {"Скорость": 18, "Цена": 5}

class DecisionResultOut(BaseModel):
    decision_id: int
    decision_title: str
    winner: Optional[OptionResult]
    ranking: List[OptionResult]
