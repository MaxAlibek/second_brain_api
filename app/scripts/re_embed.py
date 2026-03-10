import asyncio
import os
import sys

# Добавляем корень проекта (/app в докере)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlalchemy.future import select
from app.db.database import AsyncSessionLocal
from app.db.models import BrainEntry
from app.workers.celery_app import process_note_embedding

async def re_embed_all_notes():
    async with AsyncSessionLocal() as db:
        stmt = select(BrainEntry)
        result = await db.execute(stmt)
        entries = result.scalars().all()
        
        print(f"Found {len(entries)} notes. Triggering Celery tasks...")
        for entry in entries:
            process_note_embedding.delay(entry.id)
            print(f"Queued embedding task for note ID: {entry.id}")
            
if __name__ == "__main__":
    asyncio.run(re_embed_all_notes())
