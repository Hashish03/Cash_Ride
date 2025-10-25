from django.contrib import admin
from django.contrib.admin import ModelAdmin
from .models import (DriverProfile, Vehicle)
from documents.models import DriverDocument
from earnings.models import DriverEarning
from rating.models import DriverAvailability, DriverRating

@admin.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'rating', 'total_rides', 'total_earnings')
    list_filter = ('status', 'background_check_passed')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('make', 'model', 'year', 'license_plate', 'driver', 'is_active')
    list_filter = ('vehicle_type', 'is_active', 'registration_valid', 'insurance_valid')
    search_fields = ('make', 'model', 'license_plate', 'driver__user__email')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(DriverDocument)
class DriverDocumentAdmin(admin.ModelAdmin):
    list_display = ('driver', 'document_type', 'is_verified', 'expiry_date')
    list_filter = ('document_type', 'is_verified')
    search_fields = ('driver__user__email', 'document_number')
    readonly_fields = ('created_at', 'updated_at', 'verified_at')

@admin.register(DriverEarning)
class DriverEarningAdmin(admin.ModelAdmin):
    list_display = ('driver', 'ride', 'net_earnings', 'payment_status', 'created_at')
    list_filter = ('payment_status',)
    search_fields = ('driver__user__email', 'transaction_reference')
    readonly_fields = ('created_at',)

@admin.register(DriverAvailability)
class DriverAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('driver', 'is_available', 'last_online')
    list_filter = ('is_available',)
    search_fields = ('driver__user__email',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(DriverRating)
class DriverRatingAdmin(admin.ModelAdmin):
    list_display = ('driver', 'ride', 'rating', 'created_at')
    list_filter = ('rating',)
    search_fields = ('driver__user__email', 'feedback')
    readonly_fields = ('created_at',)