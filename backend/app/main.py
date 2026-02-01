from fastapi import FastAPI
from app.routers import auth
from app.database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Family Circle API",
    description="API для семейного приложения Family Circle",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

app.include_router(auth.router)

@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": "Family Circle API",
        "status": "active",
        "docs": "/docs"
    }