"""Disease.sh COVID-19 country statistics; historical reporting may be stale."""
import logging
from urllib.parse import quote

import requests

logger = logging.getLogger(__name__)


class DiseaseService:
    BASE_URL = "https://disease.sh/v3/covid-19"

    @staticmethod
    def get_country_health(country: str):
        try:
            response = requests.get(
                f"{DiseaseService.BASE_URL}/countries/{quote(country, safe='')}",
                timeout=6,
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict) or "cases" not in data:
                logger.warning("Disease.sh returned an unexpected response for %s", country)
                return None
            return data
        except (requests.RequestException, ValueError) as exc:
            logger.warning("Disease.sh request failed for %s: %s", country, exc)
            return None
