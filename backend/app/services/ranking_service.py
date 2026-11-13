from app.models.country_snapshot import CountrySnapshot
from app.services.analytics_service import AnalyticsService
from app.models.life_expectancy import LifeExpectancy


class RankingService:
    @staticmethod
    def get_rankings(db):
        # Rank countries using their newest snapshot, not every old snapshot.
        snapshots = db.query(CountrySnapshot).order_by(
            CountrySnapshot.created_at.desc(), CountrySnapshot.id.desc()
        ).all()
        latest = {}
        for snapshot in snapshots:
            latest.setdefault(snapshot.country.casefold(), snapshot)
        return [
            {
                "country": item.country,
                "health_index": AnalyticsService.index_from_snapshot(item),
                "created_at": item.created_at,
            }
            for item in sorted(
                latest.values(),
                key=AnalyticsService.index_from_snapshot,
                reverse=True,
            )
        ]

    @staticmethod
    def top_life_expectancy(db, limit=10):
        return db.query(LifeExpectancy).filter(
            LifeExpectancy.year == 2015
        ).order_by(LifeExpectancy.life_expectancy.desc()).limit(limit).all()
