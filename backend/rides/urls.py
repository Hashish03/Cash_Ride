from django.urls import path
from .views import (
    RideRequestView,
    RideDetailView,
    RideStatusView,
    RideLocationUpdateView,
    RideCancelView,
    RideRatingView,
    RideEstimateView,
    DriverLocationView,
    ActiveRideView
)

urlpatterns = [
    path('request/', RideRequestView.as_view(), name='ride-request'),
    path('<uuid:pk>/', RideDetailView.as_view(), name='ride-detail'),
    path('<uuid:pk>/status/', RideStatusView.as_view(), name='ride-status'),
    path('<uuid:pk>/location/', RideLocationUpdateView.as_view(), name='ride-location'),
    path('<uuid:pk>/cancel/', RideCancelView.as_view(), name='ride-cancel'),
    path('<uuid:pk>/rate/', RideRatingView.as_view(), name='ride-rate'),
    path('estimate/', RideEstimateView.as_view(), name='ride-estimate'),
    path('driver/location/', DriverLocationView.as_view(), name='driver-location'),
    path('active/', ActiveRideView.as_view(), name='active-ride'),
]