"""
Advanced filtering for Enginel API endpoints.

Provides comprehensive FilterSet classes using django-filter for:
- Organizations: Filter by tier, user count, storage usage
- Users: Filter by clearance, ITAR status, organization
- DesignSeries: Filter by status, classification, date ranges
- DesignAssets: Filter by file type, status, size, version
- AssemblyNodes: Filter by BOM hierarchy, part types
- ReviewSessions: Filter by status, participants, dates
- Markups: Filter by resolved status, author, criticality
- AuditLogs: Filter by action, resource, user, date ranges
"""
import django_filters
from django.db.models import Q, Count, Sum
from .models import (
    CustomUser,
    DesignSeries,
    DesignAsset,
    AssemblyNode,
    AnalysisJob,
    ReviewSession,
    Markup,
    AuditLog,
)


class CustomUserFilter(django_filters.FilterSet):
    """
    Advanced filtering for Users.
    
    Filters:
    - username/email: Case-insensitive partial match
    - security_clearance_level: Exact match
    - is_us_person: ITAR compliance filter
    - is_active/is_staff/is_superuser: Boolean filters
    - joined_after/joined_before: Account creation date range
    """
    # Text search
    username = django_filters.CharFilter(lookup_expr='icontains')
    email = django_filters.CharFilter(lookup_expr='icontains')
    first_name = django_filters.CharFilter(lookup_expr='icontains')
    last_name = django_filters.CharFilter(lookup_expr='icontains')
    organization = django_filters.CharFilter(
        field_name='organization',
        lookup_expr='icontains'
    )
    
    # Clearance level
    security_clearance_level = django_filters.ChoiceFilter(
        choices=CustomUser.CLEARANCE_CHOICES
    )
    
    # Minimum clearance (hierarchical)
    min_clearance = django_filters.ChoiceFilter(
        method='filter_min_clearance',
        choices=CustomUser.CLEARANCE_CHOICES,
        label='Minimum clearance level'
    )
    
    # ITAR compliance
    is_us_person = django_filters.BooleanFilter()
    
    # Account status
    is_active = django_filters.BooleanFilter()
    is_staff = django_filters.BooleanFilter()
    is_superuser = django_filters.BooleanFilter()
    
    # Date range filters
    joined_after = django_filters.DateTimeFilter(
        field_name='date_joined',
        lookup_expr='gte',
        label='Joined after'
    )
    joined_before = django_filters.DateTimeFilter(
        field_name='date_joined',
        lookup_expr='lte',
        label='Joined before'
    )
    
    class Meta:
        model = CustomUser
        fields = [
            'username',
            'email',
            'is_us_person',
            'security_clearance_level',
            'is_active',
            'is_staff',
        ]
    
    def filter_min_clearance(self, queryset, name, value):
        """Filter users with at least the specified clearance level."""
        clearance_hierarchy = {
            'UNCLASSIFIED': 0,
            'CONFIDENTIAL': 1,
            'SECRET': 2,
            'TOP_SECRET': 3,
        }
        
        min_level = clearance_hierarchy.get(value, 0)
        allowed_clearances = [
            level for level, rank in clearance_hierarchy.items()
            if rank >= min_level
        ]
        
        return queryset.filter(security_clearance_level__in=allowed_clearances)


