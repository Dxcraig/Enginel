"""
Core data models for Enginel - Engineering Intelligence Kernel.

Models:
- CustomUser: Extended user with ITAR compliance fields
- DesignSeries: Part number container (manages versions)
- DesignAsset: Specific version of a CAD file with metadata
- AssemblyNode: Hierarchical Bill of Materials (BOM) tree
- AnalysisJob: Tracks Celery background tasks
- ReviewSession: Collaborative design review container
- Markup: 3D annotations/comments on designs
- AuditLog: Immutable compliance audit trail
- ValidationRule: Custom validation rules for data integrity
- ValidationResult: Results from validation checks
"""
import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator, RegexValidator
from django.utils import timezone
from treebeard.mp_tree import MP_Node


class CustomUser(AbstractUser):
    """
    Extended user model with compliance attributes.
    
    Adds ITAR/CMMC compliance fields to Django's standard user model.
    Note: Uses default integer ID (not UUID) for auth system compatibility.
    """
    
    # Fix the related_name conflicts with default User model
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='customuser_set',
        related_query_name='customuser',
    )
    
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='customuser_set',
        related_query_name='customuser',
    )
    
    CLEARANCE_CHOICES = [
        ('UNCLASSIFIED', 'Unclassified'),
        ('CONFIDENTIAL', 'Confidential'),
        ('SECRET', 'Secret'),
        ('TOP_SECRET', 'Top Secret'),
    ]
    
    is_us_person = models.BooleanField(
        default=False,
        help_text="ITAR compliance: Is this user a US Person (citizen/permanent resident)?"
    )
    
    security_clearance_level = models.CharField(
        max_length=20,
        choices=CLEARANCE_CHOICES,
        default='UNCLASSIFIED',
        help_text="User's security clearance level"
    )
    
    organization = models.CharField(
        max_length=255,
        blank=True,
        help_text="Company or organization name"
    )
    
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="Contact phone number"
    )
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['username']
    
    def __str__(self):
        org = self.organization or 'No Org'
        return f"{self.username} ({org})"
    
    def has_clearance_for(self, classification):
        """
        Check if user can access content with given classification.
        
        Args:
            classification: String like 'UNCLASSIFIED', 'ITAR', 'SECRET'
        
        Returns:
            Boolean indicating access permission
        """
        if classification == 'UNCLASSIFIED':
            return True
        
        if classification == 'ITAR':
            return self.is_us_person
        
        # For clearance-based classifications
        clearance_hierarchy = {
            'UNCLASSIFIED': 0,
            'CONFIDENTIAL': 1,
            'SECRET': 2,
            'TOP_SECRET': 3,
        }
        
        user_level = clearance_hierarchy.get(self.security_clearance_level, 0)
        required_level = clearance_hierarchy.get(classification, 0)
        
        return user_level >= required_level


class APIKey(models.Model):
    """
    API Key for service-to-service authentication.
    
    Long-lived tokens for programmatic access with:
    - Configurable expiration
    - Manual revocation
    - Usage tracking
    - Scope restrictions
    """
    key = models.CharField(max_length=64, unique=True, db_index=True)
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='api_keys'
    )
    name = models.CharField(
        max_length=255,
        help_text="Descriptive name for this API key (e.g., 'Jenkins CI', 'Mobile App')"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional expiration date. Null means no expiration."
    )
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    # Optional scope restrictions
    allowed_ips = models.TextField(
        blank=True,
        help_text="Comma-separated list of allowed IP addresses"
    )
    scopes = models.TextField(
        blank=True,
        help_text="Comma-separated list of allowed scopes (e.g., 'read,write')"
    )
    
    class Meta:
        db_table = 'api_keys'
        verbose_name = 'API Key'
        verbose_name_plural = 'API Keys'
        ordering = ['-created_at']
    
    def __str__(self):
        status = "active" if self.is_active else "revoked"
        return f"{self.name} ({self.user.username}) - {status}"
    
    def save(self, *args, **kwargs):
        if not self.key:
            import secrets
            self.key = secrets.token_urlsafe(48)  # 64-char URL-safe key
        super().save(*args, **kwargs)


