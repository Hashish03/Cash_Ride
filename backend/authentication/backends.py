from django.contrib.auth.backends import BaseBackend
from django.utils import timezone  # Add this import at the top
from datetime import timedelta
from django.contrib.auth import get_user_model
from .supabase_service import supabase_auth
from .sync_service import UserSyncService
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

class SupabaseAuthBackend(BaseBackend):
    """
    Authenticate against Supabase and sync with Django user
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate user with Supabase
        """
        if not username or not password:
            return None
        
        try:
            # Try email authentication first
            success, result = supabase_auth.login_user(username, password)
            
            if not success:
                # Try phone authentication if email fails and username looks like phone
                if username.startswith('+') or username.isdigit():
                    success, result = supabase_auth.login_with_phone(username, password)
            
            if success:
                # Sync user with Django
                user = UserSyncService.sync_user_from_supabase(result)
                
                # Update login information
                user.last_login_ip = UserSyncService.get_client_ip(request) if request else None
                user.failed_login_attempts = 0
                user.save()
                
                return user
            else:
                # Handle failed login
                if request:
                    self.handle_failed_login(username, request)
                
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
        
        return None
    
    def get_user(self, user_id):
        """
        Get user by ID
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
    
    def handle_failed_login(self, username, request):
        """
        Handle failed login attempts
        """
        try:
            # Try to find user by username/email/phone
            user = None
            try:
                user = User.objects.get(email=username)
            except User.DoesNotExist:
                try:
                    user = User.objects.get(phone_number=username)
                except User.DoesNotExist:
                    pass
            
            if user:
                user.failed_login_attempts += 1
                user.last_failed_login = timezone.now()
                
                # Lock account after 5 failed attempts
                if user.failed_login_attempts >= 5:
                    user.account_locked_until = timezone.now() + timedelta(minutes=30)
                
                user.save()
                
        except Exception as e:
            logger.error(f"Failed login handling error: {str(e)}")

class TokenAuthBackend(BaseBackend):
    """
    Authenticate using Supabase JWT token
    """
    
    def authenticate(self, request, token=None, **kwargs):
        """
        Authenticate user with Supabase JWT token
        """
        if not token:
            return None
        
        try:
            # Verify token with Supabase
            success, result = supabase_auth.verify_token(token)
            
            if success:
                supabase_uid = result.get('user_id')
                
                # Find Django user
                try:
                    user = User.objects.get(supabase_uid=supabase_uid)
                    return user
                except User.DoesNotExist:
                    # Create user if not exists (for social login cases)
                    user_data = {
                        'user_id': supabase_uid,
                        'email': result.get('email'),
                        'phone': result.get('phone'),
                    }
                    return UserSyncService.sync_user_from_supabase(user_data)
            
        except Exception as e:
            logger.error(f"Token authentication error: {str(e)}")
        
        return None