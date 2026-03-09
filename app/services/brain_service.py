from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.db.models import BrainEntry
from app.schemas.brain import BrainEntryCreate, BrainEntryUpdate

# =====================================================================
# СЕРВИС ДЛЯ "SECOND BRAIN" (БИЗНЕС-ЛОГИКА)
# Здесь мы пишем функции, которые будут общаться с базой данных.
# Они получают 'db' (асинхронную сессию) и делают нужные запросы:
# CREATE (создать), READ (прочитать), UPDATE (обновить), DELETE (удалить).
# =====================================================================

async def create_brain_entry(db: AsyncSession, user_id: int, note_data: BrainEntryCreate) -> BrainEntry:
    """
    СОЗДАНИЕ (CREATE): Берем данные из Pydantic-схемы (note_data)
    и сохраняем новую заметку в таблицу 'brain_entries'.
    """
    # Создаем объект модели SQLAlchemy. 
    # **note_data.model_dump() - это крутая фишка Pydantic.
    # Она берет все поля из схемы (title, content, category) и превращает их в словарь.
    # А ** распаковывает этот словарь в аргументы: title="..." content="..."
    new_entry = BrainEntry(**note_data.model_dump(), user_id=user_id)
    
    # Добавляем в текущую транзакцию
    db.add(new_entry)
    
    # Сохраняем физически в базу
    await db.commit()
    
    # Обновляем объект, чтобы Postgres присвоил ему ID и created_at
    await db.refresh(new_entry)
    
    return new_entry


async def get_user_entries(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100) -> List[BrainEntry]:
    """
    ЧТЕНИЕ (READ MANY): Получить список всех заметок конкретного пользователя.
    Поддерживает пагинацию через skip (пропустить N) и limit (взять M).
    """
    # Формируем SQL запрос: SELECT * FROM brain_entries WHERE user_id = X
    stmt = select(BrainEntry).where(BrainEntry.user_id == user_id).offset(skip).limit(limit)
    
    # Выполняем асинхронный запрос
    result = await db.execute(stmt)
    
    # Возвращаем список результатов (scalars извлекает сами объекты моделей из строк таблицы)
    return list(result.scalars().all())


async def get_entry_by_id(db: AsyncSession, entry_id: int, user_id: int) -> Optional[BrainEntry]:
    """
    ЧТЕНИЕ (READ ONE): Получить ОДНУ конкретную заметку по её ID.
    Важно: мы всегда проверяем user_id, чтобы Вася не смог прочитать 
    секретную заметку Пети, просто угадав её ID в ссылке (например, /brain/10).
    """
    stmt = select(BrainEntry).where(BrainEntry.id == entry_id, BrainEntry.user_id == user_id)
    result = await db.execute(stmt)
    
    # Вернуть одну заметку, или None, если ничего не найдено
    return result.scalar_one_or_none()


async def update_brain_entry(db: AsyncSession, db_entry: BrainEntry, update_data: BrainEntryUpdate) -> BrainEntry:
    """
    ОБНОВЛЕНИЕ (UPDATE): Принимает уже найденную в базе заметку (db_entry)
    и новые данные (update_data).
    """
    # Превращаем данные от пользователя в словарь, но исключаем те поля,
    # которые пользователь НЕ передал (exclude_unset=True). 
    # Если он прислал только 'title', то 'content' трогать не будем.
    update_dict = update_data.model_dump(exclude_unset=True)
    
    # Пробегаемся по словарю и переписываем значения атрибутов у объекта базы
    for key, value in update_dict.items():
        setattr(db_entry, key, value)
        
    await db.commit()
    await db.refresh(db_entry)
    
    return db_entry


async def delete_brain_entry(db: AsyncSession, db_entry: BrainEntry) -> None:
    """
    УДАЛЕНИЕ (DELETE): Навсегда стирает заметку из базы.
    """
    await db.delete(db_entry)
    await db.commit()