class DesignSeriesFilter(django_filters.FilterSet):
    """
    Advanced filtering for DesignSeries (part numbers).
    
    Filters:
    - part_number/name: Case-insensitive partial match
    - status: Draft, in_review, released, obsolete
    - classification: Filter by ITAR/clearance level
    - has_versions: Filter series with/without uploaded versions
    - version_count: Filter by number of versions
    - created_by: Filter by creator user ID
    - date ranges: created_at, updated_at filters
    """
    # Text search
    part_number = django_filters.CharFilter(lookup_expr='icontains')
    name = django_filters.CharFilter(lookup_expr='icontains')
    description = django_filters.CharFilter(lookup_expr='icontains')
    
    # Status
    status = django_filters.ChoiceFilter(
        choices=[
            ('DRAFT', 'Draft'),
            ('IN_REVIEW', 'In Review'),
            ('RELEASED', 'Released'),
            ('OBSOLETE', 'Obsolete'),
        ]
    )
    
    # Classification
    classification_level = django_filters.ChoiceFilter()
    requires_itar_compliance = django_filters.BooleanFilter()
    
    # Version filters
    has_versions = django_filters.BooleanFilter(
        method='filter_has_versions',
        label='Has uploaded versions'
    )
    
    min_versions = django_filters.NumberFilter(
        method='filter_min_versions',
        label='Minimum number of versions'
    )
    
    max_versions = django_filters.NumberFilter(
        method='filter_max_versions',
        label='Maximum number of versions'
    )
    
    # Relationships
    created_by = django_filters.NumberFilter(field_name='created_by__id')
    created_by_username = django_filters.CharFilter(
        field_name='created_by__username',
        lookup_expr='icontains'
    )
    
    # Date range filters
    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte'
    )
    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte'
    )
    updated_after = django_filters.DateTimeFilter(
        field_name='updated_at',
        lookup_expr='gte'
    )
    updated_before = django_filters.DateTimeFilter(
        field_name='updated_at',
        lookup_expr='lte'
    )
    
    class Meta:
        model = DesignSeries
        fields = [
            'part_number',
            'name',
            'status',
            'classification_level',
            'requires_itar_compliance',
        ]
    
    def filter_has_versions(self, queryset, name, value):
        """Filter series that have or don't have versions."""
        if value:
            return queryset.filter(versions__isnull=False).distinct()
        return queryset.filter(versions__isnull=True)
    
    def filter_min_versions(self, queryset, name, value):
        """Filter series with at least N versions."""
        return queryset.annotate(
            version_count=Count('versions')
        ).filter(version_count__gte=value)
    
    def filter_max_versions(self, queryset, name, value):
        """Filter series with at most N versions."""
        return queryset.annotate(
            version_count=Count('versions')
        ).filter(version_count__lte=value)


