from django.db import models
from users.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone

class PaymentMethod(models.Model):
    PAYMENT_TYPES = (
        ('card', 'Credit/Debit Card'),
        ('wallet', 'Digital Wallet'),
        ('bank', 'Bank Transfer'),
        ('cash', 'Cash'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_methods')
    payment_type = models.CharField(max_length=10, choices=PAYMENT_TYPES)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Card details (encrypted in production)
    card_last4 = models.CharField(max_length=4, blank=True, null=True)
    card_brand = models.CharField(max_length=20, blank=True, null=True)
    card_exp_month = models.CharField(max_length=2, blank=True, null=True)
    card_exp_year = models.CharField(max_length=4, blank=True, null=True)
    
    # Wallet details
    wallet_provider = models.CharField(max_length=50, blank=True, null=True)
    wallet_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Bank details
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    account_last4 = models.CharField(max_length=4, blank=True, null=True)
    
    class Meta:
        ordering = ['-is_default', '-created_at']
        verbose_name = 'Payment Method'
        verbose_name_plural = 'Payment Methods'
    
    def __str__(self):
        return f"{self.get_payment_type_display()} - {self.user.email}"

class Transaction(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('disputed', 'Disputed'),
    )
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='transactions')
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['transaction_id']),
            models.Index(fields=['user', 'status']),
        ]
    
    def __str__(self):
        return f"{self.transaction_id} - {self.amount} {self.currency}"

class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='USD')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Wallet - {self.user.email}"

class Payout(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payouts')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    payout_method = models.CharField(max_length=50)
    payout_reference = models.CharField(max_length=100, blank=True, null=True)
    initiated_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-initiated_at']
    
    def __str__(self):
        return f"Payout - {self.user.email} - {self.amount} {self.currency}"