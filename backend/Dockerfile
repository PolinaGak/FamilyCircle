FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей системы (для psycopg2, pillow и т.д.)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    python3-dev \
    libmagic-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем зависимости отдельно для кэширования
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
#RUN pip install --no-cache-dir -r requirements-dev.txt

# Копируем код приложения
COPY . .

# Переменные окружения по умолчанию
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Команда по умолчанию (переопределяется в docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]