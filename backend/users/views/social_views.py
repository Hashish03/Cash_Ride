# users/views/social_views.py
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import ValidationError
from django.shortcuts import redirect
from django.conf import settings
import logging

from ..models import User
from ..services.social_service import SocialLoginService
from ..serializers import SocialLoginSerializer, SocialUnlinkSerializer

logger = logging.getLogger(__name__)


class SocialAuthView(APIView):
    """Initiate social authentication"""
    permission_classes = [AllowAny]
    
    def get(self, request, provider):
        """Get OAuth redirect URL"""
        # Generate state for CSRF protection
        import secrets
        state = secrets.token_urlsafe(32)
        request.session['oauth_state'] = state
        
        # Get auth URL
        auth_url = SocialLoginService.get_auth_url(provider, state)
        
        if not auth_url:
            return Response(
                {"detail": f"{provider} login is not configured"},
                status=status.HTTP_501_NOT_IMPLEMENTED
            )
        
        return Response({"auth_url": auth_url})


class SocialCallbackView(APIView):
    """Handle OAuth callback"""
    permission_classes = [AllowAny]
    
    def get(self, request, provider):
        """Handle OAuth callback with authorization code"""
        code = request.GET.get('code')
        state = request.GET.get('state')
        stored_state = request.session.get('oauth_state')
        
        # Verify state to prevent CSRF
        if not state or state != stored_state:
            return Response(
                {"detail": "Invalid state parameter"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Clear state from session
        if 'oauth_state' in request.session:
            del request.session['oauth_state']
        
        if not code:
            return Response(
                {"detail": "Authorization code not provided"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Authenticate with social provider
        success, result = SocialLoginService.authenticate(provider, code, request)
        
        if success:
            # Set session or JWT token
            request.session['user_id'] = result['user']['id']
            
            # Redirect to frontend with tokens
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
            redirect_url = f"{frontend_url}/auth/callback?success=true"
            
            # Add tokens to redirect URL
            import urllib.parse
            params = {
                'user_id': result['user']['id'],
                'is_new_user': result['is_new_user'],
                'provider': provider,
            }
            redirect_url += '&' + urllib.parse.urlencode(params)
            
            return redirect(redirect_url)
        else:
            # Redirect to frontend with error
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
            error_msg = urllib.parse.quote(result.get('error', 'Authentication failed'))
            redirect_url = f"{frontend_url}/auth/callback?success=false&error={error_msg}"
            return redirect(redirect_url)


class SocialLoginView(APIView):
    """Direct social login with access token"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Login with social provider access token"""
        serializer = SocialLoginSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {"detail": "Invalid data", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        provider = serializer.validated_data['provider']
        access_token = serializer.validated_data['access_token']
        
        try:
            # Validate access token and get user info
            user_info = SocialLoginService._get_user_info(provider, access_token)
            if not user_info:
                return Response(
                    {"detail": "Invalid access token"},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Mock token data for authentication
            token_data = {
                'access_token': access_token,
                'expires_in': 3600,
            }
            
            # Get or create user
            user, created = SocialLoginService._get_or_create_user(provider, user_info, token_data)
            
            # Update social account
            SocialLoginService._update_social_account(user, provider, user_info, token_data)
            
            # Record login
            SocialLoginService._record_login_history(user, request, 'social', True)
            
            # Generate authentication token (JWT)
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh = RefreshToken.for_user(user)
            
            response_data = {
                'user': user.to_dict(),
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                'is_new_user': created,
            }
            
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"Social login error: {str(e)}", exc_info=True)
            return Response(
                {"detail": "Social authentication failed"},
                status=status.HTTP_400_BAD_REQUEST
            )


class SocialUnlinkView(APIView):
    """Unlink social account from user"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Unlink social account"""
        serializer = SocialUnlinkSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {"detail": "Invalid data", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        provider = serializer.validated_data['provider']
        
        try:
            success = SocialLoginService.unlink_social_account(request.user, provider)
            
            if success:
                return Response(
                    {"detail": f"{provider} account unlinked successfully"},
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"detail": f"No {provider} account linked"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
        except ValidationError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Social unlink error: {str(e)}", exc_info=True)
            return Response(
                {"detail": "Error unlinking social account"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SocialAccountsView(APIView):
    """Get user's linked social accounts"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get all linked social accounts"""
        from ..models import SocialAccount
        
        social_accounts = SocialAccount.objects.filter(user=request.user)
        
        accounts_data = []
        for account in social_accounts:
            accounts_data.append({
                'provider': account.provider,
                'uid': account.uid,
                'is_primary': account.is_primary,
                'verified': account.verified,
                'created_at': account.created_at.isoformat(),
                'profile_url': account.profile_url,
            })
        
        return Response({
            'social_accounts': accounts_data,
            'has_password': request.user.has_usable_password(),
        })