from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Ride, RideLocationUpdate, DriverLocation, CancellationReason
from .serializers import (
    RideSerializer,
    RideRequestSerializer,
    RideLocationUpdateSerializer,
    RideStatusUpdateSerializer,
    RideRatingSerializer,
    RideEstimateSerializer
)
from .services import RideService
from django.shortcuts import get_object_or_404
from users.models import User
import logging

logger = logging.getLogger(__name__)

class RideRequestView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = RideRequestSerializer(data=request.data)
        if serializer.is_valid():
            try:
                ride = RideService.create_ride_request(request.user, serializer.validated_data)
                if ride:
                    return Response(RideSerializer(ride).data, status=status.HTTP_201_CREATED)
                return Response(
                    {"detail": "No available drivers at this time"},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            except Exception as e:
                logger.error(f"Ride request error: {str(e)}")
                return Response(
                    {"detail": "Error processing ride request"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RideDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get_ride(self, pk, user):
        return get_object_or_404(Ride, pk=pk, rider=user)
    
    def get(self, request, pk):
        ride = self.get_ride(pk, request.user)
        serializer = RideSerializer(ride)
        return Response(serializer.data)

class RideStatusView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get_ride(self, pk, user):
        return get_object_or_404(Ride, pk=pk, driver=user)
    
    def put(self, request, pk):
        ride = self.get_ride(pk, request.user)
        serializer = RideStatusUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                ride = RideService.update_ride_status(
                    ride,
                    serializer.validated_data['status'],
                    serializer.validated_data.get('current_location')
                )
                return Response(RideSerializer(ride).data)
            except Exception as e:
                logger.error(f"Ride status update error: {str(e)}")
                return Response(
                    {"detail": "Error updating ride status"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RideLocationUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get_ride(self, pk, user):
        # Allow both rider and driver to update location
        return get_object_or_404(Ride, pk=pk, models.Q(rider=user) | models.Q(driver=user))
    
    def post(self, request, pk):
        ride = self.get_ride(pk, request.user)
        serializer = RideLocationUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                is_driver = ride.driver == request.user
                RideService.update_ride_location(
                    ride,
                    serializer.validated_data['location'],
                    is_driver=is_driver
                )
                return Response(status=status.HTTP_204_NO_CONTENT)
            except Exception as e:
                logger.error(f"Location update error: {str(e)}")
                return Response(
                    {"detail": "Error updating location"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RideCancelView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get_ride(self, pk, user):
        return get_object_or_404(Ride, pk=pk, rider=user)
    
    def post(self, request, pk):
        ride = self.get_ride(pk, request.user)
        
        if ride.status in ['completed', 'cancelled']:
            return Response(
                {"detail": "Ride is already completed or cancelled"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            ride = RideService.cancel_ride(
                ride,
                'rider',
                request.data.get('reason')
            )
            return Response(RideSerializer(ride).data)
        except Exception as e:
            logger.error(f"Ride cancellation error: {str(e)}")
            return Response(
                {"detail": "Error cancelling ride"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class RideRatingView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get_ride(self, pk, user):
        return get_object_or_404(Ride, pk=pk, rider=user)
    
    def post(self, request, pk):
        ride = self.get_ride(pk, request.user)
        
        if ride.status != 'completed':
            return Response(
                {"detail": "Can only rate completed rides"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = RideRatingSerializer(data=request.data)
        if serializer.is_valid():
            try:
                ride = RideService.rate_ride(
                    ride,
                    'driver',
                    serializer.validated_data['rating'],
                    serializer.validated_data.get('feedback')
                )
                return Response(RideSerializer(ride).data)
            except Exception as e:
                logger.error(f"Ride rating error: {str(e)}")
                return Response(
                    {"detail": "Error submitting rating"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RideEstimateView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = RideEstimateSerializer(data=request.data)
        if serializer.is_valid():
            try:
                estimate = RideService.calculate_fare_estimate(
                    serializer.validated_data['pickup_location'],
                    serializer.validated_data['dropoff_location'],
                    serializer.validated_data['ride_type']
                )
                return Response(estimate)
            except Exception as e:
                logger.error(f"Fare estimate error: {str(e)}")
                return Response(
                    {"detail": "Error calculating fare estimate"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DriverLocationView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not hasattr(request.user, 'driver_profile'):
            return Response(
                {"detail": "Only drivers can update location"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        location = get_object_or_404(DriverLocation, driver=request.user)
        serializer = DriverLocationSerializer(location)
        return Response(serializer.data)
    
    def put(self, request):
        if not hasattr(request.user, 'driver_profile'):
            return Response(
                {"detail": "Only drivers can update location"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        location, _ = DriverLocation.objects.get_or_create(driver=request.user)
        serializer = DriverLocationSerializer(location, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ActiveRideView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # For riders
        active_ride = Ride.objects.filter(
            rider=request.user,
            status__in=['requested', 'driver_assigned', 'arrived', 'in_progress']
        ).first()
        
        # For drivers
        if not active_ride and hasattr(request.user, 'driver_profile'):
            active_ride = Ride.objects.filter(
                driver=request.user,
                status__in=['driver_assigned', 'arrived', 'in_progress']
            ).first()
        
        if active_ride:
            serializer = RideSerializer(active_ride)
            return Response(serializer.data)
        return Response(status=status.HTTP_204_NO_CONTENT)