"""
Serializers for Enginel API.

Handles serialization/deserialization of models to/from JSON.
"""
from rest_framework import serializers
from .models import (
    Organization, OrganizationMembership,
    CustomUser, DesignSeries, DesignAsset, AssemblyNode,
    AnalysisJob, ReviewSession, Markup, AuditLog,
    APIKey, RefreshToken, NotificationPreference, EmailNotification
)


class OrganizationSerializer(serializers.ModelSerializer):
    """
    Serializer for Organization model.
    """
    member_count = serializers.SerializerMethodField()
    storage_used_gb = serializers.SerializerMethodField()
    
    class Meta:
        model = Organization
        fields = [
            'id',
            'name',
            'slug',
            'description',
            'is_active',
            'is_us_organization',
            'subscription_tier',
            'max_users',
            'max_storage_gb',
            'member_count',
            'storage_used_gb',
            'contact_email',
            'contact_phone',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'member_count', 'storage_used_gb']
    
    def get_member_count(self, obj):
        return obj.get_member_count()
    
    def get_storage_used_gb(self, obj):
        return obj.get_storage_used_gb()


class OrganizationMembershipSerializer(serializers.ModelSerializer):
    """
    Serializer for OrganizationMembership model.
    """
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    
    class Meta:
        model = OrganizationMembership
        fields = [
            'id',
            'organization',
            'organization_name',
            'user',
            'username',
            'email',
            'role',
            'joined_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'joined_at', 'updated_at']


class CustomUserSerializer(serializers.ModelSerializer):
    """
    Serializer for CustomUser model.
    
    Excludes sensitive fields like password hash.
    """
    organizations = serializers.SerializerMethodField()
    
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
            'organizations',
        ]
        read_only_fields = ['id', 'date_joined']
    
    def get_organizations(self, obj):
        """Return list of organizations user belongs to."""
        memberships = obj.organization_memberships.select_related('organization')
        return [{
            'id': str(m.organization.id),
            'name': m.organization.name,
            'slug': m.organization.slug,
            'role': m.role,
        } for m in memberships]


class DesignSeriesSerializer(serializers.ModelSerializer):
    """
    Serializer for Design Series (Part Numbers).
    """
    version_count = serializers.IntegerField(read_only=True)
    latest_version_number = serializers.IntegerField(read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    
    class Meta:
        model = DesignSeries
        fields = [
            'id',
            'organization',
            'organization_name',
            'part_number',
            'name',
            'description',
            'version_count',
            'latest_version_number',
            'created_by_username',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


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
    
    class Meta:
        model = DesignAsset
        fields = [
            'id',
            'series',
            'version_number',
            'filename',
            'revision',
            'description',
            'classification',
            'status',
            's3_key',
            'file_hash',
            'file_size',
            'units',
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
            'file_hash',
            'file_size',
            'status',
            'is_valid_geometry',
            'validation_report',
            'metadata',
            'created_at',
            'updated_at',
            'processed_at',
        ]


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
            'units',
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
        """Ensure version number doesn't already exist for the series."""
        series = data.get('series')
        version_number = data.get('version_number')
        
        if series and version_number:
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
        from .tasks import process_design_asset
        
        file_data = validated_data.pop('file', None)
        instance = super().create(validated_data)
        
        if file_data:
            instance.file = file_data
            instance.filename = file_data.name
            instance.file_size = file_data.size
            instance.status = 'processing'
            instance.save()
            
            # Trigger async processing
            process_design_asset.delay(instance.id)
        
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

