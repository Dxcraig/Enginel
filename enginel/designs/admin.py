"""
Django Admin Configuration for Enginel.
Complete admin interface with all models and enhancements.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.db.models import Count
from .models import (
    CustomUser, DesignSeries, DesignAsset, AssemblyNode,
    AnalysisJob, ReviewSession, Markup, AuditLog
)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Admin interface for CustomUser with compliance fields."""
    
    list_display = [
        'username', 
        'email', 
        'is_us_person', 
        'security_clearance_level', 
        'organization',
        'is_staff'
    ]
    
    list_filter = [
        'is_us_person', 
        'security_clearance_level', 
        'is_staff', 
        'is_active'
    ]
    
    search_fields = ['username', 'email', 'organization']
    
    fieldsets = UserAdmin.fieldsets + (
        ('Compliance & Security', {
            'fields': (
                'is_us_person', 
                'security_clearance_level', 
                'organization', 
                'phone_number'
            )
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Compliance & Security', {
            'fields': (
                'is_us_person', 
                'security_clearance_level', 
                'organization', 
                'phone_number'
            )
        }),
    )


class DesignAssetInline(admin.TabularInline):
    """Inline display of versions within a DesignSeries."""
    model = DesignAsset
    extra = 0
    fields = ['version_number', 'filename', 'status', 'classification', 'created_at']
    readonly_fields = ['created_at']
    can_delete = False
    show_change_link = True


