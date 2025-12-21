"""
Serializers for Enginel API.

Handles serialization/deserialization of models to/from JSON.
"""
from rest_framework import serializers
from django.db.models import Max
from .models import (
    CustomUser, DesignSeries, DesignAsset, AssemblyNode,
    AnalysisJob, ReviewSession, Markup, AuditLog,
    APIKey, RefreshToken, NotificationPreference, EmailNotification,
    ValidationRule, ValidationResult, Notification
)


class CustomUserSerializer(serializers.ModelSerializer):
    """
    Serializer for CustomUser model.
    
    Excludes sensitive fields like password hash.
    """
    
    class Meta:
        model = CustomUser
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'is_us_person',
            'security_clearance_level',
            'organization',
            'phone_number',
            'date_joined',
        ]
        read_only_fields = ['id', 'date_joined']


class DesignSeriesSerializer(serializers.ModelSerializer):
    """
    Serializer for Design Series (Part Numbers).
    """
    version_count = serializers.IntegerField(read_only=True, required=False)
    latest_version_number = serializers.IntegerField(read_only=True, required=False)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, required=False)
    
    class Meta:
        model = DesignSeries
        fields = [
            'id',
            'part_number',
            'name',
            'description',
            'version_count',
            'latest_version_number',
            'created_by_username',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'version_count', 'latest_version_number', 'created_by_username']
    
    def validate_part_number(self, value):
        """Validate part number format and uniqueness."""
        if not value or not value.strip():
            raise serializers.ValidationError("Part number cannot be empty.")
        
        value = value.strip()
        
        # Check for duplicate part numbers (case-insensitive)
        if self.instance is None:  # Creating new instance
            if DesignSeries.objects.filter(part_number__iexact=value).exists():
                # Suggest alternatives
                import random
                suggestion = f"{value}-{random.randint(100, 999)}"
                raise serializers.ValidationError(
                    f"A series with part number '{value}' already exists. "
                    f"Try a unique identifier like '{suggestion}' or use a timestamp."
                )
        else:  # Updating existing instance
            if DesignSeries.objects.filter(part_number__iexact=value).exclude(pk=self.instance.pk).exists():
                raise serializers.ValidationError(f"A series with part number '{value}' already exists.")
        
        return value
    
    def validate_name(self, value):
        """Validate name field."""
        if not value or not value.strip():
            raise serializers.ValidationError("Name cannot be empty.")
        return value.strip()


class DesignAssetListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing design assets.
    
    Used in list views where full metadata isn't needed.
    """
    part_number = serializers.CharField(source='series.part_number', read_only=True)
    series_name = serializers.CharField(source='series.name', read_only=True)
    uploaded_by_username = serializers.CharField(source='uploaded_by.username', read_only=True)
    
    class Meta:
        model = DesignAsset
        fields = [
            'id',
            'series',
            'part_number',
            'series_name',
            'version_number',
            'filename',
            'revision',
            'classification',
            'status',
            'is_valid_geometry',
            'uploaded_by_username',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class DesignAssetDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for individual design asset retrieval.
    
    Includes full metadata and validation results.
    """
    series = DesignSeriesSerializer(read_only=True)
    uploaded_by = CustomUserSerializer(read_only=True)
    file_url = serializers.SerializerMethodField()
    preview_url = serializers.SerializerMethodField()
    
    class Meta:
        model = DesignAsset
        fields = [
            'id',
            'series',
            'version_number',
            'filename',
            'file_url',
            'preview_url',
            'revision',
            'description',
            'classification',
            'status',
            's3_key',
            'preview_s3_key',
            'file_hash',
            'file_size',
            'is_valid_geometry',
            'validation_report',
            'metadata',
            'tags',
            'uploaded_by',
            'created_at',
            'updated_at',
            'processed_at',
        ]
        read_only_fields = [
            'id',
            's3_key',
            'preview_s3_key',
            'file_hash',
            'file_size',
            'status',
            'is_valid_geometry',
            'validation_report',
            'metadata',
            'created_at',
            'updated_at',
            'processed_at',
            'file_url',
            'preview_url',
        ]
    
    def get_file_url(self, obj):
        """Generate pre-signed download URL if file exists."""
        from django.conf import settings
        
        if not obj.file:
            return None
        
        # If using S3, generate pre-signed URL
        if settings.USE_S3 and obj.s3_key:
            try:
                from designs.s3_service import get_s3_service
                s3_service = get_s3_service()
                return s3_service.generate_download_presigned_url(
                    obj.s3_key,
                    expiration=3600  # 1 hour
                )
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to generate pre-signed URL: {e}")
                return None
        
        # Fallback to regular URL for local storage
        return obj.file.url if obj.file else None
    
    def get_preview_url(self, obj):
        """Generate pre-signed URL for preview file (STL for web viewing)."""
        from django.conf import settings
        
        if not obj.preview_file:
            return None
        
        # If using S3, generate pre-signed URL
        if settings.USE_S3 and obj.preview_s3_key:
            try:
                from designs.s3_service import get_s3_service
                s3_service = get_s3_service()
                return s3_service.generate_download_presigned_url(
                    obj.preview_s3_key,
                    expiration=3600  # 1 hour
                )
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to generate preview pre-signed URL: {e}")
                return None
        
        # Fallback to regular URL for local storage
        return obj.preview_file.url if obj.preview_file else None


class DesignAssetCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating design assets with file upload.
    
    Supports both direct file upload and metadata-only creation
    (for two-phase upload workflow with S3 presigned URLs).
    """
    tags = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_null=True,
        default=list
    )
    file = serializers.FileField(
        required=False,
        allow_null=True,
        help_text="CAD file (STEP/IGES/STL). Optional for presigned URL workflow."
    )
    version_number = serializers.IntegerField(
        required=False,
        default=1,
        help_text="Version number (defaults to 1 if not provided)"
    )
    filename = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Filename (auto-populated from file if not provided)"
    )
    
    class Meta:
        model = DesignAsset
        fields = [
            'series',
            'version_number',
            'filename',
            'file',
            'revision',
            'description',
            'classification',
            'tags',
        ]
    
    def validate_file(self, value):
        """Validate uploaded file."""
        if value:
            # Check file extension
            allowed_extensions = ['.step', '.stp', '.iges', '.igs', '.stl']
            filename = value.name.lower()
            if not any(filename.endswith(ext) for ext in allowed_extensions):
                raise serializers.ValidationError(
                    f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
                )
            
            # Check file size (max 500MB)
            max_size = 500 * 1024 * 1024
            if value.size > max_size:
                raise serializers.ValidationError(
                    f"File too large. Maximum size: 500MB"
                )
        
        return value
    
    def validate_tags(self, value):
        """Handle null or empty tags."""
        if value is None or value == 'null' or value == '':
            return []
        return value
    
    def validate_classification(self, value):
        """Ensure user has clearance for specified classification."""
        request = self.context.get('request')
        if request and request.user:
            user = request.user
            if value == 'ITAR' and not user.is_us_person:
                raise serializers.ValidationError(
                    "You do not have clearance to upload ITAR-controlled designs."
                )
        return value
    
    def validate(self, data):
        """Ensure version number doesn't already exist for the series and auto-populate fields."""
        series = data.get('series')
        file_data = data.get('file')
        
        # Auto-populate filename from file if not provided
        if file_data and not data.get('filename'):
            data['filename'] = file_data.name
        
        # Note: version_number auto-increment happens in create() with proper locking
        # to prevent race conditions
        
        version_number = data.get('version_number')
        
        # Only check for duplicate if version_number was explicitly provided
        if version_number and series:
            if DesignAsset.objects.filter(
                series=series,
                version_number=version_number
            ).exists():
                raise serializers.ValidationError(
                    f"Version {version_number} already exists for {series.part_number}"
                )
        
        return data
    
    def create(self, validated_data):
        """Create design asset and trigger processing if file uploaded."""
        from django.db import transaction
        from .tasks import process_design_asset
        
        file_data = validated_data.pop('file', None)
        
        # Ensure filename is set
        if file_data and not validated_data.get('filename'):
            validated_data['filename'] = file_data.name
        
        # Auto-assign version_number with proper locking to prevent race conditions
        with transaction.atomic():
            if not validated_data.get('version_number'):
                series = validated_data.get('series')
                if series:
                    # Lock the series to prevent concurrent version assignments
                    from .models import DesignSeries
                    DesignSeries.objects.select_for_update().filter(pk=series.pk).first()
                    
                    # Get the next version number
                    latest_version = DesignAsset.objects.filter(series=series).aggregate(
                        Max('version_number')
                    )['version_number__max']
                    validated_data['version_number'] = (latest_version or 0) + 1
                else:
                    validated_data['version_number'] = 1
            
            # Create the instance inside the transaction to maintain the lock
            instance = super().create(validated_data)
        
        if file_data:
            instance.file = file_data
            instance.file_size = file_data.size
            instance.status = 'PROCESSING'
            instance.save()
            
            # Trigger async processing
            try:
                process_design_asset.delay(instance.id)
            except Exception as e:
                # If Celery is not available, log the error but don't fail
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to queue processing task: {e}")
                instance.status = 'PENDING'
                instance.save()
        
        return instance


