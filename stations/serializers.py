from rest_framework import serializers


class LocationSerializer(serializers.Serializer):
    street = serializers.CharField(max_length=255, allow_blank=False)
    city = serializers.CharField(max_length=255, allow_blank=False)
    state = serializers.CharField(max_length=2, min_length=2, allow_blank=False)


class RouteRequestSerializer(serializers.Serializer):
    start = LocationSerializer()
    finish = LocationSerializer()


class FuelStopSerializer(serializers.Serializer):
    station_name = serializers.CharField()
    address = serializers.CharField()
    city = serializers.CharField()
    state = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    retail_price = serializers.FloatField()
    cumulative_distance_covered = serializers.FloatField()
    gallons_consumed_after_last_stop = serializers.FloatField()
    fuel_cost = serializers.FloatField()


class RouteResponseSerializer(serializers.Serializer):
    start = serializers.DictField()
    finish = serializers.DictField()
    total_distance_miles = serializers.FloatField()
    duration_hours = serializers.FloatField()
    fuel_stops = FuelStopSerializer(many=True)
    total_fuel_cost = serializers.FloatField()
    total_gallons = serializers.FloatField()
