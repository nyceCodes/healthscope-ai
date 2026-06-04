from app.services.country_service import CountryService
from app.services.disease_service import DiseaseService

class HealthProfileService:

    @staticmethod
    def build_profile(country):

        country_data = CountryService.get_country(country)

        if not country_data:
            raise ValueError(
                f"Country '{country}' not found"
            )

        disease_data = DiseaseService.get_country_health(country) or {}

        country_info = country_data[0]

        return {
            "country": country,
            "population": country_info.get("population", 0),
            "region": country_info.get("region", ""),
            "capital": country_info.get("capital", [""])[0],
            "cases": disease_data.get("cases", 0),
            "deaths": disease_data.get("deaths", 0),
            "recovered": disease_data.get("recovered", 0),
            "active": disease_data.get("active", 0),
            "tests": disease_data.get("tests", 0),
        }