from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List

from app.db.database import get_db
from app.db.models import User, BrainEntry
from app.core.security import get_current_user
from app.services import ai_service

router = APIRouter(prefix="/ai", tags=["AI Agent"])

class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    answer: str

@router.post("/chat", response_model=ChatResponse)
async def chat_with_second_brain(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    RAG AI Agent. Задает вопрос нейросети, которая ищет ответ ТОЛЬКО Писать по вашим заметкам.
    """
    try:
        # 1. Превращаем вопрос пользователя в вектор
        # Вызов синхронный, так как API-запрос короткий (лучше вынести в thread pool для highload, но для нас ОК)
        question_vector = ai_service.generate_embedding(request.question)
        
        # 2. Ищем Топ-5 самых похожих заметок через pgvector (ORDER BY embedding <-> question_vector)
        # Обязательно фильтруем по current_user.id (ИЗОЛЯЦИЯ ЮЗЕРОВ)
        stmt = (
            select(BrainEntry)
            .where(BrainEntry.user_id == current_user.id)
            .where(BrainEntry.embedding != None)
            .order_by(BrainEntry.embedding.l2_distance(question_vector))
            .limit(5)
        )
        
        result = await db.execute(stmt)
        top_entries = result.scalars().all()
        
        # 3. Собираем тексты заметок в единый контекст
        if not top_entries:
            return ChatResponse(answer="Извините, у вас пока нет заметок для анализа или они еще не обработаны ИИ.")
            
        context_parts = []
        for entry in top_entries:
            title = entry.title or "Без названия"
            context_parts.append(f"--- ЗАМЕТКА: {title} ---\n{entry.content}\n")
            
        context_text = "\n".join(context_parts)
        
        # 4. Отправляем в LLM (RAG)
        final_answer = ai_service.generate_rag_answer(request.question, context_text)
        
        return ChatResponse(answer=final_answer)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
