from rest_framework import serializers
from .models import Ride, RideLocationUpdate, DriverLocation, RideRequestLog, CancellationReason
from users.serializers import UserProfileSerializer
from payments.serializers import TransactionSerializer
from django.contrib.gis.geos import Point
import json

class PointField(serializers.Field):
    def to_representation(self, value):
        if value:
            return {'latitude': value.y, 'longitude': value.x}
        return None
    
    def to_internal_value(self, data):
        if isinstance(data, dict):
            return Point(float(data['longitude']), float(data['latitude']))
        elif isinstance(data, str):
            coords = json.loads(data)
            return Point(float(coords['longitude']), float(coords['latitude']))
        raise serializers.ValidationError("Invalid format for Point field")

class RideSerializer(serializers.ModelSerializer):
    pickup_location = PointField()
    dropoff_location = PointField(required=False, allow_null=True)
    rider = UserProfileSerializer(read_only=True)
    driver = UserProfileSerializer(read_only=True)
    payment = TransactionSerializer(read_only=True)
    
    class Meta:
        model = Ride
        fields = [
            'id', 'rider', 'driver', 'status', 'ride_type',
            'pickup_location', 'pickup_address',
            'dropoff_location', 'dropoff_address',
            'requested_at', 'accepted_at', 'arrived_at',
            'started_at', 'completed_at',
            'base_fare', 'distance_fare', 'time_fare',
            'surge_multiplier', 'total_fare',
            'estimated_distance', 'estimated_duration',
            'actual_distance', 'actual_duration',
            'rider_rating', 'driver_rating', 'notes',
            'payment'
        ]
        read_only_fields = [
            'id', 'rider', 'driver', 'status',
            'requested_at', 'accepted_at', 'arrived_at',
            'started_at', 'completed_at',
            'base_fare', 'distance_fare', 'time_fare',
            'surge_multiplier', 'total_fare',
            'estimated_distance', 'estimated_duration',
            'actual_distance', 'actual_duration',
            'payment'
        ]

class RideRequestSerializer(serializers.Serializer):
    pickup_location = PointField()
    pickup_address = serializers.CharField(max_length=255)
    dropoff_location = PointField(required=False, allow_null=True)
    dropoff_address = serializers.CharField(max_length=255, required=False, allow_null=True)
    ride_type = serializers.ChoiceField(choices=Ride.RIDE_TYPES)
    
    def validate(self, data):
        if not data.get('dropoff_location') and not data.get('dropoff_address'):
            raise serializers.ValidationError("Either dropoff location or address is required")
        return data

class RideLocationUpdateSerializer(serializers.ModelSerializer):
    location = PointField()
    
    class Meta:
        model = RideLocationUpdate
        fields = ['ride', 'location', 'timestamp', 'is_driver_location']
        read_only_fields = ['timestamp']

class DriverLocationSerializer(serializers.ModelSerializer):
    location = PointField()
    
    class Meta:
        model = DriverLocation
        fields = ['driver', 'location', 'last_updated', 'is_available']
        read_only_fields = ['driver', 'last_updated']

class RideStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[
        ('accepted', 'Accepted'),
        ('arrived', 'Arrived'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ])
    current_location = PointField(required=False, allow_null=True)

class RideRatingSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    feedback = serializers.CharField(required=False, allow_blank=True)

class CancellationReasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = CancellationReason
        fields = ['ride', 'cancelled_by', 'reason', 'timestamp']
        read_only_fields = ['ride', 'timestamp']

class RideEstimateSerializer(serializers.Serializer):
    pickup_location = PointField()
    dropoff_location = PointField()
    ride_type = serializers.ChoiceField(choices=Ride.RIDE_TYPES)
    
    def validate(self, data):
        if data['pickup_location'] == data['dropoff_location']:
            raise serializers.ValidationError("Pickup and dropoff locations cannot be the same")
        return data