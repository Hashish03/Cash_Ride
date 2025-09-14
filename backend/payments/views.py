from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import PaymentMethod, Transaction, Wallet, Payout
from .serializers import (
    PaymentMethodSerializer,
    TransactionSerializer,
    WalletSerializer,
    PayoutSerializer,
    PaymentEstimateSerializer
)
from django.shortcuts import get_object_or_404
from django.db import transaction
from .services import PaymentService
import logging

logger = logging.getLogger(__name__)

class PaymentMethodListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        payment_methods = PaymentMethod.objects.filter(user=request.user)
        serializer = PaymentMethodSerializer(payment_methods, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = PaymentMethodSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            payment_method = serializer.save(user=request.user)
            
            # If this is the first payment method, set it as default
            if PaymentMethod.objects.filter(user=request.user).count() == 1:
                payment_method.is_default = True
                payment_method.save()
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PaymentMethodDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk, user):
        return get_object_or_404(PaymentMethod, pk=pk, user=user)
    
    def get(self, request, pk):
        payment_method = self.get_object(pk, request.user)
        serializer = PaymentMethodSerializer(payment_method)
        return Response(serializer.data)
    
    def put(self, request, pk):
        payment_method = self.get_object(pk, request.user)
        serializer = PaymentMethodSerializer(payment_method, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        payment_method = self.get_object(pk, request.user)
        
        # Don't allow deletion if it's the only payment method
        if PaymentMethod.objects.filter(user=request.user).count() == 1:
            return Response(
                {"detail": "Cannot delete the only payment method. Add another method first."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # If deleting default, set another method as default
        if payment_method.is_default:
            other_method = PaymentMethod.objects.filter(
                user=request.user
            ).exclude(pk=pk).first()
            if other_method:
                other_method.is_default = True
                other_method.save()
        
        payment_method.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class SetDefaultPaymentMethodView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        # Reset all default payment methods for user
        PaymentMethod.objects.filter(user=request.user).update(is_default=False)
        
        # Set the selected one as default
        payment_method = get_object_or_404(PaymentMethod, pk=pk, user=request.user)
        payment_method.is_default = True
        payment_method.save()
        
        return Response(
            {"detail": "Default payment method updated successfully"},
            status=status.HTTP_200_OK
        )

class TransactionListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        transactions = Transaction.objects.filter(user=request.user).order_by('-created_at')
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)

class WalletView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        serializer = WalletSerializer(wallet)
        return Response(serializer.data)

class ProcessPaymentView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # In a real implementation, this would integrate with Stripe/PayPal/etc.
        # This is a simplified version for demonstration
        
        amount = request.data.get('amount')
        payment_method_id = request.data.get('payment_method_id')
        
        if not amount or not payment_method_id:
            return Response(
                {"detail": "Amount and payment method are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            payment_method = PaymentMethod.objects.get(pk=payment_method_id, user=request.user)
        except PaymentMethod.DoesNotExist:
            return Response(
                {"detail": "Payment method not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            # Process payment through the payment service
            payment_service = PaymentService()
            transaction = payment_service.process_payment(
                user=request.user,
                amount=amount,
                payment_method=payment_method,
                description=request.data.get('description', 'Ride payment')
            )
            
            serializer = TransactionSerializer(transaction)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Payment processing failed: {str(e)}")
            return Response(
                {"detail": "Payment processing failed"},
                status=status.HTTP_400_BAD_REQUEST
            )

class PaymentEstimateView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = PaymentEstimateSerializer(data=request.data)
        if serializer.is_valid():
            # Calculate fare based on distance, duration, ride type, etc.
            # This is a simplified calculation - real implementation would be more complex
            data = serializer.validated_data
            base_fare = 2.50  # Base fare
            distance_rate = 1.50  # Per mile
            time_rate = 0.25  # Per minute
            ride_type_multiplier = 1.0  # Could vary by ride type
            
            estimated_fare = (
                base_fare + 
                (data['distance'] * distance_rate) + 
                (data['duration'] * time_rate)
            ) * data['surge_multiplier'] * ride_type_multiplier
            
            return Response({
                'estimated_fare': round(estimated_fare, 2),
                'currency': 'USD',
                'breakdown': {
                    'base_fare': base_fare,
                    'distance_cost': data['distance'] * distance_rate,
                    'time_cost': data['duration'] * time_rate,
                    'surge_multiplier': data['surge_multiplier'],
                    'ride_type_multiplier': ride_type_multiplier
                }
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PayoutListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        payouts = Payout.objects.filter(user=request.user).order_by('-initiated_at')
        serializer = PayoutSerializer(payouts, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = PayoutSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            # Check if user has sufficient balance
            wallet = Wallet.objects.get(user=request.user)
            if wallet.balance < serializer.validated_data['amount']:
                return Response(
                    {"detail": "Insufficient balance for payout"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Process payout
            payout = serializer.save(user=request.user)
            
            # Deduct from wallet (in a real app, this would be more sophisticated)
            wallet.balance -= payout.amount
            wallet.save()
            
            # In a real app, you would initiate an actual payout to the user's bank/wallet here
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)