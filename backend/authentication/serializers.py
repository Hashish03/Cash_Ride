from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import UserSession

User = get_user_model()

class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    User registration serializer
    """
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    user_type = serializers.ChoiceField(choices=User.USER_TYPES, default='rider')
    
    class Meta:
        model = User
        fields = [
            'email', 'phone_number', 'password', 'confirm_password',
            'full_name', 'user_type', 'date_of_birth'
        ]
    
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords don't match")
        return data
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered")
        return value
    
    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("Phone number already registered")
        return value

class LoginSerializer(serializers.Serializer):
    """
    Login serializer supporting email/phone
    """
    username = serializers.CharField()  # Can be email or phone
    password = serializers.CharField()
    device_id = serializers.CharField(required=False)
    platform = serializers.CharField(required=False)

class OTPRequestSerializer(serializers.Serializer):
    """
    OTP request serializer
    """
    phone_number = serializers.CharField()

class OTPVerifySerializer(serializers.Serializer):
    """
    OTP verification serializer
    """
    phone_number = serializers.CharField()
    otp_code = serializers.CharField(max_length=6)
    device_id = serializers.CharField(required=False)
    platform = serializers.CharField(required=False)

class SocialLoginSerializer(serializers.Serializer):
    """
    Social login serializer
    """
    provider = serializers.ChoiceField(choices=['google', 'facebook', 'apple'])
    access_token = serializers.CharField()
    device_id = serializers.CharField(required=False)
    platform = serializers.CharField(required=False)

class TokenRefreshSerializer(serializers.Serializer):
    """
    Token refresh serializer
    """
    refresh_token = serializers.CharField()

class UserProfileSerializer(serializers.ModelSerializer):
    """
    User profile serializer
    """
    class Meta:
        model = User
        fields = [
            'id', 'email', 'phone_number', 'full_name', 'user_type',
            'profile_picture', 'is_email_verified', 'is_phone_verified',
            'two_factor_enabled', 'created_at'
        ]
        read_only_fields = [
            'id', 'email', 'phone_number', 'is_email_verified', 
            'is_phone_verified', 'created_at'
        ]