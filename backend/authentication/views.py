from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from .serializers import *
from .supabase_service import supabase_auth
from .sync_service import UserSyncService
from backend.security.logging import SecurityLogger
import logging

logger = logging.getLogger(__name__)
security_logger = SecurityLogger()

class RegisterView(APIView):
    """
    User registration endpoint
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Register with Supabase
            success, result = supabase_auth.register_user(
                email=serializer.validated_data['email'],
                password=serializer.validated_data['password'],
                phone=serializer.validated_data.get('phone_number'),
                metadata={
                    'full_name': serializer.validated_data.get('full_name'),
                    'user_type': serializer.validated_data.get('user_type'),
                    'date_of_birth': serializer.validated_data.get('date_of_birth').isoformat() if serializer.validated_data.get('date_of_birth') else None
                }
            )
            
            if success:
                # Create Django user
                user = UserSyncService.sync_user_from_supabase(result)
                
                # Log registration
                security_logger.log_auth_attempt(
                    user_id=str(user.id),
                    ip_address=UserSyncService.get_client_ip(request),
                    success=True,
                    method='registration'
                )
                
                return Response({
                    'message': 'Registration successful. Please verify your email.',
                    'user_id': result['user_id'],
                    'email_confirmation_required': not result['email_confirmed']
                }, status=status.HTTP_201_CREATED)
            else:
                return Response(
                    {'error': result.get('error', 'Registration failed')},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return Response(
                {'error': 'Registration failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class LoginView(APIView):
    """
    User login endpoint
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        
        try:
            # Check if user is locked
            user = self.get_user_by_username(username)
            if user and user.is_account_locked():
                return Response(
                    {'error': 'Account temporarily locked due to failed login attempts'},
                    status=status.HTTP_423_LOCKED
                )
            
            # Authenticate with Django backend (which uses Supabase)
            user = authenticate(request, username=username, password=password)
            
            if user:
                # Login successful
                login(request, user)
                
                # Create session record
                session_data = {
                    'session_id': request.session.session_key,
                    'platform': serializer.validated_data.get('platform', 'web'),
                    'device_id': serializer.validated_data.get('device_id'),
                    'expires_in': 3600  # 1 hour
                }
                
                UserSyncService.create_user_session(user, session_data, request)
                
                # Get fresh tokens from Supabase
                success, tokens = supabase_auth.login_user(username, password)
                
                if success:
                    response_data = {
                        'message': 'Login successful',
                        'user': UserProfileSerializer(user).data,
                        'access_token': tokens['access_token'],
                        'refresh_token': tokens['refresh_token'],
                        'expires_at': tokens['expires_at']
                    }
                    
                    # Check if 2FA is required
                    if user.two_factor_enabled:
                        response_data['requires_2fa'] = True
                    
                    # Log successful login
                    security_logger.log_auth_attempt(
                        user_id=str(user.id),
                        ip_address=UserSyncService.get_client_ip(request),
                        success=True,
                        method='password'
                    )
                    
                    return Response(response_data, status=status.HTTP_200_OK)
            
            # Login failed
            security_logger.log_auth_attempt(
                user_id=str(user.id) if user else None,
                ip_address=UserSyncService.get_client_ip(request),
                success=False,
                method='password'
            )
            
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return Response(
                {'error': 'Login failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def get_user_by_username(self, username):
        """Get user by email or phone number"""
        try:
            return User.objects.get(email=username)
        except User.DoesNotExist:
            try:
                return User.objects.get(phone_number=username)
            except User.DoesNotExist:
                return None

class OTPRequestView(APIView):
    """
    Request OTP for phone authentication
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        phone_number = serializer.validated_data['phone_number']
        
        try:
            # Send OTP via Supabase
            success, result = supabase_auth.send_otp(phone_number)
            
            if success:
                return Response({
                    'message': 'OTP sent successfully',
                    'phone_number': phone_number
                }, status=status.HTTP_200_OK)
            else:
                return Response(
                    {'error': result.get('error', 'Failed to send OTP')},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            logger.error(f"OTP request error: {str(e)}")
            return Response(
                {'error': 'Failed to send OTP'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class OTPVerifyView(APIView):
    """
    Verify OTP and login user
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        phone_number = serializer.validated_data['phone_number']
        otp_code = serializer.validated_data['otp_code']
        
        try:
            # Verify OTP with Supabase
            success, result = supabase_auth.verify_otp(phone_number, otp_code)
            
            if success:
                # Sync user with Django
                user = UserSyncService.sync_user_from_supabase(result)
                
                # Login user
                login(request, user)
                
                # Create session
                session_data = {
                    'session_id': request.session.session_key,
                    'platform': serializer.validated_data.get('platform', 'mobile'),
                    'device_id': serializer.validated_data.get('device_id'),
                    'expires_in': 3600
                }
                
                UserSyncService.create_user_session(user, session_data, request)
                
                # Log successful login
                security_logger.log_auth_attempt(
                    user_id=str(user.id),
                    ip_address=UserSyncService.get_client_ip(request),
                    success=True,
                    method='otp'
                )
                
                return Response({
                    'message': 'OTP verification successful',
                    'user': UserProfileSerializer(user).data,
                    'access_token': result['access_token'],
                    'refresh_token': result['refresh_token']
                }, status=status.HTTP_200_OK)
            
            else:
                # Log failed attempt
                security_logger.log_auth_attempt(
                    user_id=None,
                    ip_address=UserSyncService.get_client_ip(request),
                    success=False,
                    method='otp'
                )
                
                return Response(
                    {'error': result.get('error', 'Invalid OTP')},
                    status=status.HTTP_401_UNAUTHORIZED
                )
                
        except Exception as e:
            logger.error(f"OTP verification error: {str(e)}")
            return Response(
                {'error': 'OTP verification failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class SocialLoginView(APIView):
    """
    Social media login endpoint
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = SocialLoginSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        provider = serializer.validated_data['provider']
        access_token = serializer.validated_data['access_token']
        
        try:
            # Verify social token and get user info
            user_info = self.verify_social_token(provider, access_token)
            
            if not user_info:
                return Response(
                    {'error': 'Invalid social media token'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Check if user exists
            user = self.get_or_create_social_user(provider, user_info)
            
            if user:
                # Login user
                login(request, user)
                
                # Create session
                session_data = {
                    'session_id': request.session.session_key,
                    'platform': serializer.validated_data.get('platform', 'mobile'),
                    'device_id': serializer.validated_data.get('device_id'),
                    'expires_in': 3600
                }
                
                UserSyncService.create_user_session(user, session_data, request)
                
                # Generate JWT tokens
                # (You might want to create your own JWT or use Supabase's social auth)
                
                # Log successful login
                security_logger.log_auth_attempt(
                    user_id=str(user.id),
                    ip_address=UserSyncService.get_client_ip(request),
                    success=True,
                    method=f'social_{provider}'
                )
                
                return Response({
                    'message': 'Social login successful',
                    'user': UserProfileSerializer(user).data,
                    'access_token': 'generated_jwt_token',  # Replace with actual token
                    'is_new_user': getattr(user, '_is_new_user', False)
                }, status=status.HTTP_200_OK)
            
            else:
                return Response(
                    {'error': 'Social login failed'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            logger.error(f"Social login error: {str(e)}")
            return Response(
                {'error': 'Social login failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def verify_social_token(self, provider, access_token):
        """Verify social media access token and get user info"""
        import requests
        
        try:
            if provider == 'google':
                response = requests.get(
                    f'https://www.googleapis.com/oauth2/v2/userinfo?access_token={access_token}'
                )
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'id': data.get('id'),
                        'email': data.get('email'),
                        'name': data.get('name'),
                        'picture': data.get('picture'),
                        'verified_email': data.get('verified_email', False)
                    }
            
            elif provider == 'facebook':
                response = requests.get(
                    f'https://graph.facebook.com/me?fields=id,name,email,picture&access_token={access_token}'
                )
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'id': data.get('id'),
                        'email': data.get('email'),
                        'name': data.get('name'),
                        'picture': data.get('picture', {}).get('data', {}).get('url'),
                        'verified_email': True  # Facebook emails are typically verified
                    }
            
            elif provider == 'apple':
                # Apple Sign-In requires JWT verification
                # This is more complex and requires Apple's public keys
                # For now, returning None - implement based on your needs
                pass
                
        except Exception as e:
            logger.error(f"Social token verification error: {str(e)}")
        
        return None
    
    def get_or_create_social_user(self, provider, user_info):
        """Get or create user from social media info"""
        try:
            social_id = user_info.get('id')
            email = user_info.get('email')
            
            # Try to find existing user by social ID
            social_id_field = f'{provider}_id'
            filter_kwargs = {social_id_field: social_id}
            
            try:
                user = User.objects.get(**filter_kwargs)
                return user
            except User.DoesNotExist:
                pass
            
            # Try to find by email
            if email:
                try:
                    user = User.objects.get(email=email)
                    # Update social ID
                    setattr(user, social_id_field, social_id)
                    user.save()
                    return user
                except User.DoesNotExist:
                    pass
            
            # Create new user
            if email:
                user_data = {
                    'username': email,
                    'email': email,
                    'full_name': user_info.get('name', ''),
                    'profile_picture': user_info.get('picture', ''),
                    'is_email_verified': user_info.get('verified_email', False),
                    social_id_field: social_id
                }
                
                user = User.objects.create_user(**user_data)
                user._is_new_user = True  # Flag for frontend
                
                return user
            
        except Exception as e:
            logger.error(f"Social user creation error: {str(e)}")
        
        return None

class TokenRefreshView(APIView):
    """
    Refresh JWT token
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        refresh_token = serializer.validated_data['refresh_token']
        
        try:
            # Refresh token with Supabase
            success, result = supabase_auth.refresh_token(refresh_token)
            
            if success:
                return Response({
                    'access_token': result['access_token'],
                    'refresh_token': result['refresh_token'],
                    'expires_at': result['expires_at']
                }, status=status.HTTP_200_OK)
            else:
                return Response(
                    {'error': result.get('error', 'Token refresh failed')},
                    status=status.HTTP_401_UNAUTHORIZED
                )
                
        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}")
            return Response(
                {'error': 'Token refresh failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class LogoutView(APIView):
    """
    User logout endpoint
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            # Get access token from header
            auth_header = request.META.get('HTTP_AUTHORIZATION')
            access_token = None
            
            if auth_header and auth_header.startswith('Bearer '):
                access_token = auth_header[7:]
            
            # Logout from Supabase
            if access_token:
                supabase_auth.logout_user(access_token)
            
            # Invalidate Django session
            UserSyncService.invalidate_user_sessions(request.user)
            logout(request)
            
            # Log logout
            security_logger.log_auth_attempt(
                user_id=str(request.user.id),
                ip_address=UserSyncService.get_client_ip(request),
                success=True,
                method='logout'
            )
            
            return Response({
                'message': 'Logout successful'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return Response(
                {'error': 'Logout failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ProfileView(APIView):
    """
    User profile management
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get user profile"""
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)
    
    def put(self, request):
        """Update user profile"""
        serializer = UserProfileSerializer(
            request.user, 
            data=request.data, 
            partial=True
        )
        
        if serializer.is_valid():
            user = serializer.save()
            
            # Update Supabase metadata if needed
            if user.supabase_uid:
                metadata = {
                    'full_name': user.full_name,
                    'user_type': user.user_type,
                    'profile_picture': user.profile_picture
                }
                supabase_auth.update_user_metadata(user.supabase_uid, metadata)
            
            # Log profile update
            security_logger.log_data_access(
                user_id=str(user.id),
                resource='user_profile',
                action='update'
            )
            
            return Response(serializer.data)
        
        return Response(
            {'error': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

class ChangePasswordView(APIView):
    """
    Change user password
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        
        if not current_password or not new_password:
            return Response(
                {'error': 'Both current and new passwords are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify current password
        user = authenticate(
            username=request.user.email,
            password=current_password
        )
        
        if not user:
            return Response(
                {'error': 'Current password is incorrect'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Update password in Supabase
            # Note: Supabase doesn't have direct password update API
            # You might need to use password reset flow or admin API
            
            # For now, we'll update Django password
            user.set_password(new_password)
            user.save()
            
            # Invalidate all sessions for security
            UserSyncService.invalidate_user_sessions(user)
            
            # Log password change
            security_logger.log_data_access(
                user_id=str(user.id),
                resource='user_password',
                action='change',
                sensitive=True
            )
            
            return Response({
                'message': 'Password changed successfully. Please log in again.'
            })
            
        except Exception as e:
            logger.error(f"Password change error: {str(e)}")
            return Response(
                {'error': 'Password change failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )