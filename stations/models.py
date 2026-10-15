from django.db import models


class CityLocation(models.Model):
    city = models.CharField(max_length=255)
    state = models.CharField(max_length=2)
    latitude = models.FloatField()
    longitude = models.FloatField()

    class Meta:
        unique_together = ("city", "state")

    def __str__(self):
        return f"{self.city}, {self.state}"


class FuelStation(models.Model):
    opis_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    state = models.CharField(max_length=2)
    rack_id = models.IntegerField()
    retail_price = models.FloatField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    city_location = models.ForeignKey(
        CityLocation, on_delete=models.CASCADE, related_name="stations"
    )

    def __str__(self):
        return f"{self.name} ({self.city}, {self.state}) - ${self.retail_price}"
