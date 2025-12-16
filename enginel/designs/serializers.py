"""
Serializers for Enginel API.

Handles serialization/deserialization of models to/from JSON.
"""
from rest_framework import serializers
from .models import (
    CustomUser, DesignSeries, DesignAsset, AssemblyNode,
    AnalysisJob, ReviewSession, Markup
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
    version_count = serializers.IntegerField(read_only=True)
    latest_version_number = serializers.IntegerField(read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
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
    
    Returns the entire hierarchical structure.
    """
    design_asset_id = serializers.UUIDField()
    root_nodes = AssemblyNodeSerializer(many=True)
    total_parts = serializers.IntegerField()
    max_depth = serializers.IntegerField()


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
