from django.db import models
from users.models import User
from payments.models import Transaction
from django.core.validators import MinValueValidator
from django.utils import timezone
import uuid

class Ride(models.Model):
    STATUS_CHOICES = (
        ('requested', 'Requested'),
        ('accepted', 'Accepted'),
        ('driver_assigned', 'Driver Assigned'),
        ('arrived', 'Driver Arrived'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    RIDE_TYPES = (
        ('standard', 'Standard'),
        ('premium', 'Premium'),
        ('xl', 'XL'),
        ('pet', 'Pet Friendly'),
        ('shared', 'Shared'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rides_as_rider')
    driver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='rides_as_driver')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='requested')
    ride_type = models.CharField(max_length=20, choices=RIDE_TYPES, default='standard')
    
    # Location fields
    pickup_latitude = models.FloatField()
    pickup_longitude = models.FloatField()
    dropoff_latitude = models.FloatField(null=True, blank=True)
    dropoff_longitude = models.FloatField(null=True, blank=True)
    
    # Timing fields
    requested_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    arrived_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Pricing fields
    base_fare = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    distance_fare = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    time_fare = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    surge_multiplier = models.DecimalField(max_digits=3, decimal_places=1, default=1.0)
    total_fare = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    
    # Payment reference
    payment = models.OneToOneField(Transaction, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Additional info
    estimated_distance = models.FloatField(help_text="Distance in meters", null=True, blank=True)
    estimated_duration = models.FloatField(help_text="Duration in seconds", null=True, blank=True)
    actual_distance = models.FloatField(null=True, blank=True)
    actual_duration = models.FloatField(null=True, blank=True)
    
    rider_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    driver_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['rider', 'status']),
            models.Index(fields=['driver', 'status']),
        ]
    
    def __str__(self):
        return f"Ride {self.id} - {self.get_status_display()}"

class RideNotification(models.Model):
    NOTIFICATION_TYPES = (
        ('driver_assigned', 'Driver Assigned'),
        ('ride_request', 'Ride Request'),
        ('ride_accepted', 'Ride Accepted'),
        ('ride_rejected', 'Ride Rejected'),
        ('ride_started', 'Ride Started'),
        ('ride_completed', 'Ride Completed'),
        ('ride_cancelled', 'Ride Cancelled'),
        ('payment_received', 'Payment Received'),
        ('driver_arrived', 'Driver Arrived'),
        ('rating_received', 'Rating Received'),
    )
    
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name='notifications')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ride_notifications')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    additional_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Ride Notification'
        verbose_name_plural = 'Ride Notifications'
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.get_notification_type_display()} - {self.recipient.email}"

    def mark_as_read(self):
        self.is_read = True
        self.save()

class RideLocationUpdate(models.Model):
    ride = models.ForeignKey('Ride', on_delete=models.CASCADE)
    latitude = models.FloatField()
    longitude = models.FloatField()
    is_driver_location = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['ride', 'is_driver_location']),
            models.Index(fields=['timestamp'])
        ]

    def __str__(self):
        return f"Location update for ride {self.ride_id} at {self.timestamp}"

class DriverLocation(models.Model):
    driver = models.OneToOneField(User, on_delete=models.CASCADE, related_name='location')
    location = models.CharField(max_length=255)
    last_updated = models.DateTimeField(auto_now=True)
    is_available = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-last_updated']
    
    def __str__(self):
        return f"Location for {self.driver.email}"

class RideRequestLog(models.Model):
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name='request_logs')
    driver = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=(
        ('sent', 'Sent'),
        ('rejected', 'Rejected'),
        ('timeout', 'Timeout'),
    ))
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"Request log for {self.ride.id} - {self.driver.email}"

class CancellationReason(models.Model):
    ride = models.OneToOneField(Ride, on_delete=models.CASCADE, related_name='cancellation_reason')
    cancelled_by = models.CharField(max_length=10, choices=(
        ('rider', 'Rider'),
        ('driver', 'Driver'),
        ('system', 'System'),
    ))
    reason = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)