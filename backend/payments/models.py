# models.py for payments app

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from decimal import Decimal

User = get_user_model()


class PaymentMethod(models.Model):
    """Stores user's payment methods"""
    PAYMENT_TYPES = (
        ('card', 'Credit/Debit Card'),
        ('bank', 'Bank Account'),
        ('wallet', 'Digital Wallet'),
        ('cash', 'Cash'),
        ('paypal', 'PayPal'),
        ('upi', 'UPI'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_methods')
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES)
    is_primary = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    
    # Generic fields that can store different payment method details
    provider = models.CharField(max_length=50, blank=True)  # stripe, paypal, etc.
    token = models.CharField(max_length=255, blank=True)  # Payment method token from gateway
    last_four = models.CharField(max_length=4, blank=True)  # Last 4 digits of card/account
    expiry_month = models.PositiveSmallIntegerField(null=True, blank=True)
    expiry_year = models.PositiveSmallIntegerField(null=True, blank=True)
    
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_primary', '-created_at']
        unique_together = ['user', 'token']  # Prevent duplicate tokens
    
    def __str__(self):
        return f"{self.user.email} - {self.payment_type}"


class Transaction(models.Model):
    """Records all payment transactions"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
    )
    
    GATEWAY_CHOICES = (
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('razorpay', 'Razorpay'),
        ('square', 'Square'),
        ('cash', 'Cash'),
        ('wallet', 'Wallet'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    transaction_id = models.CharField(max_length=100, unique=True)
    gateway = models.CharField(max_length=20, choices=GATEWAY_CHOICES)
    payment_method_type = models.CharField(max_length=20)
    
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    # Gateway-specific IDs
    gateway_transaction_id = models.CharField(max_length=100, blank=True)
    gateway_response = models.JSONField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['transaction_id']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['gateway', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.transaction_id} - {self.amount} {self.currency} - {self.status}"
    
    @property
    def is_successful(self):
        return self.status in ['completed', 'refunded', 'partially_refunded']
    
    @property
    def can_refund(self):
        return self.status == 'completed' and self.amount > Decimal('0.00')


class Refund(models.Model):
    """Records refunds for transactions"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )
    
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='refunds')
    refund_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    gateway_refund_id = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Refund {self.refund_id} - {self.amount} {self.currency}"


class Wallet(models.Model):
    """Digital wallet for users"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Wallet settings
    is_active = models.BooleanField(default=True)
    auto_reload = models.BooleanField(default=False)
    auto_reload_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )
    auto_reload_threshold = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.email} - {self.balance} {settings.DEFAULT_CURRENCY}"
    
    def can_pay(self, amount):
        return self.balance >= amount and self.is_active
    
    def add_funds(self, amount, description="Deposit"):
        """Add funds to wallet"""
        self.balance += amount
        self.save()
        
        # Record transaction
        self.transactions.create(
            transaction_type='credit',
            amount=amount,
            description=description,
            balance_after=self.balance
        )
        return self.balance
    
    def deduct_funds(self, amount, description="Payment"):
        """Deduct funds from wallet"""
        if not self.can_pay(amount):
            raise ValidationError("Insufficient funds or wallet inactive")
        
        self.balance -= amount
        self.save()
        
        # Record transaction
        self.transactions.create(
            transaction_type='debit',
            amount=amount,
            description=description,
            balance_after=self.balance
        )
        return self.balance


class WalletTransaction(models.Model):
    """Records all wallet transactions"""
    TRANSACTION_TYPES = (
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    )
    
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField()
    reference_id = models.CharField(max_length=100, blank=True)  # Links to external transaction
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.wallet.user.email} - {self.transaction_type} {self.amount}"