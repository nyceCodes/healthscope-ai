from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.country_snapshot import CountrySnapshot
from app.schemas.health_profile import HealthProfile
from app.services.analytics_service import AnalyticsService
from app.services.health_profile_service import HealthProfileService
from app.services.snapshot_service import SnapshotService

router = APIRouter()

@router.get(
    "/profile/{country}",
    response_model=HealthProfile
)
def country_profile(
    country: str,
    db: Session = Depends(get_db)
):
    try:
        profile = HealthProfileService.build_profile(
            country
        )
    
        profile["recovery_rate"] = (
            AnalyticsService.recovery_rate(profile)
        )

        profile["mortality_rate"] = (
            AnalyticsService.mortality_rate(profile)
        )

        profile["health_index"] = (
            AnalyticsService.health_index(profile)
        )

        SnapshotService.save_snapshot(
            db,
            profile
        )

        return profile
    
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
    )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
    )


@router.get("/history/{country}")
def country_history(
    country: str,
    db: Session = Depends(get_db)
):
    history = (
        db.query(CountrySnapshot)
        .filter(
            CountrySnapshot.country == country
        )
        .order_by(
            CountrySnapshot.created_at.desc()
        )
        .all()
    )

    return [
        {
            "id": snapshot.id,
            "country": snapshot.country,
            "population": snapshot.population,
            "cases": snapshot.cases,
            "deaths": snapshot.deaths,
            "recovered": snapshot.recovered,
            "active": snapshot.active,
            "tests": snapshot.tests,
            "recovery_rate": snapshot.recovery_rate,
            "mortality_rate": snapshot.mortality_rate,
            "health_index": snapshot.health_index,
            "created_at": snapshot.created_at,
        }
        for snapshot in history
    ]