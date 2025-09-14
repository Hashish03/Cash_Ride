from django.conf import settings
from rides.models import RideNotification
from twilio.rest import Client
import logging
from firebase_admin import messaging
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    def notify_rider_driver_assigned(ride):
        """
        Notify rider that a driver has been assigned
        """
        try:
            # Create database notification
            notification = RideNotification.objects.create(
                ride=ride,
                recipient=ride.rider,
                notification_type='driver_assigned',
                message=f"Your driver {ride.driver.first_name} is on the way"
            )
            
            # Send push notification
            if ride.rider.fcm_token:
                message = messaging.Message(
                    notification=messaging.Notification(
                        title="Driver Assigned",
                        body=f"{ride.driver.first_name} is coming to pick you up"
                    ),
                    token=ride.rider.fcm_token
                )
                messaging.send(message)
            
            # Send SMS if enabled
            if settings.TWILIO_ENABLED and ride.rider.phone_number:
                client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                client.messages.create(
                    body=f"CashRide: Your driver {ride.driver.first_name} is on the way",
                    from_=settings.TWILIO_PHONE_NUMBER,
                    to=ride.rider.phone_number
                )
            
            # Send WebSocket notification
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"user_{ride.rider.id}",
                {
                    "type": "ride.notification",
                    "notification": {
                        "id": notification.id,
                        "type": "driver_assigned",
                        "message": notification.message,
                        "timestamp": notification.created_at.isoformat(),
                        "ride_id": str(ride.id)
                    }
                }
            )
            
            return notification
        except Exception as e:
            logger.error(f"Error sending driver assigned notification: {str(e)}")
            raise

    @staticmethod
    def notify_driver_ride_request(ride, driver):
        """
        Notify driver of a new ride request
        """
        try:
            # Similar implementation as above for driver notifications
            pass
        except Exception as e:
            logger.error(f"Error sending ride request notification: {str(e)}")
            raise