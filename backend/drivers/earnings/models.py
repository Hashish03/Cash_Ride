from django.db import models
from drivers.models import DriverProfile
from rides.models import Ride
from django.core.validators import MinValueValidator

class DriverEarning(models.Model):
    driver = models.ForeignKey(DriverProfile, on_delete=models.CASCADE, related_name='earnings')
    ride = models.OneToOneField(Ride, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    commission = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    net_earnings = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    payment_status = models.CharField(max_length=20, choices=(
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('processing', 'Processing'),
    ), default='pending')
    payment_date = models.DateTimeField(null=True, blank=True)
    transaction_reference = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Earning: {self.driver.user.email} - {self.net_earnings}"

class Payout(models.Model):
    driver = models.ForeignKey(DriverProfile, on_delete=models.CASCADE, related_name='payouts')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    status = models.CharField(max_length=20, choices=(
        ('pending', 'Pending'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
    ), default='pending')
    method = models.CharField(max_length=50)
    reference = models.CharField(max_length=100, blank=True, null=True)
    initiated_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-initiated_at']
    
    def __str__(self):
        return f"Payout: {self.driver.user.email} - {self.amount}"