import logging
import requests

logger = logging.getLogger(__name__)

OSRM_ROUTE_URL = "http://router.project-osrm.org/route/v1/driving/{lng1},{lat1};{lng2},{lat2}"


def get_route(start: tuple[float, float], end: tuple[float, float]) -> dict | None:
    """
    Get driving route from OSRM.
    start/end are (lat, lng) tuples.
    Returns {"distance_miles": float, "duration_seconds": float, "geometry": str} or None.
    """
    lat1, lng1 = start
    lat2, lng2 = end
    url = OSRM_ROUTE_URL.format(lat1=lat1, lng1=lng1, lat2=lat2, lng2=lng2)
    params = {
        "overview": "full",
        "geometries": "polyline",
    }
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != "Ok" or not data.get("routes"):
            logger.warning("OSRM returned no routes: %s", data.get("code"))
            return None
        route = data["routes"][0]
        return {
            "distance_miles": route["distance"] / 1609.34,
            "duration_seconds": route["duration"],
            "geometry": route["geometry"],
        }
    except requests.RequestException:
        logger.exception("OSRM routing failed")
        return None


def decode_polyline(encoded: str) -> list[tuple[float, float]]:
    """Decode a Google-encoded polyline string into a list of (lat, lng) tuples."""
    result = []
    index = 0
    lat = 0
    lng = 0
    while index < len(encoded):
        shift = 0
        value = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            value |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        lat += (~(value >> 1) if (value & 1) else (value >> 1))

        shift = 0
        value = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            value |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        lng += (~(value >> 1) if (value & 1) else (value >> 1))

        result.append((lat / 1e5, lng / 1e5))
    return result
