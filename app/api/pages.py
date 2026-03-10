"""
Роутер для отдачи HTML-страниц (SSR через Jinja2).
Эти эндпоинты возвращают полноценные HTML-документы, а не JSON.
Вся клиентская логика (авторизация, fetch к API) живет в app.js.
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["Pages"])

# Jinja2 ищет шаблоны в папке app/templates
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница входа / регистрации."""
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Главная страница с заметками."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@router.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    """Страница AI-чата (мессенджер)."""
    return templates.TemplateResponse("chat.html", {"request": request})


@router.get("/decisions", response_class=HTMLResponse)
async def decisions_page(request: Request):
    """Страница Механизма принятия решений."""
    return templates.TemplateResponse("decisions.html", {"request": request})
