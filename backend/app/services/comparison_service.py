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

        a = (
            db.query(LifeExpectancy)
            .filter(
                LifeExpectancy.country == country_a
            )
            .order_by(
                LifeExpectancy.year.desc()
            )
            .first()
        )

        b = (
            db.query(LifeExpectancy)
            .filter(
                LifeExpectancy.country == country_b
            )
            .order_by(
                LifeExpectancy.year.desc()
            )
            .first()
        )

        return a, b