class AssemblyNodeSerializer(serializers.ModelSerializer):
    """
    Serializer for BOM tree nodes.
    
    Supports hierarchical representation of assemblies.
    """
    children = serializers.SerializerMethodField()
    
    class Meta:
        model = AssemblyNode
        fields = [
            'id',
            'design_asset',
            'name',
            'part_number',
            'node_type',
            'quantity',
            'reference_designator',
            'mass',
            'volume',
            'depth',
            'numchild',
            'children',
        ]
        read_only_fields = ['id', 'depth', 'numchild']
    
    def get_children(self, obj):
        """Recursively serialize child nodes."""
        if obj.get_children():
            return AssemblyNodeSerializer(
                obj.get_children(),
                many=True,
                context=self.context
            ).data
        return []


class BOMTreeSerializer(serializers.Serializer):
    """
    Serializer for complete BOM tree export.
    
    Returns the entire hierarchical structure with statistics.
    """
    design_asset_id = serializers.UUIDField()
    filename = serializers.CharField(required=False)
    root_nodes = AssemblyNodeSerializer(many=True)
    total_nodes = serializers.IntegerField(required=False)
    total_parts = serializers.IntegerField()
    total_assemblies = serializers.IntegerField(required=False)
    max_depth = serializers.IntegerField()
    total_mass_kg = serializers.FloatField(required=False)
    message = serializers.CharField(required=False)


class UploadURLResponseSerializer(serializers.Serializer):
    """
    Response serializer for pre-signed upload URL request.
    
    Contains the URL and necessary metadata for S3 upload.
    """
    upload_url = serializers.URLField()
    design_asset_id = serializers.UUIDField()
    expires_in_seconds = serializers.IntegerField()
    fields = serializers.DictField()


class DownloadURLResponseSerializer(serializers.Serializer):
    """
    Response serializer for pre-signed download URL request.
    
    Returns short-lived URL for secure file download.
    """
    download_url = serializers.URLField()
    expires_in_seconds = serializers.IntegerField()
    filename = serializers.CharField()


class AnalysisJobSerializer(serializers.ModelSerializer):
    """
    Serializer for background analysis jobs.
    """
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = AnalysisJob
        fields = [
            'id',
            'design_asset',
            'job_type',
            'status',
            'celery_task_id',
            'result',
            'error_message',
            'created_at',
            'started_at',
            'completed_at',
            'duration',
        ]
        read_only_fields = [
            'id',
            'celery_task_id',
            'created_at',
            'started_at',
            'completed_at',
        ]
    
    def get_duration(self, obj):
        """Calculate job duration."""
        return obj.get_duration()