class RefreshToken(models.Model):
    """
    Refresh token for obtaining new access tokens.
    
    Allows clients to get new access tokens without re-authentication.
    More secure than long-lived access tokens.
    """
    token = models.CharField(max_length=255, unique=True, db_index=True)
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='refresh_tokens'
    )
    access_token_key = models.CharField(
        max_length=64,
        help_text="The access token this refresh token is paired with"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_revoked = models.BooleanField(default=False)
    
    # Track device/client information
    device_name = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        db_table = 'refresh_tokens'
        verbose_name = 'Refresh Token'
        verbose_name_plural = 'Refresh Tokens'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token', 'is_revoked']),
            models.Index(fields=['access_token_key']),
        ]
    
    def __str__(self):
        status = "revoked" if self.is_revoked else "active"
        return f"RefreshToken for {self.user.username} - {status}"
    
    def is_valid(self):
        """Check if refresh token is still valid."""
        from django.utils import timezone
        return (
            not self.is_revoked and
            timezone.now() < self.expires_at
        )
    
    def save(self, *args, **kwargs):
        if not self.token:
            import secrets
            self.token = secrets.token_urlsafe(64)
        if not self.expires_at:
            from django.utils import timezone
            from datetime import timedelta
            from django.conf import settings
            days = getattr(settings, 'REFRESH_TOKEN_EXPIRATION_DAYS', 30)
            self.expires_at = timezone.now() + timedelta(days=days)
        super().save(*args, **kwargs)


