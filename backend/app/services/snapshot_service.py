from app.models.country_snapshot import CountrySnapshot


class SnapshotService:

    @staticmethod
    def save_snapshot(
        db,
        profile
    ):

        snapshot = CountrySnapshot(

            country=profile["country"],

            population=profile["population"],

            cases=profile["cases"],

            deaths=profile["deaths"],

            recovered=profile["recovered"],

            active=profile["active"],

            tests=profile["tests"],

            recovery_rate=profile["recovery_rate"],

            mortality_rate=profile["mortality_rate"],

            health_index=profile["health_index"]

        )

        db.add(snapshot)

        db.commit()

        db.refresh(snapshot)

        return snapshot