@admin.register(DesignSeries)
class DesignSeriesAdmin(admin.ModelAdmin):
    """Admin for Design Series (Part Numbers)."""
    
    list_display = [
        'part_number', 
        'name', 
        'version_count', 
        'latest_version',
        'created_by', 
        'created_at'
    ]
    
    list_filter = ['created_at']
    search_fields = ['part_number', 'name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('part_number', 'name', 'description')
        }),
        ('Metadata', {
            'fields': ('id', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [DesignAssetInline]
    
    def get_queryset(self, request):
        """Optimize queries with annotation."""
        qs = super().get_queryset(request)
        return qs.annotate(versions_count=Count('versions'))
    
    def version_count(self, obj):
        """Display number of versions."""
        return obj.versions_count
    version_count.short_description = 'Versions'
    version_count.admin_order_field = 'versions_count'
    
    def latest_version(self, obj):
        """Display latest version number."""
        latest = obj.get_latest_version()
        if latest:
            return f"v{latest.version_number}"
        return "No versions"
    latest_version.short_description = 'Latest'


class AssemblyNodeInline(admin.TabularInline):
    """Inline BOM nodes for a DesignAsset."""
    model = AssemblyNode
    extra = 0
    fields = ['name', 'part_number', 'node_type', 'quantity']
    show_change_link = True
    max_num = 10  # Limit to prevent overwhelming the admin


class AnalysisJobInline(admin.TabularInline):
    """Inline analysis jobs for a DesignAsset."""
    model = AnalysisJob
    extra = 0
    fields = ['job_type', 'status', 'created_at']
    readonly_fields = ['created_at']
    can_delete = False
    show_change_link = True


@admin.register(DesignAsset)
class DesignAssetAdmin(admin.ModelAdmin):
    """Admin interface for DesignAsset with filtering and search."""
    
    list_display = [
        'display_name',
        'series',
        'version_number',
        'status_badge',
        'classification_badge',
        'uploaded_by',
        'created_at'
    ]
    
    list_filter = [
        'classification',
        'status',
        'is_valid_geometry',
        'created_at',
        'series'
    ]
    
    search_fields = [
        'filename',
        'series__part_number',
        'series__name',
        's3_key',
        'revision'
    ]
    
    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
        'processed_at',
        'file_hash',
        'metadata_display',
        'validation_report_display'
    ]
    
    fieldsets = (
        ('Series & Version', {
            'fields': ('series', 'version_number', 'revision')
        }),
        ('File Information', {
            'fields': ('filename', 's3_key', 'file_size', 'file_hash', 'units')
        }),
        ('Classification & Status', {
            'fields': ('classification', 'status', 'is_valid_geometry')
        }),
        ('Processing', {
            'fields': ('processing_error', 'uploaded_by')
        }),
        ('Extracted Data', {
            'fields': ('metadata_display', 'validation_report_display'),
            'classes': ('collapse',)
        }),
        ('Additional Info', {
            'fields': ('description', 'tags'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('id', 'created_at', 'updated_at', 'processed_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [AssemblyNodeInline, AnalysisJobInline]
    
    actions = ['mark_as_completed', 'mark_as_failed']
    
    def display_name(self, obj):
        """Combined display name."""
        return f"{obj.filename}"
    display_name.short_description = 'File'
    
    def status_badge(self, obj):
        """Colored status badge."""
        colors = {
            'UPLOADING': '#FFA500',
            'PROCESSING': '#007BFF',
            'COMPLETED': '#28A745',
            'FAILED': '#DC3545',
        }
        color = colors.get(obj.status, '#6C757D')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.status
        )
    status_badge.short_description = 'Status'
    
    def classification_badge(self, obj):
        """Colored classification badge."""
        colors = {
            'UNCLASSIFIED': '#6C757D',
            'ITAR': '#DC3545',
            'EAR99': '#FFC107',
            'CUI': '#17A2B8',
        }
        color = colors.get(obj.classification, '#6C757D')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.classification
        )
    classification_badge.short_description = 'Classification'
    
    def metadata_display(self, obj):
        """Pretty JSON display."""
        if not obj.metadata:
            return "No metadata extracted yet"
        import json
        formatted = json.dumps(obj.metadata, indent=2)
        return format_html('<pre style="margin:0;">{}</pre>', formatted)
    metadata_display.short_description = 'Extracted Metadata'
    
    def validation_report_display(self, obj):
        """Pretty JSON display."""
        if not obj.validation_report:
            return "No validation report yet"
        import json
        formatted = json.dumps(obj.validation_report, indent=2)
        return format_html('<pre style="margin:0;">{}</pre>', formatted)
    validation_report_display.short_description = 'Validation Report'
    
    def mark_as_completed(self, request, queryset):
        """Admin action."""
        updated = queryset.update(status='COMPLETED')
        self.message_user(request, f'{updated} design(s) marked as completed.')
    mark_as_completed.short_description = 'Mark selected as COMPLETED'
    
    def mark_as_failed(self, request, queryset):
        """Admin action."""
        updated = queryset.update(status='FAILED')
        self.message_user(request, f'{updated} design(s) marked as failed.')
    mark_as_failed.short_description = 'Mark selected as FAILED'


@admin.register(AssemblyNode)
class AssemblyNodeAdmin(admin.ModelAdmin):
    """Admin interface for BOM tree nodes."""
    
    list_display = [
        'name',
        'part_number',
        'node_type',
        'quantity',
        'design_asset',
        'depth',
        'numchild'
    ]
    
    list_filter = [
        'node_type',
        'design_asset__series'
    ]
    
    search_fields = [
        'name',
        'part_number',
        'reference_designator'
    ]
    
    readonly_fields = [
        'id',
        'path',
        'depth',
        'numchild',
        'metadata_display'
    ]
    
    fieldsets = (
        ('BOM Information', {
            'fields': (
                'design_asset',
                'name',
                'part_number',
                'node_type',
                'quantity',
                'reference_designator'
            )
        }),
        ('Physical Properties', {
            'fields': ('mass', 'volume')
        }),
        ('Tree Structure (Read-Only)', {
            'fields': ('path', 'depth', 'numchild'),
            'classes': ('collapse',)
        }),
        ('Additional Data', {
            'fields': ('metadata_display',),
            'classes': ('collapse',)
        }),
    )
    
    def metadata_display(self, obj):
        """Pretty JSON display."""
        if not obj.component_metadata:
            return "No additional metadata"
        import json
        formatted = json.dumps(obj.component_metadata, indent=2)
        return format_html('<pre style="margin:0;">{}</pre>', formatted)
    metadata_display.short_description = 'Component Metadata'


@admin.register(AnalysisJob)
class AnalysisJobAdmin(admin.ModelAdmin):
    """Admin for Analysis Jobs."""
    
    list_display = [
        'job_type',
        'status_badge',
        'design_asset',
        'created_at',
        'duration_display'
    ]
    
    list_filter = [
        'job_type',
        'status',
        'created_at'
    ]
    
    search_fields = [
        'design_asset__series__part_number',
        'design_asset__filename',
        'celery_task_id'
    ]
    
    readonly_fields = [
        'id',
        'created_at',
        'started_at',
        'completed_at',
        'duration_display',
        'result_display'
    ]
    
    fieldsets = (
        ('Job Information', {
            'fields': ('design_asset', 'job_type', 'status', 'celery_task_id')
        }),
        ('Results', {
            'fields': ('result_display', 'error_message'),
        }),
        ('Timing', {
            'fields': ('created_at', 'started_at', 'completed_at', 'duration_display'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        """Colored status badge."""
        colors = {
            'PENDING': '#FFA500',
            'RUNNING': '#007BFF',
            'SUCCESS': '#28A745',
            'FAILED': '#DC3545',
            'RETRY': '#FFC107',
        }
        color = colors.get(obj.status, '#6C757D')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.status
        )
    status_badge.short_description = 'Status'
    
    def duration_display(self, obj):
        """Display job duration."""
        duration = obj.get_duration()
        if duration:
            return f"{duration:.2f}s"
        return "N/A"
    duration_display.short_description = 'Duration'
    
    def result_display(self, obj):
        """Pretty JSON display."""
        if not obj.result:
            return "No results yet"
        import json
        formatted = json.dumps(obj.result, indent=2)
        return format_html('<pre style="margin:0;">{}</pre>', formatted)
    result_display.short_description = 'Job Result'


class MarkupInline(admin.TabularInline):
    """Inline markups for a review session."""
    model = Markup
    extra = 0
    fields = ['title', 'author', 'is_resolved', 'created_at']
    readonly_fields = ['created_at']
    show_change_link = True


@admin.register(ReviewSession)
class ReviewSessionAdmin(admin.ModelAdmin):
    """Admin for Review Sessions."""
    
    list_display = [
        'title',
        'design_asset',
        'status',
        'created_by',
        'reviewer_count',
        'markup_count',
        'created_at'
    ]
    
    list_filter = ['status', 'created_at']
    search_fields = ['title', 'description', 'design_asset__series__part_number']
    
    readonly_fields = ['id', 'created_at']
    
    filter_horizontal = ['reviewers']
    
    fieldsets = (
        ('Review Information', {
            'fields': ('design_asset', 'title', 'description', 'status')
        }),
        ('Participants', {
            'fields': ('created_by', 'reviewers')
        }),
        ('Timestamps', {
            'fields': ('id', 'created_at', 'started_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [MarkupInline]
    
    def get_queryset(self, request):
        """Optimize queries."""
        qs = super().get_queryset(request)
        return qs.annotate(
            reviewers_count=Count('reviewers', distinct=True),
            markups_count=Count('markups', distinct=True)
        )
    
    def reviewer_count(self, obj):
        """Display reviewer count."""
        return obj.reviewers_count
    reviewer_count.short_description = 'Reviewers'
    reviewer_count.admin_order_field = 'reviewers_count'
    
    def markup_count(self, obj):
        """Display markup count."""
        return obj.markups_count
    markup_count.short_description = 'Comments'
    markup_count.admin_order_field = 'markups_count'


@admin.register(Markup)
class MarkupAdmin(admin.ModelAdmin):
    """Admin for 3D Markups."""
    
    list_display = [
        'title',
        'review_session',
        'author',
        'is_resolved',
        'created_at'
    ]
    
    list_filter = ['is_resolved', 'created_at']
    search_fields = ['title', 'comment', 'author__username']
    
    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
        'anchor_display',
        'camera_display'
    ]
    
    fieldsets = (
        ('Comment Information', {
            'fields': ('review_session', 'author', 'title', 'comment', 'is_resolved')
        }),
        ('3D Context', {
            'fields': ('anchor_display', 'camera_display'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def anchor_display(self, obj):
        """Pretty JSON display."""
        import json
        formatted = json.dumps(obj.anchor_point, indent=2)
        return format_html('<pre style="margin:0;">{}</pre>', formatted)
    anchor_display.short_description = '3D Anchor Point'
    
    def camera_display(self, obj):
        """Pretty JSON display."""
        import json
        formatted = json.dumps(obj.camera_state, indent=2)
        return format_html('<pre style="margin:0;">{}</pre>', formatted)
    camera_display.short_description = 'Camera State'


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    Admin for Audit Logs.
    Read-only to maintain immutability for compliance.
    """
    
    list_display = [
        'timestamp',
        'action_badge',
        'actor_username',
        'resource_type',
        'ip_address'
    ]
    
    list_filter = ['action', 'resource_type', 'timestamp']
    search_fields = ['actor_username', 'resource_id', 'ip_address']
    
    readonly_fields = [
        'id',
        'actor_id',
        'actor_username',
        'action',
        'resource_type',
        'resource_id',
        'ip_address',
        'user_agent',
        'changes_display',
        'timestamp'
    ]
    
    fieldsets = (
        ('Action Details', {
            'fields': ('timestamp', 'action', 'actor_username', 'actor_id')
        }),
        ('Resource', {
            'fields': ('resource_type', 'resource_id')
        }),
        ('Context', {
            'fields': ('ip_address', 'user_agent')
        }),
        ('Changes', {
            'fields': ('changes_display',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Prevent manual creation."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion to maintain immutable audit trail."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent modifications."""
        return False
    
    def action_badge(self, obj):
        """Colored action badge."""
        colors = {
            'CREATE': '#28A745',
            'READ': '#007BFF',
            'UPDATE': '#FFC107',
            'DELETE': '#DC3545',
            'DOWNLOAD': '#17A2B8',
            'UPLOAD': '#6610F2',
        }
        color = colors.get(obj.action, '#6C757D')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.action
        )
    action_badge.short_description = 'Action'
    
    def changes_display(self, obj):
        """Pretty JSON display."""
        if not obj.changes:
            return "No changes recorded"
        import json
        formatted = json.dumps(obj.changes, indent=2)
        return format_html('<pre style="margin:0;">{}</pre>', formatted)
    changes_display.short_description = 'Changes'