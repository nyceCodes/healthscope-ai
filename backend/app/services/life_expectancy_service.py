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

        return (
            db.query(
                LifeExpectancy
            )
            .filter(
                LifeExpectancy.country == country
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

        return (

            db.query(
                LifeExpectancy
            )

            .filter(
                LifeExpectancy.country == country
            )

            .order_by(
                LifeExpectancy.year.asc()
            )

            .all()

        )