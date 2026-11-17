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
from app.config import get_prediction_history_enabled
from app.models.prediction_history import PredictionHistory


def create_prediction_client(history_enabled):
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
    app.state.prediction_history_enabled = history_enabled
    app.include_router(router, prefix="/health")
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), engine, session_factory


def test_existing_life_expectancy_model_api_and_history():
    client, engine, _session_factory = create_prediction_client(
        get_prediction_history_enabled("development", None)
    )

    try:
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
        client.close()
        engine.dispose()


def test_production_predictions_are_anonymous_but_history_is_disabled():
    client, engine, session_factory = create_prediction_client(
        get_prediction_history_enabled("production", "true")
    )

    try:
        with session_factory() as db:
            db.add(
                PredictionHistory(
                    adult_mortality=75,
                    bmi=24,
                    gdp=9000,
                    schooling=12,
                    population=500_000,
                    prediction=70,
                )
            )
            db.commit()

        payload = {
            "adult_mortality": 100,
            "bmi": 25,
            "gdp": 12000,
            "schooling": 15,
            "population": 1_000_000,
        }
        prediction_without_origin = client.post(
            "/health/predict-life-expectancy",
            json=payload,
        )
        prediction_with_origin = client.post(
            "/health/predict-life-expectancy",
            json=payload,
            headers={"origin": "https://healthscope.example"},
        )
        assert prediction_without_origin.status_code == 200
        assert prediction_with_origin.status_code == 200
        assert "predicted_life_expectancy" in prediction_without_origin.json()
        assert "predicted_life_expectancy" in prediction_with_origin.json()

        history_without_origin = client.get("/health/predictions")
        history_with_origin = client.get(
            "/health/predictions",
            headers={"origin": "https://healthscope.example"},
        )
        assert history_without_origin.status_code == 404
        assert history_with_origin.status_code == 404
        assert "predictions" not in history_without_origin.text.lower()

        with session_factory() as db:
            records = db.query(PredictionHistory).all()
            assert len(records) == 1
            assert records[0].adult_mortality == 75
    finally:
        client.close()
        engine.dispose()
