from django.http import JsonResponse
from django.conf import settings
from backend.cofig.supabase import supabase
import jwt
import logging

logger = logging.getLogger(__name__)

class SupabaseAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Skip middleware for auth endpoints
        if request.path.startswith('/auth/'):
            return self.get_response(request)
            
        auth_header = request.META.get('HTTP_AUTHORIZATION', '').split()
        
        if len(auth_header) == 2 and auth_header[0].lower() == 'bearer':
            access_token = auth_header[1]
            
            try:
                # Verify token with Supabase
                user_info = supabase.auth.get_user(access_token)
                
                if user_info.user:
                    # Get Django user
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    
                    try:
                        user = User.objects.get(supabase_id=user_info.user.id)
                        request.user = user
                    except User.DoesNotExist:
                        # Auto-create user if not exists
                        user = User.objects.create(
                            supabase_id=user_info.user.id,
                            email=user_info.user.email,
                            username=user_info.user.email.split('@')[0]
                        )
                        request.user = user
                        
            except jwt.ExpiredSignatureError:
                return JsonResponse({'error': 'Token expired'}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({'error': 'Invalid token'}, status=401)
            except Exception as e:
                logger.error(f"Auth middleware error: {str(e)}")
                return JsonResponse({'error': 'Authentication failed'}, status=401)
                
        return self.get_response(request)