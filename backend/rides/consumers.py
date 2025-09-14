import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from rides.models import Ride
from django.core.exceptions import PermissionDenied

class RideTrackingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.ride_id = self.scope['url_route']['kwargs']['ride_id']
        self.user = self.scope['user']
        
        # Verify user has permission to track this ride
        if not await self.verify_ride_access():
            await self.close()
            return
        
        self.room_group_name = f"ride_{self.ride_id}_tracking"
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial ride status
        ride = await self.get_ride()
        await self.send(text_data=json.dumps({
            'type': 'ride_status',
            'status': ride.status,
            'driver_assigned': bool(ride.driver),
            'current_location': {
                'latitude': ride.pickup_location.y,
                'longitude': ride.pickup_location.x
            } if ride.pickup_location else None
        }))

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type')
        
        if message_type == 'ping':
            await self.send(text_data=json.dumps({
                'type': 'pong'
            }))

    async def location_update(self, event):
        # Send location update to client
        await self.send(text_data=json.dumps({
            'type': 'location_update',
            'location': event['location']
        }))

    async def ride_notification(self, event):
        # Send notification to client
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification']
        }))

    @database_sync_to_async
    def verify_ride_access(self):
        """Verify user is either rider or driver for this ride"""
        ride = Ride.objects.filter(
            id=self.ride_id
        ).select_related('rider', 'driver').first()
        
        if not ride:
            return False
            
        if self.user not in [ride.rider, ride.driver]:
            raise PermissionDenied("You don't have permission to track this ride")
            
        return True

    @database_sync_to_async
    def get_ride(self):
        return Ride.objects.get(id=self.ride_id)