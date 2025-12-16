"""
API Views for Enginel - Engineering Intelligence Kernel.

Provides RESTful endpoints for design asset management.
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Count, Max

from .models import (
    CustomUser, DesignSeries, DesignAsset, AssemblyNode,
    AnalysisJob, ReviewSession, Markup, AuditLog
)
from .serializers import (
    CustomUserSerializer,
    DesignSeriesSerializer,
    DesignAssetListSerializer,
    DesignAssetDetailSerializer,
    DesignAssetCreateSerializer,
    AssemblyNodeSerializer,
    BOMTreeSerializer,
    UploadURLResponseSerializer,
    DownloadURLResponseSerializer,
    AnalysisJobSerializer,
    ReviewSessionSerializer,
    ReviewSessionDetailSerializer,
    MarkupSerializer,
    AuditLogSerializer,
)
from .permissions import (
    DesignAssetPermission,
    ReviewPermission,
    IsOwnerOrReadOnly,
    CanFinalizeUpload,
    IsReviewerOrReadOnly,
    IsUSPersonForITAR,
)
from .tasks import process_design_asset
from .audit import log_audit_event, audit_action, AuditLogMixin


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


class DesignSeriesViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Design Series (Part Numbers).
    
    Each series contains multiple versions of a design.
    """
    queryset = DesignSeries.objects.annotate(
        version_count=Count('versions'),
        latest_version_number=Max('versions__version_number')
    ).select_related('created_by').all()
    serializer_class = DesignSeriesSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['part_number', 'name', 'description']
    ordering_fields = ['part_number', 'created_at']
    ordering = ['-created_at']
    
    def perform_create(self, serializer):
        """Set the creator."""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """Get all versions for this series."""
        series = self.get_object()
        versions = series.versions.all().order_by('-version_number')
        
        # Apply clearance filtering
        if not request.user.is_us_person:
            versions = versions.exclude(classification='ITAR')
        
        serializer = DesignAssetListSerializer(versions, many=True)
        return Response(serializer.data)