class MarkupSerializer(serializers.ModelSerializer):
    """
    Serializer for 3D markups/annotations.
    """
    author_username = serializers.CharField(source='author.username', read_only=True)
    
    class Meta:
        model = Markup
        fields = [
            'id',
            'review_session',
            'author',
            'author_username',
            'title',
            'comment',
            'anchor_point',
            'camera_state',
            'is_resolved',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']


class ReviewSessionSerializer(serializers.ModelSerializer):
    """
    Serializer for design review sessions.
    """
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    reviewer_usernames = serializers.SerializerMethodField()
    markup_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = ReviewSession
        fields = [
            'id',
            'design_asset',
            'title',
            'description',
            'status',
            'created_by',
            'created_by_username',
            'reviewers',
            'reviewer_usernames',
            'markup_count',
            'created_at',
            'started_at',
            'completed_at',
        ]
        read_only_fields = [
            'id',
            'created_by',
            'created_at',
            'started_at',
            'completed_at',
        ]
    
    def get_reviewer_usernames(self, obj):
        """Get list of reviewer usernames."""
        return [r.username for r in obj.reviewers.all()]


class ReviewSessionDetailSerializer(ReviewSessionSerializer):
    """
    Detailed review session with nested markups.
    """
    markups = MarkupSerializer(many=True, read_only=True)
    design_asset_detail = DesignAssetDetailSerializer(source='design_asset', read_only=True)
    
    class Meta(ReviewSessionSerializer.Meta):
        fields = ReviewSessionSerializer.Meta.fields + ['markups', 'design_asset_detail']


class AuditLogSerializer(serializers.ModelSerializer):
    """
    Serializer for audit log entries.
    
    Read-only access to immutable audit trail.
    """
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = [
            'id',
            'actor_id',
            'actor_username',
            'action',
            'action_display',
            'resource_type',
            'resource_id',
            'ip_address',
            'user_agent',
            'changes',
            'timestamp',
        ]
        read_only_fields = '__all__'  # Audit logs are immutable


# Authentication Serializers

class LoginSerializer(serializers.Serializer):
    """Serializer for login credentials."""
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)
    device_name = serializers.CharField(required=False, allow_blank=True)


class TokenSerializer(serializers.Serializer):
    """Serializer for token response."""
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    expires_in = serializers.IntegerField()
    token_type = serializers.CharField(default='Bearer')


class RefreshTokenSerializer(serializers.Serializer):
    """Serializer for refresh token request."""
    refresh_token = serializers.CharField(required=True)


class APIKeySerializer(serializers.ModelSerializer):
    """
    Serializer for API Key.
    
    Note: Full key is only returned on creation.
    For existing keys, only first/last 4 chars shown.
    """
    key_masked = serializers.SerializerMethodField()
    
    class Meta:
        model = APIKey
        fields = [
            'id',
            'name',
            'key',
            'key_masked',
            'is_active',
            'created_at',
            'expires_at',
            'last_used_at',
            'allowed_ips',
            'scopes',
        ]
        read_only_fields = ['id', 'key', 'created_at', 'last_used_at']
    
    def get_key_masked(self, obj):
        """Return masked key showing only first and last 4 characters."""
        if len(obj.key) > 8:
            return f"{obj.key[:4]}...{obj.key[-4:]}"
        return "****"
    
    def to_representation(self, instance):
        """Override to show full key only on creation."""
        data = super().to_representation(instance)
        
        # If this is a new object (being created), include full key
        if instance._state.adding or hasattr(instance, '_show_full_key'):
            data['key'] = instance.key
        else:
            # For existing objects, remove key and show only masked version
            data.pop('key', None)
        
        return data


