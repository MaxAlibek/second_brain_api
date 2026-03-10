"""
Здесь живет магия RAG (Retrieval-Augmented Generation).
Это мозг нашего "Второго Мозга" :) 
Эндпоинт принимает вопрос пользователя, находит релевантные заметки через векторный поиск (pgvector)
и скармливает их LLM (Gemini), чтобы получить ответ строго по существу. 
"""
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
    Общение с личным ИИ-ассистентом.
    Внимание: Он не придумывает ответы из интернета, а читает только твои заметки!
    """
    try:
        # ШАГ 1: Превращаем текст вопроса в массив из 768 чисел (Вектор / Эмбеддинг).
        # Делаем это синхронно под капотом FastAPI. Да, блокирует поток на долю секунды, 
        # но для пет-проекта и масштабов 1 юзера это абсолютно норм. 
        # TODO: если будет highload, вынести в run_in_threadpool.
        question_vector = ai_service.generate_embedding(request.question)
        
        # ШАГ 2: Векторный поиск по БД (Магия pgvector).
        # Мы ищем Топ-5 записей, которые математически ближе всего к вопросу (косинусное расстояние / L2).
        # КРИТИЧЕСКИ ВАЖНО: Фильтруем по current_user.id. Никаких утечек чужих секретов! 🛑
        stmt = (
            select(BrainEntry)
            .where(BrainEntry.user_id == current_user.id)
            .where(BrainEntry.embedding != None)  # Игнорируем заметки, которые Celery еще не успел обработать
            .order_by(BrainEntry.embedding.l2_distance(question_vector))
            .limit(5)
        )
        
        result = await db.execute(stmt)
        top_entries = result.scalars().all()
        
        # ШАГ 3: Сборка контекста для LLM.
        # Если заметок нет или они не по теме, честно признаемся.
        if not top_entries:
            return ChatResponse(answer="Извините, я пока не нашел в вашей базе релевантных заметок для ответа.")
            
        context_parts = []
        for entry in top_entries:
            # Склеиваем всё в один большой кусок текста (Контекст)
            title = entry.title or "Без названия"
            context_parts.append(f"--- ЗАМЕТКА: {title} ---\n{entry.content}\n")
            
        context_text = "\n".join(context_parts)
        
        # ШАГ 4: Скармливаем контекст в generative модель (Gemini 2.5 Flash).
        # Просим её ответить на вопрос, опираясь ТОЛЬКО на переданный текст.
        final_answer = ai_service.generate_rag_answer(request.question, context_text)
        
        return ChatResponse(answer=final_answer)
        
    except Exception as e:
        # Ловим все непредвиденные проблемы (например, API ключ отвалился) и отдаем наружу 500 ошибку.
        raise HTTPException(status_code=500, detail=f"AI Agent Error: {str(e)}")
