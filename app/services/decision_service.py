from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from fastapi import HTTPException, status

from app.db.models import Decision, Criterion, Option, OptionScore
from app.schemas.decision import DecisionCreate, CriterionCreate, OptionCreate, OptionScoreCreate

# =====================================================================
# ДОСТУПЫ И CRUD (ЧТЕНИЕ И СОЗДАНИЕ В БД)
# =====================================================================

async def create_decision(db: AsyncSession, user_id: int, decision_data: DecisionCreate) -> Decision:
    """
    Создает новое Решение со всеми связанными Критериями и Вариантами в одной ТРАНЗАКЦИИ.
    Мы используем атомарный коммит: если что-то упадет, откатится всё.
    """
    try:
        # 1. Сначала создаем "Контейнер" (Decision)
        new_decision = Decision(
            title=decision_data.title,
            description=decision_data.description,
            user_id=user_id
        )
        db.add(new_decision)
        await db.flush() # Получаем ID Решения, но пока НЕ фиксируем в базе намертво

        # 2. Создаем связанные критерии, если они были переданы
        if decision_data.criteria:
            for crit in decision_data.criteria:
                db_crit = Criterion(
                    name=crit.name,
                    weight=crit.weight,
                    decision_id=new_decision.id
                )
                db.add(db_crit)

        # 3. Создаем связанные варианты, если они были переданы
        if decision_data.options:
            for opt in decision_data.options:
                db_opt = Option(
                    name=opt.name,
                    decision_id=new_decision.id
                )
                db.add(db_opt)

        # 4. Фиксируем всю пачку сразу (АТОМАРНОСТЬ)
        await db.commit()
        
        # Загружаем готовый объект вместе с опциями и критериями (N+1 Защита)
        return await get_decision_by_id(db, new_decision.id, user_id)
        
    except Exception as e:
        await db.rollback() # Если где-то ошибка, отменяем все шаги (и Decision, и Criteria, и Options не создадутся)
        raise e