class CreateAPIKeySerializer(serializers.Serializer):
    """Serializer for creating a new API key."""
    name = serializers.CharField(required=True, max_length=255)
    expires_in_days = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=3650,
        help_text="Number of days until expiration (max 10 years)"
    )
    allowed_ips = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Comma-separated list of allowed IP addresses"
    )
    scopes = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Comma-separated list of allowed scopes"
    )


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """
    Serializer for NotificationPreference model.
    """
    class Meta:
        model = NotificationPreference
        fields = [
            'user',
            'email_enabled',
            'notify_design_uploaded',
            'notify_design_approved',
            'notify_design_rejected',
            'notify_review_started',
            'notify_review_completed',
            'notify_markup_added',
            'notify_job_completed',
            'notify_job_failed',
            'notify_organization_invite',
            'notify_role_changed',
            'delivery_method',
            'quiet_hours_enabled',
            'quiet_hours_start',
            'quiet_hours_end',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['user', 'created_at', 'updated_at']


class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for in-app Notification model.
    """
    actor_username = serializers.CharField(source='actor.username', read_only=True, allow_null=True)
    actor_email = serializers.EmailField(source='actor.email', read_only=True, allow_null=True)
    recipient_username = serializers.CharField(source='recipient.username', read_only=True)
    is_expired = serializers.SerializerMethodField()
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id',
            'recipient',
            'recipient_username',
            'notification_type',
            'title',
            'message',
            'resource_type',
            'resource_id',
            'action_url',
            'actor',
            'actor_username',
            'actor_email',
            'is_read',
            'is_archived',
            'read_at',
            'archived_at',
            'priority',
            'metadata',
            'created_at',
            'updated_at',
            'expires_at',
            'is_expired',
            'time_ago',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_expired', 'time_ago']
    
    def get_is_expired(self, obj):
        """Check if notification has expired."""
        return obj.is_expired()
    
    def get_time_ago(self, obj):
        """Return human-readable time since creation."""
        from django.utils import timezone
        from datetime import datetime, timedelta
        
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff < timedelta(minutes=1):
            return 'just now'
        elif diff < timedelta(hours=1):
            minutes = int(diff.total_seconds() / 60)
            return f'{minutes}m ago'
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return f'{hours}h ago'
        elif diff < timedelta(days=7):
            days = diff.days
            return f'{days}d ago'
        else:
            return obj.created_at.strftime('%b %d')


class NotificationListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for notification lists (excludes heavy fields).
    """
    actor_username = serializers.CharField(source='actor.username', read_only=True, allow_null=True)
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id',
            'notification_type',
            'title',
            'message',
            'action_url',
            'actor_username',
            'is_read',
            'priority',
            'created_at',
            'time_ago',
        ]
        read_only_fields = ['id', 'created_at', 'time_ago']
    
    def get_time_ago(self, obj):
        """Return human-readable time since creation."""
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff < timedelta(minutes=1):
            return 'just now'
        elif diff < timedelta(hours=1):
            minutes = int(diff.total_seconds() / 60)
            return f'{minutes}m ago'
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return f'{hours}h ago'
        elif diff < timedelta(days=7):
            days = diff.days
            return f'{days}d ago'
        else:
            return obj.created_at.strftime('%b %d')


class EmailNotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for EmailNotification model.
    """
    recipient_email = serializers.EmailField(source='recipient.email', read_only=True)
    recipient_username = serializers.CharField(source='recipient.username', read_only=True)
    
    class Meta:
        model = EmailNotification
        fields = [
            'id',
            'recipient',
            'recipient_email',
            'recipient_username',
            'notification_type',
            'subject',
            'message_plain',
            'message_html',
            'context_data',
            'status',
            'queued_at',
            'sent_at',
            'failed_at',
            'retry_count',
            'max_retries',
            'next_retry_at',
            'error_message',
            'priority',
        ]
        read_only_fields = [
            'id',
            'recipient',
            'queued_at',
            'sent_at',
            'failed_at',
            'retry_count',
            'error_message',
        ]


class ValidationRuleSerializer(serializers.ModelSerializer):
    """
    Serializer for ValidationRule model.
    """
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    failure_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = ValidationRule
        fields = [
            'id',
            'name',
            'description',
            'rule_type',
            'target_model',
            'target_field',
            'rule_config',
            'error_message',
            'severity',
            'is_active',
            'apply_on_create',
            'apply_on_update',
            'conditions',
            'created_by',
            'created_by_username',
            'created_at',
            'updated_at',
            'total_checks',
            'total_failures',
            'failure_rate',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
            'total_checks',
            'total_failures',
            'failure_rate',
        ]
    
    def get_failure_rate(self, obj):
        """Calculate failure rate percentage."""
        return obj.get_failure_rate()
    
    def validate_rule_config(self, value):
        """Validate rule configuration based on rule type."""
        rule_type = self.initial_data.get('rule_type')
        
        if rule_type == 'REGEX' and 'pattern' not in value:
            raise serializers.ValidationError("REGEX rules require 'pattern' in config")
        
        if rule_type == 'RANGE' and not ('min' in value or 'max' in value):
            raise serializers.ValidationError("RANGE rules require 'min' and/or 'max' in config")
        
        if rule_type == 'LENGTH' and not ('min' in value or 'max' in value):
            raise serializers.ValidationError("LENGTH rules require 'min' and/or 'max' in config")
        
        if rule_type == 'FILE_TYPE' and 'allowed_types' not in value:
            raise serializers.ValidationError("FILE_TYPE rules require 'allowed_types' in config")
        
        if rule_type == 'FILE_SIZE' and not ('min_size' in value or 'max_size' in value):
            raise serializers.ValidationError("FILE_SIZE rules require 'min_size' and/or 'max_size' in config")
        
        if rule_type == 'CUSTOM' and 'expression' not in value:
            raise serializers.ValidationError("CUSTOM rules require 'expression' in config")
        
        if rule_type == 'BUSINESS_RULE' and 'rule_name' not in value:
            raise serializers.ValidationError("BUSINESS_RULE rules require 'rule_name' in config")
        
        return value
    
    def validate_name(self, value):
        """Ensure rule name is unique."""
        if ValidationRule.objects.filter(name=value).exclude(id=self.instance.id if self.instance else None).exists():
            raise serializers.ValidationError("A validation rule with this name already exists")
        return value


class ValidationResultSerializer(serializers.ModelSerializer):
    """
    Serializer for ValidationResult model.
    """
    rule_name = serializers.CharField(source='rule.name', read_only=True)
    rule_type = serializers.CharField(source='rule.rule_type', read_only=True)
    rule_severity = serializers.CharField(source='rule.severity', read_only=True)
    validated_by_username = serializers.CharField(source='validated_by.username', read_only=True)
    override_by_username = serializers.CharField(source='override_by.username', read_only=True)
    
    class Meta:
        model = ValidationResult
        fields = [
            'id',
            'rule',
            'rule_name',
            'rule_type',
            'rule_severity',
            'target_model',
            'target_id',
            'target_field',
            'status',
            'error_message',
            'details',
            'validated_by',
            'validated_by_username',
            'validated_at',
            'was_blocked',
            'was_overridden',
            'override_reason',
            'override_by',
            'override_by_username',
            'override_at',
        ]
        read_only_fields = [
            'id',
            'validated_at',
            'validated_by',
        ]


class ValidationOverrideSerializer(serializers.Serializer):
    """
    Serializer for overriding validation failures.
    """
    reason = serializers.CharField(
        required=True,
        max_length=500,
        help_text="Reason for overriding the validation failure"
    )
    
    def validate_reason(self, value):
        """Ensure reason is provided."""
        if not value or len(value.strip()) < 10:
            raise serializers.ValidationError("Override reason must be at least 10 characters")
        return value


class FieldValidationSerializer(serializers.Serializer):
    """
    Serializer for validating field values.
    """
    model_name = serializers.CharField(
        required=True,
        help_text="Name of the model (e.g., 'DesignAsset')"
    )
    field_name = serializers.CharField(
        required=True,
        help_text="Name of the field to validate"
    )
    value = serializers.JSONField(
        required=True,
        help_text="Value to validate"
    )


class BatchValidationSerializer(serializers.Serializer):
    """
    Serializer for batch validation requests.
    """
    items = serializers.ListField(
        child=serializers.JSONField(),
        min_length=1,
        max_length=100,
        help_text="List of items to validate (max 100)"
    )
    model_name = serializers.CharField(
        required=True,
        help_text="Name of the model"
    )
    operation = serializers.ChoiceField(
        choices=['create', 'update'],
        default='create',
        help_text="Operation type"
    )


class ValidationReportSerializer(serializers.Serializer):
    """
    Serializer for validation report parameters.
    """
    model_name = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Filter by model name"
    )
    start_date = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="Report start date"
    )
    end_date = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="Report end date"
    )
