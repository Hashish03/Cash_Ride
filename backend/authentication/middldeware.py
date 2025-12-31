from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from .supabase_service import supabase_auth
from .sync_service import UserSyncService
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class SupabaseAuthMiddleware(MiddlewareMixin):
    """
    Middleware to authenticate requests using Supabase JWT tokens
    """
    
    def process_request(self, request):
        """
        Authenticate user from Authorization header
        """
        # Skip authentication for certain paths
        if self._should_skip_auth(request):
            return None
        
        # Get token from Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header.startswith('Bearer '):
            return None
        
        try:
            access_token = auth_header.split(' ')[1]
            
            # Verify token with Supabase
            token_valid, token_data = supabase_auth.verify_token(access_token)
            
            if not token_valid:
                return self._unauthorized_response('Invalid token')
            
            # Get user from token
            user_id = token_data.get('user_id')
            
            # Try to get user from database
            try:
                user = User.objects.get(supabase_uid=user_id)
            except User.DoesNotExist:
                # Sync user from token if not found
                try:
                    user = UserSyncService.sync_user_from_token(access_token)
                except Exception as e:
                    logger.error(f"Failed to sync user from token: {str(e)}")
                    return self._unauthorized_response('User not found')
            
            # Attach user to request
            request.user = user
            request.auth_token = access_token
            
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return self._unauthorized_response('Authentication failed')
        
        return None
    
    def _should_skip_auth(self, request):
        """
        Determine if authentication should be skipped for this request
        """
        # List of paths that don't require authentication
        skip_paths = [
            '/api/auth/register/',
            '/api/auth/login/',
            '/api/auth/social/login/',
            '/api/auth/social/callback/',
            '/api/auth/otp/request/',
            '/api/auth/otp/verify/',
            '/api/auth/token/refresh/',
            '/admin/',
            '/static/',
            '/media/',
        ]
        
        path = request.path
        return any(path.startswith(skip_path) for skip_path in skip_paths)
    
    def _unauthorized_response(self, message):
        """
        Return unauthorized response
        """
        return JsonResponse({
            'success': False,
            'error': message
        }, status=401)


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log API requests for debugging
    """
    
    def process_request(self, request):
        """Log incoming requests"""
        if request.path.startswith('/api/'):
            logger.info(f"{request.method} {request.path} - User: {getattr(request.user, 'email', 'Anonymous')}")
        return None
    
    def process_response(self, request, response):
        """Log responses"""
        if request.path.startswith('/api/'):
            logger.info(f"{request.method} {request.path} - Status: {response.status_code}")
        return response