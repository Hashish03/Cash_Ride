# backend/security/rate_limiting.py
from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
import hashlib

class RateLimitMiddleware:
    """
    Rate limiting middleware to prevent abuse
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Rate limit configurations
        self.rate_limits = {
            '/auth/login/': {'requests': 5, 'window': 300},  # 5 requests per 5 minutes
            '/auth/otp/request/': {'requests': 3, 'window': 600},  # 3 requests per 10 minutes
            '/auth/otp/verify/': {'requests': 10, 'window': 300},  # 10 attempts per 5 minutes
            '/auth/register/': {'requests': 3, 'window': 3600},  # 3 registrations per hour
        }
    
    def __call__(self, request):
        # Check rate limit
        if self._is_rate_limited(request):
            return JsonResponse(
                {'error': 'Rate limit exceeded. Please try again later.'},
                status=429
            )
        
        response = self.get_response(request)
        return response
    
    def _is_rate_limited(self, request):
        """Check if request should be rate limited"""
        path = request.path
        
        # Only check specific endpoints
        if path not in self.rate_limits:
            return False
        
        # Create rate limit key
        ip_address = self._get_client_ip(request)
        key = f"rate_limit:{path}:{ip_address}"
        
        # Get current count
        current_count = cache.get(key, 0)
        limit_config = self.rate_limits[path]
        
        if current_count >= limit_config['requests']:
            return True
        
        # Increment counter
        cache.set(key, current_count + 1, limit_config['window'])
        return False
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')
