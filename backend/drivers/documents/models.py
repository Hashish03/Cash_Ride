from django.db import models
from drivers.models import DriverProfile
from django.core.validators import FileExtensionValidator

class DriverDocument(models.Model):
    
    DOCUMENT_TYPES = (
        ('license', 'Driver License'),
        ('registration', 'Vehicle Registration'),
        ('insurance', 'Insurance'),
        ('photo', 'Driver Photo'),
        ('background', 'Background Check'),
        ('other', 'Other'),
    )
    
    driver = models.ForeignKey(DriverProfile, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    document_number = models.CharField(max_length=50, blank=True, null=True)
    file = models.FileField(
        upload_to='driver_documents/',
        validators=[
            FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png'])
        ]
    )
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_verified', '-created_at']
    
    def __str__(self):
        return f"{self.get_document_type_display()} - {self.driver.user.email}"