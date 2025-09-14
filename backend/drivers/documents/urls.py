from django.urls import path
from .views import (DocumentListView, DocumentDetailView)

urlpatterns = [
    
    # Documents
    path('documents/', DocumentListView.as_view(), name='document-list'),
    path('documents/<int:pk>/', DocumentDetailView.as_view(), name='document-detail'),
    path('documents/<int:pk>/download/', DocumentDetailView.as_view(), name='document-download'),
    path('documents/<int:pk>/upload/', DocumentDetailView.as_view(), name='document-upload'),
    path('documents/<int:pk>/delete/', DocumentDetailView.as_view(), name='document-delete'),
    path('documents/<int:pk>/status/', DocumentDetailView.as_view(), name='document-status'),
    path('documents/<int:pk>/approve/', DocumentDetailView.as_view(), name='document-approve'),
    path('documents/<int:pk>/reject/', DocumentDetailView.as_view(), name='document-reject'),
    path('documents/<int:pk>/resubmit/', DocumentDetailView.as_view(), name='document-resubmit'),
    path('documents/<int:pk>/history/', DocumentDetailView.as_view(), name='document-history'),
    path('documents/<int:pk>/comments/', DocumentDetailView.as_view(), name='document-comments'),
    path('documents/<int:pk>/comment/', DocumentDetailView.as_view(), name='document-comment'),
    path('documents/<int:pk>/comment/<int:comment_id>/', DocumentDetailView.as_view(), name='document-comment-detail'),
    path('documents/<int:pk>/comment/<int:comment_id>/delete/', DocumentDetailView.as_view(), name='document-comment-delete'),
    path('documents/<int:pk>/comment/<int:comment_id>/edit/', DocumentDetailView.as_view(), name='document-comment-edit'),
    path('documents/<int:pk>/comment/<int:comment_id>/reply/', DocumentDetailView.as_view(), name='document-comment-reply'),
    path('documents/<int:pk>/comment/<int:comment_id>/reply/<int:reply_id>/', DocumentDetailView.as_view(), name='document-comment-reply-detail'),
    path('documents/<int:pk>/comment/<int:comment_id>/reply/<int:reply_id>/delete/', DocumentDetailView.as_view(), name='document-comment-reply-delete'),
]