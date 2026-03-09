from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db.database import get_db
from app.db.models import User
from app.core.security import get_current_user

from app.schemas.tag import TagCreate, TagOut
from app.schemas.brain import BrainEntryOut
from app.services import tag_service

# Роутер для самих тегов (/tags)
router = APIRouter(prefix="/tags", tags=["Tags"])

# Роутер для привязки тегов к заметкам (/brain/{entry_id}/tags/{tag_id})
brain_tags_router = APIRouter(prefix="/brain", tags=["Brain Tags (Links)"])

# =====================================================================
# СОЗДАНИЕ И ПОЛУЧЕНИЕ ТЕГОВ
# =====================================================================

@router.post("/", response_model=TagOut, status_code=status.HTTP_201_CREATED)
async def create_tag(
    tag: TagCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Создать новый независимый тег.
    """
    return await tag_service.create_tag(db, current_user.id, tag)


@router.get("/", response_model=List[TagOut])
async def get_tags(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить список всех существующих тегов пользователя.
    """
    return await tag_service.get_user_tags(db, current_user.id)


# =====================================================================
# ПРИВЯЗКА ТЕГОВ К ЗАМЕТКАМ
# =====================================================================

@brain_tags_router.post("/{entry_id}/tags/{tag_id}", response_model=BrainEntryOut)
async def link_tag(
    entry_id: int,
    tag_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Прикрепить существующий тег к существующей заметке.
    """
    return await tag_service.link_tag_to_entry(db, current_user.id, entry_id, tag_id)


@brain_tags_router.delete("/{entry_id}/tags/{tag_id}", response_model=BrainEntryOut)
async def unlink_tag(
    entry_id: int,
    tag_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Открепить тег от заметки.
    """
    return await tag_service.unlink_tag_from_entry(db, current_user.id, entry_id, tag_id)
