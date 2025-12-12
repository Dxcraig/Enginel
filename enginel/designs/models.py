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
"""
import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator
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
        unique=True,
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
    s3_key = models.CharField(
        max_length=512,
        unique=True,
        help_text="Full S3 path: designs/{uuid}/{filename}"
    )
    file_size = models.BigIntegerField(
        help_text="File size in bytes"
    )
    file_hash = models.CharField(
        max_length=64,
        db_index=True,
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
    units = models.CharField(
        max_length=20,
        default='millimeters',
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
        related_name='review_sessions'
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