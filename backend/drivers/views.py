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

class DriverRegistrationView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = DriverRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            try:
                driver_profile = DriverService.register_driver(serializer.validated_data)
                return Response(
                    DriverProfileSerializer(driver_profile).data,
                    status=status.HTTP_201_CREATED
                )
            except Exception as e:
                logger.error(f"Driver registration error: {str(e)}")
                return Response(
                    {"detail": "Error processing driver registration"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DriverProfileView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not hasattr(request.user, 'driver_profile'):
            return Response(
                {"detail": "User is not a driver"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = DriverProfileSerializer(request.user.driver_profile)
        return Response(serializer.data)

class VehicleListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not hasattr(request.user, 'driver_profile'):
            return Response(
                {"detail": "User is not a driver"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        vehicles = request.user.driver_profile.vehicles.all()
        serializer = VehicleSerializer(vehicles, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        if not hasattr(request.user, 'driver_profile'):
            return Response(
                {"detail": "User is not a driver"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = VehicleSerializer(data=request.data)
        if serializer.is_valid():
            vehicle = serializer.save(driver=request.user.driver_profile)
            return Response(
                VehicleSerializer(vehicle).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VehicleDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get_vehicle(self, pk, driver_profile):
        return get_object_or_404(Vehicle, pk=pk, driver=driver_profile)
    
    def get(self, request, pk):
        if not hasattr(request.user, 'driver_profile'):
            return Response(
                {"detail": "User is not a driver"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        vehicle = self.get_vehicle(pk, request.user.driver_profile)
        serializer = VehicleSerializer(vehicle)
        return Response(serializer.data)
    
    def put(self, request, pk):
        if not hasattr(request.user, 'driver_profile'):
            return Response(
                {"detail": "User is not a driver"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        vehicle = self.get_vehicle(pk, request.user.driver_profile)
        serializer = VehicleSerializer(vehicle, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        if not hasattr(request.user, 'driver_profile'):
            return Response(
                {"detail": "User is not a driver"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        vehicle = self.get_vehicle(pk, request.user.driver_profile)
        
        # Don't allow deletion if it's the only vehicle
        if request.user.driver_profile.vehicles.count() == 1:
            return Response(
                {"detail": "Cannot delete the only vehicle. Add another vehicle first."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        vehicle.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


