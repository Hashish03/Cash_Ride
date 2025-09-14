from rest_framework import serializers
from .models import (DriverProfile, Vehicle)
from users.serializers import UserProfileSerializer
import json

class DriverProfileSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = DriverProfile
        fields = [
            'user', 'status', 'rating', 'total_rides', 'total_earnings',
            'online', 'available', 'background_check_passed',
            'background_check_date', 'preferred_ride_types',
            'auto_accept_rides', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'user', 'status', 'rating', 'total_rides', 'total_earnings',
            'created_at', 'updated_at'
        ]

class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = [
            'id', 'make', 'model', 'year', 'color', 'vehicle_type',
            'license_plate', 'is_active', 'registration_valid',
            'registration_expiry', 'insurance_valid', 'insurance_expiry',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class DriverRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=30)
    last_name = serializers.CharField(max_length=30)
    phone_number = serializers.CharField(max_length=20)
    
    # Vehicle information
    make = serializers.CharField(max_length=50)
    model = serializers.CharField(max_length=50)
    year = serializers.IntegerField()
    color = serializers.CharField(max_length=20)
    vehicle_type = serializers.CharField(max_length=20)
    license_plate = serializers.CharField(max_length=20)
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists")
        return value

