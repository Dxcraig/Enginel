"""
Core data models for Enginel - Engineering Intelligence Kernel.

Models:
- CustomUser: Extended user with ITAR compliance fields
- DesignAsset: CAD files with metadata and validation
- AssemblyNode: Hierarchical Bill of Materials (BOM) tree
"""
import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from treebeard.mp_tree import MP_Node
from auditlog.registry import auditlog


class CustomUser(AbstractUser):
    """
    Extended user model with compliance attributes.
    
    Adds ITAR/CMMC compliance fields to Django's standard user model.
    """
    
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
        ('NONE', 'No Clearance'),
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
        default='NONE',
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
        
        # Future: Add clearance level logic for SECRET, TOP_SECRET
        return True


class DesignAsset(models.Model):
    """
    CAD file with extracted metadata and validation results.
    
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
    
    # Ownership & Timestamps
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='designs',
        help_text="User who uploaded this design"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
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
        unique=True,
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
        null=True,
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
    
    # Additional Indexing Fields
    part_number = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text="Engineering part number (e.g., 'BRK-001-A')"
    )
    revision = models.CharField(
        max_length=50,
        blank=True,
        help_text="Revision or version (e.g., 'Rev A', 'v2.1')"
    )
    description = models.TextField(
        blank=True,
        help_text="Human-readable description"
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Search tags: ['aerospace', 'bracket', 'critical']"
    )
    
    class Meta:
        db_table = 'design_assets'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['classification', 'status']),
            models.Index(fields=['created_by', 'created_at']),
            models.Index(fields=['file_hash']),
        ]
        verbose_name = 'Design Asset'
        verbose_name_plural = 'Design Assets'
    
    def __str__(self):
        pn = self.part_number or 'No P/N'
        return f"{self.filename} ({pn})"
    
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
    metadata = models.JSONField(
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


# Register models for audit logging
auditlog.register(DesignAsset, exclude_fields=['updated_at'])
auditlog.register(CustomUser, exclude_fields=['last_login', 'password'])