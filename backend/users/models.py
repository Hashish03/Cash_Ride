from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """Extended user model with Supabase UUID"""
    supabase_id = models.CharField(max_length=255, unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    profile_picture = models.URLField(blank=True, null=True)
    
    # Social login fields
    social_provider = models.CharField(max_length=50, blank=True, null=True)
    social_uid = models.CharField(max_length=255, blank=True, null=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return self.email

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True, null=True)
    preferred_language = models.CharField(max_length=10, default='en')
    terms_accepted = models.BooleanField(default=False)
    marketing_opt_in = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Profile of {self.user.email}"        