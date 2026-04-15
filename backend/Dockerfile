FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей системы
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    python3-dev \
    libmagic-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем зависимости в корень /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# КОПИРУЕМ КОД В ПАПКУ backend, чтобы импорты backend.app... работали
COPY . ./backend/

# PYTHONPATH должен указывать на /app, чтобы Python видел пакет backend
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]