"""
API Views for Enginel - Engineering Intelligence Kernel.

Provides RESTful endpoints for design asset management.
"""
import logging

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Count, Max, Q
from django_filters.rest_framework import DjangoFilterBackend

logger = logging.getLogger(__name__)

from .mixins import CachedViewSetMixin, LongtermCachedMixin, ShortCachedMixin

from .models import (
    CustomUser, DesignSeries, DesignAsset, AssemblyNode,
    AnalysisJob, ReviewSession, Markup, AuditLog, Notification
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
    NotificationSerializer,
)
from .permissions import (
    DesignAssetPermission,
    ReviewPermission,
    IsOwnerOrReadOnly,
    CanFinalizeUpload,
    IsReviewerOrReadOnly,
    IsUSPersonForITAR,
)
from .filters import (
    CustomUserFilter,
    DesignSeriesFilter,
    DesignAssetFilter,
    AssemblyNodeFilter,
    AnalysisJobFilter,
    ReviewSessionFilter,
    MarkupFilter,
    AuditLogFilter,
)
from .tasks import process_design_asset
from .audit import log_audit_event, audit_action, AuditLogMixin
from .monitoring import HealthChecker, ErrorTracker, PerformanceMonitor, MetricsCollector
from .exceptions import (
    OrganizationLimitExceeded,
    InsufficientPermissions,
    raise_permission_error
)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny


class CustomUserViewSet(CachedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """
    Read-only ViewSet for user information.
    
    Allows users to view their own details and other users in their org.
    Cached for 5 minutes (list/retrieve).
    
    Filtering:
    - ?username=john - Filter by username (case-insensitive)
    - ?security_clearance_level=SECRET - Filter by clearance
    - ?min_clearance=CONFIDENTIAL - Users with at least this clearance
    - ?is_us_person=true - ITAR-compliant users only
    - ?member_of_organization=<uuid> - Filter by organization
    - ?is_active=true - Active users only
    
    Search: ?search=john (searches username, email, first_name, last_name)
    Ordering: ?ordering=username
    """
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = CustomUserFilter
    search_fields = ['username', 'email', 'first_name', 'last_name', 'organization']
    ordering_fields = ['username', 'date_joined', 'last_login']
    ordering = ['username']
    
    @action(detail=False, methods=['get', 'patch', 'put'])
    def me(self, request):
        """Get or update current user's information."""
        if request.method == 'GET':
            serializer = self.get_serializer(request.user)
            return Response(serializer.data)
        
        # Handle PATCH/PUT
        partial = request.method == 'PATCH'
        serializer = self.get_serializer(
            request.user,
            data=request.data,
            partial=partial
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class DesignSeriesViewSet(CachedViewSetMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing design series (part numbers).
    
    A design series is a container for multiple versions of the same part.
    Cached for 5 minutes (list/retrieve).
    
    Filtering:
    - ?part_number=PN-001 - Filter by part number (case-insensitive)
    - ?name=bracket - Filter by name
    - ?status=RELEASED - Filter by status (DRAFT, IN_REVIEW, RELEASED, OBSOLETE)
    - ?classification_level=SECRET - Filter by classification
    - ?requires_itar_compliance=true - ITAR-controlled parts
    - ?has_versions=true - Parts with uploaded versions
    - ?min_versions=3 - Parts with at least 3 versions
    - ?created_by_username=john - Filter by creator
    - ?created_after=2025-01-01 - Created after date
    
    Search: ?search=bracket (searches part_number, name, description)
    Ordering: ?ordering=-created_at (prefix with - for descending)
    """
    queryset = DesignSeries.objects.annotate(
        version_count=Count('versions'),
        latest_version_number=Max('versions__version_number')
    ).select_related('created_by').all()
    serializer_class = DesignSeriesSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = DesignSeriesFilter
    search_fields = ['part_number', 'name', 'description']
    ordering_fields = ['part_number', 'created_at', 'updated_at', 'status']
    ordering = ['-created_at']
    
    def create(self, request, *args, **kwargs):
        """Create a new design series with detailed error logging."""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"Series creation request - Data: {request.data}")
        logger.info(f"Series creation request - User: {request.user}")
        
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except Exception as e:
            logger.error(f"Series creation error: {str(e)}")
            logger.error(f"Validation errors: {getattr(serializer, 'errors', 'No serializer errors')}")
            raise
    
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


class DesignAssetViewSet(CachedViewSetMixin, AuditLogMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing design assets (specific versions of CAD files).
    
    Provides CRUD operations and custom actions for upload/download.
    Automatically logs CREATE/UPDATE/DELETE operations via AuditLogMixin.
    Cached for 5 minutes (list/retrieve).
    
    Filtering:
    - ?filename=bracket.step - Filter by filename (case-insensitive)
    - ?file_format=step - Filter by format (step, iges, stl, obj)
    - ?file_formats=step,iges - Multiple formats
    - ?upload_status=COMPLETED - Filter by status
    - ?min_file_size_mb=10 - Files >= 10MB
    - ?max_file_size_mb=100 - Files <= 100MB
    - ?has_geometry=true - Files with extracted geometry
    - ?has_bom=true - Assemblies with BOM data
    - ?is_assembly=true - Assembly files only
    - ?min_volume=1000 - Minimum volume (mm³)
    - ?min_mass=0.5 - Minimum mass (kg)
    - ?part_number=PN-001 - Filter by parent part number
    - ?uploaded_by_username=john - Filter by uploader
    - ?uploaded_after=2025-01-01 - Uploaded after date
    
    Search: ?search=bracket (searches filename, part_number, series name, revision)
    Ordering: ?ordering=-created_at,-file_size
    """
    queryset = DesignAsset.objects.select_related('series', 'uploaded_by').all()
    permission_classes = [IsAuthenticated, DesignAssetPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = DesignAssetFilter
    search_fields = ['filename', 'series__part_number', 'series__name', 'revision']
    ordering_fields = ['created_at', 'version_number', 'file_size', 'volume_mm3', 'mass_kg']
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
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"DesignAsset creation - User: {self.request.user}")
        logger.info(f"DesignAsset creation - Data: {self.request.data}")
        logger.info(f"DesignAsset creation - Files: {self.request.FILES}")
        
        try:
            instance = serializer.save(uploaded_by=self.request.user)
            logger.info(f"DesignAsset created successfully - ID: {instance.id}")
            return instance
        except Exception as e:
            logger.error(f"DesignAsset creation failed: {str(e)}")
            raise
    
    @action(detail=False, methods=['post'], url_path='upload-url')
    def request_upload_url(self, request):
        """
        Request a pre-signed S3 upload URL.
        
        POST /api/designs/upload-url/
        Body: {filename, part_number, classification, ...}
        
        Returns: {upload_url, design_asset_id, expires_in_seconds}
        """
        from django.conf import settings
        from designs.s3_service import get_s3_service, S3ServiceError
        
        serializer = DesignAssetCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        # Create the design asset record
        design_asset = serializer.save(
            uploaded_by=request.user,
            status='UPLOADING'
        )
        
        # Generate pre-signed S3 URL if S3 is enabled
        if settings.USE_S3:
            try:
                s3_service = get_s3_service()
                
                # Generate S3 key
                s3_key = s3_service.generate_file_key(
                    organization_id=None,
                    design_asset_id=design_asset.id,
                    filename=design_asset.filename
                )
                
                # Save S3 key to design asset
                design_asset.s3_key = s3_key
                design_asset.save(update_fields=['s3_key'])
                
                # Generate pre-signed POST for browser upload
                presigned_data = s3_service.generate_upload_presigned_post(
                    file_key=s3_key,
                    content_type=request.data.get('content_type', 'application/octet-stream'),
                    metadata={
                        'design_asset_id': str(design_asset.id),
                        'uploaded_by': request.user.username,
                    }
                )
                
                response_data = {
                    'upload_url': presigned_data['url'],
                    'design_asset_id': design_asset.id,
                    'expires_in_seconds': presigned_data['expires_in'],
                    'fields': presigned_data['fields'],
                    's3_key': s3_key,
                }
                
            except S3ServiceError as e:
                # Rollback design asset creation on S3 error
                design_asset.delete()
                return Response(
                    {'error': f'Failed to generate upload URL: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            # Local development - return placeholder
            response_data = {
                'upload_url': f'/api/designs/{design_asset.id}/upload/',
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
        
        # Link the uploaded S3 file to the FileField
        if settings.USE_S3 and design_asset.s3_key:
            # Set the file field to point to the S3 key
            # Django's FileField will use the storage backend from get_file_storage()
            design_asset.file.name = design_asset.s3_key
            design_asset.save(update_fields=['file'])
            logger.info(f"Linked file to S3: {design_asset.s3_key}, storage: {design_asset.file.storage.__class__.__name__}")
        
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
        from django.conf import settings
        from designs.s3_service import get_s3_service, S3ServiceError
        
        design_asset = self.get_object()
        
        if design_asset.status != 'COMPLETED':
            return Response(
                {'error': 'Design asset is not ready for download'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # For S3-enabled environments, generate pre-signed download URL
        if settings.USE_S3 and design_asset.s3_key:
            try:
                s3_service = get_s3_service()
                
                # Check if file exists in S3
                if not s3_service.check_file_exists(design_asset.s3_key):
                    return Response(
                        {'error': 'File not found in storage'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                # Generate pre-signed download URL
                download_url = s3_service.generate_download_presigned_url(
                    file_key=design_asset.s3_key,
                    response_headers={
                        'ResponseContentDisposition': f'attachment; filename="{design_asset.filename}"',
                        'ResponseContentType': 'application/octet-stream',
                    }
                )
                
                response_data = {
                    'download_url': download_url,
                    'expires_in_seconds': settings.AWS_DOWNLOAD_PRESIGNED_URL_EXPIRY,
                    'filename': design_asset.filename,
                }
                
                response_serializer = DownloadURLResponseSerializer(response_data)
                return Response(response_serializer.data)
                
            except S3ServiceError as e:
                return Response(
                    {'error': f'Failed to generate download URL: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        # For local development, serve file directly
        elif design_asset.file:
            from django.http import FileResponse
            response = FileResponse(
                design_asset.file.open('rb'),
                as_attachment=True,
                filename=design_asset.filename
            )
            return response
        
        else:
            return Response(
                {'error': 'No file available for download'},
                status=status.HTTP_404_NOT_FOUND
            )
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
        
        if design_asset.status != 'COMPLETED':
            return Response(
                {'error': 'Design asset must be in COMPLETED state for BOM extraction'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Queue BOM extraction task
        from .tasks import extract_bom_from_assembly
        task = extract_bom_from_assembly.delay(str(design_asset.id))
        
        return Response({
            'message': f'BOM extraction queued for {design_asset.filename}',
            'design_asset_id': str(design_asset.id),
            'task_id': task.id,
        }, status=status.HTTP_202_ACCEPTED)
    
    @action(detail=True, methods=['post'])
    def normalize_units(self, request, pk=None):
        """
        Manually trigger unit normalization for a design asset.
        
        POST /api/designs/{id}/normalize_units/
        Body: {unit: 'in'} (optional, otherwise auto-detected)
        
        Normalizes all measurements to millimeters (BASE_UNIT).
        """
        design_asset = self.get_object()
        
        if design_asset.status != 'COMPLETED':
            return Response(
                {'error': 'Design asset must be in COMPLETED state for unit normalization'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get optional unit override from request
        unit_override = request.data.get('unit')
        
        # Queue unit normalization task
        from .tasks import normalize_units
        task = normalize_units.delay(str(design_asset.id), unit_override=unit_override)
        
        return Response({
            'message': f'Unit normalization queued for {design_asset.filename}',
            'design_asset_id': str(design_asset.id),
            'task_id': task.id,
            'unit_override': unit_override,
        }, status=status.HTTP_202_ACCEPTED)
    
    @action(detail=False, methods=['get'], url_path='convert-units')
    def convert_units(self, request):
        """
        Convert a value between different units.
        
        GET /api/designs/convert-units/?value=10&from=in&to=mm&type=length
        
        Returns converted value with metadata.
        """
        from .unit_converter import convert_length, convert_area, convert_volume, validate_unit
        
        try:
            value = float(request.query_params.get('value', 0))
            from_unit = request.query_params.get('from', 'mm')
            to_unit = request.query_params.get('to', 'mm')
            conversion_type = request.query_params.get('type', 'length')
            
            # Validate units
            if not validate_unit(from_unit):
                return Response({'error': f'Invalid unit: {from_unit}'}, status=status.HTTP_400_BAD_REQUEST)
            if not validate_unit(to_unit):
                return Response({'error': f'Invalid unit: {to_unit}'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Perform conversion
            if conversion_type == 'length':
                converted_value = convert_length(value, from_unit, to_unit)
            elif conversion_type == 'area':
                converted_value = convert_area(value, from_unit, to_unit)
            elif conversion_type == 'volume':
                converted_value = convert_volume(value, from_unit, to_unit)
            else:
                return Response({'error': f'Invalid type: {conversion_type}'}, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'original_value': value,
                'original_unit': from_unit,
                'converted_value': round(converted_value, 6),
                'converted_unit': to_unit,
                'conversion_type': conversion_type,
            })
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
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
    ViewSet for managing Bill of Materials (BOM) tree nodes.
    
    Each assembly can have a hierarchical BOM structure.
    
    Filtering:
    - ?part_name=bracket - Filter by part name (case-insensitive)
    - ?part_number=PN-001 - Filter by part number
    - ?node_type=COMPONENT - Filter by type (COMPONENT, ASSEMBLY, REFERENCE, VIRTUAL)
    - ?material=aluminum - Filter by material
    - ?has_children=true - Nodes with child parts
    - ?is_root=true - Root-level nodes only
    - ?depth_level=2 - Specific depth in hierarchy
    - ?min_depth=2 - Minimum depth level
    - ?quantity=4 - Exact quantity
    - ?min_quantity=10 - Minimum quantity
    - ?design_asset=<uuid> - Filter by parent design
    
    Search: ?search=bracket (searches part_name, part_number, material, description)
    Ordering: ?ordering=depth,part_number
    """
    queryset = AssemblyNode.objects.all()
    serializer_class = AssemblyNodeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = AssemblyNodeFilter
    search_fields = ['part_name', 'part_number', 'material', 'description']
    ordering_fields = ['depth', 'part_number', 'quantity']
    ordering = ['depth', 'part_number']
    
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
    ViewSet for monitoring Celery background tasks.
    
    Provides real-time status of geometry processing jobs.
    Includes task monitoring, metrics, and progress tracking.
    
    Filtering:
    - ?task_name=process_design_asset - Filter by task type
    - ?status=COMPLETED - Filter by status (PENDING, RUNNING, COMPLETED, FAILED)
    - ?design_asset=<uuid> - Filter by design
    - ?initiated_by=<user_id> - Filter by user
    - ?started_after=2025-01-01 - Started after date
    - ?completed_after=2025-01-01 - Completed after date
    - ?min_duration=30 - Tasks taking >= 30 seconds
    - ?max_duration=300 - Tasks taking <= 5 minutes
    
    Search: ?search=process (searches task_name, celery_task_id)
    Ordering: ?ordering=-created_at
    
    Custom Actions:
    - GET /api/analysis-jobs/{id}/status/ - Get detailed task status
    - GET /api/analysis-jobs/{id}/progress/ - Get task progress
    - POST /api/analysis-jobs/{id}/cancel/ - Cancel running task
    - GET /api/analysis-jobs/active/ - List all active tasks
    - GET /api/analysis-jobs/metrics/ - Get task metrics
    - GET /api/analysis-jobs/failures/ - Get failure analysis
    """
    queryset = AnalysisJob.objects.select_related('design_asset').all()
    serializer_class = AnalysisJobSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = AnalysisJobFilter
    search_fields = ['task_name', 'celery_task_id']
    ordering_fields = ['created_at', 'completed_at', 'status']
    ordering = ['-created_at']
    
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
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """
        Get detailed task status including Celery state.
        
        GET /api/analysis-jobs/{id}/status/
        
        Returns comprehensive task information including:
        - Current state (PENDING, RUNNING, SUCCESS, FAILURE)
        - Result data or error message
        - Duration and timestamps
        - Progress information if available
        """
        from designs.task_monitor import task_monitor
        
        job = self.get_object()
        
        if not job.celery_task_id:
            return Response({
                'error': 'No Celery task ID associated with this job'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        task_info = task_monitor.get_task_info(job.celery_task_id)
        
        return Response(task_info)
    
    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        """
        Get task progress for long-running operations.
        
        GET /api/analysis-jobs/{id}/progress/
        
        Returns:
        - current: Current progress value
        - total: Total progress value
        - percent: Percentage complete
        - status: Status message
        - updated_at: Last update timestamp
        """
        from designs.task_monitor import TaskProgressTracker
        
        job = self.get_object()
        
        if not job.celery_task_id:
            return Response({
                'error': 'No Celery task ID associated with this job'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        progress = TaskProgressTracker.get_progress(job.celery_task_id)
        
        if not progress:
            return Response({
                'message': 'No progress information available',
                'percent': 0
            })
        
        return Response(progress)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancel a running task.
        
        POST /api/analysis-jobs/{id}/cancel/
        Body: {"terminate": false}  # Optional: force terminate
        
        Revokes the task and updates job status.
        """
        from designs.task_monitor import task_monitor
        
        job = self.get_object()
        
        if job.status in ['SUCCESS', 'FAILURE', 'CANCELLED']:
            return Response({
                'error': f'Cannot cancel task in {job.status} state'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not job.celery_task_id:
            return Response({
                'error': 'No Celery task ID associated with this job'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        terminate = request.data.get('terminate', False)
        success = task_monitor.cancel_task(job.celery_task_id, terminate=terminate)
        
        if success:
            return Response({
                'message': 'Task cancelled successfully',
                'task_id': job.celery_task_id,
                'terminated': terminate
            })
        else:
            return Response({
                'error': 'Failed to cancel task'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """
        Get all currently active (running) tasks.
        
        GET /api/analysis-jobs/active/
        
        Returns list of tasks being processed right now.
        """
        from designs.task_monitor import task_monitor
        
        active_tasks = task_monitor.get_active_tasks()
        
        return Response({
            'count': len(active_tasks),
            'tasks': active_tasks
        })
    
    @action(detail=False, methods=['get'])
    def metrics(self, request):
        """
        Get aggregated task metrics.
        
        GET /api/analysis-jobs/metrics/
        Query params:
        - ?job_type=GEOMETRY_EXTRACTION - Specific job type
        
        Returns metrics like success rate, avg duration, etc.
        """
        from designs.task_monitor import task_metrics
        
        job_type = request.query_params.get('job_type')
        
        metrics = task_metrics.get_task_metrics(job_type)
        
        return Response(metrics)
    
    @action(detail=False, methods=['get'])
    def failures(self, request):
        """
        Get failure analysis for debugging.
        
        GET /api/analysis-jobs/failures/
        Query params:
        - ?days=7 - Number of days to analyze (default 7)
        
        Returns failure statistics and common error messages.
        """
        from designs.task_monitor import task_metrics
        
        days = int(request.query_params.get('days', 7))
        
        analysis = task_metrics.get_failure_analysis(days)
        
        return Response(analysis)


class ReviewSessionViewSet(AuditLogMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing collaborative design reviews.
    
    Reviewers can be added/removed and markups can be attached.
    Automatically logs CREATE/UPDATE/DELETE operations via AuditLogMixin.
    
    Filtering:
    - ?title=design review - Filter by title (case-insensitive)
    - ?status=OPEN - Filter by status (OPEN, IN_PROGRESS, COMPLETED, CANCELLED)
    - ?design_asset=<uuid> - Filter by reviewed design
    - ?created_by=<user_id> - Filter by creator
    - ?has_reviewer=<user_id> - Filter by specific reviewer
    - ?created_after=2025-01-01 - Created after date
    - ?completed_after=2025-01-01 - Completed after date
    
    Search: ?search=design (searches title, description)
    Ordering: ?ordering=-created_at,status
    """
    queryset = ReviewSession.objects.select_related('design_asset', 'created_by').prefetch_related('reviewers', 'markups').annotate(
        markup_count=Count('markups')
    ).all()
    permission_classes = [IsAuthenticated, ReviewPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ReviewSessionFilter
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'completed_at', 'status']
    ordering = ['-created_at']
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
    ViewSet for managing 3D annotations/comments on designs.
    
    Each markup is associated with a review session and can be resolved.
    Automatically logs CREATE/UPDATE/DELETE operations via AuditLogMixin.
    
    Filtering:
    - ?title=issue - Filter by title (case-insensitive)
    - ?comment=dimension - Filter by comment text
    - ?is_resolved=false - Filter unresolved markups
    - ?priority=HIGH - Filter by priority (LOW, MEDIUM, HIGH, CRITICAL)
    - ?review_session=<uuid> - Filter by review session
    - ?author=<user_id> - Filter by markup author
    - ?author_username=john - Filter by author username
    - ?created_after=2025-01-01 - Created after date
    - ?resolved_after=2025-01-01 - Resolved after date
    
    Search: ?search=dimension (searches title, comment)
    Ordering: ?ordering=-created_at,priority
    """
    queryset = Markup.objects.select_related('review_session', 'author').all()
    serializer_class = MarkupSerializer
    permission_classes = [IsAuthenticated, IsReviewerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = MarkupFilter
    search_fields = ['title', 'comment']
    ordering_fields = ['created_at', 'resolved_at', 'priority', 'is_resolved']
    ordering = ['-created_at']
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


class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for in-app notifications.
    
    Users can only access their own notifications.
    Supports filtering by read status, type, and priority.
    
    Filtering:
    - ?is_read=false - Show only unread notifications
    - ?is_read=true - Show only read notifications
    - ?is_archived=false - Show only non-archived notifications
    - ?notification_type=REVIEW_ASSIGNED - Filter by notification type
    - ?priority=HIGH - Filter by priority level
    - ?resource_type=DesignAsset - Filter by related resource type
    - ?resource_id=<uuid> - Filter by specific resource
    
    Search: ?search=design (searches title, message)
    Ordering: ?ordering=-created_at (default descending by creation time)
    
    Actions:
    - GET /notifications/ - List user's notifications
    - GET /notifications/<id>/ - Get specific notification
    - PATCH /notifications/<id>/ - Update notification (mark as read, etc.)
    - DELETE /notifications/<id>/ - Delete notification
    - POST /notifications/<id>/mark_as_read/ - Mark single notification as read
    - POST /notifications/mark_all_as_read/ - Mark all notifications as read
    - POST /notifications/<id>/archive/ - Archive notification
    - GET /notifications/unread_count/ - Get unread notification count
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'message']
    ordering_fields = ['created_at', 'priority', 'is_read']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Return only notifications for current user."""
        user = self.request.user
        queryset = Notification.objects.filter(recipient=user)
        
        # Filter by read status
        is_read = self.request.query_params.get('is_read')
        if is_read is not None:
            is_read_bool = is_read.lower() == 'true'
            queryset = queryset.filter(is_read=is_read_bool)
        
        # Filter by archived status
        is_archived = self.request.query_params.get('is_archived')
        if is_archived is not None:
            is_archived_bool = is_archived.lower() == 'true'
            queryset = queryset.filter(is_archived=is_archived_bool)
        else:
            # By default, exclude archived notifications
            queryset = queryset.filter(is_archived=False)
        
        # Filter by notification type
        notification_type = self.request.query_params.get('notification_type')
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        
        # Filter by priority
        priority = self.request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
        
        # Filter by resource
        resource_type = self.request.query_params.get('resource_type')
        if resource_type:
            queryset = queryset.filter(resource_type=resource_type)
        
        resource_id = self.request.query_params.get('resource_id')
        if resource_id:
            queryset = queryset.filter(resource_id=resource_id)
        
        return queryset
    
    def get_serializer_class(self):
        """Use lightweight serializer for list view."""
        if self.action == 'list':
            from .serializers import NotificationListSerializer
            return NotificationListSerializer
        return NotificationSerializer
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark notification as read."""
        notification = self.get_object()
        notification.mark_as_read()
        return Response({'status': 'notification marked as read'})
    
    @action(detail=True, methods=['post'])
    def mark_as_unread(self, request, pk=None):
        """Mark notification as unread."""
        notification = self.get_object()
        notification.mark_as_unread()
        return Response({'status': 'notification marked as unread'})
    
    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """Mark all notifications as read for current user."""
        count = Notification.mark_all_as_read(request.user)
        return Response({
            'status': 'all notifications marked as read',
            'count': count
        })
    
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive notification."""
        notification = self.get_object()
        notification.archive()
        return Response({'status': 'notification archived'})
    
    @action(detail=True, methods=['post'])
    def unarchive(self, request, pk=None):
        """Unarchive notification."""
        notification = self.get_object()
        notification.unarchive()
        return Response({'status': 'notification unarchived'})
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications."""
        try:
            if not request.user or not request.user.is_authenticated:
                return Response({'count': 0}, status=200)
            
            count = Notification.get_unread_count(request.user)
            return Response({'count': count})
        except Exception as e:
            # Log the error but return a graceful response
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error fetching unread count: {str(e)}")
            return Response({'count': 0, 'error': str(e)}, status=200)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing audit trail (compliance logs).
    
    Read-only access to all system actions for CMMC compliance.
    Admins can view all logs; users see logs for their organization.
    
    Filtering:
    - ?action=CREATE - Filter by action (CREATE, UPDATE, DELETE, VIEW, DOWNLOAD, etc.)
    - ?actions=CREATE,UPDATE - Multiple actions
    - ?resource_type=DesignAsset - Filter by resource type
    - ?resource_id=<uuid> - Filter by specific resource
    - ?actor_username=john - Filter by user who performed action
    - ?ip_address=192.168.1.100 - Filter by IP address
    - ?ip_range=192.168.1.0/24 - Filter by IP range (CIDR)
    - ?organization=<uuid> - Filter by organization
    - ?success=true - Filter successful actions
    - ?timestamp_after=2025-01-01 - Actions after date
    - ?last_hour=true - Last hour of activity
    - ?last_day=true - Last 24 hours
    - ?last_week=true - Last 7 days
    
    Search: ?search=john (searches action, resource_type, actor_username)
    Ordering: ?ordering=-timestamp (default descending by time)
    """
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = AuditLogFilter
    search_fields = ['action', 'resource_type', 'actor_username', 'ip_address']
    ordering_fields = ['timestamp', 'action', 'resource_type']
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


# Health Check and Monitoring Endpoints

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Basic health check endpoint for load balancers.
    
    GET /api/health/
    
    Returns 200 if service is up.
    """
    return Response({'status': 'ok', 'service': 'enginel'})


@api_view(['GET'])
@permission_classes([AllowAny])
def health_detailed(request):
    """
    Detailed health check with component status.
    
    GET /api/health/detailed/
    
    Returns health status of all system components.
    """
    health_status = HealthChecker.get_full_health_status()
    
    # Return 503 if any component is unhealthy
    if health_status['status'] != 'healthy':
        return Response(health_status, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    return Response(health_status)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def monitoring_dashboard(request):
    """
    Monitoring dashboard with error stats and performance metrics.
    
    GET /api/monitoring/dashboard/
    
    Requires authentication. Admin-only in production.
    """
    # Check if user is admin
    if not request.user.is_staff:
        return Response(
            {'error': 'Admin access required'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get recent errors
    recent_errors = ErrorTracker.get_recent_errors(limit=20)
    
    # Get performance stats for key operations
    perf_stats = {
        'geometry_extraction': PerformanceMonitor.get_operation_stats('geometry_extraction'),
        'bom_extraction': PerformanceMonitor.get_operation_stats('bom_extraction'),
        'unit_normalization': PerformanceMonitor.get_operation_stats('unit_normalization'),
    }
    
    # Get metrics
    metrics = MetricsCollector.get_metrics()
    
    # Get health status
    health = HealthChecker.get_full_health_status()
    
    return Response({
        'health': health,
        'recent_errors': recent_errors,
        'performance': perf_stats,
        'metrics': metrics,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def error_logs(request):
    """
    Get recent error logs.
    
    GET /api/monitoring/errors/?limit=50
    
    Requires authentication. Admin-only in production.
    """
    if not request.user.is_staff:
        return Response(
            {'error': 'Admin access required'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    limit = int(request.GET.get('limit', 50))
    errors = ErrorTracker.get_recent_errors(limit=limit)
    
    return Response({
        'count': len(errors),
        'errors': errors
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def performance_stats(request):
    """
    Get performance statistics for all tracked operations.
    
    GET /api/monitoring/performance/
    
    Requires authentication. Admin-only in production.
    """
    if not request.user.is_staff:
        return Response(
            {'error': 'Admin access required'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    stats = PerformanceMonitor.get_all_stats()
    
    return Response(stats)


# Notification Management Views

@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def notification_preferences(request):
    """
    Get or update current user's notification preferences.
    
    GET /api/notifications/preferences/
    - Returns user's notification preferences
    
    PATCH /api/notifications/preferences/
    - Updates notification preferences
    
    Request body (PATCH):
    {
        "email_enabled": true,
        "notify_design_uploaded": true,
        "delivery_method": "IMMEDIATE",
        "quiet_hours_enabled": false
    }
    """
    from .models import NotificationPreference
    from .serializers import NotificationPreferenceSerializer
    from .notifications import NotificationService
    
    # Get or create preferences
    prefs = NotificationService.get_or_create_preferences(request.user)
    
    if request.method == 'GET':
        serializer = NotificationPreferenceSerializer(prefs)
        return Response(serializer.data)
    
    elif request.method == 'PATCH':
        serializer = NotificationPreferenceSerializer(
            prefs,
            data=request.data,
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_history(request):
    """
    Get current user's notification history.
    
    GET /api/notifications/history/
    
    Query parameters:
    - status: Filter by status (PENDING, SENT, FAILED)
    - type: Filter by notification type
    - page: Page number (default: 1)
    - page_size: Items per page (default: 50)
    """
    from .models import EmailNotification
    from .serializers import EmailNotificationSerializer
    from rest_framework.pagination import PageNumberPagination
    
    # Build queryset
    notifications = EmailNotification.objects.filter(
        recipient=request.user
    ).order_by('-queued_at')
    
    # Apply filters
    status_filter = request.GET.get('status')
    if status_filter:
        notifications = notifications.filter(status=status_filter)
    
    type_filter = request.GET.get('type')
    if type_filter:
        notifications = notifications.filter(notification_type=type_filter)
    
    # Paginate
    paginator = PageNumberPagination()
    paginator.page_size = int(request.GET.get('page_size', 50))
    page = paginator.paginate_queryset(notifications, request)
    
    serializer = EmailNotificationSerializer(page, many=True)
    
    return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_stats(request):
    """
    Get notification statistics for current user.
    
    GET /api/notifications/stats/
    
    Returns counts by status and type.
    """
    from .models import EmailNotification
    from django.db.models import Count
    
    # Count by status
    status_counts = EmailNotification.objects.filter(
        recipient=request.user
    ).values('status').annotate(count=Count('id'))
    
    # Count by type
    type_counts = EmailNotification.objects.filter(
        recipient=request.user
    ).values('notification_type').annotate(count=Count('id'))
    
    # Recent unread count
    recent_pending = EmailNotification.objects.filter(
        recipient=request.user,
        status='PENDING'
    ).count()
    
    return Response({
        'by_status': {item['status']: item['count'] for item in status_counts},
        'by_type': {item['notification_type']: item['count'] for item in type_counts},
        'pending_count': recent_pending,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_notification(request):
    """
    Send a test notification to current user.
    
    POST /api/notifications/test/
    
    Useful for testing email configuration.
    """
    from .notifications import NotificationService
    
    notification = NotificationService.create_notification(
        recipient=request.user,
        notification_type='SECURITY_ALERT',
        subject='Test Notification from Enginel',
        message_plain=f"""
Hello {request.user.first_name or request.user.username},

This is a test notification to verify your email settings are configured correctly.

If you received this email, your notifications are working properly!

Best regards,
The Enginel Team
        """.strip(),
        priority='NORMAL'
    )
    
    if notification:
        return Response({
            'message': 'Test notification queued successfully',
            'notification_id': str(notification.id),
            'recipient': request.user.email,
        })
    else:
        return Response({
            'message': 'Notification not sent (disabled or rate limited)',
        }, status=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# VALIDATION VIEWS
# ============================================================================

from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from .models import ValidationRule, ValidationResult
from .serializers import (
    ValidationRuleSerializer,
    ValidationResultSerializer,
    ValidationOverrideSerializer,
    FieldValidationSerializer,
    BatchValidationSerializer,
    ValidationReportSerializer,
)
from .validation_service import ValidationService


class ValidationRuleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing validation rules.
    
    Provides CRUD operations for validation rules and statistics.
    """
    serializer_class = ValidationRuleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['rule_type', 'target_model', 'severity', 'is_active']
    search_fields = ['name', 'description', 'target_field']
    ordering_fields = ['created_at', 'name', 'total_checks', 'total_failures']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter rules by user's organization."""
        user = self.request.user
        
        # Superusers see all rules
        if user.is_staff:
            return ValidationRule.objects.all()
        
        # Users see all rules
        return ValidationRule.objects.all()
    
    def perform_create(self, serializer):
        """Set created_by to current user."""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a validation rule."""
        rule = self.get_object()
        rule.is_active = True
        rule.save(update_fields=['is_active'])
        
        return Response({
            'message': f'Validation rule "{rule.name}" activated',
            'is_active': True
        })
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a validation rule."""
        rule = self.get_object()
        rule.is_active = False
        rule.save(update_fields=['is_active'])
        
        return Response({
            'message': f'Validation rule "{rule.name}" deactivated',
            'is_active': False
        })
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get statistics for a specific rule."""
        rule = self.get_object()
        
        # Recent results
        recent_results = ValidationResult.objects.filter(rule=rule).order_by('-validated_at')[:100]
        
        # Calculate stats
        total = recent_results.count()
        passed = recent_results.filter(status='PASSED').count()
        failed = recent_results.filter(status='FAILED').count()
        
        return Response({
            'rule': ValidationRuleSerializer(rule).data,
            'statistics': {
                'total_checks': rule.total_checks,
                'total_failures': rule.total_failures,
                'failure_rate': rule.get_failure_rate(),
                'recent_100': {
                    'total': total,
                    'passed': passed,
                    'failed': failed,
                    'pass_rate': round((passed / total * 100), 2) if total > 0 else 0
                }
            }
        })


class ValidationResultViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing validation results.
    
    Read-only access to validation history.
    """
    serializer_class = ValidationResultSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'target_model', 'was_blocked', 'was_overridden']
    search_fields = ['rule__name', 'error_message', 'target_id']
    ordering_fields = ['validated_at', 'status']
    ordering = ['-validated_at']
    pagination_class = PageNumberPagination
    
    def get_queryset(self):
        """Filter results by user's organization."""
        user = self.request.user
        
        queryset = ValidationResult.objects.select_related(
            'rule',
            'validated_by',
            'override_by'
        )
        
        # Return all results
        return queryset
    
    @action(detail=True, methods=['post'])
    def override(self, request, pk=None):
        """Override a validation failure."""
        result = self.get_object()
        
        # Validate request
        serializer = ValidationOverrideSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Check permissions - only staff or org admins can override
        if not (request.user.is_staff or self._is_org_admin(request.user)):
            return Response({
                'error': 'You do not have permission to override validations'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Override the result
        result.override(
            user=request.user,
            reason=serializer.validated_data['reason']
        )
        
        return Response({
            'message': 'Validation overridden successfully',
            'result': ValidationResultSerializer(result).data
        })
    
    def _is_org_admin(self, user):
        """Check if user is staff or superuser."""
        return user.is_staff or user.is_superuser


class ValidateFieldView(APIView):
    """
    API view for validating field values.
    
    POST /api/validation/validate-field/
    {
        "model_name": "DesignAsset",
        "field_name": "filename",
        "value": "test.step"
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Validate a field value."""
        serializer = FieldValidationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        # Run validation
        service = ValidationService()
        is_valid, results = service.validate_field_value(
            model_name=data['model_name'],
            field_name=data['field_name'],
            value=data['value'],
            user=request.user
        )
        
        return Response({
            'is_valid': is_valid,
            'field_name': data['field_name'],
            'value': data['value'],
            'results': ValidationResultSerializer(results, many=True).data
        })


class ValidateBatchView(APIView):
    """
    API view for batch validation.
    
    POST /api/validation/validate-batch/
    {
        "model_name": "DesignAsset",
        "operation": "create",
        "items": [{...}, {...}]
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Validate multiple items."""
        serializer = BatchValidationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        # Note: Batch validation would need model instances
        # For now, return structure
        return Response({
            'message': 'Batch validation endpoint',
            'model_name': data['model_name'],
            'operation': data['operation'],
            'item_count': len(data['items']),
            'note': 'Full batch validation requires model instance creation'
        })


class ValidationReportView(APIView):
    """
    API view for validation reports.
    
    GET /api/validation/report/?model_name=DesignAsset&start_date=...&end_date=...
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Generate validation report."""
        serializer = ValidationReportSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        # Generate report
        service = ValidationService()
        report = service.get_validation_report(
            model_name=data.get('model_name'),
            start_date=data.get('start_date'),
            end_date=data.get('end_date')
        )
        
        return Response(report)


class ValidationStatisticsView(APIView):
    """
    API view for validation statistics summary.
    
    GET /api/validation/statistics/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get validation statistics."""
        user = request.user
        
        # Get rules count
        rules_query = ValidationRule.objects.filter(is_active=True)
        
        total_rules = rules_query.count()
        rules_by_type = {}
        for rule in rules_query:
            rules_by_type[rule.rule_type] = rules_by_type.get(rule.rule_type, 0) + 1
        
        # Get recent results
        from django.utils import timezone
        from datetime import timedelta
        
        last_7_days = timezone.now() - timedelta(days=7)
        
        results_query = ValidationResult.objects.filter(validated_at__gte=last_7_days)
        
        total_checks = results_query.count()
        passed = results_query.filter(status='PASSED').count()
        failed = results_query.filter(status='FAILED').count()
        blocked = results_query.filter(was_blocked=True).count()
        
        return Response({
            'rules': {
                'total_active': total_rules,
                'by_type': rules_by_type
            },
            'last_7_days': {
                'total_checks': total_checks,
                'passed': passed,
                'failed': failed,
                'blocked': blocked,
                'pass_rate': round((passed / total_checks * 100), 2) if total_checks > 0 else 0
            }
        })

