from django.urls import path
from .views import (
    DriverRegistrationView,
    DriverProfileView,
    VehicleListView,
    VehicleDetailView,
    DriverStatusView,
    RatingsListView
)

urlpatterns = [

    # Driver registration and profile
    path('register/', DriverRegistrationView.as_view(), name='driver-register'),
    path('profile/', DriverProfileView.as_view(), name='driver-profile'),
    
    # Vehicles
    path('vehicles/', VehicleListView.as_view(), name='vehicle-list'),
    path('vehicles/<uuid:pk>/', VehicleDetailView.as_view(), name='vehicle-detail'),
    
    path('status/', DriverStatusView.as_view(), name='driver-status'),
    path('ratings/', RatingsListView.as_view(), name='ratings-list'),
]