import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.routers import auth, family, invitation, chat, event, album, photo, tree
from backend.app.core.celery import celery_app

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Family Circle API starting up...")
    try:
        celery_app.broker_connection().ensure_connection(max_retries=2)
        logger.info("✅ Celery broker (Redis) connected")
    except Exception as e:
        logger.warning(f"⚠️  Celery broker not available: {e}")
    yield
    logger.info("👋 Family Circle API shutting down...")


app = FastAPI(
    title="Family Circle API",
    description="API для семейного приложения Family Circle",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    swagger_ui_parameters={
        "persistAuthorization": True,
        "displayRequestDuration": True,
    }
)

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.exception_handler(429)
async def rate_limit_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=429, content={"detail": "Too many requests"})

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:3000",
        "http://111.88.144.235",
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