class DesignAssetFilter(django_filters.FilterSet):
    """
    Advanced filtering for DesignAssets (CAD files).
    
    Filters:
    - filename: Case-insensitive partial match
    - file_format: step, iges, stl, obj, etc.
    - upload_status: pending, processing, completed, failed
    - file_size: Range filters in bytes
    - has_geometry: Filter files with extracted geometry
    - has_bom: Filter assemblies with BOM data
    - part_number: Filter by parent series part number
    - revision: Filter by version/revision
    - uploaded_by: Filter by uploader user ID
    - date ranges: created_at, last_modified filters
    """
    # Text search
    filename = django_filters.CharFilter(lookup_expr='icontains')
    revision = django_filters.CharFilter(lookup_expr='icontains')
    
    # Part number from parent series
    part_number = django_filters.CharFilter(
        field_name='series__part_number',
        lookup_expr='icontains'
    )
    series_name = django_filters.CharFilter(
        field_name='series__name',
        lookup_expr='icontains'
    )
    
    # File attributes
    file_format = django_filters.CharFilter(lookup_expr='iexact')
    
    # File format choices (multiple)
    file_formats = django_filters.MultipleChoiceFilter(
        field_name='file_format',
        choices=[
            ('step', 'STEP'),
            ('stp', 'STP'),
            ('iges', 'IGES'),
            ('igs', 'IGS'),
            ('stl', 'STL'),
            ('obj', 'OBJ'),
            ('3mf', '3MF'),
        ],
        lookup_expr='iexact',
        label='File formats'
    )
    
    # Upload status
    upload_status = django_filters.ChoiceFilter(
        choices=[
            ('PENDING', 'Pending'),
            ('PROCESSING', 'Processing'),
            ('COMPLETED', 'Completed'),
            ('FAILED', 'Failed'),
        ]
    )
    
    # File size range (in bytes)
    min_file_size = django_filters.NumberFilter(
        field_name='file_size',
        lookup_expr='gte',
        label='Minimum file size (bytes)'
    )
    max_file_size = django_filters.NumberFilter(
        field_name='file_size',
        lookup_expr='lte',
        label='Maximum file size (bytes)'
    )
    
    # File size in MB for convenience
    min_file_size_mb = django_filters.NumberFilter(
        method='filter_min_size_mb',
        label='Minimum file size (MB)'
    )
    max_file_size_mb = django_filters.NumberFilter(
        method='filter_max_size_mb',
        label='Maximum file size (MB)'
    )
    
    # Geometry metadata filters
    has_geometry = django_filters.BooleanFilter(
        method='filter_has_geometry',
        label='Has extracted geometry metadata'
    )
    
    has_bom = django_filters.BooleanFilter(
        method='filter_has_bom',
        label='Has Bill of Materials'
    )
    
    is_assembly = django_filters.BooleanFilter(
        field_name='is_assembly'
    )
    
    # Numeric range filters for geometry
    min_volume = django_filters.NumberFilter(
        field_name='volume_mm3',
        lookup_expr='gte',
        label='Minimum volume (mm³)'
    )
    max_volume = django_filters.NumberFilter(
        field_name='volume_mm3',
        lookup_expr='lte',
        label='Maximum volume (mm³)'
    )
    
    min_surface_area = django_filters.NumberFilter(
        field_name='surface_area_mm2',
        lookup_expr='gte',
        label='Minimum surface area (mm²)'
    )
    max_surface_area = django_filters.NumberFilter(
        field_name='surface_area_mm2',
        lookup_expr='lte',
        label='Maximum surface area (mm²)'
    )
    
    min_mass = django_filters.NumberFilter(
        field_name='mass_kg',
        lookup_expr='gte',
        label='Minimum mass (kg)'
    )
    max_mass = django_filters.NumberFilter(
        field_name='mass_kg',
        lookup_expr='lte',
        label='Maximum mass (kg)'
    )
    
    # Relationships
    uploaded_by = django_filters.NumberFilter(field_name='uploaded_by__id')
    uploaded_by_username = django_filters.CharFilter(
        field_name='uploaded_by__username',
        lookup_expr='icontains'
    )
    
    series_id = django_filters.UUIDFilter(field_name='series__id')
    
    # Date range filters
    uploaded_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte'
    )
    uploaded_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte'
    )
    modified_after = django_filters.DateTimeFilter(
        field_name='last_modified',
        lookup_expr='gte'
    )
    modified_before = django_filters.DateTimeFilter(
        field_name='last_modified',
        lookup_expr='lte'
    )
    
    class Meta:
        model = DesignAsset
        fields = [
            'filename',
            'file_format',
            'upload_status',
            'is_assembly',
            'revision',
        ]
    
    def filter_min_size_mb(self, queryset, name, value):
        """Filter by minimum file size in MB."""
        bytes_value = value * 1024 * 1024
        return queryset.filter(file_size__gte=bytes_value)
    
    def filter_max_size_mb(self, queryset, name, value):
        """Filter by maximum file size in MB."""
        bytes_value = value * 1024 * 1024
        return queryset.filter(file_size__lte=bytes_value)
    
    def filter_has_geometry(self, queryset, name, value):
        """Filter assets with or without geometry metadata."""
        if value:
            return queryset.filter(
                Q(volume_mm3__isnull=False) | Q(surface_area_mm2__isnull=False)
            )
        return queryset.filter(
            volume_mm3__isnull=True,
            surface_area_mm2__isnull=True
        )
    
    def filter_has_bom(self, queryset, name, value):
        """Filter assets with or without BOM data."""
        if value:
            return queryset.filter(bom_root__isnull=False)
        return queryset.filter(bom_root__isnull=True)


