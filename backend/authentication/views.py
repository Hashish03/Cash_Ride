from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import get_user_model
from django.db import transaction
from .serializers import (
    UserRegistrationSerializer, LoginSerializer, OTPRequestSerializer,
    OTPVerifySerializer, SocialLoginSerializer, TokenRefreshSerializer,
    UserProfileSerializer
)
from .models import UserSession
from .supabase_service import supabase_auth
from .sync_service import UserSyncService
from backend.security.logging import SecurityLogger
import logging

User = get_user_model()
logger = logging.getLogger(__name__)
SecurityLogger = logging.getLogger(__name__)

class UserRegistrationView(APIView):
    """
    Register a new user with Supabase and local database
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with transaction.atomic():
                # Prepare metadata
                metadata = {
                    'full_name': serializer.validated_data.get('full_name', ''),
                    'user_type': serializer.validated_data.get('user_type', 'rider'),
                }
                
                # Create user in Supabase
                success, supabase_data = supabase_auth.register_user(
                    email=serializer.validated_data['email'],
                    password=serializer.validated_data['password'],
                    phone=serializer.validated_data.get('phone_number'),
                    metadata=metadata
                )
                
                if not success:
                    return Response({
                        'success': False,
                        'error': supabase_data.get('error', 'Registration failed')
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Create user in local database
                user = User.objects.create(
                    email=serializer.validated_data['email'],
                    phone_number=serializer.validated_data.get('phone_number'),
                    full_name=serializer.validated_data.get('full_name', ''),
                    user_type=serializer.validated_data.get('user_type', 'rider'),
                    date_of_birth=serializer.validated_data.get('date_of_birth'),
                    supabase_uid=supabase_data['user_id'],
                    is_email_verified=supabase_data.get('email_confirmed', False),
                    is_phone_verified=supabase_data.get('phone_confirmed', False)
                )
                user.set_password(serializer.validated_data['password'])
                user.save()
                
                # Log the user in to get tokens
                login_success, login_data = supabase_auth.login_user(
                    email=serializer.validated_data['email'],
                    password=serializer.validated_data['password']
                )
                
                # Create session if device info provided
                if request.data.get('device_id') and login_success:
                    UserSyncService.create_user_session(
                        user=user,
                        access_token=login_data.get('access_token'),
                        refresh_token=login_data.get('refresh_token'),
                        device_id=request.data.get('device_id'),
                        platform=request.data.get('platform', 'web'),
                        request=request
                    )
                
                response_data = {
                    'success': True,
                    'message': 'Registration successful. Please verify your email.',
                    'user': UserProfileSerializer(user).data,
                }
                
                if login_success:
                    response_data['access_token'] = login_data.get('access_token')
                    response_data['refresh_token'] = login_data.get('refresh_token')
                
                return Response(response_data, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LoginView(APIView):
    """
    Login with email/phone and password
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            
            # Check if username is email or phone
            user = None
            success = False
            auth_data = {}
            
            if '@' in username:
                # Email login
                user = User.objects.filter(email=username).first()
                success, auth_data = supabase_auth.login_user(username, password)
            else:
                # Phone login
                user = User.objects.filter(phone_number=username).first()
                success, auth_data = supabase_auth.login_with_phone(username, password)
            
            if not success or not user:
                return Response({
                    'success': False,
                    'error': auth_data.get('error', 'Invalid credentials')
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Update or create session
            if serializer.validated_data.get('device_id'):
                UserSyncService.create_user_session(
                    user=user,
                    access_token=auth_data.get('access_token'),
                    refresh_token=auth_data.get('refresh_token'),
                    device_id=serializer.validated_data['device_id'],
                    platform=serializer.validated_data.get('platform', 'web'),
                    request=request
                )
            
            return Response({
                'success': True,
                'user': UserProfileSerializer(user).data,
                'access_token': auth_data.get('access_token'),
                'refresh_token': auth_data.get('refresh_token'),
                'expires_at': auth_data.get('expires_at')
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return Response({
                'success': False,
                'error': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)


class SocialLoginView(APIView):
    """
    Social login with Google, Facebook, or Apple
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = SocialLoginSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            provider = serializer.validated_data['provider']
            redirect_url = f"{request.scheme}://{request.get_host()}/api/auth/social/callback/"
            
            # Get OAuth URL from Supabase
            oauth_url = supabase_auth.social_login(provider, redirect_url)
            
            if not oauth_url:
                return Response({
                    'success': False,
                    'error': 'Failed to generate OAuth URL'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            return Response({
                'success': True,
                'provider': provider,
                'url': oauth_url
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Social login error: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SocialAuthCallbackView(APIView):
    """
    Handle OAuth callback from social providers
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        try:
            access_token = request.GET.get('access_token')
            refresh_token = request.GET.get('refresh_token')
            error = request.GET.get('error')
            
            if error:
                return Response({
                    'success': False,
                    'error': error
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not access_token:
                return Response({
                    'success': False,
                    'error': 'No access token received'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Verify token and get user info
            token_valid, token_data = supabase_auth.verify_token(access_token)
            
            if not token_valid:
                return Response({
                    'success': False,
                    'error': 'Invalid token'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Sync user from token data
            sync_data = {
                'user_id': token_data.get('user_id'),
                'email': token_data.get('email'),
                'phone': token_data.get('phone'),
                'user_metadata': {},
                'email_confirmed': bool(token_data.get('email')),
                'phone_confirmed': bool(token_data.get('phone') and not token_data.get('email')),
            }
            
            user = UserSyncService.sync_user_from_supabase(sync_data)
            created = not User.objects.filter(supabase_uid=token_data.get('user_id')).exists()
            
            # Create session if device info provided
            device_id = request.GET.get('device_id')
            if device_id and access_token:
                UserSyncService.create_user_session(
                    user=user,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    device_id=device_id,
                    platform=request.GET.get('platform', 'web'),
                    request=request
                )
            
            return Response({
                'success': True,
                'user': UserProfileSerializer(user).data,
                'access_token': access_token,
                'refresh_token': refresh_token,
                'is_new_user': created
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Social auth callback error: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OTPRequestView(APIView):
    """
    Request OTP for phone verification
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            phone_number = serializer.validated_data['phone_number']
            
            # Send OTP via Supabase
            success, result = supabase_auth.send_otp(phone_number)
            
            if not success:
                return Response({
                    'success': False,
                    'error': result.get('error', 'Failed to send OTP')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            return Response({
                'success': True,
                'message': 'OTP sent successfully'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"OTP request error: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OTPVerifyView(APIView):
    """
    Verify OTP and login/register user
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            phone_number = serializer.validated_data['phone_number']
            otp_code = serializer.validated_data['otp_code']
            
            # Verify OTP with Supabase
            success, auth_data = supabase_auth.verify_otp(phone_number, otp_code)
            
            if not success:
                return Response({
                    'success': False,
                    'error': auth_data.get('error', 'Invalid or expired OTP')
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Sync user from auth data
            sync_data = {
                'user_id': auth_data['user_id'],
                'phone': phone_number,
                'phone_confirmed': True,
                'user_metadata': {},
            }
            
            # Check if user is new
            user_exists = User.objects.filter(phone_number=phone_number).exists()
            user = UserSyncService.sync_user_from_supabase(sync_data)
            created = not user_exists
            
            # Create session if device info provided
            if serializer.validated_data.get('device_id'):
                UserSyncService.create_user_session(
                    user=user,
                    access_token=auth_data.get('access_token'),
                    refresh_token=auth_data.get('refresh_token'),
                    device_id=serializer.validated_data['device_id'],
                    platform=serializer.validated_data.get('platform', 'web'),
                    request=request
                )
            
            return Response({
                'success': True,
                'user': UserProfileSerializer(user).data,
                'access_token': auth_data.get('access_token'),
                'refresh_token': auth_data.get('refresh_token'),
                'is_new_user': created
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"OTP verify error: {str(e)}")
            return Response({
                'success': False,
                'error': 'Invalid or expired OTP'
            }, status=status.HTTP_401_UNAUTHORIZED)


class TokenRefreshView(APIView):
    """
    Refresh access token using refresh token
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            refresh_token = serializer.validated_data['refresh_token']
            
            # Refresh token with Supabase
            success, token_data = supabase_auth.refresh_token(refresh_token)
            
            if not success:
                return Response({
                    'success': False,
                    'error': token_data.get('error', 'Invalid refresh token')
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Update session in database
            updated_sessions = 0
            sessions = UserSession.objects.filter(refresh_token=refresh_token)
            for session in sessions:
                UserSyncService.update_user_session(
                    user=session.user,
                    device_id=session.device_id,
                    refresh_token=token_data.get('refresh_token')
                )
                updated_sessions += 1
            
            logger.info(f"Updated {updated_sessions} session(s) with new refresh token")
            
            return Response({
                'success': True,
                'access_token': token_data.get('access_token'),
                'refresh_token': token_data.get('refresh_token'),
                'expires_at': token_data.get('expires_at')
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}")
            return Response({
                'success': False,
                'error': 'Invalid refresh token'
            }, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    """
    Logout user and invalidate session
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            # Get access token from header
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                access_token = auth_header.split(' ')[1]
                supabase_auth.logout_user(access_token)
            
            # Deactivate sessions
            device_id = request.data.get('device_id')
            UserSyncService.invalidate_user_sessions(request.user, device_id)
            
            return Response({
                'success': True,
                'message': 'Logged out successfully'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Get and update user profile
    """
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        self.perform_update(serializer)
        
        # Update Supabase metadata if needed
        if instance.supabase_uid:
            metadata = {
                'full_name': instance.full_name,
                'user_type': instance.user_type,
            }
            supabase_auth.update_user_metadata(instance.supabase_uid, metadata)
        
        return Response({
            'success': True,
            'user': serializer.data
        }, status=status.HTTP_200_OK)


class DeleteAccountView(APIView):
    """
    Delete user account from both local DB and Supabase
    """
    permission_classes = [IsAuthenticated]
    
    def delete(self, request):
        try:
            user = request.user
            
            # Get access token
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                access_token = auth_header.split(' ')[1]
                supabase_auth.logout_user(access_token)
            
            # Delete all sessions
            UserSyncService.invalidate_user_sessions(user)
            UserSession.objects.filter(user=user).delete()
            
            # Delete user from local database
            user.delete()
            
            return Response({
                'success': True,
                'message': 'Account deleted successfully'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Account deletion error: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)