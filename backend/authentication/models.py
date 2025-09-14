from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid
from security.encryption import EncryptedField

class CustomUser(AbstractUser):
    """
    Extended user model that syncs with Supabase Auth
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    supabase_uid = models.CharField(max_length=255, unique=True, null=True, blank=True)
    
    # Contact Information
    phone_number = EncryptedField(max_length=20, unique=True, null=True, blank=True)
    is_phone_verified = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    
    # User Type
    USER_TYPES = [
        ('rider', 'Rider'),
        ('driver', 'Driver'),
        ('admin', 'Admin'),
    ]
    user_type = models.CharField(max_length=10, choices=USER_TYPES, default='rider')
    
    # Profile Information
    full_name = models.CharField(max_length=255, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    profile_picture = models.URLField(blank=True)
    
    # Security Features
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = EncryptedField(blank=True, null=True)
    backup_codes = models.JSONField(default=list, blank=True)
    failed_login_attempts = models.IntegerField(default=0)
    last_failed_login = models.DateTimeField(null=True, blank=True)
    account_locked_until = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Social Auth
    google_id = models.CharField(max_length=255, blank=True, null=True)
    facebook_id = models.CharField(max_length=255, blank=True, null=True)
    apple_id = models.CharField(max_length=255, blank=True, null=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['phone_number']
    
    class Meta:
        db_table = 'auth_user'
        indexes = [
            models.Index(fields=['supabase_uid']),
            models.Index(fields=['phone_number']),
            models.Index(fields=['user_type']),
        ]
    
    def __str__(self):
        return f"{self.email} ({self.user_type})"
    
    def is_account_locked(self):
        """Check if account is temporarily locked"""
        if self.account_locked_until:
            from django.utils import timezone
            return timezone.now() < self.account_locked_until
        return False

class UserSession(models.Model):
    """Track active user sessions for security"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sessions')
    session_id = models.CharField(max_length=255, unique=True)
    device_info = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['session_id']),
        ]