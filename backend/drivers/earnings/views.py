from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import DriverEarningSerializer, PayoutSerializer, PayoutRequestSerializer
from .services import EarningService
from django.shortcuts import get_object_or_404
import logging

logger = logging.getLogger(__name__)

class EarningsListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not hasattr(request.user, 'driver_profile'):
            return Response(
                {"detail": "User is not a driver"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        earnings = request.user.driver_profile.earnings.all().order_by('-created_at')
        serializer = DriverEarningSerializer(earnings, many=True)
        return Response(serializer.data)

class PayoutListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not hasattr(request.user, 'driver_profile'):
            return Response(
                {"detail": "User is not a driver"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        payouts = request.user.driver_profile.payouts.all().order_by('-initiated_at')
        serializer = PayoutSerializer(payouts, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        if not hasattr(request.user, 'driver_profile'):
            return Response(
                {"detail": "User is not a driver"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = PayoutRequestSerializer(data=request.data)
        if serializer.is_valid():
            try:
                payout = EarningService.process_payout(
                    request.user.driver_profile,
                    serializer.validated_data['amount'],
                    serializer.validated_data['method']
                )
                return Response(
                    PayoutSerializer(payout).data,
                    status=status.HTTP_201_CREATED
                )
            except Exception as e:
                logger.error(f"Payout error: {str(e)}")
                return Response(
                    {"detail": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)