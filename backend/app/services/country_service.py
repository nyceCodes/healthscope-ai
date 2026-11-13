"""Optional REST Countries v5 adapter.

REST Countries v3.1 is retired. The live v5 service requires a user's own key.
Do not use the public demo key for production country data; it returns samples.
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
import requests
from urllib.parse import quote

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
logger = logging.getLogger(__name__)


class CountryService:
    BASE_URL = "https://api.restcountries.com/countries/v5"

    @staticmethod
    def get_country(country: str):
        """Return normalized country metadata, or None if no key/unavailable."""
        key = os.getenv("REST_COUNTRIES_API_KEY", "").strip()
        if not key:
            return None
        if key == "rc_live_demo":
            logger.warning("REST Countries demo key only returns sample data; ignoring it")
            return None
        try:
            response = requests.get(
                f"{CountryService.BASE_URL}/names.common/{quote(country, safe='')}",
                headers={"Authorization": f"Bearer {key}"},
                timeout=5,
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            payload = response.json()
            objects = payload.get("data", {}).get("objects", [])
            if not objects:
                return None
            item = objects[0]
            capitals = item.get("capitals") or []
            capital = capitals[0].get("name", "") if capitals and isinstance(capitals[0], dict) else ""
            return {
                "country": (item.get("names") or {}).get("common") or country,
                "population": item.get("population"),
                "region": item.get("region") or "",
                "capital": capital,
            }
        except (requests.RequestException, ValueError, KeyError, TypeError, AttributeError) as exc:
            logger.warning("REST Countries v5 request failed for %s: %s", country, exc)
            return None
