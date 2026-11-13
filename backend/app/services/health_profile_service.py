"""Create a profile from live COVID data and optional country metadata.

Offline fallback is handled by the API router, using previously saved snapshots.
"""
from app.services.country_service import CountryService
from app.services.disease_service import DiseaseService


class HealthProfileService:
    @staticmethod
    def build_profile(country: str):
        country = country.strip()
        if not country:
            raise ValueError("Enter a country name")

        # disease.sh also supplies a population and geographic label. This
        # keeps the app usable without requiring a REST Countries API key.
        disease_data = DiseaseService.get_country_health(country)
        if disease_data is None:
            return None

        country_data = CountryService.get_country(country) or {}
        population = country_data.get("population") or disease_data.get("population") or 0
        country_name = country_data.get("country") or disease_data.get("country") or country

        def count(key):
            value = disease_data.get(key)
            return int(value) if isinstance(value, (int, float)) and value >= 0 else 0

        return {
            "country": str(country_name),
            "population": int(population),
            "region": country_data.get("region") or disease_data.get("continent") or "",
            "capital": country_data.get("capital") or "",
            "cases": count("cases"),
            "deaths": count("deaths"),
            "recovered": count("recovered"),
            "active": count("active"),
            "tests": count("tests"),
            "data_source": "disease.sh" + (" + REST Countries v5" if country_data else ""),
            "data_as_of": None,
            "data_status": "Reported COVID-19 data (not necessarily current)",
        }