class DesignSeries(models.Model):
    """
    Represents an abstract product/part (e.g., "Turbine Blade").
    Container for all versions of a design with a stable part number.
    
    Example:
    - Part Number: TB-001
    - Name: "Turbine Blade Assembly"
    - Versions: v1, v2, v3 (each is a separate DesignAsset)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    part_number = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Stable part number across all versions (e.g., 'TB-001', 'BRK-42-A')"
    )
    
    name = models.CharField(
        max_length=255,
        help_text="Human-readable name"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Detailed description of this part/assembly"
    )
    
    # Ownership
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='design_series_created'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'design_series'
        verbose_name = 'Design Series'
        verbose_name_plural = 'Design Series'
        ordering = ['-created_at']
        unique_together = [['part_number']]
        indexes = [
            models.Index(fields=['part_number']),
        ]
    
    def __str__(self):
        return f"{self.part_number} - {self.name}"
    
    def get_latest_version(self):
        """Returns the most recent DesignAsset for this series."""
        return self.versions.order_by('-version_number').first()
    
    def get_version_count(self):
        """Returns total number of versions."""
        return self.versions.count()


class DesignAsset(models.Model):
    """
    Specific revision/version of a design with extracted metadata.
    
    Lifecycle:
    1. User requests upload → Record created (UPLOADING)
    2. File uploaded to S3 → Status: PROCESSING
    3. Celery extracts geometry → Status: COMPLETED/FAILED
    4. User downloads → Audit logged
    """
    
    CLASSIFICATION_CHOICES = [
        ('UNCLASSIFIED', 'Unclassified'),
        ('ITAR', 'ITAR Controlled'),
        ('EAR99', 'Export Administration Regulations'),
        ('CUI', 'Controlled Unclassified Information'),
    ]
    
    STATUS_CHOICES = [
        ('UPLOADING', 'Upload in Progress'),
        ('PROCESSING', 'Processing Geometry'),
        ('COMPLETED', 'Processing Complete'),
        ('FAILED', 'Processing Failed'),
    ]
    
    # Primary Key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier (prevents enumeration attacks)"
    )
    
    # Version Management (NEW - this is the key architectural change)
    series = models.ForeignKey(
        DesignSeries,
        on_delete=models.CASCADE,
        related_name='versions',
        help_text="Parent series (part number) this version belongs to"
    )
    
    version_number = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Sequential version number (1, 2, 3...)"
    )
    
    # Ownership & Timestamps
    uploaded_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='uploaded_designs',
        help_text="User who uploaded this design"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When geometry processing completed"
    )
    
    # File Information
    filename = models.CharField(
        max_length=255,
        help_text="Original filename (e.g., 'bracket_v2.step')"
    )
    
    def upload_to_path(instance, filename):
        """Generate upload path: designs/{uuid}/{filename}"""
        import os
        ext = os.path.splitext(filename)[1].lower()
        return f'designs/{instance.id}/{instance.id}{ext}'
    
    def get_file_storage():
        """Get the appropriate storage backend based on settings."""
        from django.conf import settings
        if settings.USE_S3:
            from storages.backends.s3boto3 import S3Boto3Storage
            return S3Boto3Storage()
        from django.core.files.storage import FileSystemStorage
        return FileSystemStorage()
    
    file = models.FileField(
        storage=get_file_storage,
        upload_to=upload_to_path,
        null=True,
        blank=True,
        max_length=512,
        help_text="Actual CAD file (STEP/IGES)"
    )
    
    s3_key = models.CharField(
        max_length=512,
        unique=True,
        null=True,
        blank=True,
        help_text="Full S3 path: designs/{uuid}/{filename}"
    )
    file_size = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="File size in bytes"
    )
    file_hash = models.CharField(
        max_length=64,
        db_index=True,
        blank=True,
        default='',
        help_text="SHA-256 hash for integrity verification"
    )
    
    # Classification
    classification = models.CharField(
        max_length=20,
        choices=CLASSIFICATION_CHOICES,
        default='UNCLASSIFIED',
        db_index=True,
        help_text="Export control classification"
    )
    
    # Processing Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='UPLOADING',
        db_index=True,
        help_text="Current processing status"
    )
    processing_error = models.TextField(
        blank=True,
        help_text="Error message if processing failed"
    )
    
    # Extracted Metadata (JSON)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Extracted physical properties: volume, surface_area, center_of_mass, etc."
    )
    
    # Validation Results
    is_valid_geometry = models.BooleanField(
        null=True,
        help_text="Passed Design Rule Checks (manifold, watertight, etc.)"
    )
    validation_report = models.JSONField(
        default=dict,
        blank=True,
        help_text="Detailed validation results"
    )
    
    # Units
    UNITS_CHOICES = [
        ('mm', 'Millimeters'),
        ('cm', 'Centimeters'),
        ('m', 'Meters'),
        ('km', 'Kilometers'),
        ('um', 'Micrometers (Microns)'),
        ('nm', 'Nanometers'),
        ('in', 'Inches'),
        ('ft', 'Feet'),
        ('yd', 'Yards'),
        ('mi', 'Miles'),
    ]
    
    units = models.CharField(
        max_length=2,
        choices=UNITS_CHOICES,
        default='mm',
        help_text="Native units of the CAD file"
    )
    
    # Optional Metadata
    revision = models.CharField(
        max_length=50,
        blank=True,
        help_text="Revision label (e.g., 'Rev A', 'v2.1')"
    )
    description = models.TextField(
        blank=True,
        help_text="Human-readable description of this version"
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Search tags: ['aerospace', 'bracket', 'critical']"
    )
    
    class Meta:
        db_table = 'design_assets'
        ordering = ['-created_at']
        verbose_name = 'Design Asset'
        verbose_name_plural = 'Design Assets'
        
        # CRITICAL: Prevent duplicate versions
        constraints = [
            models.UniqueConstraint(
                fields=['series', 'version_number'],
                name='unique_version_per_series'
            )
        ]
        
        indexes = [
            models.Index(fields=['classification', 'status']),
            models.Index(fields=['uploaded_by', 'created_at']),
            models.Index(fields=['file_hash']),
            models.Index(fields=['series', '-version_number']),
        ]
    
    def __str__(self):
        return f"{self.series.part_number} v{self.version_number} - {self.filename}"
    
    def can_be_accessed_by(self, user):
        """
        Check if user has permission to access this design.
        
        Args:
            user: CustomUser instance
        
        Returns:
            Boolean indicating access permission
        """
        if not user.has_clearance_for(self.classification):
            return False
        
        if self.classification == 'ITAR' and not user.is_us_person:
            return False
        
        return True


class AssemblyNode(MP_Node):
    """
    Hierarchical BOM structure using Materialized Path.
    
    Example:
    Root Assembly (Drone)
    ├── Frame Assembly
    │   ├── Top Plate (x1)
    │   └── Standoff (x4)
    └── Electronics
        └── Flight Controller (x1)
    """
    
    NODE_TYPES = [
        ('ASSEMBLY', 'Assembly'),
        ('SUBASSEMBLY', 'Sub-Assembly'),
        ('PART', 'Part'),
        ('HARDWARE', 'Commercial Hardware'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    design_asset = models.ForeignKey(
        DesignAsset,
        on_delete=models.CASCADE,
        related_name='bom_nodes',
        help_text="Parent design this BOM belongs to"
    )
    
    # BOM Attributes
    name = models.CharField(
        max_length=255,
        help_text="Component name"
    )
    part_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Part number"
    )
    quantity = models.IntegerField(
        default=1,
        help_text="Quantity in assembly"
    )
    reference_designator = models.CharField(
        max_length=50,
        blank=True,
        help_text="Reference designator (e.g., 'R1', 'C23')"
    )
    node_type = models.CharField(
        max_length=20,
        choices=NODE_TYPES,
        default='PART'
    )
    
    # Geometric Properties
    mass = models.FloatField(
        null=True,
        blank=True,
        help_text="Mass in kilograms"
    )
    volume = models.FloatField(
        null=True,
        blank=True,
        help_text="Volume in cubic mm"
    )
    
    # Additional Metadata
    component_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional part data (material, finish, supplier, cost, etc.)"
    )
    
    # treebeard adds: path, depth, numchild
    node_order_by = ['part_number', 'name']
    
    class Meta:
        db_table = 'assembly_nodes'
        verbose_name = 'BOM Node'
        verbose_name_plural = 'BOM Nodes'
    
    def __str__(self):
        indent = "  " * (self.depth - 1) if self.depth > 0 else ""
        return f"{indent}{self.name} (x{self.quantity})"
    
    def get_total_mass(self):
        """Calculate total mass including all children."""
        total = self.mass or 0
        for child in self.get_children():
            total += (child.get_total_mass() * child.quantity)
        return total
    
    def get_part_count(self):
        """Count total number of unique parts."""
        count = 1 if self.node_type == 'PART' else 0
        for child in self.get_children():
            count += child.get_part_count()
        return count


class AnalysisJob(models.Model):
    """
    Tracks asynchronous background tasks (Celery jobs).
    Used for geometry extraction, validation, and other heavy computations.
    """
    
    JOB_TYPES = [
        ('HASH_CALCULATION', 'Hash Calculation'),
        ('GEOMETRY_EXTRACTION', 'Geometry Extraction'),
        ('BOM_PARSING', 'BOM Parsing'),
        ('VALIDATION', 'Validation Check'),
        ('INTERFERENCE_CHECK', 'Interference Check'),
        ('MASS_PROPERTIES', 'Mass Properties Calculation'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('RETRY', 'Retrying'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    design_asset = models.ForeignKey(
        DesignAsset,
        on_delete=models.CASCADE,
        related_name='analysis_jobs'
    )
    
    job_type = models.CharField(max_length=30, choices=JOB_TYPES)
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )
    
    celery_task_id = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        help_text="Celery task UUID for tracking"
    )
    
    result = models.JSONField(
        default=dict,
        blank=True,
        help_text="Job output data"
    )
    
    error_message = models.TextField(
        blank=True,
        help_text="Error details if job failed"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'analysis_jobs'
        verbose_name = 'Analysis Job'
        verbose_name_plural = 'Analysis Jobs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'job_type']),
            models.Index(fields=['celery_task_id']),
            models.Index(fields=['design_asset', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_job_type_display()} - {self.status}"
    
    def get_duration(self):
        """Calculate job duration if completed."""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return delta.total_seconds()
        return None


class ReviewSession(models.Model):
    """
    Container for a collaborative design review process.
    Multiple engineers can be assigned to review a design.
    """
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('ACTIVE', 'Active Review'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    design_asset = models.ForeignKey(
        DesignAsset,
        on_delete=models.CASCADE,
        related_name='review_sessions',
        help_text="Design being reviewed"
    )
    
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT'
    )
    
    # Participants
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reviews_created'
    )
    
    reviewers = models.ManyToManyField(
        CustomUser,
        related_name='assigned_reviews',
        help_text="Engineers assigned to review this design"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'review_sessions'
        verbose_name = 'Review Session'
        verbose_name_plural = 'Review Sessions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.status})"


class Markup(models.Model):
    """
    3D annotation (redline) anchored to a coordinate in 3D space.
    Contains camera position to restore exact view when clicked.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    review_session = models.ForeignKey(
        ReviewSession,
        on_delete=models.CASCADE,
        related_name='markups'
    )
    
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='markups_created'
    )
    
    title = models.CharField(max_length=255)
    comment = models.TextField()
    
    # 3D Position
    anchor_point = models.JSONField(
        help_text="3D coordinate: {x, y, z}"
    )
    
    camera_state = models.JSONField(
        help_text="Camera position and target: {position: {x,y,z}, target: {x,y,z}, up: {x,y,z}}"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    is_resolved = models.BooleanField(
        default=False,
        help_text="Has this comment been addressed?"
    )
    
    class Meta:
        db_table = 'markups'
        verbose_name = 'Markup'
        verbose_name_plural = 'Markups'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} by {self.author.username if self.author else 'Unknown'}"


