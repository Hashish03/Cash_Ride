from django.urls import path
from . import views

urlpatterns = [
    # Registration & Login
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    
    # Social Authentication
    path('social/login/', views.SocialLoginView.as_view(), name='social_login'),
    path('social/callback/', views.SocialAuthCallbackView.as_view(), name='social_callback'),
    
    # OTP Authentication
    path('otp/request/', views.OTPRequestView.as_view(), name='otp_request'),
    path('otp/verify/', views.OTPVerifyView.as_view(), name='otp_verify'),
    
    # Token Management
    path('token/refresh/', views.TokenRefreshView.as_view(), name='token_refresh'),
    
    # User Profile
    path('profile/', views.UserProfileView.as_view(), name='user_profile'),
    path('account/delete/', views.DeleteAccountView.as_view(), name='delete_account'),
]