from app.models.country_snapshot import CountrySnapshot
from app.models.life_expectancy import (
    LifeExpectancy
)

class RankingService:

    @staticmethod
    def get_rankings(db):

        snapshots = (

            db.query(CountrySnapshot)

            .order_by(
                CountrySnapshot.health_index.desc()
            )

            .all()

        )

        return [
            {
                "country": s.country,
                "health_index": s.health_index,
                "created_at": s.created_at
            }
            for s in snapshots
        ]
        

    @staticmethod
    def top_life_expectancy(
        db,
        limit=10
    ):

        return (

            db.query(
                LifeExpectancy
            )

            .filter(
                LifeExpectancy.year == 2015
            )

            .order_by(
                LifeExpectancy.life_expectancy.desc()
            )

            .limit(limit)

            .all()

        )
    
