from django.db import models
from users.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

class DriverProfile(models.Model):

    DRIVER_STATUS = (
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('suspended', 'Suspended'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='driver_profile')
    status = models.CharField(max_length=20, choices=DRIVER_STATUS, default='pending')
    rating = models.FloatField(default=5.0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    total_rides = models.PositiveIntegerField(default=0)
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    online = models.BooleanField(default=False)
    available = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Background check information
    background_check_passed = models.BooleanField(default=False)
    background_check_date = models.DateField(null=True, blank=True)
    
    # Driver preferences
    preferred_ride_types = models.JSONField(default=list)  # List of ride types driver prefers
    auto_accept_rides = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Driver Profile: {self.user.email}"

class Vehicle(models.Model):

    VEHICLE_TYPES = (
        ('sedan', 'Sedan'),
        ('suv', 'SUV'),
        ('van', 'Van'),
        ('luxury', 'Luxury'),
        ('electric', 'Electric'),
    )
    
    VEHICLE_COLORS = (
        ('white', 'White'),
        ('black', 'Black'),
        ('silver', 'Silver'),
        ('red', 'Red'),
        ('blue', 'Blue'),
        ('other', 'Other'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    driver = models.ForeignKey(DriverProfile, on_delete=models.CASCADE, related_name='vehicles')
    make = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    year = models.PositiveIntegerField()
    color = models.CharField(max_length=20, choices=VEHICLE_COLORS)
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPES)
    license_plate = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Vehicle documents
    registration_valid = models.BooleanField(default=False)
    registration_expiry = models.DateField(null=True, blank=True)
    insurance_valid = models.BooleanField(default=False)
    insurance_expiry = models.DateField(null=True, blank=True)
    
    class Meta:
        ordering = ['-is_active', '-created_at']
    
    def __str__(self):
        return f"{self.year} {self.make} {self.model} ({self.license_plate})"


