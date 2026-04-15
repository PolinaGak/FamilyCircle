import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, family, invitation, chat, event, album, photo, tree
from app.core.celery import celery_app  # Импорт для регистрации задач

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan контекст для запуска/остановки приложения.
    Заменяет устаревающие @app.on_event("startup"/"shutdown")
    """
    # Startup
    logger.info("🚀 Family Circle API starting up...")

    # Проверка подключения к Redis (опционально, но полезно)
    try:
        celery_app.broker_connection().ensure_connection(max_retries=2)
        logger.info("✅ Celery broker (Redis) connected")
    except Exception as e:
        logger.warning(f"⚠️  Celery broker not available: {e}")
        logger.warning("⚠️  Background tasks will not work until Redis is available")

    yield

    # Shutdown
    logger.info("👋 Family Circle API shutting down...")


app = FastAPI(
    title="Family Circle API",
    description="API для семейного приложения Family Circle",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,  # Добавляем lifespan
    swagger_ui_parameters={
        "persistAuthorization": True,
        "displayRequestDuration": True,
    }
)

# CORS middleware (исправлен пробел в конце URL)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",  # убран пробел в конце!
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Роутеры
app.include_router(auth.router)
app.include_router(family.router)
app.include_router(invitation.router)
app.include_router(event.router)
app.include_router(chat.router)
app.include_router(photo.router)
app.include_router(album.router)
app.include_router(tree.router)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    openapi_schema.setdefault("components", {})
    openapi_schema["components"]["securitySchemes"] = {
        "OAuth2PasswordBearer": {
            "type": "oauth2",
            "flows": {
                "password": {
                    "tokenUrl": "/auth/login",
                    "scopes": {}
                }
            },
            "description": "Введите email и пароль для получения токена"
        }
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi