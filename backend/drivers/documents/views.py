from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import DriverDocument
from .serializers import DriverDocumentSerializer, DocumentUploadSerializer
from .services import DocumentService
from django.shortcuts import get_object_or_404
import logging

logger = logging.getLogger(__name__)

class DocumentListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not hasattr(request.user, 'driver_profile'):
            return Response(
                {"detail": "User is not a driver"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        documents = request.user.driver_profile.documents.all()
        serializer = DriverDocumentSerializer(documents, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        if not hasattr(request.user, 'driver_profile'):
            return Response(
                {"detail": "User is not a driver"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = DocumentUploadSerializer(data=request.data)
        if serializer.is_valid():
            try:
                document = DocumentService.upload_document(
                    request.user.driver_profile,
                    serializer.validated_data,
                    request.FILES['file']
                )
                return Response(
                    DriverDocumentSerializer(document).data,
                    status=status.HTTP_201_CREATED
                )
            except Exception as e:
                logger.error(f"Document upload error: {str(e)}")
                return Response(
                    {"detail": "Error uploading document"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DocumentDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get_document(self, pk, driver_profile):
        return get_object_or_404(DriverDocument, pk=pk, driver=driver_profile)
    
    def get(self, request, pk):
        if not hasattr(request.user, 'driver_profile'):
            return Response(
                {"detail": "User is not a driver"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        document = self.get_document(pk, request.user.driver_profile)
        serializer = DriverDocumentSerializer(document)
        return Response(serializer.data)
    
    def delete(self, request, pk):
        if not hasattr(request.user, 'driver_profile'):
            return Response(
                {"detail": "User is not a driver"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        document = self.get_document(pk, request.user.driver_profile)
        document.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)