from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI

from app.config import get_cors_settings
from app.api.error_handlers import request_validation_error_response
from app.database.database import Base
from app.database.database import engine
from fastapi.exceptions import RequestValidationError

from app.models.country_snapshot import CountrySnapshot
from app.models.nutrition_search import NutritionSearch

from app.models.life_expectancy import (
    LifeExpectancy
)

from app.models.prediction_history import (
    PredictionHistory
)
from app.models.health_indicator import (
    HealthCountry,
    HealthDataImport,
    HealthDataSource,
    HealthIndicator,
    HealthIndicatorObservation,
)

cors_origins, cors_origin_regex = get_cors_settings()
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="HealthScope AI",
    version="1.0.0"
)
app.add_exception_handler(
    RequestValidationError,
    request_validation_error_response,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=cors_origin_regex,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
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

from app.api.health_data_routes import router as health_data_router

app.include_router(
    health_data_router,
    prefix="/health/data",
    tags=["Global Health Data"],
)