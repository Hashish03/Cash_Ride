from django.contrib import admin
from .models import Ride, RideLocationUpdate, DriverLocation, RideRequestLog, CancellationReason

@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = ('id', 'rider', 'driver', 'status', 'total_fare', 'requested_at')
    list_filter = ('status', 'ride_type')
    search_fields = ('rider__email', 'driver__email', 'pickup_address', 'dropoff_address')
    readonly_fields = ('requested_at', 'accepted_at', 'arrived_at', 'started_at', 'completed_at')

@admin.register(RideLocationUpdate)
class RideLocationUpdateAdmin(admin.ModelAdmin):
    list_display = ('ride', 'timestamp', 'is_driver_location')
    list_filter = ('is_driver_location',)
    readonly_fields = ('timestamp',)

@admin.register(DriverLocation)
class DriverLocationAdmin(admin.ModelAdmin):
    list_display = ('driver', 'is_available', 'last_updated')
    list_filter = ('is_available',)
    readonly_fields = ('last_updated',)

@admin.register(RideRequestLog)
class RideRequestLogAdmin(admin.ModelAdmin):
    list_display = ('ride', 'driver', 'status', 'timestamp')
    list_filter = ('status',)
    readonly_fields = ('timestamp',)

@admin.register(CancellationReason)
class CancellationReasonAdmin(admin.ModelAdmin):
    list_display = ('ride', 'cancelled_by', 'timestamp')
    list_filter = ('cancelled_by',)
    readonly_fields = ('timestamp',)
