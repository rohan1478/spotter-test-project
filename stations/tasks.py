import csv
import logging
from celery import shared_task
from stations.models import CityLocation, FuelStation
from stations.services.geocoding import geocode_city_state

logger = logging.getLogger(__name__)


def _parse_and_deduplicate(csv_path: str) -> dict:
    """Read CSV, keep lowest-price row per OPIS ID. Returns {opis_id: row_dict}."""
    best = {}
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            opis_id = int(row["OPIS Truckstop ID"])
            price = float(row["Retail Price"])
            if opis_id not in best or price < best[opis_id]["price"]:
                best[opis_id] = {
                    "opis_id": opis_id,
                    "name": row["Truckstop Name"].strip(),
                    "address": row["Address"].strip(),
                    "city": row["City"].strip(),
                    "state": row["State"].strip(),
                    "rack_id": int(row["Rack ID"]),
                    "price": price,
                }
    return best


def _ensure_city_locations(cities: set[tuple[str, str]]) -> dict:
    """Geocode any City+State pairs not yet in DB. Returns {(city,state): CityLocation}."""
    existing = {
        (cl.city, cl.state): cl
        for cl in CityLocation.objects.all()
        if (cl.city, cl.state) in cities
    }

    result = dict(existing)
    to_geocode = cities - set(existing.keys())

    for city, state in to_geocode:
        coords = geocode_city_state(city, state)
        if coords is None:
            logger.warning("Skipping city: %s, %s — geocoding failed", city, state)
            continue
        lat, lng = coords
        cl = CityLocation.objects.create(
            city=city, state=state, latitude=lat, longitude=lng
        )
        result[(city, state)] = cl

    return result


@shared_task
def ingest_fuel_prices_csv(csv_path: str) -> dict:
    """Ingest fuel prices CSV: deduplicate, geocode, upsert stations."""
    best = _parse_and_deduplicate(csv_path)
    logger.info("Parsed %d unique stations from CSV", len(best))

    # Collect unique city+state pairs
    cities = {(row["city"], row["state"]) for row in best.values()}
    city_locs = _ensure_city_locations(cities)

    created = 0
    updated = 0
    skipped = 0

    for row in best.values():
        key = (row["city"], row["state"])
        cl = city_locs.get(key)
        if cl is None:
            skipped += 1
            continue

        _, was_created = FuelStation.objects.update_or_create(
            opis_id=row["opis_id"],
            defaults={
                "name": row["name"],
                "address": row["address"],
                "city": row["city"],
                "state": row["state"],
                "rack_id": row["rack_id"],
                "retail_price": row["price"],
                "latitude": cl.latitude,
                "longitude": cl.longitude,
                "city_location": cl,
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1

    result = {
        "stations_created": created,
        "stations_updated": updated,
        "stations_skipped": skipped,
        "cities_geocoded": len(city_locs),
    }
    logger.info("Ingestion complete: %s", result)
    return result
