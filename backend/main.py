from fastapi import FastAPI

app = FastAPI(
    title="HealthScope AI",
    version="1.0.0"
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