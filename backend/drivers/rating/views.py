from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import  Vehicle
from .serializers import (
    DriverProfileSerializer,
    VehicleSerializer,
    DriverRegistrationSerializer, 
)
from .services import DriverService
from django.shortcuts import get_object_or_404
from users.models import User
import logging

logger = logging.getLogger(__name__)


class RatingsListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not hasattr(request.user, 'driver_profile'):
            return Response(
                {"detail": "User is not a driver"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        ratings = request.user.driver_profile.ratings.all().order_by('-created_at')
        serializer = DriverRatingSerializer(ratings, many=True)
        return Response(serializer.data)
      
class DriverStatusView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not hasattr(request.user, 'driver_profile'):
            return Response(
                {"detail": "User is not a driver"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = DriverProfileSerializer(request.user.driver_profile)
        return Response(serializer.data)
    
    def put(self, request):
        if not hasattr(request.user, 'driver_profile'):
            return Response(
                {"detail": "User is not a driver"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = DriverStatusUpdateSerializer(data=request.data)
        if serializer.is_valid():
            try:
                driver_profile = DriverService.update_driver_status(
                    request.user.driver_profile,
                    serializer.validated_data['online'],
                    serializer.validated_data['available'],
                    serializer.validated_data.get('location')
                )
                return Response(DriverProfileSerializer(driver_profile).data)
            except Exception as e:
                logger.error(f"Driver status update error: {str(e)}")
                return Response(
                    {"detail": "Error updating driver status"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
  