async def get_user_decisions(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100) -> List[Decision]:
    """Возвращает список всех решений юзера."""
    stmt = (
        select(Decision)
        .where(Decision.user_id == user_id)
        .order_by(Decision.created_at.desc())
        .offset(skip).limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_decision_by_id(db: AsyncSession, decision_id: int, user_id: int) -> Optional[Decision]:
    """
    Получить ОДНО решение.
    ИЗОЛЯЦИЯ: Строго проверяем user_id.
    N+1 ЗАЩИТА: делаем selectinload для 'criteria' и 'options'.
    """
    stmt = (
        select(Decision)
        .options(
            selectinload(Decision.criteria),
            selectinload(Decision.options).selectinload(Option.scores) # Подгружаем вместе с вариантами их оценки
        )
        .where(Decision.id == decision_id, Decision.user_id == user_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# =====================================================================
# ДОБАВЛЕНИЕ ОДИНОЧНЫХ КРИТЕРИЕВ И ВАРИАНТОВ (Уже после создания Решения)
# =====================================================================

async def add_criterion(db: AsyncSession, decision_id: int, user_id: int, crit_data: CriterionCreate) -> Criterion:
    # ИЗОЛЯЦИЯ: Сначала проверяем, что Решение принадлежит юзеру
    decision = await get_decision_by_id(db, decision_id, user_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    new_crit = Criterion(name=crit_data.name, weight=crit_data.weight, decision_id=decision_id)
    db.add(new_crit)
    await db.commit()
    await db.refresh(new_crit)
    return new_crit


async def add_option(db: AsyncSession, decision_id: int, user_id: int, opt_data: OptionCreate) -> Option:
    decision = await get_decision_by_id(db, decision_id, user_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    new_opt = Option(name=opt_data.name, decision_id=decision_id)
    db.add(new_opt)
    await db.commit()
    await db.refresh(new_opt)
    return new_opt


# =====================================================================
# ВЫСТАВЛЕНИЕ ОЦЕНОК И МАГИЯ ПОДСЧЕТА (АЛГОРИТМ)
# =====================================================================

async def submit_score(db: AsyncSession, user_id: int, score_data: OptionScoreCreate) -> OptionScore:
    """Выставить оценку (score от 1 до 10) для варианта по определенному критерию"""
    
    # 1. Мы должны убедиться, что Вариант (Option) и Критерий (Criterion) принадлежат одному юзеру
    stmt_opt = select(Option).join(Decision).where(Option.id == score_data.option_id, Decision.user_id == user_id)
    result_opt = await db.execute(stmt_opt)
    if not result_opt.scalar_one_or_none():
         raise HTTPException(status_code=404, detail="Option not found or access denied")
         
    stmt_crit = select(Criterion).join(Decision).where(Criterion.id == score_data.criterion_id, Decision.user_id == user_id)
    result_crit = await db.execute(stmt_crit)
    if not result_crit.scalar_one_or_none():
         raise HTTPException(status_code=404, detail="Criterion not found or access denied")

    # 2. Проверяем, стояла ли уже оценка. Если да - апдейтим, если нет - создаем
    stmt_existing = select(OptionScore).where(
        OptionScore.option_id == score_data.option_id, 
        OptionScore.criterion_id == score_data.criterion_id
    )
    result_existing = await db.execute(stmt_existing)
    existing_score = result_existing.scalar_one_or_none()

    if existing_score:
        existing_score.score = score_data.score
        db_score = existing_score
    else:
        db_score = OptionScore(
            score=score_data.score,
            option_id=score_data.option_id,
            criterion_id=score_data.criterion_id
        )
        db.add(db_score)

    await db.commit()
    await db.refresh(db_score)
    return db_score


async def calculate_results(db: AsyncSession, decision_id: int, user_id: int) -> dict:
    """
    МАГИЯ РАСЧЕТОВ (Weighted Scoring Model)
    1. Проверяет Целостность Данных (все ли оценено?)
    2. Умножает балл на вес критерия.
    3. Складывает баллы для каждого варианта.
    4. Строит массив от победителя (по убыванию баллов).
    """
    decision = await get_decision_by_id(db, decision_id, user_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    if not decision.criteria or not decision.options:
         raise HTTPException(status_code=400, detail="Cannot calculate results: missing criteria or options.")

    # ЦЕЛОСТНОСТЬ ДАННЫХ: проверяем формулу "Кол-во вариантов * Кол-во критериев"
    required_scores_count = len(decision.options) * len(decision.criteria)
    
    # Подсчитываем сколько всего оценок проставлено у всех вариантов этого решения
    actual_scores_count = sum(len(opt.scores) for opt in decision.options)

    if actual_scores_count < required_scores_count:
        raise HTTPException(
            status_code=400, 
            detail=f"Incomplete data. You need to assign {required_scores_count} scores, but only {actual_scores_count} were found. Please evaluate all options against all criteria."
        )

    # Словарь "быстрого доступа" для получения веса и названия критерия по его ID
    criteria_map = {c.id: {"weight": c.weight, "name": c.name} for c in decision.criteria}

    ranking = []
    
    # Считаем
    for opt in decision.options:
        total = 0
        breakdown = {}
        for score_obj in opt.scores:
            crit_info = criteria_map[score_obj.criterion_id]
            
            # ФОРМУЛА: Балл Варианта * Вес Критерия
            points = score_obj.score * crit_info["weight"]
            
            total += points
            breakdown[crit_info["name"]] = points
            
        ranking.append({
            "option_id": opt.id,
            "option_name": opt.name,
            "total_score": total,
            "breakdown": breakdown
        })

    # Сортируем по убыванию (от самого крутого к самому отстойному)
    ranking.sort(key=lambda x: x["total_score"], reverse=True)

    winner = ranking[0] if ranking else None

    # Возвращаем JSON совместимый со схемой DecisionResultOut
    return {
        "decision_id": decision.id,
        "decision_title": decision.title,
        "winner": winner,
        "ranking": ranking
    }
