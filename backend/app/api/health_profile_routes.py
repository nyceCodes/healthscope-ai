from fastapi import APIRouter, HTTPException


from app.services.health_profile_service import HealthProfileService
from app.services.analytics_service import AnalyticsService
from app.schemas.health_profile import HealthProfile

router = APIRouter()

@router.get(
    "/profile/{country}",
    response_model=HealthProfile
)
def country_profile(country):
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

        return profile
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )