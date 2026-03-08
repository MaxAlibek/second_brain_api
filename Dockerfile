# Выбираем легкий и быстрый базовый образ Python
FROM python:3.12-slim

# Рабочая директория внутри контейнера
WORKDIR /app

# Устанавливаем системные зависимости (например, для компиляции некоторых Python пакетов, если понадобится)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл с зависимостями
COPY requirements.txt .

# Устанавливаем Python пакеты
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь оставшийся код в контейнер
COPY . .

# Открываем порт 8000, на котором работает FastAPI
EXPOSE 8000

# Команда для запуска нашего сервера
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