class AssemblyNodeFilter(django_filters.FilterSet):
    """
    Advanced filtering for AssemblyNodes (BOM tree).
    
    Filters:
    - part_name/part_number: Case-insensitive partial match
    - node_type: component, assembly, reference, virtual
    - has_children: Filter nodes with/without child parts
    - depth_level: Filter by hierarchy depth
    - quantity: Range filters for part quantities
    - design_asset: Filter by parent design asset
    """
    # Text search
    part_name = django_filters.CharFilter(lookup_expr='icontains')
    part_number = django_filters.CharFilter(lookup_expr='icontains')
    material = django_filters.CharFilter(lookup_expr='icontains')
    description = django_filters.CharFilter(lookup_expr='icontains')
    
    # Node type
    node_type = django_filters.ChoiceFilter(
        choices=[
            ('COMPONENT', 'Component'),
            ('ASSEMBLY', 'Assembly'),
            ('REFERENCE', 'Reference'),
            ('VIRTUAL', 'Virtual'),
        ]
    )
    
    # Hierarchy filters
    has_children = django_filters.BooleanFilter(
        method='filter_has_children',
        label='Has child nodes'
    )
    
    is_root = django_filters.BooleanFilter(
        method='filter_is_root',
        label='Is root node'
    )
    
    depth_level = django_filters.NumberFilter(
        field_name='depth',
        lookup_expr='exact'
    )
    
    min_depth = django_filters.NumberFilter(
        field_name='depth',
        lookup_expr='gte',
        label='Minimum depth level'
    )
    max_depth = django_filters.NumberFilter(
        field_name='depth',
        lookup_expr='lte',
        label='Maximum depth level'
    )
    
    # Quantity filters
    quantity = django_filters.NumberFilter(field_name='quantity')
    min_quantity = django_filters.NumberFilter(
        field_name='quantity',
        lookup_expr='gte'
    )
    max_quantity = django_filters.NumberFilter(
        field_name='quantity',
        lookup_expr='lte'
    )
    
    # Relationships
    design_asset = django_filters.UUIDFilter(field_name='design_asset__id')
    
    class Meta:
        model = AssemblyNode
        fields = [
            'part_name',
            'part_number',
            'node_type',
            'material',
        ]
    
    def filter_has_children(self, queryset, name, value):
        """Filter nodes with or without children."""
        if value:
            return queryset.filter(numchild__gt=0)
        return queryset.filter(numchild=0)
    
    def filter_is_root(self, queryset, name, value):
        """Filter root-level nodes."""
        if value:
            return queryset.filter(depth=1)
        return queryset.filter(depth__gt=1)


class AnalysisJobFilter(django_filters.FilterSet):
    """
    Advanced filtering for AnalysisJobs (Celery tasks).
    
    Filters:
    - task_name: Exact match for task type
    - status: pending, running, completed, failed
    - design_asset: Filter by associated design asset
    - initiated_by: Filter by user who started the task
    - date ranges: created_at, completed_at filters
    - duration: Filter by execution time
    """
    # Task identification
    task_name = django_filters.CharFilter(lookup_expr='icontains')
    celery_task_id = django_filters.CharFilter(lookup_expr='exact')
    
    # Status
    status = django_filters.ChoiceFilter(
        choices=[
            ('PENDING', 'Pending'),
            ('RUNNING', 'Running'),
            ('COMPLETED', 'Completed'),
            ('FAILED', 'Failed'),
        ]
    )
    
    # Relationships
    design_asset = django_filters.UUIDFilter(field_name='design_asset__id')
    initiated_by = django_filters.NumberFilter(field_name='initiated_by__id')
    
    # Date range filters
    started_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte'
    )
    started_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte'
    )
    completed_after = django_filters.DateTimeFilter(
        field_name='completed_at',
        lookup_expr='gte'
    )
    completed_before = django_filters.DateTimeFilter(
        field_name='completed_at',
        lookup_expr='lte'
    )
    
    # Duration filter (in seconds)
    min_duration = django_filters.NumberFilter(
        method='filter_min_duration',
        label='Minimum duration (seconds)'
    )
    max_duration = django_filters.NumberFilter(
        method='filter_max_duration',
        label='Maximum duration (seconds)'
    )
    
    class Meta:
        model = AnalysisJob
        fields = ['task_name', 'status']
    
    def filter_min_duration(self, queryset, name, value):
        """Filter tasks by minimum execution time."""
        return queryset.filter(
            completed_at__isnull=False
        ).extra(
            where=[f"EXTRACT(EPOCH FROM (completed_at - created_at)) >= {value}"]
        )
    
    def filter_max_duration(self, queryset, name, value):
        """Filter tasks by maximum execution time."""
        return queryset.filter(
            completed_at__isnull=False
        ).extra(
            where=[f"EXTRACT(EPOCH FROM (completed_at - created_at)) <= {value}"]
        )


