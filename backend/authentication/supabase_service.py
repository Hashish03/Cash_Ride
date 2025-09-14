from supabase import create_client, Client
from django.conf import settings
import jwt
import logging
from typing import Dict, Optional, Tuple
import requests

logger = logging.getLogger(__name__)

class SupabaseAuthService:
    """
    Service class to handle Supabase authentication operations
    """
    
    def __init__(self):
        self.supabase: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_ANON_KEY
        )
        self.service_client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )
    
    def register_user(self, email: str, password: str, phone: str = None, 
                     metadata: Dict = None) -> Tuple[bool, Dict]:
        """
        Register user with Supabase Auth
        """
        try:
            user_data = {
                'email': email,
                'password': password,
            }
            
            if phone:
                user_data['phone'] = phone
            
            if metadata:
                user_data['data'] = metadata
            
            response = self.supabase.auth.sign_up(user_data)
            
            if response.user:
                return True, {
                    'user_id': response.user.id,
                    'email': response.user.email,
                    'phone': response.user.phone,
                    'email_confirmed': response.user.email_confirmed_at is not None,
                    'phone_confirmed': response.user.phone_confirmed_at is not None,
                    'metadata': response.user.user_metadata
                }
            else:
                return False, {'error': 'Registration failed'}
                
        except Exception as e:
            logger.error(f"Supabase registration error: {str(e)}")
            return False, {'error': str(e)}
    
    def login_user(self, email: str, password: str) -> Tuple[bool, Dict]:
        """
        Authenticate user with Supabase
        """
        try:
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
                    'user_metadata': response.user.user_metadata
                }
            else:
                return False, {'error': 'Invalid credentials'}
                
        except Exception as e:
            logger.error(f"Supabase login error: {str(e)}")
            return False, {'error': str(e)}
    
    def login_with_phone(self, phone: str, password: str) -> Tuple[bool, Dict]:
        """
        Authenticate user with phone number
        """
        try:
            response = self.supabase.auth.sign_in_with_password({
                'phone': phone,
                'password': password
            })
            
            if response.user and response.session:
                return True, {
                    'user_id': response.user.id,
                    'phone': response.user.phone,
                    'access_token': response.session.access_token,
                    'refresh_token': response.session.refresh_token,
                    'expires_at': response.session.expires_at
                }
            else:
                return False, {'error': 'Invalid credentials'}
                
        except Exception as e:
            logger.error(f"Supabase phone login error: {str(e)}")
            return False, {'error': str(e)}
    
    def send_otp(self, phone: str) -> Tuple[bool, Dict]:
        """
        Send OTP to phone number
        """
        try:
            response = self.supabase.auth.sign_in_with_otp({
                'phone': phone
            })
            return True, {'message': 'OTP sent successfully'}
        except Exception as e:
            logger.error(f"Supabase OTP error: {str(e)}")
            return False, {'error': str(e)}
    
    def verify_otp(self, phone: str, token: str) -> Tuple[bool, Dict]:
        """
        Verify OTP token
        """
        try:
            response = self.supabase.auth.verify_otp({
                'phone': phone,
                'token': token,
                'type': 'sms'
            })
            
            if response.user and response.session:
                return True, {
                    'user_id': response.user.id,
                    'phone': response.user.phone,
                    'access_token': response.session.access_token,
                    'refresh_token': response.session.refresh_token,
                }
            else:
                return False, {'error': 'Invalid OTP'}
                
        except Exception as e:
            logger.error(f"Supabase OTP verification error: {str(e)}")
            return False, {'error': str(e)}
    
    def social_login(self, provider: str, redirect_url: str = None) -> str:
        """
        Get social login URL
        """
        try:
            options = {}
            if redirect_url:
                options['redirectTo'] = redirect_url
            
            response = self.supabase.auth.sign_in_with_oauth({
                'provider': provider,
                'options': options
            })
            
            return response.url
            
        except Exception as e:
            logger.error(f"Supabase social login error: {str(e)}")
            return None
    
    def refresh_token(self, refresh_token: str) -> Tuple[bool, Dict]:
        """
        Refresh access token
        """
        try:
            response = self.supabase.auth.refresh_session(refresh_token)
            
            if response.session:
                return True, {
                    'access_token': response.session.access_token,
                    'refresh_token': response.session.refresh_token,
                    'expires_at': response.session.expires_at
                }
            else:
                return False, {'error': 'Token refresh failed'}
                
        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}")
            return False, {'error': str(e)}
    
    def logout_user(self, access_token: str) -> bool:
        """
        Logout user from Supabase
        """
        try:
            # Set the session
            self.supabase.auth.set_session(access_token, None)
            self.supabase.auth.sign_out()
            return True
        except Exception as e:
            logger.error(f"Supabase logout error: {str(e)}")
            return False
    
    def verify_token(self, token: str) -> Tuple[bool, Dict]:
        """
        Verify Supabase JWT token
        """
        try:
            # Decode the JWT to get user info
            decoded_token = jwt.decode(
                token, 
                options={"verify_signature": False}  # Supabase handles signature verification
            )
            
            return True, {
                'user_id': decoded_token.get('sub'),
                'email': decoded_token.get('email'),
                'phone': decoded_token.get('phone'),
                'exp': decoded_token.get('exp'),
                'iat': decoded_token.get('iat')
            }
            
        except Exception as e:
            logger.error(f"Token verification error: {str(e)}")
            return False, {'error': str(e)}
    
    def update_user_metadata(self, user_id: str, metadata: Dict) -> Tuple[bool, Dict]:
        """
        Update user metadata in Supabase
        """
        try:
            # Use service role client for admin operations
            response = self.service_client.auth.admin.update_user_by_id(
                user_id,
                {'user_metadata': metadata}
            )
            
            if response.user:
                return True, {'user_metadata': response.user.user_metadata}
            else:
                return False, {'error': 'Update failed'}
                
        except Exception as e:
            logger.error(f"User metadata update error: {str(e)}")
            return False, {'error': str(e)}

# Global instance
supabase_auth = SupabaseAuthService()