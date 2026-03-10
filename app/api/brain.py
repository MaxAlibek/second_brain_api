from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db.database import get_db
from app.db.models import User
from app.core.security import get_current_user
from app.schemas.brain import BrainEntryCreate, BrainEntryUpdate, BrainEntryOut
from app.services import brain_service
from app.workers.celery_app import process_note_embedding

# =====================================================================
# API РОУТЕР ДЛЯ ЗАМЕТОК (ENDPOINTS)
# Это наш "пульт управления". Сюда приходят веб-запросы от клиентов (фронтенда, мобилки).
# Роутер проверяет 'get_current_user', чтобы только авторизованные 
# пользователи с токеном могли создавать и читать свои заметки.
# =====================================================================

router = APIRouter(
    prefix="/brain",
    tags=["Brain Entries"]
)

@router.post("/", response_model=BrainEntryOut, status_code=status.HTTP_201_CREATED)
async def create_entry(
    note_data: BrainEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    **Создать новую мысль (заметку).**
    - `note_data`: То, что прислал пользователь (текст, заголовок).
    - `current_user`: Текущий юзер (достается из JWT-токена).
    """
    # Вызываем сервис, передаем ему сессию БД, ID юзера и данные заметки.
    entry = await brain_service.create_brain_entry(db, current_user.id, note_data)
    
    # ТРИГГЕР: Запускаем фоновую задачу Celery для генерации вектора
    process_note_embedding.delay(entry.id)
    
    return entry


@router.get("/", response_model=List[BrainEntryOut])
async def get_entries(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    **Получить список всех записей (мыслей) текущего пользователя.**
    - `skip`, `limit`: для постраничной разбивки (чтобы не грузить миллион записей сразу).
    """
    return await brain_service.get_user_entries(db, current_user.id, skip, limit)


@router.get("/{entry_id}", response_model=BrainEntryOut)
async def get_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    **Открыть конкретную заметку по ID.**
    Если заметки не существует или она чужая - возвращаем ошибку 404.
    """
    db_entry = await brain_service.get_entry_by_id(db, entry_id, current_user.id)
    if db_entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Entry not found or you don't have access"
        )
    return db_entry


@router.put("/{entry_id}", response_model=BrainEntryOut)
async def update_entry(
    entry_id: int,
    update_data: BrainEntryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    **Отредактировать существующую заметку.**
    """
    # Сначала пытаемся найти заметку
    db_entry = await brain_service.get_entry_by_id(db, entry_id, current_user.id)
    if db_entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
        
    # Если нашли - обновляем через сервис
    updated_entry = await brain_service.update_brain_entry(db, db_entry, update_data)
    
    # ТРИГГЕР: Обновляем вектор в фоне при изменении текста заметки
    process_note_embedding.delay(updated_entry.id)
    
    return updated_entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    **Удалить заметку навсегда.**
    После успешного удаления не возвращаем никаких данных (код 204 No Content).
    """
    db_entry = await brain_service.get_entry_by_id(db, entry_id, current_user.id)
    if db_entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
        
    await brain_service.delete_brain_entry(db, db_entry)
    # Возвращать ничего не нужно, статус-код 204 сам всё скажет
