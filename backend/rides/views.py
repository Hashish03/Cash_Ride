from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListAPIView
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
import logging

from .models import Ride, RideLocationUpdate, DriverLocation, CancellationReason
from .serializers import (
    RideSerializer,
    RideRequestSerializer,
    RideLocationUpdateSerializer,
    RideStatusUpdateSerializer,
    RideRatingSerializer,
    RideEstimateSerializer,
    DriverLocationSerializer,
    RideListSerializer,
    RideCancelSerializer,
    RidePaymentSerializer
)
from .services import RideService, PaymentService
from users.models import User
from drivers.models import DriverProfile
from payments.models import Transaction

logger = logging.getLogger(__name__)


class RideRequestView(APIView):
    """API endpoint for requesting a ride"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Request a new ride
        """
        serializer = RideRequestSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            try:
                ride_data = serializer.validated_data
                
                # Create ride request
                ride = RideService.create_ride_request(
                    user=request.user,
                    pickup_location=ride_data['pickup_location'],
                    dropoff_location=ride_data['dropoff_location'],
                    ride_type=ride_data.get('ride_type', 'standard'),
                    payment_method=ride_data.get('payment_method', 'cash'),
                    estimated_fare=ride_data.get('estimated_fare'),
                    notes=ride_data.get('notes'),
                    scheduled_time=ride_data.get('scheduled_time')
                )
                
                if ride:
                    # Serialize response
                    response_data = RideSerializer(ride).data
                    response_data['message'] = 'Ride requested successfully'
                    return Response(response_data, status=status.HTTP_201_CREATED)
                
                return Response(
                    {
                        "detail": "No available drivers found at this time. Please try again later.",
                        "code": "no_drivers_available"
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
                
            except ValidationError as e:
                return Response(
                    {"detail": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                logger.error(f"Ride request error: {str(e)}", exc_info=True)
                return Response(
                    {
                        "detail": "An error occurred while processing your ride request",
                        "code": "ride_request_failed"
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(
            {
                "detail": "Invalid request data",
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )


class RideDetailView(APIView):
    """API endpoint for ride details"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk, user):
        """Get ride object with permission check"""
        ride = get_object_or_404(Ride, pk=pk)
        
        # Check if user is authorized to view this ride
        if ride.rider != user and (not hasattr(user, 'driver_profile') or ride.driver != user):
            raise PermissionDenied("You are not authorized to view this ride")
        
        return ride
    
    def get(self, request, pk):
        """Get ride details"""
        try:
            ride = self.get_object(pk, request.user)
            serializer = RideSerializer(ride, context={'request': request})
            return Response(serializer.data)
        except PermissionDenied as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Error fetching ride details: {str(e)}")
            return Response(
                {"detail": "Error fetching ride details"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RideStatusUpdateView(APIView):
    """API endpoint for updating ride status (for drivers)"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk, user):
        """Get ride object with driver permission check"""
        if not hasattr(user, 'driver_profile'):
            raise PermissionDenied("Only drivers can update ride status")
        
        ride = get_object_or_404(Ride, pk=pk, driver=user)
        return ride
    
    def put(self, request, pk):
        """Update ride status"""
        try:
            ride = self.get_object(pk, request.user)
            
            # Check if ride can be updated
            if ride.status in ['completed', 'cancelled']:
                return Response(
                    {"detail": f"Cannot update status of a {ride.status} ride"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = RideStatusUpdateSerializer(
                data=request.data,
                context={'ride': ride}
            )
            
            if serializer.is_valid():
                status_update = serializer.validated_data['status']
                current_location = serializer.validated_data.get('current_location')
                
                # Update ride status
                updated_ride = RideService.update_ride_status(
                    ride=ride,
                    new_status=status_update,
                    current_location=current_location,
                    updated_by='driver'
                )
                
                # Serialize response
                response_serializer = RideSerializer(updated_ride)
                return Response(response_serializer.data)
            
            return Response(
                {"detail": "Invalid status update data", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except PermissionDenied as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except ValidationError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Ride status update error: {str(e)}", exc_info=True)
            return Response(
                {"detail": "Error updating ride status"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RideLocationUpdateView(APIView):
    """API endpoint for updating ride location"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk, user):
        """Get ride object with permission check"""
        ride = get_object_or_404(Ride, pk=pk)
        
        # Check if user is authorized to update location
        if ride.rider != user and (not hasattr(user, 'driver_profile') or ride.driver != user):
            raise PermissionDenied("You are not authorized to update this ride's location")
        
        return ride
    
    def post(self, request, pk):
        """Update ride location"""
        try:
            ride = self.get_object(pk, request.user)
            
            serializer = RideLocationUpdateSerializer(data=request.data)
            if serializer.is_valid():
                location = serializer.validated_data['location']
                location_type = serializer.validated_data.get('location_type', 'driver')
                
                # Determine if update is from driver or rider
                is_driver = hasattr(request.user, 'driver_profile') and ride.driver == request.user
                
                # Update location
                RideService.update_ride_location(
                    ride=ride,
                    location=location,
                    location_type=location_type,
                    updated_by='driver' if is_driver else 'rider'
                )
                
                return Response(
                    {"detail": "Location updated successfully"},
                    status=status.HTTP_200_OK
                )
            
            return Response(
                {"detail": "Invalid location data", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except PermissionDenied as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except ValidationError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Location update error: {str(e)}", exc_info=True)
            return Response(
                {"detail": "Error updating location"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RideCancelView(APIView):
    """API endpoint for cancelling a ride"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk, user):
        """Get ride object with permission check"""
        ride = get_object_or_404(Ride, pk=pk)
        
        # Check if user is authorized to cancel this ride
        if ride.rider != user and (not hasattr(user, 'driver_profile') or ride.driver != user):
            raise PermissionDenied("You are not authorized to cancel this ride")
        
        return ride
    
    def post(self, request, pk):
        """Cancel a ride"""
        try:
            ride = self.get_object(pk, request.user)
            
            serializer = RideCancelSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {"detail": "Invalid cancellation data", "errors": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            reason = serializer.validated_data.get('reason')
            cancellation_note = serializer.validated_data.get('cancellation_note')
            
            # Determine who is cancelling
            cancelled_by = 'driver' if hasattr(request.user, 'driver_profile') and ride.driver == request.user else 'rider'
            
            # Check if ride can be cancelled
            if ride.status in ['completed', 'cancelled']:
                return Response(
                    {"detail": f"Ride is already {ride.status}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Cancel the ride
            cancelled_ride = RideService.cancel_ride(
                ride=ride,
                cancelled_by=cancelled_by,
                reason=reason,
                cancellation_note=cancellation_note
            )
            
            # Serialize response
            response_serializer = RideSerializer(cancelled_ride)
            return Response(response_serializer.data)
            
        except PermissionDenied as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except ValidationError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Ride cancellation error: {str(e)}", exc_info=True)
            return Response(
                {"detail": "Error cancelling ride"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RideRatingView(APIView):
    """API endpoint for rating a ride"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk, user):
        """Get ride object with rider permission check"""
        ride = get_object_or_404(Ride, pk=pk, rider=user)
        return ride
    
    def post(self, request, pk):
        """Rate a ride (rider rates driver)"""
        try:
            ride = self.get_object(pk, request.user)
            
            # Check if ride can be rated
            if ride.status != 'completed':
                return Response(
                    {"detail": "Can only rate completed rides"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if already rated
            if ride.driver_rating is not None:
                return Response(
                    {"detail": "You have already rated this ride"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = RideRatingSerializer(data=request.data)
            if serializer.is_valid():
                rating = serializer.validated_data['rating']
                feedback = serializer.validated_data.get('feedback')
                
                # Submit rating
                rated_ride = RideService.rate_ride(
                    ride=ride,
                    rated_by='rider',
                    rating_for='driver',
                    rating=rating,
                    feedback=feedback
                )
                
                # Serialize response
                response_serializer = RideSerializer(rated_ride)
                return Response(response_serializer.data)
            
            return Response(
                {"detail": "Invalid rating data", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except PermissionDenied as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except ValidationError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Ride rating error: {str(e)}", exc_info=True)
            return Response(
                {"detail": "Error submitting rating"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DriverRatingView(APIView):
    """API endpoint for driver to rate rider"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk, user):
        """Get ride object with driver permission check"""
        if not hasattr(user, 'driver_profile'):
            raise PermissionDenied("Only drivers can rate riders")
        
        ride = get_object_or_404(Ride, pk=pk, driver=user)
        return ride
    
    def post(self, request, pk):
        """Rate a rider (driver rates rider)"""
        try:
            ride = self.get_object(pk, request.user)
            
            # Check if ride can be rated
            if ride.status != 'completed':
                return Response(
                    {"detail": "Can only rate completed rides"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if already rated
            if ride.rider_rating is not None:
                return Response(
                    {"detail": "You have already rated this rider"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = RideRatingSerializer(data=request.data)
            if serializer.is_valid():
                rating = serializer.validated_data['rating']
                feedback = serializer.validated_data.get('feedback')
                
                # Submit rating
                rated_ride = RideService.rate_ride(
                    ride=ride,
                    rated_by='driver',
                    rating_for='rider',
                    rating=rating,
                    feedback=feedback
                )
                
                # Serialize response
                response_serializer = RideSerializer(rated_ride)
                return Response(response_serializer.data)
            
            return Response(
                {"detail": "Invalid rating data", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except PermissionDenied as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Driver rating error: {str(e)}", exc_info=True)
            return Response(
                {"detail": "Error submitting rating"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RideEstimateView(APIView):
    """API endpoint for fare estimation"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Get fare estimate for a ride"""
        serializer = RideEstimateSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                estimate_data = serializer.validated_data
                
                # Calculate fare estimate
                estimate = RideService.calculate_fare_estimate(
                    pickup_location=estimate_data['pickup_location'],
                    dropoff_location=estimate_data['dropoff_location'],
                    ride_type=estimate_data.get('ride_type', 'standard'),
                    vehicle_type=estimate_data.get('vehicle_type'),
                    distance_km=estimate_data.get('distance_km'),
                    duration_minutes=estimate_data.get('duration_minutes'),
                    surge_multiplier=estimate_data.get('surge_multiplier', 1.0)
                )
                
                return Response(estimate)
                
            except ValidationError as e:
                return Response(
                    {"detail": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                logger.error(f"Fare estimate error: {str(e)}", exc_info=True)
                return Response(
                    {"detail": "Error calculating fare estimate"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(
            {"detail": "Invalid estimation data", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )


class DriverLocationView(APIView):
    """API endpoint for driver location management"""
    permission_classes = [IsAuthenticated]
    
    def check_driver_permission(self, user):
        """Check if user is a driver"""
        if not hasattr(user, 'driver_profile'):
            raise PermissionDenied("Only drivers can access this endpoint")
    
    def get(self, request):
        """Get driver's current location"""
        try:
            self.check_driver_permission(request.user)
            
            location = get_object_or_404(DriverLocation, driver=request.user)
            serializer = DriverLocationSerializer(location)
            return Response(serializer.data)
            
        except PermissionDenied as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Get driver location error: {str(e)}")
            return Response(
                {"detail": "Error fetching driver location"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def put(self, request):
        """Update driver's location"""
        try:
            self.check_driver_permission(request.user)
            
            location, created = DriverLocation.objects.get_or_create(
                driver=request.user,
                defaults={
                    'latitude': 0.0,
                    'longitude': 0.0,
                    'is_online': False
                }
            )
            
            serializer = DriverLocationSerializer(
                location,
                data=request.data,
                partial=True,
                context={'request': request}
            )
            
            if serializer.is_valid():
                updated_location = serializer.save()
                
                # If location is being updated, also update driver's online status
                if 'is_online' in serializer.validated_data:
                    driver_profile = request.user.driver_profile
                    driver_profile.is_online = serializer.validated_data['is_online']
                    driver_profile.last_online_at = timezone.now()
                    driver_profile.save()
                
                return Response(DriverLocationSerializer(updated_location).data)
            
            return Response(
                {"detail": "Invalid location data", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except PermissionDenied as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Update driver location error: {str(e)}")
            return Response(
                {"detail": "Error updating driver location"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ActiveRideView(APIView):
    """API endpoint for active ride"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get user's active ride"""
        try:
            active_ride = None
            
            # Check for rider's active ride
            active_ride = Ride.objects.filter(
                rider=request.user,
                status__in=['requested', 'driver_assigned', 'arrived', 'in_progress']
            ).order_by('-created_at').first()
            
            # Check for driver's active ride
            if not active_ride and hasattr(request.user, 'driver_profile'):
                active_ride = Ride.objects.filter(
                    driver=request.user,
                    status__in=['driver_assigned', 'arrived', 'in_progress']
                ).order_by('-created_at').first()
            
            if active_ride:
                serializer = RideSerializer(active_ride, context={'request': request})
                return Response(serializer.data)
            
            return Response(
                {"detail": "No active ride found"},
                status=status.HTTP_404_NOT_FOUND
            )
            
        except Exception as e:
            logger.error(f"Get active ride error: {str(e)}")
            return Response(
                {"detail": "Error fetching active ride"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RideListView(ListAPIView):
    """API endpoint for ride history"""
    permission_classes = [IsAuthenticated]
    serializer_class = RideListSerializer
    
    def get_queryset(self):
        """Get rides for current user"""
        user = self.request.user
        ride_type = self.request.query_params.get('type', 'all')
        status_filter = self.request.query_params.get('status')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        # Base queryset based on user role
        if hasattr(user, 'driver_profile'):
            queryset = Ride.objects.filter(driver=user)
        else:
            queryset = Ride.objects.filter(rider=user)
        
        # Apply filters
        if ride_type == 'completed':
            queryset = queryset.filter(status='completed')
        elif ride_type == 'cancelled':
            queryset = queryset.filter(status='cancelled')
        elif ride_type == 'upcoming':
            queryset = queryset.filter(
                status__in=['requested', 'driver_assigned', 'arrived'],
                scheduled_time__gte=timezone.now()
            )
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        # Order by latest first
        return queryset.order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Ride list error: {str(e)}")
            return Response(
                {"detail": "Error fetching ride history"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RidePaymentView(APIView):
    """API endpoint for ride payment"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk, user):
        """Get ride object with permission check"""
        ride = get_object_or_404(Ride, pk=pk)
        
        # Check if user is authorized to make payment
        if ride.rider != user:
            raise PermissionDenied("You are not authorized to pay for this ride")
        
        return ride
    
    def post(self, request, pk):
        """Process ride payment"""
        try:
            ride = self.get_object(pk, request.user)
            
            # Check if payment is needed
            if ride.status != 'completed':
                return Response(
                    {"detail": "Payment can only be made for completed rides"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if ride.payment_status == 'paid':
                return Response(
                    {"detail": "Ride has already been paid"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = RidePaymentSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {"detail": "Invalid payment data", "errors": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            payment_method = serializer.validated_data.get('payment_method', 'cash')
            tip_amount = serializer.validated_data.get('tip_amount', 0)
            
            # Process payment
            payment_result = RideService.process_ride_payment(
                ride=ride,
                payment_method=payment_method,
                tip_amount=tip_amount
            )
            
            return Response(payment_result)
            
        except PermissionDenied as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except ValidationError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Ride payment error: {str(e)}", exc_info=True)
            return Response(
                {"detail": "Error processing payment"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RideReceiptView(APIView):
    """API endpoint for ride receipt"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk, user):
        """Get ride object with permission check"""
        ride = get_object_or_404(Ride, pk=pk)
        
        # Check if user is authorized to view receipt
        if ride.rider != user and (not hasattr(user, 'driver_profile') or ride.driver != user):
            raise PermissionDenied("You are not authorized to view this receipt")
        
        return ride
    
    def get(self, request, pk):
        """Get ride receipt"""
        try:
            ride = self.get_object(pk, request.user)
            
            # Check if ride has receipt
            if ride.status != 'completed' or ride.payment_status != 'paid':
                return Response(
                    {"detail": "Receipt is not available for this ride"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Generate receipt data
            receipt = {
                'ride_id': ride.id,
                'receipt_number': f"RCPT-{ride.id:08d}",
                'date': ride.completed_at.strftime('%Y-%m-%d %H:%M:%S') if ride.completed_at else None,
                'rider': {
                    'name': ride.rider.get_full_name() or ride.rider.email,
                    'phone': ride.rider.phone_number
                },
                'driver': {
                    'name': ride.driver.get_full_name() if ride.driver else None,
                    'phone': ride.driver.phone_number if ride.driver else None,
                    'vehicle': ride.vehicle_type if hasattr(ride, 'vehicle_type') else 'Standard'
                },
                'trip_details': {
                    'pickup': ride.pickup_location,
                    'dropoff': ride.dropoff_location,
                    'distance': f"{ride.distance_km:.2f} km" if ride.distance_km else None,
                    'duration': f"{ride.duration_minutes} min" if ride.duration_minutes else None
                },
                'fare_breakdown': {
                    'base_fare': float(ride.base_fare) if ride.base_fare else 0.0,
                    'distance_fare': float(ride.distance_fare) if ride.distance_fare else 0.0,
                    'time_fare': float(ride.time_fare) if ride.time_fare else 0.0,
                    'service_fee': float(ride.service_fee) if ride.service_fee else 0.0,
                    'surge_multiplier': float(ride.surge_multiplier) if ride.surge_multiplier else 1.0,
                    'tip': float(ride.tip_amount) if ride.tip_amount else 0.0,
                    'total': float(ride.total_fare) if ride.total_fare else 0.0
                },
                'payment_info': {
                    'method': ride.payment_method,
                    'status': ride.payment_status,
                    'transaction_id': ride.transaction.transaction_id if hasattr(ride, 'transaction') else None
                }
            }
            
            return Response(receipt)
            
        except PermissionDenied as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Receipt generation error: {str(e)}")
            return Response(
                {"detail": "Error generating receipt"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RideSupportView(APIView):
    """API endpoint for ride support/issues"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        """Report an issue with a ride"""
        try:
            ride = get_object_or_404(Ride, pk=pk)
            
            # Check if user is authorized to report issue
            if ride.rider != request.user and (not hasattr(request.user, 'driver_profile') or ride.driver != request.user):
                raise PermissionDenied("You are not authorized to report an issue for this ride")
            
            issue_type = request.data.get('issue_type')
            description = request.data.get('description')
            
            if not issue_type or not description:
                return Response(
                    {"detail": "Issue type and description are required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create support ticket
            support_ticket = RideService.create_support_ticket(
                ride=ride,
                reported_by=request.user,
                issue_type=issue_type,
                description=description,
                priority=request.data.get('priority', 'medium')
            )
            
            return Response(
                {
                    "detail": "Support ticket created successfully",
                    "ticket_id": support_ticket.id,
                    "status": support_ticket.status
                },
                status=status.HTTP_201_CREATED
            )
            
        except PermissionDenied as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Support ticket creation error: {str(e)}")
            return Response(
                {"detail": "Error creating support ticket"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )