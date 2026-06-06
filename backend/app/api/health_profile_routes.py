from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.country_snapshot import CountrySnapshot
from app.schemas.health_profile import HealthProfile
from app.services.analytics_service import AnalyticsService
from app.services.health_profile_service import HealthProfileService
from app.services.snapshot_service import SnapshotService

from app.services.ranking_service import RankingService

from fastapi import Query

from app.models.life_expectancy import (
    LifeExpectancy
)

from app.services.life_expectancy_service import (
    LifeExpectancyService
)

from app.services.country_report_service import (
    CountryReportService
)

from app.services.intelligence_service import (
    IntelligenceService
)

from app.services.ml_service import (
    MLService
)

from app.schemas.life_prediction import (
    LifePredictionRequest
)

from app.services.risk_assessment_service import (
    RiskAssessmentService
)

from app.services.prediction_history_service import (
    PredictionHistoryService
)


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

@router.get("/rankings")
def rankings(
    db: Session = Depends(get_db)
):

    return RankingService.get_rankings(db)

@router.get("/compare")
def compare_countries(
    countries: list[str] = Query(...),
):

    results = []

    for country in countries:

        profile = (
            HealthProfileService
            .build_profile(country)
        )

        profile["health_index"] = (
            AnalyticsService
            .health_index(profile)
        )

        results.append(profile)

    return results


@router.get("/trends/{country}")
def country_trends(
    country: str,
    db: Session = Depends(get_db)
):
    history = (

    db.query(CountrySnapshot)

    .filter(
        CountrySnapshot.country == country
    )

    .order_by(
        CountrySnapshot.created_at.asc()
    )

    .all()

)
    return [
    {
        "date": item.created_at,
        "health_index": item.health_index,
        "recovery_rate": item.recovery_rate,
        "mortality_rate": item.mortality_rate
    }
    for item in history
]

@router.get(
    "/life-expectancy/{country}"
)
def life_expectancy(
    country: str,
    db: Session = Depends(get_db)
):

    record = (
        LifeExpectancyService
        .latest_country_record(
            db,
            country
        )
    )

    if not record:
        raise HTTPException(
            status_code=404,
            detail="Country not found"
        )

    return {
        "country": record.country,
        "year": record.year,
        "status": record.status,
        "life_expectancy": record.life_expectancy,
        "adult_mortality": record.adult_mortality,
        "bmi": record.bmi,
        "gdp": record.gdp,
        "schooling": record.schooling,
        "population": record.population
    }


from app.services.comparison_service import (
    ComparisonService
)
@router.get(
    "/compare/{country_a}/{country_b}"
)
def compare_countries(
    country_a: str,
    country_b: str,
    db: Session = Depends(get_db)
):

    a, b = (
        ComparisonService.compare_countries(
            db,
            country_a,
            country_b
        )
    )

    if not a or not b:
        raise HTTPException(
            status_code=404,
            detail="Country not found"
        )

    life_gap = round(
        b.life_expectancy -
        a.life_expectancy,
        2
    )

    schooling_gap = round(
        b.schooling -
        a.schooling,
        2
    )

    return {
        "country_a": a.country,
        "country_b": b.country,

        "life_expectancy_a":
            a.life_expectancy,

        "life_expectancy_b":
            b.life_expectancy,

        "life_expectancy_gap":
            life_gap,

        "schooling_a":
            a.schooling,

        "schooling_b":
            b.schooling,

        "schooling_gap":
            schooling_gap,

        "winner":
            b.country
            if b.life_expectancy >
            a.life_expectancy
            else a.country
    }

@router.get(
    "/top-life-expectancy"
)
def top_life_expectancy(
    db: Session = Depends(get_db)
):

    records = (
        RankingService
        .top_life_expectancy(db)
    )

    return [

        {
            "country": r.country,
            "life_expectancy":
                r.life_expectancy,

            "gdp":
                r.gdp,

            "schooling":
                r.schooling
        }

        for r in records
    ]

@router.get(
    "/country-report/{country}"
)
def country_report(
    country: str,
    db: Session = Depends(get_db)
):

    snapshot, life_record, top_country = (
        CountryReportService
        .build_report(
            db,
            country
        )
    )

    if not life_record:

        raise HTTPException(
            status_code=404,
            detail="Country not found"
        )

    gap = round(
        top_country.life_expectancy
        -
        life_record.life_expectancy,
        2
    )

    report = {

        "country": country,

        "health_profile": {

            "health_index":
                snapshot.health_index
                if snapshot
                else None,

            "recovery_rate":
                snapshot.recovery_rate
                if snapshot
                else None,

            "mortality_rate":
                snapshot.mortality_rate
                if snapshot
                else None
        },

        "life_expectancy": {

            "year":
                life_record.year,

            "value":
                life_record.life_expectancy,

            "schooling":
                life_record.schooling,

            "gdp":
                life_record.gdp
        },

        "global_comparison": {

            "top_country":
                top_country.country,

            "life_expectancy_gap":
                gap
        }

    }

    report["insights"] = (
        IntelligenceService
        .generate_insights(
            report
        )
    )

    return report


@router.get(
    "/life-trend/{country}"
)
def country_life_trend(
    country: str,
    db: Session = Depends(get_db)
):

    records = (

        LifeExpectancyService
        .country_trend(
            db,
            country
        )

    )

    return [

        {
            "year": r.year,
            "life_expectancy":
                r.life_expectancy,

            "schooling":
                r.schooling,

            "gdp":
                r.gdp
        }

        for r in records

    ]

@router.get(
    "/risk-assessment/{country}"
)
def risk_assessment(
    country: str,
    db: Session = Depends(get_db)
):

    snapshot, life_record, top_country = (
        CountryReportService
        .build_report(
            db,
            country
        )
    )

    if not life_record:

        raise HTTPException(
            status_code=404,
            detail="Country not found"
        )

    report = {

        "health_profile": {

            "health_index":
                snapshot.health_index
                if snapshot
                else None
        },

        "life_expectancy": {

            "value":
                life_record.life_expectancy,

            "schooling":
                life_record.schooling
        }
    }

    result = (
        RiskAssessmentService
        .assess_risk(
            report
        )
    )

    return {

        "country": country,

        **result
    }

@router.post(
    "/predict-life-expectancy"
)
def predict_life_expectancy(
    request: LifePredictionRequest,
    db: Session = Depends(get_db)
):

    prediction = (
        MLService
        .predict_life_expectancy(
            request.adult_mortality,
            request.bmi,
            request.gdp,
            request.schooling,
            request.population
        )
    )

    PredictionHistoryService.save_prediction(

        db,

        request.adult_mortality,

        request.bmi,

        request.gdp,

        request.schooling,

        request.population,

        prediction

    )

    return {
        "predicted_life_expectancy":
            prediction
    }

@router.get(
    "/predictions"
)
def prediction_history(
    db: Session = Depends(get_db)
):

    predictions = (
        PredictionHistoryService
        .get_predictions(db)
    )

    return [

        {
            "id":
                p.id,

            "adult_mortality":
                p.adult_mortality,

            "bmi":
                p.bmi,

            "gdp":
                p.gdp,

            "schooling":
                p.schooling,

            "population":
                p.population,

            "prediction":
                p.prediction,

            "created_at":
                p.created_at
        }

        for p in predictions

    ]