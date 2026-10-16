# Fuel Route Optimizer API

A Django REST API that calculates driving routes between two US locations and finds the most cost-effective fuel stops along the way. The vehicle has a 500-mile range and consumes fuel at 10 miles per gallon.

## Tech Stack

- **Django 5.2** - Web framework
- **Django REST Framework** - API layer
- **drf-spectacular** - OpenAPI/Swagger documentation
- **Celery** - Async task processing (CSV ingestion)
- **Redis** - Celery message broker
- **SQLite** - Database
- **OSRM** - Open Source Routing Machine (route calculation)
- **Mapbox Geocoding API** - Address to coordinates conversion
- **Docker & Docker Compose** - Containerization

## How It Works

1. User sends start and finish addresses (street, city, state)
2. Addresses are geocoded to coordinates via Mapbox
3. A driving route is fetched from OSRM (1 API call)
4. Fuel stations from the database are matched to the route corridor
5. A greedy algorithm selects the cheapest stations within the vehicle's range
6. The API returns fuel stops, total cost, and total gallons consumed

## Local Setup

### Prerequisites

- Docker and Docker Compose
- A Mapbox access token (free at https://account.mapbox.com)

### 1. Clone and configure

```bash
git clone <repo-url>
cd spotter-assessment
```

Create a `.env` file:

```
DJANGO_SECRET_KEY=change-me-in-production
DEBUG=True
MAPBOX_ACCESS_TOKEN=pk.your_mapbox_token_here
FUEL_PRICES_CSV_PATH=/app/data/fuel-prices-for-be-assessment.csv
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

### 2. Build and start containers

```bash
docker-compose up --build -d
```

### 3. Run migrations

```bash
docker-compose exec web python manage.py migrate
```

### 4. Seed fuel station data

Load the pre-geocoded station fixture (recommended - no Mapbox calls needed):

```bash
docker-compose exec web python manage.py loaddata data/stations_fixture.json
```

Alternatively, ingest from the raw CSV (requires Mapbox token, takes several minutes to geocode ~3,900 cities):

```bash
docker-compose exec web python manage.py ingest_fuel_prices
```

### 5. Access the API

- **Swagger UI:** http://localhost:8000/api/docs/
- **API endpoint:** `POST http://localhost:8000/api/route/`

## API Usage

### Request

```bash
curl -X POST http://localhost:8000/api/route/ \
  -H "Content-Type: application/json" \
  -d '{
    "start": {
      "street": "1 Main St",
      "city": "Los Angeles",
      "state": "CA"
    },
    "finish": {
      "street": "1 Main St",
      "city": "New York",
      "state": "NY"
    }
  }'
```

All three fields (`street`, `city`, `state`) are required. State must be a valid 2-letter US state abbreviation.

### Response

```json
{
  "start": {
    "address": "1 Main St, Los Angeles, CA",
    "latitude": 34.052218,
    "longitude": -118.243395
  },
  "finish": {
    "address": "1 Main St, New York, NY",
    "latitude": 40.703694,
    "longitude": -73.990399
  },
  "total_distance_miles": 2795.4,
  "duration_hours": 49.93,
  "fuel_stops": [
    {
      "station_name": "ERNIES TRUCK PLAZA",
      "address": "I-15, EXIT 112",
      "city": "Beaver",
      "state": "UT",
      "latitude": 38.274197,
      "longitude": -112.639501,
      "retail_price": 3.399,
      "cumulative_distance_covered": 490,
      "gallons_consumed_after_last_stop": 49,
      "fuel_cost": 166.55
    }
  ],
  "total_fuel_cost": 874.73,
  "total_gallons": 279.54
}
```

## External API Calls Per Request

| API | Calls | Purpose |
|-----|-------|---------|
| Mapbox Geocoding | 2 | Geocode start and finish addresses |
| OSRM | 1 | Calculate driving route |
| **Total** | **3** | |

Fuel station matching is done entirely locally against the database.
