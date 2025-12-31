from django.contrib.auth import get_user_model
from .supabase_service import supabase_auth
from .models import UserSession
from django.utils import timezone
from datetime import timedelta
import logging
import uuid

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
        
        Args:
            supabase_user_data: Dict containing user data from Supabase
                Expected keys: user_id, email, phone, metadata, email_confirmed, phone_confirmed
        
        Returns:
            User: Django user instance
        """
        supabase_uid = supabase_user_data.get('user_id')
        email = supabase_user_data.get('email')
        phone = supabase_user_data.get('phone')
        user_metadata = supabase_user_data.get('user_metadata', {}) or supabase_user_data.get('metadata', {})
        
        if not supabase_uid:
            logger.error("No supabase_uid provided in sync data")
            raise ValueError("supabase_uid is required for user sync")
        
        try:
            # Try to find existing user by supabase_uid first (most reliable)
            user = None
            try:
                user = User.objects.get(supabase_uid=supabase_uid)
                logger.info(f"Found existing user by supabase_uid: {supabase_uid}")
            except User.DoesNotExist:
                pass
            
            # Try by email if not found
            if not user and email:
                try:
                    user = User.objects.get(email=email)
                    user.supabase_uid = supabase_uid
                    logger.info(f"Found existing user by email: {email}")
                except User.DoesNotExist:
                    pass
            
            # Try by phone if not found
            if not user and phone:
                try:
                    user = User.objects.get(phone_number=phone)
                    user.supabase_uid = supabase_uid
                    logger.info(f"Found existing user by phone: {phone}")
                except User.DoesNotExist:
                    pass
            
            # Create new user if not found
            if not user:
                user_data = {
                    'email': email,
                    'phone_number': phone,
                    'supabase_uid': supabase_uid,
                    'full_name': user_metadata.get('full_name', ''),
                    'user_type': user_metadata.get('user_type', 'rider'),
                    'is_email_verified': supabase_user_data.get('email_confirmed', False),
                    'is_phone_verified': supabase_user_data.get('phone_confirmed', False),
                }
                
                # Username is required by default User model
                user_data['username'] = email or phone or f"user_{uuid.uuid4().hex[:8]}"
                
                user = User.objects.create(**user_data)
                logger.info(f"Created new user: {user.email or user.phone_number}")
            else:
                # Update existing user information
                user.is_email_verified = supabase_user_data.get('email_confirmed', user.is_email_verified)
                user.is_phone_verified = supabase_user_data.get('phone_confirmed', user.is_phone_verified)
                
                # Update from metadata if provided
                if 'full_name' in user_metadata and user_metadata['full_name']:
                    user.full_name = user_metadata['full_name']
                if 'user_type' in user_metadata and user_metadata['user_type']:
                    user.user_type = user_metadata['user_type']
                if 'profile_picture' in user_metadata and user_metadata['profile_picture']:
                    user.profile_picture = user_metadata['profile_picture']
                
                # Update email/phone if they were missing
                if email and not user.email:
                    user.email = email
                if phone and not user.phone_number:
                    user.phone_number = phone
                
                logger.info(f"Updated existing user: {user.id}")
            
            user.save()
            return user
            
        except Exception as e:
            logger.error(f"User sync error: {str(e)}", exc_info=True)
            raise
    
    @staticmethod
    def create_user_session(
        user: User, 
        access_token: str,
        refresh_token: str,
        device_id: str = None,
        platform: str = 'web',
        request = None
    ) -> UserSession:
        """
        Create or update user session record
        
        Args:
            user: Django user instance
            access_token: Supabase access token
            refresh_token: Supabase refresh token
            device_id: Unique device identifier
            platform: Platform type (web, android, ios)
            request: Django request object (optional)
        
        Returns:
            UserSession: Created or updated session
        """
        if user is None:
            logger.error("User object is None in create_user_session")
            raise ValueError("User object cannot be None")
        
        # Verify token to get expiry
        token_valid, token_data = supabase_auth.verify_token(access_token)
        if not token_valid:
            logger.warning("Invalid access token provided for session creation")
        
        # Generate device_id if not provided
        if not device_id:
            device_id = f"{platform}_{uuid.uuid4().hex[:12]}"
        
        # Get IP and user agent
        ip_address = None
        user_agent = ''
        if request:
            ip_address = UserSyncService.get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Calculate expiry time (default 1 hour if not in token)
        expires_in = 3600  # Default 1 hour
        if token_valid and token_data.get('exp'):
            expires_at = timezone.datetime.fromtimestamp(
                token_data['exp'], 
                tz=timezone.get_current_timezone()
            )
        else:
            expires_at = timezone.now() + timedelta(seconds=expires_in)
        
        # Expire old sessions for this device (keep history)
        UserSession.objects.filter(
            user=user,
            device_id=device_id,
            is_active=True
        ).update(is_active=False)
        
        # Create new session
        session = UserSession.objects.create(
            user=user,
            device_id=device_id,
            platform=platform,
            refresh_token=refresh_token,
            ip_address=ip_address,
            user_agent=user_agent,
            is_active=True,
            expires_at=expires_at
        )
        
        logger.info(f"Created session for user {user.id} on device {device_id}")
        return session
    
    @staticmethod
    def update_user_session(
        user: User,
        device_id: str,
        refresh_token: str = None,
        is_active: bool = None
    ) -> UserSession:
        """
        Update existing user session
        
        Args:
            user: Django user instance
            device_id: Device identifier
            refresh_token: New refresh token (optional)
            is_active: Active status (optional)
        
        Returns:
            UserSession: Updated session or None
        """
        try:
            session = UserSession.objects.get(
                user=user,
                device_id=device_id,
                is_active=True
            )
            
            if refresh_token:
                session.refresh_token = refresh_token
            
            if is_active is not None:
                session.is_active = is_active
            
            session.last_activity = timezone.now()
            session.save()
            
            logger.info(f"Updated session for user {user.id} on device {device_id}")
            return session
            
        except UserSession.DoesNotExist:
            logger.warning(f"No active session found for user {user.id} on device {device_id}")
            return None
    
    @staticmethod
    def get_client_ip(request) -> str:
        """
        Get client IP address from request
        
        Args:
            request: Django request object
        
        Returns:
            str: Client IP address
        """
        # Check for proxy headers first
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # X-Forwarded-For can contain multiple IPs, get the first one
            return x_forwarded_for.split(',')[0].strip()
        
        # Check for other common proxy headers
        x_real_ip = request.META.get('HTTP_X_REAL_IP')
        if x_real_ip:
            return x_real_ip.strip()
        
        # Fall back to REMOTE_ADDR
        return request.META.get('REMOTE_ADDR', '')
    
    @staticmethod
    def invalidate_user_sessions(user: User, device_id: str = None):
        """
        Invalidate user sessions
        
        Args:
            user: Django user instance
            device_id: Optional device ID to invalidate specific device
        """
        try:
            query = UserSession.objects.filter(user=user, is_active=True)
            
            if device_id:
                query = query.filter(device_id=device_id)
                logger.info(f"Invalidating sessions for user {user.id} on device {device_id}")
            else:
                logger.info(f"Invalidating all sessions for user {user.id}")
            
            count = query.update(is_active=False)
            logger.info(f"Invalidated {count} session(s)")
            
        except Exception as e:
            logger.error(f"Error invalidating sessions: {str(e)}")
    
    @staticmethod
    def cleanup_expired_sessions():
        """
        Clean up expired sessions (can be run as periodic task)
        """
        try:
            expired_count = UserSession.objects.filter(
                expires_at__lt=timezone.now(),
                is_active=True
            ).update(is_active=False)
            
            logger.info(f"Cleaned up {expired_count} expired sessions")
            return expired_count
            
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {str(e)}")
            return 0
    
    @staticmethod
    def get_active_sessions(user: User):
        """
        Get all active sessions for a user
        
        Args:
            user: Django user instance
        
        Returns:
            QuerySet: Active user sessions
        """
        return UserSession.objects.filter(
            user=user,
            is_active=True,
            expires_at__gt=timezone.now()
        ).order_by('-created_at')
    
    @staticmethod
    def sync_user_from_token(access_token: str) -> User:
        """
        Sync user from Supabase access token
        
        Args:
            access_token: Supabase JWT access token
        
        Returns:
            User: Django user instance
        """
        try:
            # Verify and decode token
            token_valid, token_data = supabase_auth.verify_token(access_token)
            
            if not token_valid:
                raise ValueError("Invalid access token")
            
            # Prepare sync data
            sync_data = {
                'user_id': token_data.get('sub'),
                'email': token_data.get('email'),
                'phone': token_data.get('phone'),
                'user_metadata': token_data.get('user_metadata', {}),
                'email_confirmed': bool(token_data.get('email_confirmed_at')),
                'phone_confirmed': bool(token_data.get('phone_confirmed_at')),
            }
            
            # Sync user
            user = UserSyncService.sync_user_from_supabase(sync_data)
            return user
            
        except Exception as e:
            logger.error(f"Error syncing user from token: {str(e)}")
            raise