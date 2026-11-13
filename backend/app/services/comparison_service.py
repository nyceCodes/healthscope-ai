from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.life_expectancy import (
    LifeExpectancy
)


class ComparisonService:

    @staticmethod
    def compare_countries(
        db: Session,
        country_a: str,
        country_b: str
    ):
        a_key = country_a.strip().casefold()
        b_key = country_b.strip().casefold()

        a = (
            db.query(LifeExpectancy)
            .filter(
                func.lower(LifeExpectancy.country) == a_key
            )
            .order_by(
                LifeExpectancy.year.desc()
            )
            .first()
        )

        b = (
            db.query(LifeExpectancy)
            .filter(
                func.lower(LifeExpectancy.country) == b_key
            )
            .order_by(
                LifeExpectancy.year.desc()
            )
            .first()
        )

        return a, b