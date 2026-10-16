import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

MAPBOX_GEOCODE_URL = "https://api.mapbox.com/geocoding/v5/mapbox.places/{query}.json"


def geocode_city_state(city: str, state: str) -> tuple[float, float] | None:
    """Geocode a City+State pair via Mapbox. Returns (lat, lng) or None."""
    query = f"{city}, {state}, United States"
    url = MAPBOX_GEOCODE_URL.format(query=requests.utils.quote(query))
    params = {
        "access_token": settings.MAPBOX_ACCESS_TOKEN,
        "country": "US",
        "types": "place",
        "limit": 1,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        features = resp.json().get("features", [])
        if not features:
            logger.warning("No geocode result for %s, %s", city, state)
            return None
        lng, lat = features[0]["center"]
        return lat, lng
    except requests.RequestException:
        logger.exception("Geocoding failed for %s, %s", city, state)
        return None


def geocode_address(street: str, city: str, state: str) -> tuple[float, float] | None:
    """Geocode a full US address via Mapbox. Returns (lat, lng) or None."""
    parts = [street, city, state]
    query = ", ".join(parts) + ", United States"
    url = MAPBOX_GEOCODE_URL.format(query=requests.utils.quote(query))
    params = {
        "access_token": settings.MAPBOX_ACCESS_TOKEN,
        "country": "US",
        "limit": 1,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        features = resp.json().get("features", [])
        if not features:
            logger.warning("No geocode result for address: %s", query)
            return None
        lng, lat = features[0]["center"]
        return lat, lng
    except requests.RequestException:
        logger.exception("Geocoding failed for address: %s", query)
        return None
