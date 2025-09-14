from django.urls import path
from .views import (
    RegisterView, LoginView, LogoutView,
    SocialLoginView, UserProfileView
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('social-login/', SocialLoginView.as_view(), name='social-login'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    
    # Add these paths for social providers
    path('google/', SocialLoginView.as_view(), name='google-login'),
    path('facebook/', SocialLoginView.as_view(), name='facebook-login'),
    path('apple/', SocialLoginView.as_view(), name='apple-login'),
    path('github/', SocialLoginView.as_view(), name='github-login'),
    path('twitter/', SocialLoginView.as_view(), name='twitter-login'),
]