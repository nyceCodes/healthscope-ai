import math

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.health_profile_routes import router
from app.database.database import Base
from app.database.session import get_db
from app.api.error_handlers import request_validation_error_response


def test_existing_life_expectancy_model_api_and_history():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)

    def override_get_db():
        with session_factory() as db:
            yield db

    app = FastAPI()
    app.add_exception_handler(
        RequestValidationError,
        request_validation_error_response,
    )
    app.include_router(router, prefix="/health")
    app.dependency_overrides[get_db] = override_get_db

    try:
        client = TestClient(app)
        response = client.post(
            "/health/predict-life-expectancy",
            json={
                "adult_mortality": 100,
                "bmi": 25,
                "gdp": 12000,
                "schooling": 15,
                "population": 1_000_000,
            },
        )
        assert response.status_code == 200
        prediction = response.json()["predicted_life_expectancy"]
        assert isinstance(prediction, float)
        assert math.isfinite(prediction)

        invalid_inputs = [
            {"adult_mortality": -1},
            {"bmi": 0},
            {"schooling": -1},
            {"population": 0},
        ]
        for invalid_input in invalid_inputs:
            payload = {
                "adult_mortality": 100,
                "bmi": 25,
                "gdp": 12000,
                "schooling": 15,
                "population": 1_000_000,
                **invalid_input,
            }
            invalid_response = client.post(
                "/health/predict-life-expectancy",
                json=payload,
            )
            assert invalid_response.status_code == 422

        non_finite_response = client.post(
            "/health/predict-life-expectancy",
            content=(
                '{"adult_mortality":100,"bmi":25,"gdp":1e309,'
                '"schooling":15,"population":1000000}'
            ),
            headers={"content-type": "application/json"},
        )
        assert non_finite_response.status_code == 422
        validation_detail = non_finite_response.json()["detail"][0]
        assert validation_detail["loc"] == ["body", "gdp"]
        assert "input" not in validation_detail

        history = client.get("/health/predictions")
        assert history.status_code == 200
        assert len(history.json()) == 1
        assert history.json()[0]["prediction"] == prediction
    finally:
        engine.dispose()
