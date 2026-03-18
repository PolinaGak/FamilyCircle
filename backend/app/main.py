from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from app.routers import auth, family, invitation

app = FastAPI(
    title="Family Circle API",
    description="API для семейного приложения Family Circle",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    swagger_ui_parameters={
        "persistAuthorization": True,
        "displayRequestDuration": True,
    }
)
app.include_router(auth.router)
app.include_router(family.router)
app.include_router(invitation.router)


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