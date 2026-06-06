from sqlalchemy import (
    Column,
    Integer,
    Float,
    DateTime
)

from datetime import datetime

from app.database.database import Base


class PredictionHistory(Base):

    __tablename__ = (
        "prediction_history"
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    adult_mortality = Column(
        Float
    )

    bmi = Column(
        Float
    )

    gdp = Column(
        Float
    )

    schooling = Column(
        Float
    )

    population = Column(
        Float
    )

    prediction = Column(
        Float
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )