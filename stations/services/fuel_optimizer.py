import math
from stations.models import FuelStation
from stations.services.routing import decode_polyline

VEHICLE_RANGE_MILES = 500
MPG = 10
STATION_CORRIDOR_MILES = 10
FUEL_THRESHOLD_MILES = 100  # Start looking for fuel when remaining range drops below this


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distance in miles between two lat/lng points."""
    R = 3958.8
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _build_mile_markers(points: list[tuple[float, float]]) -> list[float]:
    """Compute cumulative distance (miles) at each polyline point."""
    markers = [0.0]
    for i in range(1, len(points)):
        d = _haversine(points[i - 1][0], points[i - 1][1], points[i][0], points[i][1])
        markers.append(markers[-1] + d)
    return markers


def _sample_route_points(points: list[tuple[float, float]], markers: list[float], interval_miles: float = 5.0) -> list[tuple[float, float, float]]:
    """Sample route at regular intervals. Returns [(lat, lng, mile_marker), ...]."""
    sampled = [(points[0][0], points[0][1], 0.0)]
    next_mile = interval_miles
    for i in range(1, len(points)):
        while markers[i] >= next_mile:
            frac = (next_mile - markers[i - 1]) / (markers[i] - markers[i - 1]) if markers[i] != markers[i - 1] else 0
            lat = points[i - 1][0] + frac * (points[i][0] - points[i - 1][0])
            lng = points[i - 1][1] + frac * (points[i][1] - points[i - 1][1])
            sampled.append((lat, lng, next_mile))
            next_mile += interval_miles
    sampled.append((points[-1][0], points[-1][1], markers[-1]))
    return sampled


def _find_nearby_stations(points: list[tuple[float, float]], markers: list[float], total_distance: float) -> list[dict]:
    """Find fuel stations near the route, with their mile markers."""
    lats = [p[0] for p in points]
    lngs = [p[1] for p in points]
    pad = 0.2
    stations_qs = FuelStation.objects.filter(
        latitude__gte=min(lats) - pad,
        latitude__lte=max(lats) + pad,
        longitude__gte=min(lngs) - pad,
        longitude__lte=max(lngs) + pad,
    )

    sampled = _sample_route_points(points, markers)

    nearby = []
    for station in stations_qs:
        best_dist = float("inf")
        best_mile = 0.0
        for lat, lng, mile in sampled:
            d = _haversine(station.latitude, station.longitude, lat, lng)
            if d < best_dist:
                best_dist = d
                best_mile = mile

        if best_dist <= STATION_CORRIDOR_MILES:
            nearby.append({
                "station": station,
                "mile_marker": best_mile,
                "distance_from_route": best_dist,
            })

    nearby.sort(key=lambda x: x["mile_marker"])
    return nearby


def find_optimal_fuel_stops(geometry: str, total_distance: float) -> dict:
    """
    Given an encoded polyline and total distance, find optimal fuel stops.
    Returns {
        "fuel_stops": [{"station": FuelStation, "mile_marker": float, ...}],
        "total_fuel_cost": float,
        "total_gallons": float,
    }
    """
    points = decode_polyline(geometry)
    markers = _build_mile_markers(points)

    if total_distance <= VEHICLE_RANGE_MILES:
        total_gallons = total_distance / MPG
        return {
            "fuel_stops": [],
            "total_fuel_cost": 0.0,
            "total_gallons": total_gallons,
        }

    nearby_stations = _find_nearby_stations(points, markers, total_distance)

    fuel_stops = []
    current_mile = 0.0
    remaining_range = VEHICLE_RANGE_MILES

    while current_mile + remaining_range < total_distance:
        # Don't look for fuel until remaining range is below threshold
        search_start = current_mile + remaining_range - FUEL_THRESHOLD_MILES
        max_reachable = current_mile + remaining_range
        reachable = [
            s for s in nearby_stations
            if search_start <= s["mile_marker"] <= max_reachable
        ]

        if not reachable:
            # No station in the threshold window — widen to anything reachable
            reachable = [
                s for s in nearby_stations
                if current_mile < s["mile_marker"] <= max_reachable
            ]

        if not reachable:
            break

        best = min(reachable, key=lambda s: s["station"].retail_price)
        fuel_stops.append(best)

        current_mile = best["mile_marker"]
        remaining_range = VEHICLE_RANGE_MILES

    total_gallons = total_distance / MPG
    total_fuel_cost = 0.0

    if fuel_stops:
        prev_mile = 0.0
        for stop in fuel_stops:
            segment_distance = stop["mile_marker"] - prev_mile
            gallons = segment_distance / MPG
            stop["gallons_needed"] = gallons
            stop["fuel_cost"] = gallons * stop["station"].retail_price
            total_fuel_cost += stop["fuel_cost"]
            prev_mile = stop["mile_marker"]

        # Final segment: last stop to destination — add to totals only
        last_segment = total_distance - prev_mile
        last_gallons = last_segment / MPG
        last_cost = last_gallons * fuel_stops[-1]["station"].retail_price
        total_fuel_cost += last_cost

    return {
        "fuel_stops": fuel_stops,
        "total_fuel_cost": round(total_fuel_cost, 2),
        "total_gallons": round(total_gallons, 2),
    }
