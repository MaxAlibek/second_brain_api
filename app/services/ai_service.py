import os
from google import genai
from google.genai import types

# Initialize Gemini Client
from app.core.config import settings

try:
    if settings.GEMINI_API_KEY:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
    else:
        client = genai.Client()
except Exception as e:
    client = None
    print(f"Warning: Could not initialize Gemini Client. Missing API key? {e}")

# We use the recommended models
# We use the supported models for this specific API key
EMBEDDING_MODEL = "models/gemini-embedding-001"
# gemini-2.5-flash is free, very fast, and good for general chat/RAG
CHAT_MODEL = "gemini-2.5-flash"


def generate_embedding(text: str) -> list[float]:
    """
    Создает Вектор (массив из 768 чисел) для переданного текста, используя Gemini API.
    Эта функция вызывается синхронно (так как Celery работает синхронно).
    """
    if not client:
        raise ValueError("Gemini Client is not initialized. Check GEMINI_API_KEY.")
    
    # Запрашиваем эмбеддинг
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(output_dimensionality=768)
    )
    
    # Возвращаем массив чисел
    return response.embeddings[0].values


def generate_rag_answer(question: str, context: str) -> str:
    """
    Генерирует умный ответ с помощью RAG (Retrieval-Augmented Generation).
    ИИ получает строгий системный промпт отвечать ТОЛЬКО по предоставленному контексту.
    """
    if not client:
        raise ValueError("Gemini Client is not initialized. Check GEMINI_API_KEY.")

    prompt = f"""
    Ты — умный и полезный ИИ-помощник (Second Brain).
    Пользователь задал вопрос, и система нашла в его личных заметках следующий контекст.
    Твоя задача: Ответить на вопрос пользователя, опираясь СТРОГО на предоставленный контекст.
    Если контекст не содержит ответа или он пуст, честно скажи: "Я не нашел информации об этом в ваших заметках". 
    Не выдумывай факты.

    КОНТЕКСТ ИЗ ЗАМЕТОК:
    {context}

    ВОПРОС ПОЛЬЗОВАТЕЛЯ:
    {question}
    """

    response = client.models.generate_content(
        model=CHAT_MODEL,
        contents=prompt
    )

    return response.text
