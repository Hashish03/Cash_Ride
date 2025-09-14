# backend/utils/notifications.py
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import requests
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    """
    Unified notification service for email and SMS
    """
    
    def __init__(self):
        self.email_enabled = hasattr(settings, 'EMAIL_HOST')
        self.sms_enabled = hasattr(settings, 'SMS_API_KEY')
    
    def send_welcome_email(self, user, verification_link=None):
        """Send welcome email to new user"""
        if not self.email_enabled:
            return False
        
        try:
            subject = 'Welcome to Cash Ride!'
            template = 'emails/welcome.html'
            
            context = {
                'user': user,
                'verification_link': verification_link,
                'app_name': 'Cash Ride',
                'support_email': settings.DEFAULT_FROM_EMAIL,
            }
            
            html_message = render_to_string(template, context)
            
            send_mail(
                subject=subject,
                message='',  # Plain text version
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info(f"Welcome email sent to {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send welcome email: {str(e)}")
            return False
    
    def send_password_reset_email(self, user, reset_link):
        """Send password reset email"""
        if not self.email_enabled:
            return False
        
        try:
            subject = 'Reset Your Cash Ride Password'
            template = 'emails/password_reset.html'
            
            context = {
                'user': user,
                'reset_link': reset_link,
                'app_name': 'Cash Ride',
                'support_email': settings.DEFAULT_FROM_EMAIL,
            }
            
            html_message = render_to_string(template, context)
            
            send_mail(
                subject=subject,
                message='',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info(f"Password reset email sent to {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send password reset email: {str(e)}")
            return False
    
    def send_security_alert_email(self, user, alert_type, ip_address=None, device_info=None):
        """Send security alert email"""
        if not self.email_enabled:
            return False
        
        try:
            subject = 'Security Alert - Cash Ride Account'
            template = 'emails/security_alert.html'
            
            context = {
                'user': user,
                'alert_type': alert_type,
                'ip_address': ip_address,
                'device_info': device_info,
                'app_name': 'Cash Ride',
                'support_email': settings.DEFAULT_FROM_EMAIL,
            }
            
            html_message = render_to_string(template, context)
            
            send_mail(
                subject=subject,
                message='',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info(f"Security alert email sent to {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send security alert email: {str(e)}")
            return False
    
    def send_sms(self, phone_number, message):
        """Send SMS using configured SMS service"""
        if not self.sms_enabled:
            return False
        
        try:
            # Example using Twilio (adjust based on your SMS provider)
            from twilio.rest import Client
            
            client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
            
            message = client.messages.create(
                body=message,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=phone_number
            )
            
            logger.info(f"SMS sent to {phone_number}: {message.sid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send SMS: {str(e)}")
            return False