class ReviewSessionFilter(django_filters.FilterSet):
    """
    Advanced filtering for ReviewSessions.
    
    Filters:
    - title: Case-insensitive partial match
    - status: open, in_progress, completed, cancelled
    - design_asset: Filter by reviewed design
    - created_by/reviewers: Filter by participants
    - date ranges: created_at, completed_at filters
    """
    # Text search
    title = django_filters.CharFilter(lookup_expr='icontains')
    description = django_filters.CharFilter(lookup_expr='icontains')
    
    # Status
    status = django_filters.ChoiceFilter(
        choices=[
            ('DRAFT', 'Draft'),
            ('ACTIVE', 'Active'),
            ('COMPLETED', 'Completed'),
            ('CANCELLED', 'Cancelled'),
        ]
    )
    
    # Relationships
    design_asset = django_filters.UUIDFilter(field_name='design_asset__id')
    created_by = django_filters.NumberFilter(field_name='created_by__id')
    
    # Reviewer filter
    has_reviewer = django_filters.NumberFilter(
        method='filter_has_reviewer',
        label='Has specific reviewer (user ID)'
    )
    
    # Date range filters
    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte'
    )
    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte'
    )
    completed_after = django_filters.DateTimeFilter(
        field_name='completed_at',
        lookup_expr='gte'
    )
    completed_before = django_filters.DateTimeFilter(
        field_name='completed_at',
        lookup_expr='lte'
    )
    
    class Meta:
        model = ReviewSession
        fields = ['title', 'status']
    
    def filter_has_reviewer(self, queryset, name, value):
        """Filter sessions with specific reviewer."""
        return queryset.filter(reviewers__id=value)


class MarkupFilter(django_filters.FilterSet):
    """
    Advanced filtering for Markups (3D annotations).
    
    Filters:
    - title/comment: Case-insensitive partial match
    - is_resolved: Boolean filter for resolved status
    - priority: Filter by criticality level
    - review_session: Filter by parent review
    - author: Filter by markup creator
    - date ranges: created_at, resolved_at filters
    """
    # Text search
    title = django_filters.CharFilter(lookup_expr='icontains')
    comment = django_filters.CharFilter(lookup_expr='icontains')
    
    # Status
    is_resolved = django_filters.BooleanFilter()
    
    # Priority/severity
    priority = django_filters.ChoiceFilter(
        choices=[
            ('LOW', 'Low'),
            ('MEDIUM', 'Medium'),
            ('HIGH', 'High'),
            ('CRITICAL', 'Critical'),
        ]
    )
    
    # Relationships
    review_session = django_filters.UUIDFilter(field_name='review_session__id')
    author = django_filters.NumberFilter(field_name='author__id')
    author_username = django_filters.CharFilter(
        field_name='author__username',
        lookup_expr='icontains'
    )
    
    # Date range filters
    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte'
    )
    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte'
    )
    resolved_after = django_filters.DateTimeFilter(
        field_name='resolved_at',
        lookup_expr='gte'
    )
    resolved_before = django_filters.DateTimeFilter(
        field_name='resolved_at',
        lookup_expr='lte'
    )
    
    class Meta:
        model = Markup
        fields = ['title', 'is_resolved', 'priority']