class AuditLog(models.Model):
    """
    Immutable audit trail for CMMC compliance.
    
    Note: actor_id stored as raw integer (no FK) to preserve history 
    after user deletion, satisfying CMMC data retention requirements.
    """
    
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('READ', 'Read'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('DOWNLOAD', 'Download'),
        ('UPLOAD', 'Upload'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Actor info (no FK - preserves data after user deletion)
    actor_id = models.IntegerField(help_text="User ID who performed action")
    actor_username = models.CharField(max_length=150)
    
    # Action details
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    resource_type = models.CharField(max_length=50, help_text="Model name")
    resource_id = models.UUIDField(help_text="Object UUID")
    
    # Context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Metadata
    changes = models.JSONField(
        default=dict,
        blank=True,
        help_text="Before/after values for updates"
    )
    
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'audit_logs'
        verbose_name = 'Audit Log Entry'
        verbose_name_plural = 'Audit Log Entries'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['actor_id', 'timestamp']),
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['action', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.action} on {self.resource_type} by {self.actor_username}"


class Notification(models.Model):
    """
    In-app notification system for real-time user alerts.
    
    Tracks all in-app notifications (bell icon) separate from email notifications.
    Supports read/unread status, archiving, and various notification types.
    """
    
    NOTIFICATION_TYPES = [
        ('DESIGN_UPLOADED', 'Design Uploaded'),
        ('DESIGN_APPROVED', 'Design Approved'),
        ('DESIGN_REJECTED', 'Design Rejected'),
        ('DESIGN_UPDATED', 'Design Updated'),
        ('REVIEW_ASSIGNED', 'Review Assigned'),
        ('REVIEW_STARTED', 'Review Started'),
        ('REVIEW_COMPLETED', 'Review Completed'),
        ('REVIEW_COMMENT', 'Review Comment Added'),
        ('MARKUP_ADDED', 'Markup Added'),
        ('MARKUP_RESOLVED', 'Markup Resolved'),
        ('MENTION', 'Mentioned in Comment'),
        ('VALIDATION_FAILED', 'Validation Failed'),
        ('VALIDATION_PASSED', 'Validation Passed'),
        ('JOB_COMPLETED', 'Processing Job Completed'),
        ('JOB_FAILED', 'Processing Job Failed'),
        ('SYSTEM_ALERT', 'System Alert'),
        ('SECURITY_ALERT', 'Security Alert'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Recipient
    recipient = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='notifications',
        db_index=True,
        help_text="User who will receive this notification"
    )
    
    # Notification content
    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPES,
        db_index=True,
        help_text="Type of notification"
    )
    
    title = models.CharField(
        max_length=255,
        help_text="Notification title/headline"
    )
    
    message = models.TextField(
        help_text="Notification message body"
    )
    
    # Related resource (optional)
    resource_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Type of related resource (e.g., DesignAsset, ReviewSession)"
    )
    
    resource_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="ID of related resource"
    )
    
    # Action URL (where clicking notification takes user)
    action_url = models.CharField(
        max_length=500,
        blank=True,
        help_text="URL to navigate to when notification is clicked"
    )
    
    # Actor (who triggered the notification)
    actor = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='triggered_notifications',
        help_text="User who triggered this notification"
    )
    
    # Status
    is_read = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Has the user read this notification?"
    )
    
    is_archived = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Has the user archived this notification?"
    )
    
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the notification was read"
    )
    
    archived_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the notification was archived"
    )
    
    # Priority
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('NORMAL', 'Normal'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]
    
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='NORMAL',
        db_index=True,
        help_text="Notification priority level"
    )
    
    # Metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional notification data"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Expiry (for time-sensitive notifications)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="When this notification expires (optional)"
    )
    
    class Meta:
        db_table = 'notifications'
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', 'created_at']),
            models.Index(fields=['recipient', 'is_archived', 'created_at']),
            models.Index(fields=['notification_type', 'created_at']),
            models.Index(fields=['resource_type', 'resource_id']),
        ]
    
    def __str__(self):
        return f"{self.notification_type} for {self.recipient.username}: {self.title}"
    
    def mark_as_read(self):
        """Mark notification as read."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at', 'updated_at'])
    
    def mark_as_unread(self):
        """Mark notification as unread."""
        if self.is_read:
            self.is_read = False
            self.read_at = None
            self.save(update_fields=['is_read', 'read_at', 'updated_at'])
    
    def archive(self):
        """Archive notification."""
        if not self.is_archived:
            self.is_archived = True
            self.archived_at = timezone.now()
            self.save(update_fields=['is_archived', 'archived_at', 'updated_at'])
    
    def unarchive(self):
        """Unarchive notification."""
        if self.is_archived:
            self.is_archived = False
            self.archived_at = None
            self.save(update_fields=['is_archived', 'archived_at', 'updated_at'])
    
    def is_expired(self):
        """Check if notification has expired."""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    @classmethod
    def create_notification(cls, recipient, notification_type, title, message, **kwargs):
        """
        Helper method to create notifications easily.
        
        Usage:
            Notification.create_notification(
                recipient=user,
                notification_type='DESIGN_UPLOADED',
                title='New Design Uploaded',
                message='A new design has been uploaded to series XYZ',
                resource_type='DesignAsset',
                resource_id=design.id,
                action_url=f'/designs/{design.id}',
                actor=uploader
            )
        """
        return cls.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            message=message,
            **kwargs
        )
    
    @classmethod
    def mark_all_as_read(cls, recipient):
        """Mark all unread notifications as read for a user."""
        return cls.objects.filter(
            recipient=recipient,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
    
    @classmethod
    def get_unread_count(cls, recipient):
        """Get count of unread notifications for a user."""
        return cls.objects.filter(
            recipient=recipient,
            is_read=False,
            is_archived=False
        ).count()


class NotificationPreference(models.Model):
    """
    User preferences for email notifications.
    
    Controls which types of notifications a user wants to receive
    and delivery preferences (immediate, digest, etc.)
    """
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
        primary_key=True
    )
    
    # Email preferences
    email_enabled = models.BooleanField(
        default=True,
        help_text="Master switch for all email notifications"
    )
    
    # Notification type preferences
    notify_design_uploaded = models.BooleanField(
        default=True,
        help_text="Notify when a new design is uploaded to a series I follow"
    )
    
    notify_design_approved = models.BooleanField(
        default=True,
        help_text="Notify when my design is approved"
    )
    
    notify_design_rejected = models.BooleanField(
        default=True,
        help_text="Notify when my design is rejected"
    )
    
    notify_review_started = models.BooleanField(
        default=True,
        help_text="Notify when a review session is started on my design"
    )
    
    notify_review_completed = models.BooleanField(
        default=True,
        help_text="Notify when a review session is completed"
    )
    
    notify_markup_added = models.BooleanField(
        default=True,
        help_text="Notify when someone adds a markup to my design"
    )
    
    notify_job_completed = models.BooleanField(
        default=True,
        help_text="Notify when background processing job completes"
    )
    
    notify_job_failed = models.BooleanField(
        default=True,
        help_text="Notify when background processing job fails"
    )
    
    # Delivery preferences
    DELIVERY_CHOICES = [
        ('IMMEDIATE', 'Immediate - Send emails immediately'),
        ('HOURLY', 'Hourly Digest - Bundle notifications hourly'),
        ('DAILY', 'Daily Digest - Send one email per day'),
        ('WEEKLY', 'Weekly Digest - Send one email per week'),
    ]
    
    delivery_method = models.CharField(
        max_length=20,
        choices=DELIVERY_CHOICES,
        default='IMMEDIATE',
        help_text="How to deliver email notifications"
    )
    
    # Quiet hours
    quiet_hours_enabled = models.BooleanField(
        default=False,
        help_text="Enable quiet hours (no notifications during specified times)"
    )
    
    quiet_hours_start = models.TimeField(
        null=True,
        blank=True,
        help_text="Start of quiet hours (e.g., 22:00)"
    )
    
    quiet_hours_end = models.TimeField(
        null=True,
        blank=True,
        help_text="End of quiet hours (e.g., 08:00)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notification_preferences'
        verbose_name = 'Notification Preference'
        verbose_name_plural = 'Notification Preferences'
    
    def __str__(self):
        return f"Notification preferences for {self.user.username}"
    
    def is_in_quiet_hours(self):
        """Check if current time is within user's quiet hours."""
        if not self.quiet_hours_enabled or not self.quiet_hours_start or not self.quiet_hours_end:
            return False
        
        from django.utils import timezone
        current_time = timezone.now().time()
        
        # Handle overnight quiet hours (e.g., 22:00 to 08:00)
        if self.quiet_hours_start > self.quiet_hours_end:
            return current_time >= self.quiet_hours_start or current_time <= self.quiet_hours_end
        else:
            return self.quiet_hours_start <= current_time <= self.quiet_hours_end


