"""
Входная точка нашего FastAPI приложения (Main Entrypoint).
Здесь мы собираем воедино все роутеры (Мозг, Теги, ИИ, Принятие решений, Фронтенд).
Я постарался сделать структуру модульной, чтобы файл main.py не разрастался до тысяч строк.
"""

from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from app.api import auth  # наш роутер для регистрации и логина
from app.core.security import get_current_user

# Инициализация приложения. Title будет красиво смотреться в Swagger UI (/docs)
app = FastAPI(
    title="Second Brain API",
    description="Твой личный цифровой ассистент с векторным поиском и ИИ.",
    version="1.0.0"
)

# ---------------------------------------------------------
# Статические файлы (CSS, JS)
# ---------------------------------------------------------
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# ---------------------------------------------------------
# Подключение роутеров (Маршрутизация)
# ---------------------------------------------------------

# Авторизация (JWT токены)
app.include_router(auth.router, prefix="/auth", tags=["auth"])

# Ядро системы (Second Brain): Заметки и Теги
from app.api import brain, tags, decisions
app.include_router(brain.router)
app.include_router(tags.router)
app.include_router(tags.brain_tags_router)

# Фича: Механизм принятия решений (Weighted Scoring Engine)
app.include_router(decisions.router)

# Фича: ИИ Агент (RAG, Векторный поиск)
from app.api import ai
app.include_router(ai.router)

# Фронтенд: HTML-страницы (Jinja2 SSR)
from app.api import pages
app.include_router(pages.router)


# ---------------------------------------------------------
# Тестовые / Утилитные Эндпоинты
# ---------------------------------------------------------

@app.get("/me", tags=["utils"])
async def read_me(current_user: dict = Depends(get_current_user)):
    """
    Удобный эндпоинт, чтобы проверить "А кто я сейчас?".
    Требуется передать заголовок Authorization: Bearer <token>.
    """
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
    }

@app.get("/", tags=["utils"])
async def root():
    """Перенаправляем на страницу логина (фронтенд)."""
    return RedirectResponse(url="/login")