class AuditLogFilter(django_filters.FilterSet):
    """
    Advanced filtering for AuditLogs (compliance trail).
    
    Filters:
    - action: create, update, delete, view, download, share
    - resource_type: DesignAsset, DesignSeries, User, etc.
    - resource_id: Filter by specific resource UUID
    - actor_username: Filter by user who performed action
    - ip_address: Filter by source IP
    - date ranges: timestamp filters
    - success: Filter successful vs failed actions
    """
    # Action type
    action = django_filters.CharFilter(lookup_expr='iexact')
    
    # Action choices (multiple)
    actions = django_filters.MultipleChoiceFilter(
        field_name='action',
        choices=[
            ('CREATE', 'Create'),
            ('UPDATE', 'Update'),
            ('DELETE', 'Delete'),
            ('VIEW', 'View'),
            ('DOWNLOAD', 'Download'),
            ('SHARE', 'Share'),
            ('UPLOAD', 'Upload'),
            ('APPROVE', 'Approve'),
            ('REJECT', 'Reject'),
        ],
        lookup_expr='iexact',
        label='Actions'
    )
    
    # Resource identification
    resource_type = django_filters.CharFilter(lookup_expr='icontains')
    resource_id = django_filters.CharFilter(lookup_expr='exact')
    
    # Actor identification
    actor_id = django_filters.NumberFilter()
    actor_username = django_filters.CharFilter(lookup_expr='icontains')
    
    # Network/security
    ip_address = django_filters.CharFilter(lookup_expr='exact')
    ip_range = django_filters.CharFilter(
        method='filter_ip_range',
        label='IP range (e.g., 192.168.1.0/24)'
    )
    
    # Success filter
    success = django_filters.BooleanFilter(
        method='filter_success',
        label='Action was successful'
    )
    
    # Date range filters
    timestamp_after = django_filters.DateTimeFilter(
        field_name='timestamp',
        lookup_expr='gte'
    )
    timestamp_before = django_filters.DateTimeFilter(
        field_name='timestamp',
        lookup_expr='lte'
    )
    
    # Recent activity shortcuts
    last_hour = django_filters.BooleanFilter(
        method='filter_last_hour',
        label='Last hour'
    )
    last_day = django_filters.BooleanFilter(
        method='filter_last_day',
        label='Last 24 hours'
    )
    last_week = django_filters.BooleanFilter(
        method='filter_last_week',
        label='Last 7 days'
    )
    
    class Meta:
        model = AuditLog
        fields = [
            'action',
            'resource_type',
            'actor_username',
            'ip_address',
        ]
    
    def filter_ip_range(self, queryset, name, value):
        """Filter by IP range (CIDR notation)."""
        # Simple implementation - could be enhanced with ipaddress module
        if '/' in value:
            prefix = value.split('/')[0]
            base = '.'.join(prefix.split('.')[:-1])
            return queryset.filter(ip_address__startswith=base)
        return queryset.filter(ip_address=value)
    
    def filter_success(self, queryset, name, value):
        """Filter by success status (no errors in details)."""
        if value:
            return queryset.exclude(details__contains='error')
        return queryset.filter(details__contains='error')
    
    def filter_last_hour(self, queryset, name, value):
        """Filter to last hour of activity."""
        if value:
            from django.utils import timezone
            from datetime import timedelta
            cutoff = timezone.now() - timedelta(hours=1)
            return queryset.filter(timestamp__gte=cutoff)
        return queryset
    
    def filter_last_day(self, queryset, name, value):
        """Filter to last 24 hours of activity."""
        if value:
            from django.utils import timezone
            from datetime import timedelta
            cutoff = timezone.now() - timedelta(days=1)
            return queryset.filter(timestamp__gte=cutoff)
        return queryset
    
    def filter_last_week(self, queryset, name, value):
        """Filter to last 7 days of activity."""
        if value:
            from django.utils import timezone
            from datetime import timedelta
            cutoff = timezone.now() - timedelta(days=7)
            return queryset.filter(timestamp__gte=cutoff)
        return queryset
