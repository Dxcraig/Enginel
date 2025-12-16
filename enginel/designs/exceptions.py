"""
Custom exception classes for Enginel.

Provides domain-specific exceptions with detailed error messages
and appropriate HTTP status codes for API responses.
"""
from rest_framework.exceptions import APIException
from rest_framework import status


class EnginelBaseException(APIException):
    """Base exception for all Enginel-specific errors."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = 'An internal error occurred.'
    default_code = 'enginel_error'


class GeometryProcessingError(EnginelBaseException):
    """Raised when CAD file geometry extraction fails."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = 'Failed to process geometry from CAD file.'
    default_code = 'geometry_processing_error'


class FileValidationError(EnginelBaseException):
    """Raised when uploaded file fails validation."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'File validation failed.'
    default_code = 'file_validation_error'


class OrganizationLimitExceeded(EnginelBaseException):
    """Raised when organization exceeds resource limits."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'Organization resource limit exceeded.'
    default_code = 'organization_limit_exceeded'


class InsufficientPermissions(EnginelBaseException):
    """Raised when user lacks required organization role."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'Insufficient permissions for this operation.'
    default_code = 'insufficient_permissions'


class ITARViolation(EnginelBaseException):
    """Raised when ITAR compliance rules are violated."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'ITAR compliance violation: Access denied.'
    default_code = 'itar_violation'


class ClearanceLevelInsufficient(EnginelBaseException):
    """Raised when user security clearance is insufficient."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'Insufficient security clearance level.'
    default_code = 'clearance_insufficient'


class UnitConversionError(EnginelBaseException):
    """Raised when unit conversion fails."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = 'Unit conversion failed.'
    default_code = 'unit_conversion_error'


class BOMExtractionError(EnginelBaseException):
    """Raised when BOM extraction from assembly fails."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = 'Failed to extract Bill of Materials.'
    default_code = 'bom_extraction_error'


class StorageQuotaExceeded(EnginelBaseException):
    """Raised when organization storage quota is exceeded."""
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    default_detail = 'Organization storage quota exceeded.'
    default_code = 'storage_quota_exceeded'


class UserLimitExceeded(EnginelBaseException):
    """Raised when organization user limit is exceeded."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'Organization user limit exceeded.'
    default_code = 'user_limit_exceeded'


class DesignNotReady(EnginelBaseException):
    """Raised when attempting to access a design that's still processing."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'Design is still processing.'
    default_code = 'design_not_ready'


class DuplicatePartNumber(EnginelBaseException):
    """Raised when part number already exists in organization."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'Part number already exists in this organization.'
    default_code = 'duplicate_part_number'


class TaskTimeoutError(EnginelBaseException):
    """Raised when Celery task exceeds timeout."""
    status_code = status.HTTP_504_GATEWAY_TIMEOUT
    default_detail = 'Background task timed out.'
    default_code = 'task_timeout'


class ExternalServiceError(EnginelBaseException):
    """Raised when external service (S3, etc.) fails."""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'External service unavailable.'
    default_code = 'external_service_error'


class InvalidFileFormat(FileValidationError):
    """Raised when file format is not supported."""
    default_detail = 'Unsupported file format. Only STEP and IGES files are allowed.'
    default_code = 'invalid_file_format'


class FileSizeExceeded(FileValidationError):
    """Raised when file size exceeds limit."""
    default_detail = 'File size exceeds maximum allowed limit.'
    default_code = 'file_size_exceeded'


class CorruptedFile(FileValidationError):
    """Raised when file appears to be corrupted."""
    default_detail = 'File appears to be corrupted or incomplete.'
    default_code = 'corrupted_file'


def raise_geometry_error(message: str, original_exception: Exception = None):
    """
    Helper to raise geometry processing error with context.
    
    Args:
        message: Error description
        original_exception: Original exception that caused the error
    """
    if original_exception:
        detail = f"{message}: {str(original_exception)}"
    else:
        detail = message
    raise GeometryProcessingError(detail=detail)


def raise_validation_error(message: str, field: str = None):
    """
    Helper to raise validation error with field context.
    
    Args:
        message: Error description
        field: Field name that failed validation
    """
    if field:
        detail = f"{field}: {message}"
    else:
        detail = message
    raise FileValidationError(detail=detail)


def raise_permission_error(required_role: str = None, current_role: str = None):
    """
    Helper to raise permission error with role context.
    
    Args:
        required_role: Role required for operation
        current_role: User's current role
    """
    if required_role and current_role:
        detail = f"Operation requires {required_role} role, but user has {current_role} role."
    else:
        detail = "Insufficient permissions for this operation."
    raise InsufficientPermissions(detail=detail)
