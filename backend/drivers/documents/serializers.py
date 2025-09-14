from rest_framework import serializers
from .models import DriverDocument

class DriverDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverDocument
        fields = [
            'id', 'document_type', 'document_number', 'file',
            'is_verified', 'verified_by', 'verified_at',
            'expiry_date', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'is_verified', 'verified_by', 'verified_at',
            'created_at', 'updated_at'
        ]

class DocumentUploadSerializer(serializers.Serializer):
    document_type = serializers.CharField(max_length=20)
    file = serializers.FileField()
    document_number = serializers.CharField(max_length=50, required=False)
    expiry_date = serializers.DateField(required=False)