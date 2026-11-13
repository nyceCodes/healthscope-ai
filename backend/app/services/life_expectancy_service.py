from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.life_expectancy import (
    LifeExpectancy
)


class LifeExpectancyService:

    @staticmethod
    def latest_country_record(
        db: Session,
        country: str
    ):
        country_key = country.strip().casefold()
        return (
            db.query(
                LifeExpectancy
            )
            .filter(
                func.lower(LifeExpectancy.country) == country_key
            )
            .order_by(
                LifeExpectancy.year.desc()
            )
            .first()
        )

    @staticmethod
    def country_trend(
        db: Session,
        country: str
    ):
        country_key = country.strip().casefold()
        return (
            db.query(
                LifeExpectancy
            )
            .filter(
                func.lower(LifeExpectancy.country) == country_key
            )
            .order_by(
                LifeExpectancy.year.asc()
            )
            .all()
        )