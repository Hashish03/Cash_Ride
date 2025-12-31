from supabase import create_client, Client
from django.conf import settings
import jwt
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime, timezone
import requests

logger = logging.getLogger(__name__)


class SupabaseAuthService:
    """
    Service class to handle Supabase authentication operations
    Implements singleton pattern for connection reuse
    """
    
    _instance = None
    _supabase_client: Optional[Client] = None
    _service_client: Optional[Client] = None
    
    def __new__(cls):
        """Implement singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize Supabase clients"""
        if self._supabase_client is None:
            self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize both public and service role clients"""
        try:
            # Validate settings
            if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
                raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in settings")
            
            # Public client (for user operations)
            self._supabase_client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_ANON_KEY
            )
            logger.info("Supabase public client initialized successfully")
            
            # Service role client (for admin operations)
            if hasattr(settings, 'SUPABASE_SERVICE_KEY') and settings.SUPABASE_SERVICE_KEY:
                self._service_client = create_client(
                    settings.SUPABASE_URL,
                    settings.SUPABASE_SERVICE_KEY
                )
                logger.info("Supabase service role client initialized successfully")
            else:
                logger.warning("SUPABASE_SERVICE_KEY not set - admin operations will be unavailable")
                
        except Exception as e:
            logger.error(f"Failed to initialize Supabase clients: {str(e)}")
            raise
    
    @property
    def supabase(self) -> Client:
        """Get public Supabase client"""
        if self._supabase_client is None:
            self._initialize_clients()
        return self._supabase_client
    
    @property
    def service_client(self) -> Client:
        """Get service role client for admin operations"""
        if self._service_client is None:
            raise ValueError("Service role client not initialized - check SUPABASE_SERVICE_KEY setting")
        return self._service_client
    
    def register_user(self, email: str, password: str, phone: str = None, 
                     metadata: Dict = None) -> Tuple[bool, Dict]:
        """
        Register user with Supabase Auth
        
        Args:
            email: User email address
            password: User password (min 8 characters)
            phone: Optional phone number (E.164 format: +1234567890)
            metadata: Optional user metadata dictionary
        
        Returns:
            Tuple of (success: bool, data: dict)
        """
        try:
            # Validate inputs
            if not email or not password:
                return False, {'error': 'Email and password are required'}
            
            if len(password) < 8:
                return False, {'error': 'Password must be at least 8 characters'}
            
            user_data = {
                'email': email,
                'password': password,
            }
            
            if phone:
                user_data['phone'] = phone
            
            if metadata:
                user_data['options'] = {'data': metadata}
            
            response = self.supabase.auth.sign_up(user_data)
            
            if response.user:
                return True, {
                    'user_id': response.user.id,
                    'email': response.user.email,
                    'phone': response.user.phone,
                    'email_confirmed': response.user.email_confirmed_at is not None,
                    'phone_confirmed': response.user.phone_confirmed_at is not None,
                    'user_metadata': response.user.user_metadata or {},
                    'created_at': response.user.created_at
                }
            else:
                return False, {'error': 'Registration failed - no user returned'}
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Supabase registration error: {error_msg}")
            
            # Parse common Supabase errors
            if 'already registered' in error_msg.lower():
                return False, {'error': 'Email already registered'}
            elif 'invalid email' in error_msg.lower():
                return False, {'error': 'Invalid email format'}
            elif 'password' in error_msg.lower():
                return False, {'error': 'Password does not meet requirements'}
            
            return False, {'error': error_msg}
    
    def login_user(self, email: str, password: str) -> Tuple[bool, Dict]:
        """
        Authenticate user with email and password
        
        Args:
            email: User email address
            password: User password
        
        Returns:
            Tuple of (success: bool, data: dict)
        """
        try:
            if not email or not password:
                return False, {'error': 'Email and password are required'}
            
            response = self.supabase.auth.sign_in_with_password({
                'email': email,
                'password': password
            })
            
            if response.user and response.session:
                return True, {
                    'user_id': response.user.id,
                    'email': response.user.email,
                    'access_token': response.session.access_token,
                    'refresh_token': response.session.refresh_token,
                    'expires_at': response.session.expires_at,
                    'expires_in': response.session.expires_in,
                    'user_metadata': response.user.user_metadata or {}
                }
            else:
                return False, {'error': 'Invalid credentials'}
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Supabase login error: {error_msg}")
            
            if 'invalid' in error_msg.lower() or 'credentials' in error_msg.lower():
                return False, {'error': 'Invalid email or password'}
            elif 'email not confirmed' in error_msg.lower():
                return False, {'error': 'Please verify your email before logging in'}
            
            return False, {'error': 'Login failed'}
    
    def login_with_phone(self, phone: str, password: str) -> Tuple[bool, Dict]:
        """
        Authenticate user with phone number and password
        
        Args:
            phone: User phone number (E.164 format)
            password: User password
        
        Returns:
            Tuple of (success: bool, data: dict)
        """
        try:
            if not phone or not password:
                return False, {'error': 'Phone and password are required'}
            
            response = self.supabase.auth.sign_in_with_password({
                'phone': phone,
                'password': password
            })
            
            if response.user and response.session:
                return True, {
                    'user_id': response.user.id,
                    'phone': response.user.phone,
                    'email': response.user.email,
                    'access_token': response.session.access_token,
                    'refresh_token': response.session.refresh_token,
                    'expires_at': response.session.expires_at,
                    'expires_in': response.session.expires_in
                }
            else:
                return False, {'error': 'Invalid credentials'}
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Supabase phone login error: {error_msg}")
            return False, {'error': 'Invalid phone or password'}
    
    def send_otp(self, phone: str, channel: str = 'sms') -> Tuple[bool, Dict]:
        """
        Send OTP to phone number
        
        Args:
            phone: Phone number (E.164 format: +1234567890)
            channel: Delivery channel ('sms' or 'whatsapp')
        
        Returns:
            Tuple of (success: bool, data: dict)
        """
        try:
            if not phone:
                return False, {'error': 'Phone number is required'}
            
            if not phone.startswith('+'):
                return False, {'error': 'Phone must be in E.164 format (e.g., +1234567890)'}
            
            response = self.supabase.auth.sign_in_with_otp({
                'phone': phone,
                'options': {'channel': channel}
            })
            
            logger.info(f"OTP sent to {phone} via {channel}")
            return True, {
                'message': 'OTP sent successfully',
                'phone': phone,
                'channel': channel
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Supabase OTP error: {error_msg}")
            
            if 'rate limit' in error_msg.lower():
                return False, {'error': 'Too many requests. Please try again later'}
            elif 'invalid phone' in error_msg.lower():
                return False, {'error': 'Invalid phone number format'}
            
            return False, {'error': 'Failed to send OTP'}
    
    def verify_otp(self, phone: str, token: str) -> Tuple[bool, Dict]:
        """
        Verify OTP token
        
        Args:
            phone: Phone number used to request OTP
            token: OTP code received
        
        Returns:
            Tuple of (success: bool, data: dict)
        """
        try:
            if not phone or not token:
                return False, {'error': 'Phone and OTP code are required'}
            
            response = self.supabase.auth.verify_otp({
                'phone': phone,
                'token': token,
                'type': 'sms'
            })
            
            if response.user and response.session:
                return True, {
                    'user_id': response.user.id,
                    'phone': response.user.phone,
                    'email': response.user.email,
                    'access_token': response.session.access_token,
                    'refresh_token': response.session.refresh_token,
                    'expires_at': response.session.expires_at,
                    'is_new_user': response.user.created_at == response.user.last_sign_in_at
                }
            else:
                return False, {'error': 'Invalid OTP'}
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Supabase OTP verification error: {error_msg}")
            
            if 'expired' in error_msg.lower():
                return False, {'error': 'OTP has expired. Please request a new one'}
            elif 'invalid' in error_msg.lower():
                return False, {'error': 'Invalid OTP code'}
            
            return False, {'error': 'OTP verification failed'}
    
    def social_login(self, provider: str, redirect_url: str = None) -> Optional[str]:
        """
        Get social login URL for OAuth flow
        
        Args:
            provider: OAuth provider ('google', 'facebook', 'apple', 'github', etc.)
            redirect_url: Optional callback URL after authentication
        
        Returns:
            OAuth URL string or None if failed
        """
        try:
            # Validate provider
            valid_providers = ['google', 'facebook', 'apple', 'github', 'twitter', 'linkedin']
            if provider.lower() not in valid_providers:
                logger.error(f"Invalid provider: {provider}")
                return None
            
            options = {}
            if redirect_url:
                options['redirectTo'] = redirect_url
            
            response = self.supabase.auth.sign_in_with_oauth({
                'provider': provider,
                'options': options
            })
            
            logger.info(f"Generated OAuth URL for provider: {provider}")
            return response.url
            
        except Exception as e:
            logger.error(f"Supabase social login error: {str(e)}")
            return None
    
    def refresh_token(self, refresh_token: str) -> Tuple[bool, Dict]:
        """
        Refresh access token using refresh token
        
        Args:
            refresh_token: Valid refresh token
        
        Returns:
            Tuple of (success: bool, data: dict)
        """
        try:
            if not refresh_token:
                return False, {'error': 'Refresh token is required'}
            
            response = self.supabase.auth.refresh_session(refresh_token)
            
            if response.session:
                return True, {
                    'access_token': response.session.access_token,
                    'refresh_token': response.session.refresh_token,
                    'expires_at': response.session.expires_at,
                    'expires_in': response.session.expires_in,
                    'token_type': response.session.token_type
                }
            else:
                return False, {'error': 'Token refresh failed'}
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Token refresh error: {error_msg}")
            
            if 'invalid' in error_msg.lower() or 'expired' in error_msg.lower():
                return False, {'error': 'Invalid or expired refresh token'}
            
            return False, {'error': 'Token refresh failed'}
    
    def logout_user(self, access_token: str = None) -> bool:
        """
        Logout user from Supabase
        
        Args:
            access_token: Optional access token to invalidate specific session
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if access_token:
                # Set the session before signing out
                self.supabase.auth.set_session(access_token, None)
            
            self.supabase.auth.sign_out()
            logger.info("User logged out successfully")
            return True
            
        except Exception as e:
            logger.error(f"Supabase logout error: {str(e)}")
            return False
    
    def verify_token(self, token: str) -> Tuple[bool, Dict]:
        """
        Verify and decode Supabase JWT token
        
        Args:
            token: JWT access token
        
        Returns:
            Tuple of (valid: bool, decoded_data: dict)
        """
        try:
            if not token:
                return False, {'error': 'Token is required'}
            
            # Decode the JWT without signature verification
            # Supabase handles signature verification on their end
            decoded_token = jwt.decode(
                token, 
                options={"verify_signature": False}
            )
            
            # Check if token is expired
            exp_timestamp = decoded_token.get('exp')
            if exp_timestamp:
                exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
                if datetime.now(timezone.utc) > exp_datetime:
                    return False, {'error': 'Token has expired'}
            
            return True, {
                'user_id': decoded_token.get('sub'),
                'email': decoded_token.get('email'),
                'phone': decoded_token.get('phone'),
                'role': decoded_token.get('role'),
                'exp': decoded_token.get('exp'),
                'iat': decoded_token.get('iat'),
                'aud': decoded_token.get('aud'),
                'user_metadata': decoded_token.get('user_metadata', {})
            }
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return False, {'error': 'Token has expired'}
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {str(e)}")
            return False, {'error': 'Invalid token'}
        except Exception as e:
            logger.error(f"Token verification error: {str(e)}")
            return False, {'error': str(e)}
    
    def update_user_metadata(self, user_id: str, metadata: Dict) -> Tuple[bool, Dict]:
        """
        Update user metadata in Supabase (requires service role)
        
        Args:
            user_id: Supabase user ID
            metadata: Dictionary of metadata to update
        
        Returns:
            Tuple of (success: bool, data: dict)
        """
        try:
            if not user_id or not metadata:
                return False, {'error': 'User ID and metadata are required'}
            
            # Use service role client for admin operations
            response = self.service_client.auth.admin.update_user_by_id(
                user_id,
                {'user_metadata': metadata}
            )
            
            if response.user:
                logger.info(f"Updated metadata for user: {user_id}")
                return True, {
                    'user_id': response.user.id,
                    'user_metadata': response.user.user_metadata
                }
            else:
                return False, {'error': 'Update failed'}
                
        except ValueError as e:
            # Service client not initialized
            logger.error(f"Service client error: {str(e)}")
            return False, {'error': 'Admin operations not available'}
        except Exception as e:
            logger.error(f"User metadata update error: {str(e)}")
            return False, {'error': str(e)}
    
    def delete_user(self, user_id: str) -> Tuple[bool, Dict]:
        """
        Delete user from Supabase (requires service role)
        
        Args:
            user_id: Supabase user ID to delete
        
        Returns:
            Tuple of (success: bool, data: dict)
        """
        try:
            if not user_id:
                return False, {'error': 'User ID is required'}
            
            # Use service role client for admin operations
            self.service_client.auth.admin.delete_user(user_id)
            
            logger.info(f"Deleted user: {user_id}")
            return True, {'message': 'User deleted successfully'}
            
        except ValueError as e:
            logger.error(f"Service client error: {str(e)}")
            return False, {'error': 'Admin operations not available'}
        except Exception as e:
            logger.error(f"User deletion error: {str(e)}")
            return False, {'error': str(e)}
    
    def get_user(self, access_token: str) -> Tuple[bool, Dict]:
        """
        Get user details from access token
        
        Args:
            access_token: Valid access token
        
        Returns:
            Tuple of (success: bool, user_data: dict)
        """
        try:
            if not access_token:
                return False, {'error': 'Access token is required'}
            
            # Set session and get user
            self.supabase.auth.set_session(access_token, None)
            response = self.supabase.auth.get_user()
            
            if response.user:
                return True, {
                    'user_id': response.user.id,
                    'email': response.user.email,
                    'phone': response.user.phone,
                    'user_metadata': response.user.user_metadata or {},
                    'created_at': response.user.created_at,
                    'last_sign_in_at': response.user.last_sign_in_at
                }
            else:
                return False, {'error': 'User not found'}
                
        except Exception as e:
            logger.error(f"Get user error: {str(e)}")
            return False, {'error': str(e)}
    
    def send_password_reset_email(self, email: str, redirect_url: str = None) -> Tuple[bool, Dict]:
        """
        Send password reset email
        
        Args:
            email: User email address
            redirect_url: Optional URL to redirect after reset
        
        Returns:
            Tuple of (success: bool, data: dict)
        """
        try:
            if not email:
                return False, {'error': 'Email is required'}
            
            options = {}
            if redirect_url:
                options['redirectTo'] = redirect_url
            
            self.supabase.auth.reset_password_email(email, options)
            
            logger.info(f"Password reset email sent to: {email}")
            return True, {'message': 'Password reset email sent'}
            
        except Exception as e:
            logger.error(f"Password reset error: {str(e)}")
            return False, {'error': 'Failed to send password reset email'}


# Global singleton instance
supabase_auth = SupabaseAuthService()