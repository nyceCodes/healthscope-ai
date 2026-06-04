from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI

from app.database.database import Base
from app.database.database import engine

from app.models.country_snapshot import CountrySnapshot
from app.models.nutrition_search import NutritionSearch

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="HealthScope AI",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "message": "HealthScope AI API Running"
    }

from app.api.health_profile_routes import (
    router as health_profile_router
)

app.include_router(
    health_profile_router,
    prefix="/health",
    tags=["Health Profile"]
)

print(Base.metadata.tables.keys())