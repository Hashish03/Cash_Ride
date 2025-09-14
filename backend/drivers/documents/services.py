import logging
from django.utils import timezone
from .models import DriverDocument
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

class DocumentService:
    @staticmethod
    def upload_document(driver_profile, document_data, file):
        """
        Uploads and validates a driver document
        """
        try:
            document = DriverDocument.objects.create(
                driver=driver_profile,
                document_type=document_data['document_type'],
                file=file,
                document_number=document_data.get('document_number'),
                expiry_date=document_data.get('expiry_date')
            )
            return document
        except Exception as e:
            logger.error(f"Document upload error: {str(e)}")
            raise ValidationError("Error uploading document")

    @staticmethod
    def verify_document(document_id, verified_by):
        """
        Marks a document as verified by admin
        """
        try:
            document = DriverDocument.objects.get(pk=document_id)
            document.is_verified = True
            document.verified_by = verified_by
            document.verified_at = timezone.now()
            document.save()
            return document
        except DriverDocument.DoesNotExist:
            logger.error(f"Document not found: {document_id}")
            raise ValidationError("Document not found")