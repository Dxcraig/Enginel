"""
API Views for Enginel - Engineering Intelligence Kernel.

Provides RESTful endpoints for design asset management.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import CustomUser, DesignAsset, AssemblyNode
from .serializers import (
    CustomUserSerializer,
    DesignAssetListSerializer,
    DesignAssetDetailSerializer,
    DesignAssetCreateSerializer,
    AssemblyNodeSerializer,
    BOMTreeSerializer,
    UploadURLResponseSerializer,
    DownloadURLResponseSerializer,
)


class CustomUserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing users.
    
    Provides read-only access to user information.
    """
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user's information."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class DesignAssetViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing design assets (CAD files).
    
    Provides CRUD operations and custom actions for upload/download.
    """
    queryset = DesignAsset.objects.select_related('created_by', 'updated_by').all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return DesignAssetListSerializer
        elif self.action == 'create':
            return DesignAssetCreateSerializer
        return DesignAssetDetailSerializer
    
    def get_queryset(self):
        """Filter designs based on user's clearance level."""
        user = self.request.user
        queryset = super().get_queryset()
        
        # If user is not a US person, exclude ITAR designs
        if not user.is_us_person:
            queryset = queryset.exclude(classification='ITAR')
        
        return queryset
    
    def perform_create(self, serializer):
        """Set the creator when creating a design asset."""
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['post'], url_path='upload-url')
    def request_upload_url(self, request):
        """
        Request a pre-signed S3 upload URL.
        
        POST /api/designs/upload-url/
        Body: {filename, part_number, classification, ...}
        
        Returns: {upload_url, design_asset_id, expires_in_seconds}
        """
        serializer = DesignAssetCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        # Create the design asset record
        design_asset = serializer.save(
            created_by=request.user,
            status='UPLOADING'
        )
        
        # TODO: Generate pre-signed S3 URL
        # For now, return placeholder response
        response_data = {
            'upload_url': 'https://s3.amazonaws.com/placeholder',
            'design_asset_id': design_asset.id,
            'expires_in_seconds': 3600,
            'fields': {
                'key': f'designs/{design_asset.id}/{design_asset.filename}',
                'Content-Type': 'application/octet-stream',
            }
        }
        
        response_serializer = UploadURLResponseSerializer(response_data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def finalize(self, request, pk=None):
        """
        Finalize upload and trigger processing.
        
        POST /api/designs/{id}/finalize/
        
        Queues Celery task for geometry extraction.
        """
        design_asset = self.get_object()
        
        if design_asset.status != 'UPLOADING':
            return Response(
                {'error': 'Design asset is not in UPLOADING state'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update status to processing
        design_asset.status = 'PROCESSING'
        design_asset.save()
        
        # TODO: Queue Celery task for processing
        # process_design_asset.delay(design_asset.id)
        
        serializer = self.get_serializer(design_asset)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """
        Get pre-signed download URL.
        
        GET /api/designs/{id}/download/
        
        Returns short-lived URL (60s) and logs access.
        """
        design_asset = self.get_object()
        
        if design_asset.status != 'COMPLETED':
            return Response(
                {'error': 'Design asset is not ready for download'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # TODO: Generate pre-signed S3 download URL
        # TODO: Log download in AuditEntry
        
        response_data = {
            'download_url': 'https://s3.amazonaws.com/placeholder',
            'expires_in_seconds': 60,
            'filename': design_asset.filename,
        }
        
        response_serializer = DownloadURLResponseSerializer(response_data)
        return Response(response_serializer.data)
    
    @action(detail=True, methods=['get'])
    def bom(self, request, pk=None):
        """
        Get hierarchical Bill of Materials.
        
        GET /api/designs/{id}/bom/
        
        Returns complete BOM tree structure.
        """
        design_asset = self.get_object()
        
        # Get root nodes (nodes without parents)
        root_nodes = AssemblyNode.get_root_nodes().filter(design_asset=design_asset)
        
        # Calculate tree statistics
        all_nodes = AssemblyNode.objects.filter(design_asset=design_asset)
        total_parts = all_nodes.count()
        max_depth = max([node.get_depth() for node in all_nodes], default=0)
        
        response_data = {
            'design_asset_id': design_asset.id,
            'root_nodes': root_nodes,
            'total_parts': total_parts,
            'max_depth': max_depth,
        }
        
        serializer = BOMTreeSerializer(response_data)
        return Response(serializer.data)


class AssemblyNodeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing BOM tree nodes.
    
    Provides CRUD for assembly hierarchy.
    """
    queryset = AssemblyNode.objects.all()
    serializer_class = AssemblyNodeSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter nodes based on user's design access."""
        user = self.request.user
        queryset = super().get_queryset()
        
        # Filter out nodes from ITAR designs if user lacks clearance
        if not user.is_us_person:
            queryset = queryset.exclude(design_asset__classification='ITAR')
        
        return queryset
