from django.urls import path
from .views import EarningsListView, PayoutListView


urlpatterns = [
    
    # Earnings
    path('earnings/', EarningsListView.as_view(), name='earnings-list'),
    path('earnings/<int:pk>/', EarningsListView.as_view(), name='earning-detail'),
    path('earnings/record/', EarningsListView.as_view(), name='record-earning'),
    path('earnings/ride/<int:ride_id>/', EarningsListView.as_view(), name='ride-earnings'),
    path('earnings/driver/<uuid:driver_id>/', EarningsListView.as_view(), name='driver-earnings'),
    path('earnings/driver/<uuid:driver_id>/ride/<int:ride_id>/', EarningsListView.as_view(), name='driver-ride-earnings'),
    path('earnings/driver/<uuid:driver_id>/total/', EarningsListView.as_view(), name='driver-total-earnings'),
    path('earnings/driver/<uuid:driver_id>/total/ride/<int:ride_id>/', EarningsListView.as_view(), name='driver-total-ride-earnings'),
    path('earnings/driver/<uuid:driver_id>/total/ride/<int:ride_id>/commission/', EarningsListView.as_view(), name='driver-ride-commission'),
    path('earnings/driver/<uuid:driver_id>/total/ride/<int:ride_id>/net/', EarningsListView.as_view(), name='driver-ride-net-earnings'),
    # Payouts
    path('payouts/', PayoutListView.as_view(), name='payouts-list'),
    path('payouts/request/', PayoutListView.as_view(), name='payout-request'),
    path('payouts/<int:pk>/', PayoutListView.as_view(), name='payout-detail'),
    path('payouts/driver/<uuid:driver_id>/', PayoutListView.as_view(), name='driver-payouts'),
    path('payouts/driver/<uuid:driver_id>/request/', PayoutListView.as_view(), name='driver-payout-request'),
    path('payouts/driver/<uuid:driver_id>/request/<int:amount>/', PayoutListView.as_view(), name='driver-payout-request-amount'),
    path('payouts/driver/<uuid:driver_id>/request/<int:amount>/method/<str:method>/', PayoutListView.as_view(), name='driver-payout-request-amount-method'),
    path('payouts/driver/<uuid:driver_id>/request/<int:amount>/method/<str:method>/status/', PayoutListView.as_view(), name='driver-payout-request-amount-method-status'),
    path('payouts/driver/<uuid:driver_id>/request/<int:amount>/method/<str:method>/status/<str:status>/', PayoutListView.as_view(), name='driver-payout-request-amount-method-status-detail'),
    path('payouts/driver/<uuid:driver_id>/request/<int:amount>/method/<str:method>/status/<str:status>/initiated_at/', PayoutListView.as_view(), name='driver-payout-request-amount-method-status-initiated'),
    path('payouts/driver/<uuid:driver_id>/request/<int:amount>/method/<str:method>/status/<str:status>/initiated_at/<str:initiated_at>/', PayoutListView.as_view(), name='driver-payout-request-amount-method-status-initiated-detail'),
    path('payouts/driver/<uuid:driver_id>/request/<int:amount>/method/<str:method>/status/<str:status>/initiated_at/<str:initiated_at>/completed_at/', PayoutListView.as_view(), name='driver-payout-request-amount-method-status-initiated-completed'),
    path('payouts/driver/<uuid:driver_id>/request/<int:amount>/method/<str:method>/status/<str:status>/initiated_at/<str:initiated_at>/completed_at/<str:completed_at>/', PayoutListView.as_view(), name='driver-payout-request-amount-method-status-initiated-completed-detail'),
]