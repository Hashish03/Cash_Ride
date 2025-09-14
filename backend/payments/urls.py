from django.urls import path
from .views import (
    PaymentMethodListView,
    PaymentMethodDetailView,
    SetDefaultPaymentMethodView,
    TransactionListView,
    WalletView,
    ProcessPaymentView,
    PaymentEstimateView,
    PayoutListView
)

urlpatterns = [
    path('methods/', PaymentMethodListView.as_view(), name='payment-methods'),
    path('methods/<int:pk>/', PaymentMethodDetailView.as_view(), name='payment-method-detail'),
    path('methods/<int:pk>/set-default/', SetDefaultPaymentMethodView.as_view(), name='set-default-payment'),
    path('transactions/', TransactionListView.as_view(), name='transactions'),
    path('wallet/', WalletView.as_view(), name='wallet'),
    path('process/', ProcessPaymentView.as_view(), name='process-payment'),
    path('estimate/', PaymentEstimateView.as_view(), name='payment-estimate'),
    path('payouts/', PayoutListView.as_view(), name='payouts'),
]