from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.conf import settings
from .serializers import (
    UserSerializer, UserProfileSerializer,
    RegisterSerializer, LoginSerializer, SocialAuthSerializer
)
from backend.supabase import supabase
import logging

logger = logging.getLogger(__name__)

class RegisterView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Create user in Supabase
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            
            response = supabase.auth.sign_up({
                'email': email,
                'password': password,
            })
            
            if response.user:
                # Create user in Django
                user_data = {
                    'email': email,
                    'username': serializer.validated_data['username'],
                    'first_name': serializer.validated_data.get('first_name', ''),
                    'last_name': serializer.validated_data.get('last_name', ''),
                    'supabase_id': response.user.id,
                    'phone_number': serializer.validated_data.get('phone_number'),
                }
                
                user_serializer = UserSerializer(data=user_data)
                if user_serializer.is_valid():
                    user = user_serializer.save()
                    
                    # Create user profile
                    UserProfile.objects.create(user=user)
                    
                    return Response({
                        'user': user_serializer.data,
                        'message': 'User registered successfully. Please check your email for verification.'
                    }, status=status.HTTP_201_CREATED)
                
                # If Django user creation fails, delete Supabase user
                supabase.auth.admin.delete_user(response.user.id)
                return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({'error': 'User registration failed'}, 
                          status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            
            response = supabase.auth.sign_in_with_password({
                'email': email,
                'password': password
            })
            
            if response.user:
                # Get or create Django user
                user, created = User.objects.get_or_create(
                    supabase_id=response.user.id,
                    defaults={
                        'email': email,
                        'username': email.split('@')[0],
                        'supabase_id': response.user.id
                    }
                )
                
                if not created:
                    user_serializer = UserSerializer(user)
                    return Response({
                        'user': user_serializer.data,
                        'access_token': response.session.access_token,
                        'refresh_token': response.session.refresh_token
                    }, status=status.HTTP_200_OK)
                
                return Response({
                    'user': UserSerializer(user).data,
                    'access_token': response.session.access_token,
                    'refresh_token': response.session.refresh_token
                }, status=status.HTTP_200_OK)
            
            return Response({'error': 'Invalid credentials'}, 
                           status=status.HTTP_401_UNAUTHORIZED)
            
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class SocialLoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = SocialAuthSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            provider = serializer.validated_data['provider']
            access_token = serializer.validated_data['access_token']
            refresh_token = serializer.validated_data.get('refresh_token')
            
            # Authenticate with Supabase
            response = supabase.auth.sign_in_with_oauth({
                'provider': provider,
                'options': {
                    'redirect_to': f"{settings.FRONTEND_URL}/auth/callback",
                    'skip_browser_redirect': True,
                }
            })
            
            # For actual implementation, you'll need to handle the OAuth flow properly
            # This is a simplified version
            
            if response.user:
                # Get user info from Supabase
                user_info = supabase.auth.get_user(response.session.access_token)
                
                # Create or update Django user
                user, created = User.objects.update_or_create(
                    supabase_id=user_info.user.id,
                    defaults={
                        'email': user_info.user.email,
                        'username': user_info.user.email.split('@')[0],
                        'first_name': user_info.user.user_metadata.get('full_name', '').split(' ')[0],
                        'last_name': ' '.join(user_info.user.user_metadata.get('full_name', '').split(' ')[1:]),
                        'profile_picture': user_info.user.user_metadata.get('avatar_url', ''),
                        'social_provider': provider,
                        'social_uid': user_info.user.id,
                        'email_verified': True
                    }
                )
                
                if created:
                    UserProfile.objects.create(user=user)
                
                return Response({
                    'user': UserSerializer(user).data,
                    'access_token': response.session.access_token,
                    'refresh_token': response.session.refresh_token
                }, status=status.HTTP_200_OK)
            
            return Response({'error': 'Social authentication failed'}, 
                          status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"Social login error: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            # Get access token from Authorization header
            auth_header = request.META.get('HTTP_AUTHORIZATION', '').split()
            if len(auth_header) != 2 or auth_header[0].lower() != 'bearer':
                return Response({'error': 'Invalid authorization header'}, 
                               status=status.HTTP_400_BAD_REQUEST)
            
            access_token = auth_header[1]
            supabase.auth.sign_out(access_token)
            
            return Response({'message': 'Successfully logged out'}, 
                          status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        profile = user.profile
        return Response({
            'user': UserSerializer(user).data,
            'profile': UserProfileSerializer(profile).data
        }, status=status.HTTP_200_OK)