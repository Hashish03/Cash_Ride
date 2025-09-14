from rest_framework import serializers
from .models import DriverRating, DriverAvailability
from rides.serializers import RideSerializer
import json

class LocationField(serializers.Field):
    """
    Custom field to handle location as latitude/longitude dictionary
    Replaces the GDAL PointField
    """
    def to_representation(self, value):
        if value and isinstance(value, dict):
            return {
                'latitude': value.get('latitude'),
                'longitude': value.get('longitude')
            }
        return None
    
    def to_internal_value(self, data):
        if isinstance(data, dict):
            return {
                'latitude': float(data.get('latitude')),
                'longitude': float(data.get('longitude'))
            }
        elif isinstance(data, str):
            try:
                coords = json.loads(data)
                return {
                    'latitude': float(coords.get('latitude')),
                    'longitude': float(coords.get('longitude'))
                }
            except (json.JSONDecodeError, ValueError):
                pass
        raise serializers.ValidationError(
            "Invalid location format. Expected {'latitude': x, 'longitude': y} or JSON string"
        )

class DriverRatingSerializer(serializers.ModelSerializer):
    ride = RideSerializer(read_only=True)
    
    class Meta:
        model = DriverRating
        fields = ['id', 'ride', 'rating', 'feedback', 'created_at']
        read_only_fields = ['id', 'ride', 'created_at']

class DriverStatusUpdateSerializer(serializers.Serializer):
    online = serializers.BooleanField()
    available = serializers.BooleanField()
    location = LocationField(required=False, allow_null=True)

class DriverAvailabilitySerializer(serializers.ModelSerializer):
    location = LocationField(required=False, allow_null=True)
    
    class Meta:
        model = DriverAvailability
        fields = [
            'is_available', 'last_online', 'location',
            'current_ride', 'preferred_areas', 'updated_at'
        ]
        read_only_fields = ['last_online', 'current_ride', 'updated_at']
        
        extra_kwargs = {
            'preferred_areas': {'required': False, 'allow_null': True}
        }