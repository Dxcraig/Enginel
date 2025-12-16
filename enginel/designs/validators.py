"""
Custom validators for Enginel data validation.

Provides reusable validators for:
- File validation (type, size, content)
- CAD file validation (STEP, IGES, STL)
- Geometry validation (manifold, watertight)
- Business rule validation
- ITAR compliance validation
- Data format validation
"""
import re
import os
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, EmailValidator
from django.utils.deconstruct import deconstructible

# Optional python-magic import for MIME type validation
try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False


# ============================================================================
# FILE VALIDATORS
# ============================================================================

@deconstructible
class FileExtensionValidator:
    """Validate file extensions."""
    
    def __init__(self, allowed_extensions, case_sensitive=False):
        self.allowed_extensions = allowed_extensions
        self.case_sensitive = case_sensitive
    
    def __call__(self, value):
        if not value:
            return
        
        filename = getattr(value, 'name', str(value))
        ext = os.path.splitext(filename)[1]
        
        if not self.case_sensitive:
            ext = ext.lower()
            allowed = [e.lower() for e in self.allowed_extensions]
        else:
            allowed = self.allowed_extensions
        
        if ext not in allowed:
            raise ValidationError(
                f"Unsupported file extension '{ext}'. Allowed: {', '.join(self.allowed_extensions)}"
            )
    
    def __eq__(self, other):
        return (
            isinstance(other, FileExtensionValidator) and
            self.allowed_extensions == other.allowed_extensions and
            self.case_sensitive == other.case_sensitive
        )


@deconstructible
class FileSizeValidator:
    """Validate file size within min/max limits."""
    
    def __init__(self, min_size=None, max_size=None):
        self.min_size = min_size
        self.max_size = max_size
    
    def __call__(self, value):
        if not value:
            return
        
        file_size = getattr(value, 'size', None)
        if file_size is None:
            return
        
        if self.min_size and file_size < self.min_size:
            raise ValidationError(
                f"File size {self._format_size(file_size)} is below minimum {self._format_size(self.min_size)}"
            )
        
        if self.max_size and file_size > self.max_size:
            raise ValidationError(
                f"File size {self._format_size(file_size)} exceeds maximum {self._format_size(self.max_size)}"
            )
    
    @staticmethod
    def _format_size(size_bytes):
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f}TB"
    
    def __eq__(self, other):
        return (
            isinstance(other, FileSizeValidator) and
            self.min_size == other.min_size and
            self.max_size == other.max_size
        )


@deconstructible
class FileMimeTypeValidator:
    """Validate file MIME type using python-magic."""
    
    def __init__(self, allowed_types):
        self.allowed_types = allowed_types
    
    def __call__(self, value):
        if not value:
            return
        
        if not HAS_MAGIC:
            # Skip MIME validation if python-magic not installed
            return
        
        try:
            # Read first chunk of file
            file_content = value.read(2048)
            value.seek(0)  # Reset file pointer
            
            # Detect MIME type
            mime = magic.from_buffer(file_content, mime=True)
            
            if mime not in self.allowed_types:
                raise ValidationError(
                    f"Invalid file type '{mime}'. Allowed: {', '.join(self.allowed_types)}"
                )
        except Exception as e:
            raise ValidationError(f"Could not validate file type: {str(e)}")
    
    def __eq__(self, other):
        return (
            isinstance(other, FileMimeTypeValidator) and
            self.allowed_types == other.allowed_types
        )


# ============================================================================
# CAD FILE VALIDATORS
# ============================================================================

@deconstructible
class CADFileValidator:
    """Validate CAD file format and basic structure."""
    
    SUPPORTED_FORMATS = {
        'step': ['.step', '.stp'],
        'iges': ['.iges', '.igs'],
        'stl': ['.stl'],
    }
    
    def __init__(self, formats=None):
        self.formats = formats or ['step', 'iges', 'stl']
    
    def __call__(self, value):
        if not value:
            return
        
        filename = getattr(value, 'name', str(value))
        ext = os.path.splitext(filename)[1].lower()
        
        # Check extension
        valid_extensions = []
        for fmt in self.formats:
            valid_extensions.extend(self.SUPPORTED_FORMATS.get(fmt, []))
        
        if ext not in valid_extensions:
            raise ValidationError(
                f"Unsupported CAD format. Allowed: {', '.join(valid_extensions)}"
            )
        
        # Basic content validation
        try:
            content = value.read(1024)
            value.seek(0)
            
            if ext in ['.step', '.stp']:
                if not self._validate_step_content(content):
                    raise ValidationError("Invalid STEP file format")
            
            elif ext in ['.iges', '.igs']:
                if not self._validate_iges_content(content):
                    raise ValidationError("Invalid IGES file format")
            
            elif ext == '.stl':
                if not self._validate_stl_content(content):
                    raise ValidationError("Invalid STL file format")
        
        except Exception as e:
            raise ValidationError(f"CAD file validation failed: {str(e)}")
    
    @staticmethod
    def _validate_step_content(content):
        """Check if content looks like STEP format."""
        try:
            text = content.decode('utf-8', errors='ignore')
            return 'ISO-10303' in text or 'HEADER;' in text
        except:
            return False
    
    @staticmethod
    def _validate_iges_content(content):
        """Check if content looks like IGES format."""
        try:
            text = content.decode('utf-8', errors='ignore')
            # IGES files have 'S' markers in first column
            return text.startswith('S') or 'IGES' in text[:100]
        except:
            return False
    
    @staticmethod
    def _validate_stl_content(content):
        """Check if content looks like STL format."""
        try:
            # ASCII STL starts with 'solid'
            text = content.decode('utf-8', errors='ignore')
            if text.strip().startswith('solid'):
                return True
            
            # Binary STL has specific header structure
            if len(content) >= 84:
                return True
        except:
            pass
        return False
    
    def __eq__(self, other):
        return (
            isinstance(other, CADFileValidator) and
            self.formats == other.formats
        )


