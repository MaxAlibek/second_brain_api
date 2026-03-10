"""
Celery Worker — Фоновый обработчик задач.

Зачем это нужно?
Когда пользователь создает заметку, нам нужно сходить к Google Gemini API,
получить вектор (embedding) и сохранить его в БД. Этот процесс занимает 1-3 секунды.
Если делать это прямо в эндпоинте FastAPI, пользователь будет ждать — неприятно.

Решение: Celery + Redis.
FastAPI моментально отвечает "201 Created", а в фоне Celery подхватывает задачу
и спокойно генерирует вектор. Пользователь ничего не замечает.

Нюанс: Celery — синхронный фреймворк, а наша БД — асинхронная (asyncpg).
Поэтому внутри задачи мы вызываем asyncio.run(), чтобы запустить асинхронную корутину.
Это безопасно, потому что каждый воркер Celery работает в своем процессе.
"""

import os
import asyncio
from celery import Celery
from sqlalchemy.future import select

from app.db.database import AsyncSessionLocal
from app.db.models import BrainEntry
from app.services import ai_service

# ---------------------------------------------------------------------------
# Конфигурация Celery
# ---------------------------------------------------------------------------
# Redis выступает и как брокер (передача задач), и как бэкенд (хранение результатов).
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery = Celery(
    "second_brain_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL
)


# ---------------------------------------------------------------------------
# Асинхронная логика генерации эмбеддинга
# ---------------------------------------------------------------------------
async def _async_generate_and_save_embedding(entry_id: int):
    """
    Ядро фоновой задачи. Открывает соединение с БД, загружает заметку,
    генерирует вектор через Gemini API и сохраняет его обратно.
    """
    async with AsyncSessionLocal() as db:
        # Загружаем конкретную заметку по ID, подгружая связанные теги
        from sqlalchemy.orm import selectinload
        stmt = select(BrainEntry).options(selectinload(BrainEntry.tags)).where(BrainEntry.id == entry_id)
        result = await db.execute(stmt)
        entry = result.scalar_one_or_none()

        if not entry:
            print(f"[Celery] Заметка с ID {entry_id} не найдена в БД. Возможно, была удалена.")
            return

        # Склеиваем заголовок, категорию, теги и контент — так вектор будет точнее передавать смысл
        meta_info = []
        if entry.category:
            meta_info.append(f"Category: {entry.category}")
            
        tags_list = [t.name for t in entry.tags] if getattr(entry, 'tags', None) else []
        if tags_list:
            meta_info.append(f"Tags: {', '.join(tags_list)}")
            
        meta_prefix = "\n".join(meta_info) + "\n" if meta_info else ""
        
        text_to_embed = f"Title: {entry.title or 'No Title'}\n{meta_prefix}Content: {entry.content}"

        print(f"[Celery] Генерирую вектор для заметки #{entry_id}...")
        
        try:
            # Вызываем Gemini API (синхронно, но внутри asyncio.run это нормально)
            embedding_vector = ai_service.generate_embedding(text_to_embed)
            
            # Записываем вектор в pgvector-колонку. SQLAlchemy сам сериализует list[float] -> Vector.
            entry.embedding = embedding_vector
            
            await db.commit()
            print(f"[Celery] Вектор успешно сохранен для заметки #{entry_id}")
            
        except Exception as e:
            await db.rollback()
            print(f"[Celery] Ошибка при генерации вектора для заметки #{entry_id}: {e}")


# ---------------------------------------------------------------------------
# Celery Task (точка входа)
# ---------------------------------------------------------------------------
@celery.task(name="process_note_embedding")
def process_note_embedding(entry_id: int):
    """
    Публичная задача Celery. Вызывается из FastAPI через .delay(entry_id).
    Оборачивает асинхронную корутину в asyncio.run() для совместимости.
    """
    print(f"[Celery] Получена задача: сгенерировать вектор для заметки #{entry_id}")
    asyncio.run(_async_generate_and_save_embedding(entry_id))
    return f"Embedding generated for entry {entry_id}"
