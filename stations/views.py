from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiResponse
from stations.serializers import RouteRequestSerializer, RouteResponseSerializer
from stations.services.geocoding import geocode_address
from stations.services.routing import get_route
from stations.services.fuel_optimizer import find_optimal_fuel_stops
from stations.services.validators import validate_presence, validate_state


class RouteView(APIView):
    @extend_schema(
        request=RouteRequestSerializer,
        responses={
            200: RouteResponseSerializer,
            400: OpenApiResponse(description="Validation error (unknown fields, invalid state, missing required fields, or geocoding/routing failure)"),
        },
        description="Get optimal fuel stops along a route between two US locations",
    )
    def post(self, request):
        # Validate no unknown fields before serializer runs
        validate_presence(request.data.get("start", {}), label="start")
        validate_presence(request.data.get("finish", {}), label="finish")

        serializer = RouteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Validate and normalize state abbreviations
        data["start"]["state"] = validate_state(data["start"]["state"], label="start")
        data["finish"]["state"] = validate_state(data["finish"]["state"], label="finish")

        start_loc = data["start"]
        start_coords = geocode_address(
            street=start_loc["street"],
            city=start_loc["city"],
            state=start_loc["state"],
        )
        if not start_coords:
            return Response(
                {"error": "Could not geocode start location"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        finish_loc = data["finish"]
        finish_coords = geocode_address(
            street=finish_loc["street"],
            city=finish_loc["city"],
            state=finish_loc["state"],
        )
        if not finish_coords:
            return Response(
                {"error": "Could not geocode finish location"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        route = get_route(start_coords, finish_coords)
        if not route:
            return Response(
                {"error": "Could not find a route between the locations"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = find_optimal_fuel_stops(route["geometry"], route["distance_miles"])

        fuel_stops = []
        for stop in result["fuel_stops"]:
            station = stop["station"]
            fuel_stops.append({
                "station_name": station.name,
                "address": station.address,
                "city": station.city,
                "state": station.state,
                "latitude": station.latitude,
                "longitude": station.longitude,
                "retail_price": station.retail_price,
                "cumulative_distance_covered": round(stop["mile_marker"], 1),
                "gallons_consumed_after_last_stop": round(stop["gallons_needed"], 2),
                "fuel_cost": round(stop["fuel_cost"], 2),
            })

        response_data = {
            "start": {
                "address": f"{start_loc['street']}, {start_loc['city']}, {start_loc['state']}",
                "latitude": start_coords[0],
                "longitude": start_coords[1],
            },
            "finish": {
                "address": f"{finish_loc['street']}, {finish_loc['city']}, {finish_loc['state']}",
                "latitude": finish_coords[0],
                "longitude": finish_coords[1],
            },
            "total_distance_miles": round(route["distance_miles"], 1),
            "duration_hours": round(route["duration_seconds"] / 3600, 2),
            "fuel_stops": fuel_stops,
            "total_fuel_cost": result["total_fuel_cost"],
            "total_gallons": result["total_gallons"],
        }

        return Response(response_data, status=status.HTTP_200_OK)