class EmailNotification(models.Model):
    """
    Email notification queue and delivery tracking.
    
    Stores all email notifications with delivery status, retry logic,
    and rate limiting support.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Recipient
    recipient = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='email_notifications'
    )
    
    # Email content
    NOTIFICATION_TYPES = [
        ('DESIGN_UPLOADED', 'Design Uploaded'),
        ('DESIGN_APPROVED', 'Design Approved'),
        ('DESIGN_REJECTED', 'Design Rejected'),
        ('REVIEW_STARTED', 'Review Started'),
        ('REVIEW_COMPLETED', 'Review Completed'),
        ('MARKUP_ADDED', 'Markup Added'),
        ('JOB_COMPLETED', 'Job Completed'),
        ('JOB_FAILED', 'Job Failed'),
        ('PASSWORD_RESET', 'Password Reset'),
        ('ACCOUNT_ACTIVATED', 'Account Activated'),
        ('SECURITY_ALERT', 'Security Alert'),
    ]
    
    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPES,
        db_index=True,
        help_text="Type of notification"
    )
    
    subject = models.CharField(
        max_length=255,
        help_text="Email subject line"
    )
    
    message_plain = models.TextField(
        help_text="Plain text email body"
    )
    
    message_html = models.TextField(
        blank=True,
        help_text="HTML email body (optional)"
    )
    
    # Context data for template rendering
    context_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional context for email template"
    )
    
    # Delivery status
    STATUS_CHOICES = [
        ('PENDING', 'Pending - Waiting to send'),
        ('QUEUED', 'Queued - In delivery queue'),
        ('SENDING', 'Sending - Currently being sent'),
        ('SENT', 'Sent - Successfully delivered'),
        ('FAILED', 'Failed - Delivery failed'),
        ('CANCELLED', 'Cancelled - User or system cancelled'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        db_index=True
    )
    
    # Delivery tracking
    queued_at = models.DateTimeField(auto_now_add=True, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    
    retry_count = models.PositiveIntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=3)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    
    error_message = models.TextField(blank=True)
    
    # Priority
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('NORMAL', 'Normal'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]
    
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='NORMAL',
        db_index=True
    )
    
    # Rate limiting
    rate_limit_key = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        help_text="Key for rate limiting (e.g., 'user:<id>:hour')"
    )
    
    class Meta:
        db_table = 'email_notifications'
        verbose_name = 'Email Notification'
        verbose_name_plural = 'Email Notifications'
        ordering = ['-queued_at']
        indexes = [
            models.Index(fields=['recipient', 'status']),
            models.Index(fields=['status', 'priority', 'queued_at']),
            models.Index(fields=['notification_type', 'queued_at']),
            models.Index(fields=['next_retry_at']),
        ]
    
    def __str__(self):
        return f"{self.notification_type} to {self.recipient.email} ({self.status})"
    
    def mark_sent(self):
        """Mark notification as successfully sent."""
        self.status = 'SENT'
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at'])
    
    def mark_failed(self, error_message):
        """Mark notification as failed with error message."""
        self.status = 'FAILED'
        self.failed_at = timezone.now()
        self.error_message = error_message
        self.retry_count += 1
        
        # Schedule retry if under max retries
        if self.retry_count < self.max_retries:
            from django.conf import settings
            retry_delay = settings.NOTIFICATION_RETRY_DELAY
            self.next_retry_at = timezone.now() + timezone.timedelta(seconds=retry_delay)
            self.status = 'PENDING'
        
        self.save(update_fields=['status', 'failed_at', 'error_message', 'retry_count', 'next_retry_at'])
    
    def can_send_now(self):
        """Check if notification can be sent now (rate limiting, retry timing)."""
        if self.status not in ['PENDING', 'FAILED']:
            return False
        
        if self.retry_count >= self.max_retries:
            return False
        
        if self.next_retry_at and timezone.now() < self.next_retry_at:
            return False
        
        return True


class ValidationRule(models.Model):
    """
    Custom validation rules for data integrity checks.
    
    Defines reusable validation rules that can be applied to different
    models and fields. Rules can be built-in or custom Python expressions.
    """
    
    RULE_TYPE_CHOICES = [
        ('REGEX', 'Regular Expression'),
        ('RANGE', 'Numeric Range'),
        ('LENGTH', 'String Length'),
        ('FORMAT', 'Format Validation'),
        ('CUSTOM', 'Custom Python Expression'),
        ('FILE_TYPE', 'File Type Validation'),
        ('FILE_SIZE', 'File Size Validation'),
        ('UNIQUENESS', 'Uniqueness Check'),
        ('RELATIONSHIP', 'Relationship Validation'),
        ('BUSINESS_RULE', 'Business Logic Rule'),
    ]
    
    SEVERITY_CHOICES = [
        ('INFO', 'Informational'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical'),
    ]
    
    TARGET_MODEL_CHOICES = [
        ('DesignAsset', 'Design Asset'),
        ('DesignSeries', 'Design Series'),
        ('CustomUser', 'User'),
        ('ReviewSession', 'Review Session'),
        ('Markup', 'Markup'),
        ('AssemblyNode', 'Assembly Node'),
        ('*', 'All Models'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Rule definition
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Unique name for this validation rule"
    )
    
    description = models.TextField(
        help_text="Description of what this rule validates"
    )
    
    rule_type = models.CharField(
        max_length=20,
        choices=RULE_TYPE_CHOICES,
        help_text="Type of validation to perform"
    )
    
    target_model = models.CharField(
        max_length=50,
        choices=TARGET_MODEL_CHOICES,
        help_text="Model this rule applies to"
    )
    
    target_field = models.CharField(
        max_length=100,
        blank=True,
        help_text="Specific field to validate (leave blank for model-level validation)"
    )
    
    # Rule configuration
    rule_config = models.JSONField(
        default=dict,
        help_text="Configuration for the rule (regex pattern, min/max values, etc.)"
    )
    
    error_message = models.CharField(
        max_length=500,
        help_text="Error message to display when validation fails"
    )
    
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default='ERROR',
        help_text="Severity level of validation failure"
    )
    
    # Conditional application
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this rule is currently active"
    )
    
    apply_on_create = models.BooleanField(
        default=True,
        help_text="Apply validation when creating new records"
    )
    
    apply_on_update = models.BooleanField(
        default=True,
        help_text="Apply validation when updating existing records"
    )
    
    conditions = models.JSONField(
        default=dict,
        blank=True,
        help_text="Conditional logic for when to apply this rule"
    )
    
    # Metadata
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_validation_rules'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Statistics
    total_checks = models.PositiveIntegerField(
        default=0,
        help_text="Total number of times this rule has been checked"
    )
    
    total_failures = models.PositiveIntegerField(
        default=0,
        help_text="Total number of validation failures"
    )
    
    class Meta:
        db_table = 'validation_rules'
        verbose_name = 'Validation Rule'
        verbose_name_plural = 'Validation Rules'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['target_model', 'target_field']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.rule_type})"
    
    def get_failure_rate(self):
        """Calculate validation failure rate."""
        if self.total_checks == 0:
            return 0.0
        return round((self.total_failures / self.total_checks) * 100, 2)
    
    def increment_checks(self):
        """Increment total checks counter."""
        self.total_checks += 1
        self.save(update_fields=['total_checks'])
    
    def increment_failures(self):
        """Increment total failures counter."""
        self.total_failures += 1
        self.save(update_fields=['total_failures'])


class ValidationResult(models.Model):
    """
    Results from validation checks performed on data.
    
    Stores the outcome of validation rules applied to specific records,
    enabling audit trails and validation reporting.
    """
    
    STATUS_CHOICES = [
        ('PASSED', 'Passed'),
        ('FAILED', 'Failed'),
        ('SKIPPED', 'Skipped'),
        ('ERROR', 'Validation Error'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # What was validated
    rule = models.ForeignKey(
        ValidationRule,
        on_delete=models.CASCADE,
        related_name='results',
        help_text="Validation rule that was applied"
    )
    
    target_model = models.CharField(
        max_length=50,
        help_text="Model that was validated"
    )
    
    target_id = models.UUIDField(
        help_text="ID of the record that was validated"
    )
    
    target_field = models.CharField(
        max_length=100,
        blank=True,
        help_text="Specific field that was validated"
    )
    
    # Validation outcome
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        help_text="Outcome of the validation"
    )
    
    error_message = models.TextField(
        blank=True,
        help_text="Error message if validation failed"
    )
    
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Detailed validation results and context"
    )
    
    # Context
    validated_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='validation_results',
        help_text="User who triggered the validation"
    )
    
    validated_at = models.DateTimeField(auto_now_add=True)
    
    # Action taken
    was_blocked = models.BooleanField(
        default=False,
        help_text="Whether the operation was blocked due to validation failure"
    )
    
    was_overridden = models.BooleanField(
        default=False,
        help_text="Whether validation failure was overridden by user"
    )
    
    override_reason = models.TextField(
        blank=True,
        help_text="Reason for overriding validation failure"
    )
    
    override_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='validation_overrides',
        help_text="User who overrode the validation"
    )
    
    override_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When validation was overridden"
    )
    
    class Meta:
        db_table = 'validation_results'
        verbose_name = 'Validation Result'
        verbose_name_plural = 'Validation Results'
        ordering = ['-validated_at']
        indexes = [
            models.Index(fields=['target_model', 'target_id']),
            models.Index(fields=['status']),
            models.Index(fields=['validated_at']),
            models.Index(fields=['was_blocked']),
        ]
    
    def __str__(self):
        return f"{self.rule.name} on {self.target_model}:{self.target_id} - {self.status}"
    
    def override(self, user, reason):
        """Override a failed validation."""
        if self.status != 'FAILED':
            return False
        
        self.was_overridden = True
        self.override_reason = reason
        self.override_by = user
        self.override_at = timezone.now()
        self.save(update_fields=['was_overridden', 'override_reason', 'override_by', 'override_at'])
        
        return True