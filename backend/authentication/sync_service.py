from django.contrib.auth import get_user_model
from .supabase_service import supabase_auth
from .models import UserSession
from django.utils import timezone
from datetime import timedelta
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

class UserSyncService:
    """
    Service to sync users between Supabase and Django
    """
    
    @staticmethod
    def sync_user_from_supabase(supabase_user_data: dict) -> User:
        """
        Create or update Django user from Supabase user data
        """
        supabase_uid = supabase_user_data.get('user_id')
        email = supabase_user_data.get('email')
        phone = supabase_user_data.get('phone')
        metadata = supabase_user_data.get('metadata', {})
        
        try:
            # Try to find existing user
            user = None
            if supabase_uid:
                try:
                    user = User.objects.get(supabase_uid=supabase_uid)
                except User.DoesNotExist:
                    pass
            
            if not user and email:
                try:
                    user = User.objects.get(email=email)
                    user.supabase_uid = supabase_uid
                except User.DoesNotExist:
                    pass
            
            if not user and phone:
                try:
                    user = User.objects.get(phone_number=phone)
                    user.supabase_uid = supabase_uid
                except User.DoesNotExist:
                    pass
            
            # Create new user if not found
            if not user:
                user = User.objects.create_user(
                    username=email or phone,
                    email=email,
                    phone_number=phone,
                    supabase_uid=supabase_uid
                )
                logger.info(f"Created new user: {user.email}")
            
            # Update user information
            user.is_email_verified = supabase_user_data.get('email_confirmed', False)
            user.is_phone_verified = supabase_user_data.get('phone_confirmed', False)
            
            # Update from metadata
            if 'full_name' in metadata:
                user.full_name = metadata['full_name']
            if 'user_type' in metadata:
                user.user_type = metadata['user_type']
            if 'profile_picture' in metadata:
                user.profile_picture = metadata['profile_picture']
            
            user.save()
            
            return user
            
        except Exception as e:
            logger.error(f"User sync error: {str(e)}")
            raise
    
    @staticmethod
    def create_user_session(user: User, session_data: dict, request) -> UserSession:
        """
        Create user session record
        """
        if user is None:
            logger.error("User object is None in create_user_session.")
            raise ValueError("User object cannot be None.")

        device_info = {
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'platform': session_data.get('platform', 'web'),
            'device_id': session_data.get('device_id'),
        }
        
        ip_address = UserSyncService.get_client_ip(request)
        
        # Expire old sessions (optional - for security)
        UserSession.objects.filter(
            user=user,
            expires_at__lt=timezone.now()
        ).delete()
        
        session = UserSession.objects.create(
            user=user,
            session_id=session_data.get('session_id', ''),
            device_info=device_info,
            ip_address=ip_address,
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            expires_at=timezone.now() + timedelta(
                seconds=session_data.get('expires_in', 3600)
            )
        )
        
        return session
    
    @staticmethod
    def get_client_ip(request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
    
    @staticmethod
    def invalidate_user_sessions(user: User):
        """Invalidate all user sessions"""
        UserSession.objects.filter(user=user, is_active=True).update(
            is_active=False
        )