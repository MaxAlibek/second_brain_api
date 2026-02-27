from fastapi import FastAPI, Depends
from app.api import auth  # наш роутер для регистрации и логина
from app.core.security import get_current_user

app = FastAPI(title="Second Brain API")

# Подключаем роутер авторизации
app.include_router(auth.router, prefix="/auth", tags=["auth"])

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