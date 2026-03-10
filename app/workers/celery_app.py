import os
import asyncio
from celery import Celery
from sqlalchemy.future import select

from app.db.database import AsyncSessionLocal
from app.db.models import BrainEntry
# Import ai_service from our FastAPI app
from app.services import ai_service

# Retrieve REDIS_URL from env or use a local default fallback (like when not in docker)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Initialize Celery
celery = Celery(
    "second_brain_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL
)

async def _async_generate_and_save_embedding(entry_id: int):
    """
    Асинхронная корутина. Открывает соединение с БД, достает заметку, 
    генерирует ей вектор и сохраняет обратно в базу.
    """
    async with AsyncSessionLocal() as db:
        # Load the entry
        stmt = select(BrainEntry).where(BrainEntry.id == entry_id)
        result = await db.execute(stmt)
        entry = result.scalar_one_or_none()

        if not entry:
            print(f"Task Failed: BrainEntry with ID {entry_id} not found.")
            return

        # Prepare text to embed (we combine Title and Content for better semantic meaning)
        text_to_embed = f"Title: {entry.title or 'No Title'}\nContent: {entry.content}"

        print(f"Generating embedding for Entry {entry_id}...")
        
        try:
            # Generate the vector array
            embedding_vector = ai_service.generate_embedding(text_to_embed)
            
            # Save it to the database using the pgvector Vector column
            # Note: SQLAlchemy handles the float array implicitly mapping it to pgvector
            entry.embedding = embedding_vector
            
            await db.commit()
            print(f"Success: Embedding saved for Entry {entry_id}")
            
        except Exception as e:
            await db.rollback()
            print(f"Task Failed: Could not generate or save embedding. Error: {e}")


@celery.task(name="process_note_embedding")
def process_note_embedding(entry_id: int):
    """
    Фоновая задача Celery. 
    Поскольку Celery воркер - синхронный, мы запускаем асинхронный цикл событий для 
    выполнения работы в нашей асинхронной базе данных (asyncpg).
    """
    print(f"Celery received task to embed Entry {entry_id}")
    asyncio.run(_async_generate_and_save_embedding(entry_id))
    return f"Task completed for entry {entry_id}"
