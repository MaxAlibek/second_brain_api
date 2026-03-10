"""
Роутер для Механизма принятия решений (Decision Engine).
Позволяет создавать Решения, добавлять Критерии (с весами), Варианты,
выставлять Оценки и запускать математический расчет лучшего выбора.
Использует алгоритм Weighted Scoring: оценка * вес критерия = итоговый балл.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db.database import get_db
from app.db.models import User
from app.core.security import get_current_user

from app.schemas.decision import (
    DecisionCreate, DecisionOut, 
    CriterionCreate, CriterionOut, 
    OptionCreate, OptionOut, 
    OptionScoreCreate, OptionScoreOut,
    DecisionResultOut
)
from app.services import decision_service

# Роутер для Решений (/decisions)
router = APIRouter(prefix="/decisions", tags=["Decision Engine"])

# =====================================================================
# РАБОТА С САМИМИ РЕШЕНИЯМИ (DECISIONS)
# =====================================================================

@router.post("/", response_model=DecisionOut, status_code=status.HTTP_201_CREATED)
async def create_decision(
    decision: DecisionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Создает новое Решение (Decision). 
    Вы можете передать сразу списки 'criteria' и 'options' внутри JSON, и они создадутся АТОМАРНО вместе с Решением.
    """
    return await decision_service.create_decision(db, current_user.id, decision)


@router.get("/", response_model=List[DecisionOut])
async def get_decisions(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получить список всех Решений текущего пользователя."""
    return await decision_service.get_user_decisions(db, current_user.id, skip, limit)


@router.get("/{decision_id}", response_model=DecisionOut)
async def get_decision(
    decision_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получить детальную информацию об ОДНОМ Решении (со всеми вложенными Критериями, Вариантами и Оценками)."""
    decision = await decision_service.get_decision_by_id(db, decision_id, current_user.id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    return decision


# =====================================================================
# ДОБАВЛЕНИЕ КРИТЕРИЕВ И ВАРИАНТОВ В УЖЕ СОЗДАННОЕ РЕШЕНИЕ
# =====================================================================

@router.post("/{decision_id}/criteria", response_model=CriterionOut, status_code=status.HTTP_201_CREATED)
async def add_criterion(
    decision_id: int,
    criterion: CriterionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Добавить новый Критерий оценки (и его вес 1-10) к существующему Решению."""
    return await decision_service.add_criterion(db, decision_id, current_user.id, criterion)


@router.post("/{decision_id}/options", response_model=OptionOut, status_code=status.HTTP_201_CREATED)
async def add_option(
    decision_id: int,
    option: OptionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Добавить новый Вариант выбора к существующему Решению."""
    return await decision_service.add_option(db, decision_id, current_user.id, option)


# =====================================================================
# ВЫСТАВЛЕНИЕ ОЦЕНОК И МАТЕМАТИКА (RESULTS)
# =====================================================================

@router.post("/{decision_id}/scores", response_model=OptionScoreOut, status_code=status.HTTP_201_CREATED)
async def submit_score(
    decision_id: int,
    score: OptionScoreCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Выставить оценку (от 1 до 10) конкретному Варианту по конкретному Критерию.
    Если оценка уже стоит, она будет перезаписана (обновлена).
    decision_id в пути нужен только для красоты URL в API, валидация все равно идет по option_id и criterion_id.
    """
    return await decision_service.submit_score(db, current_user.id, score)


@router.get("/{decision_id}/results", response_model=DecisionResultOut)
async def get_decision_results(
    decision_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Запуск 'Магии' принятия решений!
    Перемножает оценки на вес критериев, складывает их и выдает отсортированный ТОП победителей.
    Внимание: выдаст 400 Bad Request, если не все варианты оценены по всем критериям (защита Целостности Данных).
    """
    return await decision_service.calculate_results(db, decision_id, current_user.id)