# ============================================================================
# STRING VALIDATORS
# ============================================================================

@deconstructible
class PartNumberValidator(RegexValidator):
    """Validate part number format (alphanumeric with hyphens/underscores)."""
    
    regex = r'^[A-Z0-9][A-Z0-9_-]*[A-Z0-9]$'
    message = 'Part number must contain only uppercase letters, numbers, hyphens, and underscores. Must start and end with alphanumeric character.'
    flags = 0


@deconstructible
class RevisionValidator(RegexValidator):
    """Validate revision format (letters or alphanumeric)."""
    
    regex = r'^[A-Z]$|^[A-Z0-9]{1,10}$'
    message = 'Revision must be a single uppercase letter or alphanumeric string (max 10 characters).'
    flags = 0


@deconstructible
class SlugValidator(RegexValidator):
    """Validate URL-safe slug format."""
    
    regex = r'^[a-z0-9]+(?:-[a-z0-9]+)*$'
    message = 'Slug must contain only lowercase letters, numbers, and hyphens. Cannot start or end with hyphen.'
    flags = 0


@deconstructible
class AlphanumericValidator(RegexValidator):
    """Validate alphanumeric strings."""
    
    regex = r'^[a-zA-Z0-9]+$'
    message = 'Value must contain only letters and numbers.'
    flags = 0


# ============================================================================
# NUMERIC VALIDATORS
# ============================================================================

@deconstructible
class PositiveNumberValidator:
    """Validate positive number (greater than zero)."""
    
    def __call__(self, value):
        if value is not None and value <= 0:
            raise ValidationError('Value must be positive (greater than 0).')
    
    def __eq__(self, other):
        return isinstance(other, PositiveNumberValidator)


@deconstructible
class NonNegativeNumberValidator:
    """Validate non-negative number (greater than or equal to zero)."""
    
    def __call__(self, value):
        if value is not None and value < 0:
            raise ValidationError('Value must be non-negative (>= 0).')
    
    def __eq__(self, other):
        return isinstance(other, NonNegativeNumberValidator)


@deconstructible
class RangeValidator:
    """Validate numeric value within range."""
    
    def __init__(self, min_value=None, max_value=None, inclusive=True):
        self.min_value = min_value
        self.max_value = max_value
        self.inclusive = inclusive
    
    def __call__(self, value):
        if value is None:
            return
        
        if self.min_value is not None:
            if self.inclusive and value < self.min_value:
                raise ValidationError(f'Value must be >= {self.min_value}')
            elif not self.inclusive and value <= self.min_value:
                raise ValidationError(f'Value must be > {self.min_value}')
        
        if self.max_value is not None:
            if self.inclusive and value > self.max_value:
                raise ValidationError(f'Value must be <= {self.max_value}')
            elif not self.inclusive and value >= self.max_value:
                raise ValidationError(f'Value must be < {self.max_value}')
    
    def __eq__(self, other):
        return (
            isinstance(other, RangeValidator) and
            self.min_value == other.min_value and
            self.max_value == other.max_value and
            self.inclusive == other.inclusive
        )


# ============================================================================
# BUSINESS RULE VALIDATORS
# ============================================================================

@deconstructible
class ITARComplianceValidator:
    """Validate ITAR compliance requirements."""
    
    def __init__(self, user_field='uploaded_by'):
        self.user_field = user_field
    
    def __call__(self, value):
        """
        Validate ITAR classification against user clearance.
        
        Args:
            value: Dictionary with 'classification' and user object
        """
        if not isinstance(value, dict):
            return
        
        classification = value.get('classification')
        user = value.get(self.user_field)
        
        if classification == 'ITAR' and user and not getattr(user, 'is_us_person', True):
            raise ValidationError(
                'You do not have clearance to work with ITAR-controlled designs. '
                'Only US persons can access ITAR data.'
            )
    
    def __eq__(self, other):
        return (
            isinstance(other, ITARComplianceValidator) and
            self.user_field == other.user_field
        )


