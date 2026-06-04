from app.models.country_snapshot import CountrySnapshot


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