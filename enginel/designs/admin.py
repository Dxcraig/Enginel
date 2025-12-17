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
    AnalysisJob, ReviewSession, Markup, AuditLog,
    NotificationPreference, EmailNotification, Notification,
    ValidationRule, ValidationResult
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


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    """Admin interface for NotificationPreference."""
    
    list_display = [
        'user',
        'email_enabled',
        'delivery_method',
        'quiet_hours_enabled',
        'updated_at'
    ]
    
    list_filter = [
        'email_enabled',
        'delivery_method',
        'quiet_hours_enabled',
    ]
    
    search_fields = ['user__username', 'user__email']
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Email Settings', {
            'fields': ('email_enabled', 'delivery_method')
        }),
        ('Notification Types', {
            'fields': (
                'notify_design_uploaded',
                'notify_design_approved',
                'notify_design_rejected',
                'notify_review_started',
                'notify_review_completed',
                'notify_markup_added',
                'notify_job_completed',
                'notify_job_failed',
            )
        }),
        ('Quiet Hours', {
            'fields': (
                'quiet_hours_enabled',
                'quiet_hours_start',
                'quiet_hours_end',
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin interface for in-app Notifications."""
    
    list_display = [
        'id',
        'recipient',
        'notification_type',
        'title',
        'is_read',
        'is_archived',
        'priority',
        'created_at'
    ]
    
    list_filter = [
        'notification_type',
        'is_read',
        'is_archived',
        'priority',
        'created_at',
    ]
    
    search_fields = [
        'title',
        'message',
        'recipient__username',
        'recipient__email',
        'actor__username'
    ]
    
    readonly_fields = ['id', 'created_at', 'updated_at', 'read_at', 'archived_at']
    
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Recipient', {
            'fields': ('recipient', 'actor')
        }),
        ('Notification Content', {
            'fields': (
                'notification_type',
                'title',
                'message',
                'priority',
            )
        }),
        ('Related Resource', {
            'fields': (
                'resource_type',
                'resource_id',
                'action_url',
            ),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': (
                'is_read',
                'read_at',
                'is_archived',
                'archived_at',
            )
        }),
        ('Metadata', {
            'fields': (
                'metadata',
                'expires_at',
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_read', 'mark_as_unread', 'archive_notifications']
    
    def mark_as_read(self, request, queryset):
        """Mark selected notifications as read."""
        count = 0
        for notification in queryset:
            if not notification.is_read:
                notification.mark_as_read()
                count += 1
        self.message_user(request, f'{count} notification(s) marked as read.')
    mark_as_read.short_description = 'Mark selected as read'
    
    def mark_as_unread(self, request, queryset):
        """Mark selected notifications as unread."""
        count = 0
        for notification in queryset:
            if notification.is_read:
                notification.mark_as_unread()
                count += 1
        self.message_user(request, f'{count} notification(s) marked as unread.')
    mark_as_unread.short_description = 'Mark selected as unread'
    
    def archive_notifications(self, request, queryset):
        """Archive selected notifications."""
        count = 0
        for notification in queryset:
            if not notification.is_archived:
                notification.archive()
                count += 1
        self.message_user(request, f'{count} notification(s) archived.')
    archive_notifications.short_description = 'Archive selected notifications'


@admin.register(EmailNotification)
class EmailNotificationAdmin(admin.ModelAdmin):
    """Admin interface for EmailNotification."""
    
    list_display = [
        'id',
        'recipient',
        'notification_type',
        'status_badge',
        'priority',
        'queued_at',
        'sent_at',
        'retry_count',
    ]
    
    list_filter = [
        'status',
        'notification_type',
        'priority',
        'queued_at',
    ]
    
    search_fields = [
        'recipient__username',
        'recipient__email',
        'subject',
    ]
    
    readonly_fields = [
        'id',
        'queued_at',
        'sent_at',
        'failed_at',
        'retry_count',
        'error_message',
    ]
    
    fieldsets = (
        ('Recipient', {
            'fields': ('recipient',)
        }),
        ('Email Content', {
            'fields': (
                'notification_type',
                'subject',
                'message_plain',
                'message_html',
                'context_data',
            )
        }),
        ('Delivery', {
            'fields': (
                'status',
                'priority',
                'queued_at',
                'sent_at',
                'failed_at',
            )
        }),
        ('Retry Logic', {
            'fields': (
                'retry_count',
                'max_retries',
                'next_retry_at',
                'error_message',
            )
        }),
    )
    
    date_hierarchy = 'queued_at'
    
    actions = ['mark_as_sent', 'mark_as_cancelled', 'retry_failed']
    
    def status_badge(self, obj):
        """Colored status badge."""
        colors = {
            'PENDING': '#FFC107',
            'QUEUED': '#007BFF',
            'SENDING': '#17A2B8',
            'SENT': '#28A745',
            'FAILED': '#DC3545',
            'CANCELLED': '#6C757D',
        }
        color = colors.get(obj.status, '#6C757D')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.status
        )
    status_badge.short_description = 'Status'
    
    def mark_as_sent(self, request, queryset):
        """Mark selected notifications as sent."""
        count = queryset.update(status='SENT')
        self.message_user(request, f'{count} notifications marked as sent.')
    mark_as_sent.short_description = 'Mark as sent'
    
    def mark_as_cancelled(self, request, queryset):
        """Mark selected notifications as cancelled."""
        count = queryset.update(status='CANCELLED')
        self.message_user(request, f'{count} notifications cancelled.')
    mark_as_cancelled.short_description = 'Cancel notifications'
    
    def retry_failed(self, request, queryset):
        """Reset failed notifications for retry."""
        count = queryset.filter(status='FAILED').update(
            status='PENDING',
            next_retry_at=None
        )
        self.message_user(request, f'{count} notifications queued for retry.')
    retry_failed.short_description = 'Retry failed notifications'


@admin.register(ValidationRule)
class ValidationRuleAdmin(admin.ModelAdmin):
    """Admin interface for ValidationRule model."""
    
    list_display = [
        'name',
        'rule_type',
        'target_model',
        'target_field',
        'severity_badge',
        'is_active',
        'failure_rate_display',
        'total_checks',
        'total_failures',
        'created_at'
    ]
    
    list_filter = [
        'rule_type',
        'target_model',
        'severity',
        'is_active',
        'apply_on_create',
        'apply_on_update',
    ]
    
    search_fields = [
        'name',
        'description',
        'target_field',
        'error_message'
    ]
    
    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
        'total_checks',
        'total_failures',
        'failure_rate_display'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id',
                'name',
                'description',
                'is_active'
            )
        }),
        ('Rule Definition', {
            'fields': (
                'rule_type',
                'target_model',
                'target_field',
                'rule_config',
                'error_message',
                'severity'
            )
        }),
        ('Application Settings', {
            'fields': (
                'apply_on_create',
                'apply_on_update',
                'conditions'
            )
        }),
        ('Metadata', {
            'fields': (
                'created_by',
            )
        }),
        ('Statistics', {
            'fields': (
                'total_checks',
                'total_failures',
                'failure_rate_display',
                'created_at',
                'updated_at'
            )
        })
    )
    
    actions = [
        'activate_rules',
        'deactivate_rules',
        'reset_statistics'
    ]
    
    def severity_badge(self, obj):
        """Display severity with colored badge."""
        colors = {
            'INFO': '#17A2B8',
            'WARNING': '#FFC107',
            'ERROR': '#DC3545',
            'CRITICAL': '#721C24'
        }
        color = colors.get(obj.severity, '#6C757D')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.severity
        )
    severity_badge.short_description = 'Severity'
    
    def failure_rate_display(self, obj):
        """Display failure rate as percentage."""
        rate = obj.get_failure_rate()
        if rate == 0:
            color = '#28A745'
        elif rate < 10:
            color = '#FFC107'
        else:
            color = '#DC3545'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}%</span>',
            color, rate
        )
    failure_rate_display.short_description = 'Failure Rate'
    
    def activate_rules(self, request, queryset):
        """Activate selected rules."""
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} validation rules activated.')
    activate_rules.short_description = 'Activate selected rules'
    
    def deactivate_rules(self, request, queryset):
        """Deactivate selected rules."""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} validation rules deactivated.')
    deactivate_rules.short_description = 'Deactivate selected rules'
    
    def reset_statistics(self, request, queryset):
        """Reset statistics for selected rules."""
        count = queryset.update(total_checks=0, total_failures=0)
        self.message_user(request, f'Statistics reset for {count} rules.')
    reset_statistics.short_description = 'Reset statistics'


@admin.register(ValidationResult)
class ValidationResultAdmin(admin.ModelAdmin):
    """Admin interface for ValidationResult model."""
    
    list_display = [
        'rule_name',
        'target_model',
        'target_id',
        'status_badge',
        'severity_display',
        'was_blocked',
        'was_overridden',
        'validated_by',
        'validated_at'
    ]
    
    list_filter = [
        'status',
        'target_model',
        'was_blocked',
        'was_overridden',
        'validated_at'
    ]
    
    search_fields = [
        'rule__name',
        'target_id',
        'error_message',
        'override_reason'
    ]
    
    readonly_fields = [
        'id',
        'rule',
        'target_model',
        'target_id',
        'target_field',
        'status',
        'error_message',
        'details',
        'validated_by',
        'validated_at',
        'was_blocked',
        'was_overridden',
        'override_reason',
        'override_by',
        'override_at'
    ]
    
    fieldsets = (
        ('Validation Context', {
            'fields': (
                'id',
                'rule',
                'target_model',
                'target_id',
                'target_field'
            )
        }),
        ('Result', {
            'fields': (
                'status',
                'error_message',
                'details',
                'was_blocked'
            )
        }),
        ('Validation Info', {
            'fields': (
                'validated_by',
                'validated_at'
            )
        }),
        ('Override Info', {
            'fields': (
                'was_overridden',
                'override_reason',
                'override_by',
                'override_at'
            )
        })
    )
    
    actions = ['mark_as_overridden']
    
    def rule_name(self, obj):
        """Display rule name."""
        return obj.rule.name
    rule_name.short_description = 'Rule'
    
    def status_badge(self, obj):
        """Display status with colored badge."""
        colors = {
            'PASSED': '#28A745',
            'FAILED': '#DC3545',
            'SKIPPED': '#6C757D',
            'ERROR': '#FFC107'
        }
        color = colors.get(obj.status, '#6C757D')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.status
        )
    status_badge.short_description = 'Status'
    
    def severity_display(self, obj):
        """Display rule severity."""
        return obj.rule.severity
    severity_display.short_description = 'Severity'
    
    def mark_as_overridden(self, request, queryset):
        """Mark selected results as overridden."""
        count = queryset.filter(status='FAILED', was_overridden=False).update(
            was_overridden=True,
            override_by=request.user,
            override_reason='Overridden by admin in bulk action'
        )
        self.message_user(request, f'{count} validation results marked as overridden.')
    mark_as_overridden.short_description = 'Mark as overridden'