@deconstructible
class OrganizationQuotaValidator:
    """Validate organization quota limits."""
    
    def __init__(self, quota_type='storage'):
        self.quota_type = quota_type
    
    def __call__(self, value):
        """
        Validate organization hasn't exceeded quota.
        
        Args:
            value: Organization object
        """
        if self.quota_type == 'storage':
            if hasattr(value, 'is_at_storage_limit') and value.is_at_storage_limit():
                raise ValidationError(
                    f'Organization has reached storage limit ({value.max_storage_gb}GB). '
                    'Please upgrade your plan or delete old files.'
                )
        
        elif self.quota_type == 'users':
            if hasattr(value, 'is_at_user_limit') and value.is_at_user_limit():
                raise ValidationError(
                    f'Organization has reached user limit ({value.max_users}). '
                    'Please upgrade your plan.'
                )
    
    def __eq__(self, other):
        return (
            isinstance(other, OrganizationQuotaValidator) and
            self.quota_type == other.quota_type
        )


@deconstructible
class UniqueVersionValidator:
    """Validate version number is unique within series."""
    
    def __call__(self, value):
        """
        Validate version number uniqueness.
        
        Args:
            value: Dictionary with 'series' and 'version_number'
        """
        if not isinstance(value, dict):
            return
        
        series = value.get('series')
        version_number = value.get('version_number')
        instance_id = value.get('id')
        
        if not series or not version_number:
            return
        
        from designs.models import DesignAsset
        
        query = DesignAsset.objects.filter(
            series=series,
            version_number=version_number
        )
        
        # Exclude current instance when updating
        if instance_id:
            query = query.exclude(id=instance_id)
        
        if query.exists():
            raise ValidationError(
                f'Version {version_number} already exists for this design series. '
                'Please use a different version number.'
            )
    
    def __eq__(self, other):
        return isinstance(other, UniqueVersionValidator)


# ============================================================================
# GEOMETRY VALIDATORS
# ============================================================================

@deconstructible
class GeometryValidator:
    """Validate 3D geometry properties."""
    
    def __init__(self, check_manifold=True, check_watertight=True, min_volume=0):
        self.check_manifold = check_manifold
        self.check_watertight = check_watertight
        self.min_volume = min_volume
    
    def __call__(self, value):
        """
        Validate geometry properties.
        
        Args:
            value: Dictionary with geometry metadata
        """
        if not isinstance(value, dict):
            return
        
        errors = []
        
        if self.check_manifold and not value.get('is_manifold', True):
            errors.append('Geometry is not manifold (has non-manifold edges/vertices)')
        
        if self.check_watertight and not value.get('is_watertight', True):
            errors.append('Geometry is not watertight (has holes or gaps)')
        
        volume = value.get('volume', 0)
        if volume < self.min_volume:
            errors.append(f'Volume {volume} is below minimum {self.min_volume}')
        
        if errors:
            raise ValidationError('; '.join(errors))
    
    def __eq__(self, other):
        return (
            isinstance(other, GeometryValidator) and
            self.check_manifold == other.check_manifold and
            self.check_watertight == other.check_watertight and
            self.min_volume == other.min_volume
        )


# ============================================================================
# COLLECTION VALIDATORS
# ============================================================================

@deconstructible
class MaxLengthListValidator:
    """Validate maximum length of list/array."""
    
    def __init__(self, max_length):
        self.max_length = max_length
    
    def __call__(self, value):
        if value and len(value) > self.max_length:
            raise ValidationError(
                f'List exceeds maximum length of {self.max_length} items.'
            )
    
    def __eq__(self, other):
        return (
            isinstance(other, MaxLengthListValidator) and
            self.max_length == other.max_length
        )


@deconstructible
class MinLengthListValidator:
    """Validate minimum length of list/array."""
    
    def __init__(self, min_length):
        self.min_length = min_length
    
    def __call__(self, value):
        if value is not None and len(value) < self.min_length:
            raise ValidationError(
                f'List must contain at least {self.min_length} items.'
            )
    
    def __eq__(self, other):
        return (
            isinstance(other, MinLengthListValidator) and
            self.min_length == other.min_length
        )


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def validate_file_hash(file_obj, expected_hash, algorithm='sha256'):
    """
    Validate file integrity using hash comparison.
    
    Args:
        file_obj: File object to validate
        expected_hash: Expected hash value
        algorithm: Hash algorithm (sha256, md5, etc.)
    
    Raises:
        ValidationError: If hash doesn't match
    """
    import hashlib
    
    hasher = hashlib.new(algorithm)
    
    for chunk in file_obj.chunks():
        hasher.update(chunk)
    
    calculated_hash = hasher.hexdigest()
    
    if calculated_hash != expected_hash:
        raise ValidationError(
            f'File integrity check failed. Expected {expected_hash}, got {calculated_hash}'
        )
    
    file_obj.seek(0)


def validate_json_schema(data, schema):
    """
    Validate JSON data against schema.
    
    Args:
        data: JSON data to validate
        schema: JSON schema definition
    
    Raises:
        ValidationError: If data doesn't match schema
    """
    try:
        import jsonschema
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as e:
        raise ValidationError(f'JSON schema validation failed: {str(e)}')
    except ImportError:
        # jsonschema not installed, skip validation
        pass
