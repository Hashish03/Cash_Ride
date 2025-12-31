# users/services/social_service.py
import logging
from typing import Dict, Any, Optional, Tuple
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from ..models import SocialAccount, LoginHistory
import requests
from urllib.parse import urlencode

logger = logging.getLogger(__name__)
User = get_user_model()


class SocialLoginService:
    """Service for handling social login authentication"""
    
    PROVIDER_CONFIGS = {
        'google': {
            'auth_url': 'https://accounts.google.com/o/oauth2/v2/auth',
            'token_url': 'https://oauth2.googleapis.com/token',
            'userinfo_url': 'https://www.googleapis.com/oauth2/v3/userinfo',
            'scope': 'openid email profile',
            'client_id': getattr(settings, 'GOOGLE_CLIENT_ID', ''),
            'client_secret': getattr(settings, 'GOOGLE_CLIENT_SECRET', ''),
            'redirect_uri': getattr(settings, 'GOOGLE_REDIRECT_URI', ''),
        },
        'facebook': {
            'auth_url': 'https://www.facebook.com/v12.0/dialog/oauth',
            'token_url': 'https://graph.facebook.com/v12.0/oauth/access_token',
            'userinfo_url': 'https://graph.facebook.com/v12.0/me',
            'scope': 'email,public_profile',
            'client_id': getattr(settings, 'FACEBOOK_CLIENT_ID', ''),
            'client_secret': getattr(settings, 'FACEBOOK_CLIENT_SECRET', ''),
            'redirect_uri': getattr(settings, 'FACEBOOK_REDIRECT_URI', ''),
        },
        'apple': {
            'auth_url': 'https://appleid.apple.com/auth/authorize',
            'token_url': 'https://appleid.apple.com/auth/token',
            'userinfo_url': None,  # Apple returns user info in ID token
            'scope': 'name email',
            'client_id': getattr(settings, 'APPLE_CLIENT_ID', ''),
            'client_secret': getattr(settings, 'APPLE_CLIENT_SECRET', ''),
            'redirect_uri': getattr(settings, 'APPLE_REDIRECT_URI', ''),
        },
        'github': {
            'auth_url': 'https://github.com/login/oauth/authorize',
            'token_url': 'https://github.com/login/oauth/access_token',
            'userinfo_url': 'https://api.github.com/user',
            'scope': 'user:email',
            'client_id': getattr(settings, 'GITHUB_CLIENT_ID', ''),
            'client_secret': getattr(settings, 'GITHUB_CLIENT_SECRET', ''),
            'redirect_uri': getattr(settings, 'GITHUB_REDIRECT_URI', ''),
        },
    }
    
    @classmethod
    def get_auth_url(cls, provider: str, state: str = None) -> Optional[str]:
        """Get OAuth authorization URL for provider"""
        config = cls.PROVIDER_CONFIGS.get(provider)
        if not config or not config['client_id']:
            logger.error(f"Provider {provider} not configured")
            return None
        
        params = {
            'client_id': config['client_id'],
            'redirect_uri': config['redirect_uri'],
            'scope': config['scope'],
            'response_type': 'code',
        }
        
        if state:
            params['state'] = state
        
        # Provider-specific parameters
        if provider == 'google':
            params['access_type'] = 'offline'
            params['prompt'] = 'consent'
        elif provider == 'facebook':
            params['display'] = 'popup'
        elif provider == 'apple':
            params['response_mode'] = 'form_post'
        
        return f"{config['auth_url']}?{urlencode(params)}"
    
    @classmethod
    def authenticate(cls, provider: str, code: str, request=None) -> Tuple[bool, Dict[str, Any]]:
        """Authenticate user with social provider"""
        try:
            # Exchange code for access token
            token_data = cls._exchange_code_for_token(provider, code)
            if not token_data:
                return False, {'error': 'Failed to exchange code for token'}
            
            # Get user info
            user_info = cls._get_user_info(provider, token_data['access_token'])
            if not user_info:
                return False, {'error': 'Failed to get user info'}
            
            # Get or create user
            user, created = cls._get_or_create_user(provider, user_info, token_data)
            
            # Create or update social account
            social_account = cls._update_social_account(user, provider, user_info, token_data)
            
            # Record login history
            if request:
                cls._record_login_history(user, request, 'social', True)
            
            # Prepare response
            response_data = {
                'user': user.to_dict(),
                'social_account': {
                    'provider': social_account.provider,
                    'uid': social_account.uid,
                    'is_primary': social_account.is_primary,
                },
                'is_new_user': created,
                'access_token': token_data.get('access_token'),
                'refresh_token': token_data.get('refresh_token'),
                'expires_in': token_data.get('expires_in'),
            }
            
            return True, response_data
            
        except Exception as e:
            logger.error(f"Social authentication error: {str(e)}", exc_info=True)
            return False, {'error': str(e)}
    
    @classmethod
    def _exchange_code_for_token(cls, provider: str, code: str) -> Optional[Dict]:
        """Exchange authorization code for access token"""
        config = cls.PROVIDER_CONFIGS.get(provider)
        if not config:
            return None
        
        data = {
            'client_id': config['client_id'],
            'client_secret': config['client_secret'],
            'redirect_uri': config['redirect_uri'],
            'grant_type': 'authorization_code',
            'code': code,
        }
        
        try:
            response = requests.post(config['token_url'], data=data)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Token exchange failed: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Token exchange error: {str(e)}")
            return None
    
    @classmethod
    def _get_user_info(cls, provider: str, access_token: str) -> Optional[Dict]:
        """Get user info from provider"""
        config = cls.PROVIDER_CONFIGS.get(provider)
        if not config or not config['userinfo_url']:
            return None
        
        headers = {'Authorization': f'Bearer {access_token}'}
        
        try:
            response = requests.get(config['userinfo_url'], headers=headers)
            if response.status_code == 200:
                user_info = response.json()
                
                # Normalize user info
                normalized = cls._normalize_user_info(provider, user_info)
                return normalized
            else:
                logger.error(f"User info fetch failed: {response.text}")
                return None
        except Exception as e:
            logger.error(f"User info fetch error: {str(e)}")
            return None
    
    @classmethod
    def _normalize_user_info(cls, provider: str, user_info: Dict) -> Dict:
        """Normalize user info from different providers"""
        normalized = {
            'provider': provider,
            'uid': user_info.get('sub') or user_info.get('id') or user_info.get('user_id'),
            'email': user_info.get('email'),
            'first_name': '',
            'last_name': '',
            'profile_picture': '',
        }
        
        if provider == 'google':
            normalized['first_name'] = user_info.get('given_name', '')
            normalized['last_name'] = user_info.get('family_name', '')
            normalized['profile_picture'] = user_info.get('picture', '')
            normalized['email_verified'] = user_info.get('email_verified', False)
        
        elif provider == 'facebook':
            name_parts = (user_info.get('name') or '').split(' ', 1)
            normalized['first_name'] = name_parts[0] if name_parts else ''
            normalized['last_name'] = name_parts[1] if len(name_parts) > 1 else ''
            normalized['profile_picture'] = f"https://graph.facebook.com/{normalized['uid']}/picture?type=large"
        
        elif provider == 'github':
            name_parts = (user_info.get('name') or '').split(' ', 1)
            normalized['first_name'] = name_parts[0] if name_parts else ''
            normalized['last_name'] = name_parts[1] if len(name_parts) > 1 else ''
            normalized['profile_picture'] = user_info.get('avatar_url', '')
        
        return normalized
    
    @classmethod
    def _get_or_create_user(cls, provider: str, user_info: Dict, token_data: Dict) -> Tuple[User, bool]:
        """Get or create user from social login data"""
        uid = user_info['uid']
        email = user_info.get('email')
        
        try:
            # Try to find by social account
            social_account = SocialAccount.objects.filter(
                provider=provider,
                uid=uid
            ).select_related('user').first()
            
            if social_account:
                user = social_account.user
                created = False
            else:
                # Try to find by email
                if email:
                    user = User.objects.filter(email=email).first()
                    if user:
                        created = False
                    else:
                        # Create new user
                        user = User.objects.create_user(
                            email=email,
                            first_name=user_info.get('first_name', ''),
                            last_name=user_info.get('last_name', ''),
                            profile_picture=user_info.get('profile_picture', ''),
                            social_provider=provider,
                            social_uid=uid,
                            email_verified=True,
                        )
                        created = True
                else:
                    # Create user with placeholder email
                    placeholder_email = f"{provider}_{uid}@{provider}.com"
                    user = User.objects.create_user(
                        email=placeholder_email,
                        first_name=user_info.get('first_name', ''),
                        last_name=user_info.get('last_name', ''),
                        profile_picture=user_info.get('profile_picture', ''),
                        social_provider=provider,
                        social_uid=uid,
                        email_verified=True,
                    )
                    created = True
            
            # Update user profile picture if not set
            if not user.profile_picture and user_info.get('profile_picture'):
                user.profile_picture = user_info['profile_picture']
                user.save()
            
            return user, created
            
        except Exception as e:
            logger.error(f"Error getting/creating user: {str(e)}")
            raise
    
    @classmethod
    def _update_social_account(cls, user: User, provider: str, user_info: Dict, token_data: Dict) -> SocialAccount:
        """Create or update social account record"""
        defaults = {
            'access_token': token_data.get('access_token'),
            'refresh_token': token_data.get('refresh_token'),
            'expires_at': timezone.now() + timezone.timedelta(seconds=token_data.get('expires_in', 3600)),
            'profile_url': user_info.get('profile_url', ''),
            'profile_data': user_info,
            'verified': user_info.get('email_verified', True),
        }
        
        social_account, created = SocialAccount.objects.update_or_create(
            user=user,
            provider=provider,
            uid=user_info['uid'],
            defaults=defaults
        )
        
        # Mark as primary if first social account
        if created and not SocialAccount.objects.filter(user=user, is_primary=True).exists():
            social_account.is_primary = True
            social_account.save()
        
        return social_account
    
    @classmethod
    def _record_login_history(cls, user: User, request, auth_method: str, successful: bool) -> LoginHistory:
        """Record login attempt in history"""
        from .utils import get_client_ip, parse_user_agent
        
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        device_info = parse_user_agent(user_agent)
        
        login_history = LoginHistory.objects.create(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            auth_method=auth_method,
            successful=successful,
            **device_info
        )
        
        return login_history
    
    @classmethod
    def unlink_social_account(cls, user: User, provider: str) -> bool:
        """Unlink social account from user"""
        try:
            # Check if user has password or other social accounts
            has_password = user.has_usable_password()
            other_accounts = SocialAccount.objects.filter(user=user).exclude(provider=provider)
            
            # Cannot unlink if no password and no other accounts
            if not has_password and not other_accounts.exists():
                raise ValidationError(
                    "Cannot unlink last authentication method. Please set a password first."
                )
            
            # Delete social account
            deleted_count, _ = SocialAccount.objects.filter(
                user=user,
                provider=provider
            ).delete()
            
            # Clear social fields if this was the primary social account
            if user.social_provider == provider:
                user.social_provider = None
                user.social_uid = None
                user.save()
            
            return deleted_count > 0
            
        except Exception as e:
            logger.error(f"Error unlinking social account: {str(e)}")
            raise


# Utility functions
def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def parse_user_agent(user_agent):
    """Parse user agent string for device info"""
    # Simplified parsing - in production, use a library like user-agents
    if 'Mobile' in user_agent:
        device_type = 'mobile'
    elif 'Tablet' in user_agent:
        device_type = 'tablet'
    else:
        device_type = 'desktop'
    
    browser = 'Unknown'
    if 'Chrome' in user_agent:
        browser = 'Chrome'
    elif 'Firefox' in user_agent:
        browser = 'Firefox'
    elif 'Safari' in user_agent:
        browser = 'Safari'
    elif 'Edge' in user_agent:
        browser = 'Edge'
    
    platform = 'Unknown'
    if 'Windows' in user_agent:
        platform = 'Windows'
    elif 'Mac' in user_agent:
        platform = 'Mac'
    elif 'Linux' in user_agent:
        platform = 'Linux'
    elif 'Android' in user_agent:
        platform = 'Android'
    elif 'iPhone' in user_agent:
        platform = 'iOS'
    
    return {
        'device_type': device_type,
        'browser': browser,
        'platform': platform,
    }