from fastapi import FastAPI, Depends
from app.api import auth  # наш роутер для регистрации и логина
from app.core.security import get_current_user

app = FastAPI(title="Second Brain API")

# Подключаем роутер авторизации
app.include_router(auth.router, prefix="/auth", tags=["auth"])

# Подключаем роутер для заметок (Second Brain) и тегов
from app.api import brain, tags, decisions
app.include_router(brain.router)
app.include_router(tags.router)
app.include_router(tags.brain_tags_router)

# Подключаем роутер для механизма принятия решений (Decision Engine)
app.include_router(decisions.router)

# Подключаем роутер для ИИ Агента (RAG)
from app.api import ai
app.include_router(ai.router)

# Пример защищенного эндпоинта
@app.get("/me")
async def read_me(current_user = Depends(get_current_user)):
    """
    Возвращает данные текущего пользователя.
    Требуется передать Authorization: Bearer <token>
    """
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
    }

# Приветственный эндпоинт
@app.get("/")
async def root():
    return {"message": "Second Brain API is running"}