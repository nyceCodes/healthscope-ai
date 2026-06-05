from sqlalchemy.orm import Session

from app.models.life_expectancy import (
    LifeExpectancy
)

from app.models.country_snapshot import (
    CountrySnapshot
)


class CountryReportService:

    @staticmethod
    def build_report(
        db: Session,
        country: str
    ):

        latest_snapshot = (

            db.query(
                CountrySnapshot
            )

            .filter(
                CountrySnapshot.country == country
            )

            .order_by(
                CountrySnapshot.created_at.desc()
            )

            .first()

        )

        life_record = (

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

        top_country = (

            db.query(
                LifeExpectancy
            )

            .filter(
                LifeExpectancy.year == 2015
            )

            .order_by(
                LifeExpectancy.life_expectancy.desc()
            )

            .first()

        )

        return (
            latest_snapshot,
            life_record,
            top_country
        )