# backend/security/logging.py
import logging
from django.utils import timezone
from django.db import models
import json

class SecurityLog(models.Model):
    """
    Security events logging model
    """
    EVENT_TYPES = [
        ('auth_attempt', 'Authentication Attempt'),
        ('auth_success', 'Authentication Success'),
        ('auth_failure', 'Authentication Failure'),
        ('suspicious_activity', 'Suspicious Activity'),
        ('data_access', 'Data Access'),
        ('permission_denied', 'Permission Denied'),
        ('account_locked', 'Account Locked'),
        ('password_change', 'Password Change'),
        ('profile_update', 'Profile Update'),
    ]
    
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    user_id = models.CharField(max_length=255, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    description = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    severity = models.CharField(
        max_length=10,
        choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')],
        default='medium'
    )
    
    class Meta:
        db_table = 'security_logs'
        indexes = [
            models.Index(fields=['event_type', 'timestamp']),
            models.Index(fields=['user_id', 'timestamp']),
            models.Index(fields=['ip_address', 'timestamp']),
            models.Index(fields=['severity', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.event_type} - {self.user_id} - {self.timestamp}"

class SecurityLogger:
    """
    Security logging utility class
    """
    
    def __init__(self):
        self.logger = logging.getLogger('security')
    
    def log_auth_attempt(self, user_id=None, ip_address=None, success=True, 
                        method='password', metadata=None):
        """Log authentication attempt"""
        event_type = 'auth_success' if success else 'auth_failure'
        severity = 'low' if success else 'medium'
        
        description = f"Authentication {'successful' if success else 'failed'} using {method}"
        
        SecurityLog.objects.create(
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            description=description,
            metadata=metadata or {},
            severity=severity
        )
        
        # Also log to file
        log_level = logging.INFO if success else logging.WARNING
        self.logger.log(log_level, f"Auth attempt: {description} - User: {user_id} - IP: {ip_address}")
    
    def log_suspicious_activity(self, description, user_id=None, ip_address=None, 
                              metadata=None, severity='high'):
        """Log suspicious activity"""
        SecurityLog.objects.create(
            event_type='suspicious_activity',
            user_id=user_id,
            ip_address=ip_address,
            description=description,
            metadata=metadata or {},
            severity=severity
        )
        
        self.logger.warning(f"Suspicious activity: {description} - User: {user_id} - IP: {ip_address}")
    
    def log_data_access(self, user_id, resource, action='read', metadata=None, sensitive=False):
        """Log data access events"""
        severity = 'high' if sensitive else 'low'
        description = f"Data access: {action} on {resource}"
        
        SecurityLog.objects.create(
            event_type='data_access',
            user_id=user_id,
            description=description,
            metadata=metadata or {},
            severity=severity
        )
        
        log_level = logging.WARNING if sensitive else logging.INFO
        self.logger.log(log_level, f"Data access: {description} - User: {user_id}")
    
    def log_permission_denied(self, user_id, resource, action, ip_address=None):
        """Log permission denied events"""
        description = f"Permission denied: {action} on {resource}"
        
        SecurityLog.objects.create(
            event_type='permission_denied',
            user_id=user_id,
            ip_address=ip_address,
            description=description,
            severity='medium'
        )
        
        self.logger.warning(f"Permission denied: {description} - User: {user_id} - IP: {ip_address}")
    
    def log_account_locked(self, user_id, reason, ip_address=None):
        """Log account lockout events"""
        description = f"Account locked: {reason}"
        
        SecurityLog.objects.create(
            event_type='account_locked',
            user_id=user_id,
            ip_address=ip_address,
            description=description,
            severity='high'
        )
        
        self.logger.error(f"Account locked: {description} - User: {user_id} - IP: {ip_address}")
