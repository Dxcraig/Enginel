"""
Serializers for Enginel API.

Handles serialization/deserialization of models to/from JSON.
"""
from rest_framework import serializers
from .models import CustomUser, DesignAsset, AssemblyNode


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


class DesignAssetListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing design assets.
    
    Used in list views where full metadata isn't needed.
    """
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = DesignAsset
        fields = [
            'id',
            'filename',
            'part_number',
            'revision',
            'classification',
            'status',
            'is_valid_geometry',
            'created_by_username',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class DesignAssetDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for individual design asset retrieval.
    
    Includes full metadata and validation results.
    """
    created_by = CustomUserSerializer(read_only=True)
    updated_by = CustomUserSerializer(read_only=True)
    
    class Meta:
        model = DesignAsset
        fields = [
            'id',
            'filename',
            'part_number',
            'revision',
            'description',
            'classification',
            'status',
            's3_key',
            'file_hash',
            'file_size_bytes',
            'file_format',
            'is_valid_geometry',
            'validation_errors',
            'metadata',
            'tags',
            'created_by',
            'created_at',
            'updated_by',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            's3_key',
            'file_hash',
            'file_size_bytes',
            'status',
            'is_valid_geometry',
            'validation_errors',
            'metadata',
            'created_at',
            'updated_at',
        ]


class DesignAssetCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for initiating design asset upload.
    
    Used when requesting a pre-signed upload URL.
    """
    
    class Meta:
        model = DesignAsset
        fields = [
            'filename',
            'part_number',
            'revision',
            'description',
            'classification',
            'file_format',
            'tags',
        ]
    
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


class AssemblyNodeSerializer(serializers.ModelSerializer):
    """
    Serializer for BOM tree nodes.
    
    Supports hierarchical representation of assemblies.
    """
    children = serializers.SerializerMethodField()
    depth = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = AssemblyNode
        fields = [
            'id',
            'design_asset',
            'name',
            'part_number',
            'quantity',
            'reference_designator',
            'notes',
            'depth',
            'children',
        ]
        read_only_fields = ['id', 'depth']
    
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
