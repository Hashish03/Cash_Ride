from django.db import models
from drivers.models import DriverProfile
from django.core.validators import MinValueValidator, MaxValueValidator

class DriverAvailability(models.Model):
    # Replace PointField with:
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    # Other existing fields...
    is_available = models.BooleanField(default=False)
    last_online = models.DateTimeField(auto_now=True)
    current_ride = models.ForeignKey(
        'rides.Ride', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    preferred_areas = models.JSONField(null=True, blank=True)
    
    @property
    def location(self):
        if self.latitude and self.longitude:
            return {
                'latitude': self.latitude,
                'longitude': self.longitude
            }
        return None
    
    @location.setter
    def location(self, value):
        if value and isinstance(value, dict):
            self.latitude = value.get('latitude')
            self.longitude = value.get('longitude')
        else:
            self.latitude = None
            self.longitude = None


class DriverRating(models.Model):
    
    driver = models.ForeignKey(DriverProfile, on_delete=models.CASCADE, related_name='ratings')
    ride = models.OneToOneField('rides.Ride', on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    feedback = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Rating: {self.rating} for {self.driver.user.email}"