from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from fastapi import HTTPException, status

from app.db.models import Tag, BrainEntry, BrainEntryTag
from app.schemas.tag import TagCreate


async def create_tag(db: AsyncSession, user_id: int, tag_data: TagCreate) -> Tag:
    """
    Создает новый тег.
    Мы не используем UniqueConstraint для перехвата дубликатов на уровне БД,
    чтобы выдавать понятную ошибку (Хотя UniqueConstraint в базе всё равно есть для гарантии).
    """
    # Сначала проверяем, нет ли уже тега с таким именем у этого пользователя
    stmt = select(Tag).where(Tag.user_id == user_id, Tag.name == tag_data.name)
    result = await db.execute(stmt)
    existing_tag = result.scalar_one_or_none()
    
    if existing_tag:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Tag with this name already exists"
        )

    new_tag = Tag(name=tag_data.name, user_id=user_id)
    db.add(new_tag)
    await db.commit()
    await db.refresh(new_tag)
    
    return new_tag


async def get_user_tags(db: AsyncSession, user_id: int) -> List[Tag]:
    """
    Получить все теги пользователя.
    """
    stmt = select(Tag).where(Tag.user_id == user_id).order_by(Tag.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def link_tag_to_entry(db: AsyncSession, user_id: int, entry_id: int, tag_id: int) -> BrainEntry:
    """
    Прикрепить существующий тег к существующей заметке.
    """
    # 1. Находим заметку (и убеждаемся что она принадлежит юзеру)
    stmt = select(BrainEntry).options(selectinload(BrainEntry.tags)).where(BrainEntry.id == entry_id, BrainEntry.user_id == user_id)
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Заметка не найдена")

    # 2. Находим тег (и убеждаемся что он принадлежит юзеру)
    stmt_tag = select(Tag).where(Tag.id == tag_id, Tag.user_id == user_id)
    result_tag = await db.execute(stmt_tag)
    tag = result_tag.scalar_one_or_none()
    if not tag:
        raise HTTPException(status_code=404, detail="Тег не найден")

    # 3. Прикрепляем, если он еще не прикреплен
    if any(t.id == tag.id for t in entry.tags):
        # Тег уже есть на заметке, ничего не делаем, просто возвращаем заметку
        return entry

    # SQLAlchemy автоматически вставит запись в brain_entry_tags
    entry.tags.append(tag)
    await db.commit()
    
    # 4. Перезагружаем заметку с тегами
    result_reloaded = await db.execute(select(BrainEntry).options(selectinload(BrainEntry.tags)).where(BrainEntry.id == entry_id))
    return result_reloaded.scalar_one()


async def unlink_tag_from_entry(db: AsyncSession, user_id: int, entry_id: int, tag_id: int) -> BrainEntry:
    """
    Открепить тег от заметки.
    """
    # 1. Находим заметку с тегами
    stmt = select(BrainEntry).options(selectinload(BrainEntry.tags)).where(BrainEntry.id == entry_id, BrainEntry.user_id == user_id)
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Заметка не найдена")

    # 2. Ищем тег в списке загруженных тегов
    tag_to_remove = next((t for t in entry.tags if t.id == tag_id), None)
    
    if tag_to_remove:
        # SQLAlchemy автоматически удалит связь из brain_entry_tags!
        entry.tags.remove(tag_to_remove)
        await db.commit()
        
    # 3. Вернуть обновленную заметку
    result_reloaded = await db.execute(select(BrainEntry).options(selectinload(BrainEntry.tags)).where(BrainEntry.id == entry_id))
    return result_reloaded.scalar_one()