class DesignAssetViewSet(AuditLogMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing design assets (specific versions of CAD files).
    
    Provides CRUD operations and custom actions for upload/download.
    Automatically logs CREATE/UPDATE/DELETE operations via AuditLogMixin.
    """
    queryset = DesignAsset.objects.select_related('series', 'uploaded_by').all()
    permission_classes = [IsAuthenticated, DesignAssetPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['filename', 'series__part_number', 'series__name', 'revision']
    ordering_fields = ['created_at', 'version_number']
    ordering = ['-created_at']
    audit_resource_type = 'DesignAsset'
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return DesignAssetListSerializer
        elif self.action in ['create', 'request_upload_url']:
            return DesignAssetCreateSerializer
        return DesignAssetDetailSerializer
    
    def get_queryset(self):
        """Filter designs based on user's clearance level."""
        user = self.request.user
        queryset = super().get_queryset()
        
        # If user is not a US person, exclude ITAR designs
        if not user.is_us_person:
            queryset = queryset.exclude(classification='ITAR')
        
        # Optional: filter by series
        series_id = self.request.query_params.get('series')
        if series_id:
            queryset = queryset.filter(series_id=series_id)
        
        return queryset
    
    def perform_create(self, serializer):
        """
        Create design asset with optional file upload.
        
        If file is provided, trigger immediate processing.
        If no file, create record for two-phase S3 upload.
        AuditLogMixin will automatically log CREATE action.
        """
        instance = serializer.save(uploaded_by=self.request.user)
        return instance
    
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
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, CanFinalizeUpload])
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
        
        # Queue Celery task for processing
        task = process_design_asset.delay(str(design_asset.id))
        
        serializer = self.get_serializer(design_asset)
        response_data = serializer.data
        response_data['task_id'] = task.id
        
        return Response(response_data)
    
    @action(detail=True, methods=['get'])
    @audit_action('DOWNLOAD')
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
        
        # For local development, serve file directly
        if design_asset.file:
            from django.http import FileResponse
            response = FileResponse(design_asset.file.open('rb'), as_attachment=True, filename=design_asset.filename)
            return response
        
        # TODO: For production, generate pre-signed S3 download URL
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
        
        Returns complete BOM tree structure with nested components.
        """
        design_asset = self.get_object()
        
        # Get root nodes (top-level assemblies)
        root_nodes = AssemblyNode.get_root_nodes().filter(design_asset=design_asset)
        
        if not root_nodes.exists():
            return Response({
                'design_asset_id': str(design_asset.id),
                'message': 'No BOM data available. BOM extraction may still be processing.',
                'root_nodes': [],
                'total_parts': 0,
                'max_depth': 0
            })
        
        # Calculate tree statistics
        all_nodes = AssemblyNode.objects.filter(design_asset=design_asset)
        total_parts = all_nodes.filter(node_type='PART').count()
        total_assemblies = all_nodes.filter(node_type='ASSEMBLY').count()
        max_depth = max([node.get_depth() for node in all_nodes], default=0)
        
        # Calculate total mass
        total_mass = sum(node.get_total_mass() for node in root_nodes)
        
        response_data = {
            'design_asset_id': str(design_asset.id),
            'filename': design_asset.filename,
            'root_nodes': root_nodes,
            'total_nodes': all_nodes.count(),
            'total_parts': total_parts,
            'total_assemblies': total_assemblies,
            'max_depth': max_depth,
            'total_mass_kg': round(total_mass, 4),
        }
        
        serializer = BOMTreeSerializer(response_data)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def extract_bom(self, request, pk=None):
        """
        Manually trigger BOM extraction for a design asset.
        
        POST /api/designs/{id}/extract_bom/
        
        Useful for re-extracting BOM or if automatic extraction failed.
        """
        design_asset = self.get_object()
        
        if not design_asset.file:
            return Response(
                {'error': 'No file available for BOM extraction'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Queue BOM extraction task
        from .tasks import extract_bom_from_assembly
        task = extract_bom_from_assembly.delay(str(design_asset.id))
        
        return Response({
            'message': 'BOM extraction started',
            'task_id': task.id,
            'design_asset_id': str(design_asset.id)
        }, status=status.HTTP_202_ACCEPTED)


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


class AnalysisJobViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing analysis jobs.
    
    Read-only access to background task status.
    """
    queryset = AnalysisJob.objects.select_related('design_asset').all()
    serializer_class = AnalysisJobSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter jobs based on design access."""
        user = self.request.user
        queryset = super().get_queryset()
        
        # Filter by design asset ID if provided
        design_asset_id = self.request.query_params.get('design_asset')
        if design_asset_id:
            queryset = queryset.filter(design_asset_id=design_asset_id)
        
        # Filter out ITAR jobs if user lacks clearance
        if not user.is_us_person:
            queryset = queryset.exclude(design_asset__classification='ITAR')
        
        return queryset


class ReviewSessionViewSet(AuditLogMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing design review sessions.
    
    Allows creating review sessions and assigning reviewers.
    Automatically logs CREATE/UPDATE/DELETE operations via AuditLogMixin.
    """
    queryset = ReviewSession.objects.select_related('design_asset', 'created_by').prefetch_related('reviewers', 'markups').annotate(
        markup_count=Count('markups')
    ).all()
    audit_resource_type = 'ReviewSession'
    permission_classes = [IsAuthenticated, ReviewPermission]
    
    def get_serializer_class(self):
        """Return detailed serializer for retrieve action."""
        if self.action == 'retrieve':
            return ReviewSessionDetailSerializer
        return ReviewSessionSerializer
    
    def get_queryset(self):
        """Filter reviews based on design access."""
        user = self.request.user
        queryset = super().get_queryset()
        
        # Filter out ITAR design reviews if user lacks clearance
        if not user.is_us_person:
            queryset = queryset.exclude(design_asset__classification='ITAR')
        
        return queryset
    
    def perform_create(self, serializer):
        """Set the creator."""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start a review session."""
        review = self.get_object()
        
        if review.status != 'DRAFT':
            return Response(
                {'error': 'Review session must be in DRAFT status to start'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from django.utils import timezone
        review.status = 'ACTIVE'
        review.started_at = timezone.now()
        review.save()
        
        serializer = self.get_serializer(review)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete a review session."""
        review = self.get_object()
        
        if review.status != 'ACTIVE':
            return Response(
                {'error': 'Review session must be ACTIVE to complete'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from django.utils import timezone
        review.status = 'COMPLETED'
        review.completed_at = timezone.now()
        review.save()
        
        serializer = self.get_serializer(review)
        return Response(serializer.data)


class MarkupViewSet(AuditLogMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing 3D markups/annotations.
    
    Allows creating comments anchored to 3D coordinates.
    Automatically logs CREATE/UPDATE/DELETE operations via AuditLogMixin.
    """
    queryset = Markup.objects.select_related('review_session', 'author').all()
    serializer_class = MarkupSerializer
    permission_classes = [IsAuthenticated, IsReviewerOrReadOnly]
    audit_resource_type = 'Markup'
    
    def get_queryset(self):
        """Filter markups based on review session access."""
        user = self.request.user
        queryset = super().get_queryset()
        
        # Filter by review session if provided
        review_session_id = self.request.query_params.get('review_session')
        if review_session_id:
            queryset = queryset.filter(review_session_id=review_session_id)
        
        # Filter out ITAR markups if user lacks clearance
        if not user.is_us_person:
            queryset = queryset.exclude(
                review_session__design_asset__classification='ITAR'
            )
        
        return queryset
    
    def perform_create(self, serializer):
        """Set the author."""
        serializer.save(author=self.request.user)
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Mark a markup as resolved."""
        markup = self.get_object()
        markup.is_resolved = True
        markup.save()
        
        serializer = self.get_serializer(markup)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def unresolve(self, request, pk=None):
        """Mark a markup as unresolved."""
        markup = self.get_object()
        markup.is_resolved = False
        markup.save()
        
        serializer = self.get_serializer(markup)
        return Response(serializer.data)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing audit log entries.
    
    Read-only access to immutable audit trail for compliance.
    Supports filtering by actor, resource, action, and date range.
    """
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['timestamp', 'action', 'actor_username']
    ordering = ['-timestamp']
    
    def get_queryset(self):
        """Filter audit logs based on query parameters."""
        queryset = super().get_queryset()
        
        # Filter by actor ID
        actor_id = self.request.query_params.get('actor_id')
        if actor_id:
            queryset = queryset.filter(actor_id=actor_id)
        
        # Filter by resource type
        resource_type = self.request.query_params.get('resource_type')
        if resource_type:
            queryset = queryset.filter(resource_type=resource_type)
        
        # Filter by resource ID
        resource_id = self.request.query_params.get('resource_id')
        if resource_id:
            queryset = queryset.filter(resource_id=resource_id)
        
        # Filter by action
        action = self.request.query_params.get('action')
        if action:
            queryset = queryset.filter(action=action)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def my_actions(self, request):
        """Get audit logs for current user."""
        queryset = self.get_queryset().filter(actor_id=request.user.id)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def downloads(self, request):
        """Get all download audit logs."""
        queryset = self.get_queryset().filter(action='DOWNLOAD')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

