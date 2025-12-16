"""
Input validators for Enginel security.

Provides comprehensive validation for:
- User inputs (usernames, emails, etc.)
- File uploads
- API parameters
- URL paths
- JSON payloads
"""

import re
import json
from django.core.validators import RegexValidator, URLValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


# Username validator
username_validator = RegexValidator(
    regex=r'^[a-zA-Z0-9_-]{3,30}$',
    message=_(
        'Username must be 3-30 characters and contain only letters, '
        'numbers, hyphens, and underscores.'
    ),
    code='invalid_username'
)


# Part number validator (alphanumeric with hyphens)
part_number_validator = RegexValidator(
    regex=r'^[A-Z0-9-]{3,50}$',
    message=_(
        'Part number must be 3-50 characters and contain only uppercase letters, '
        'numbers, and hyphens.'
    ),
    code='invalid_part_number'
)


# Revision validator
revision_validator = RegexValidator(
    regex=r'^[A-Za-z0-9.-]{1,20}$',
    message=_(
        'Revision must be 1-20 characters and contain only letters, '
        'numbers, dots, and hyphens.'
    ),
    code='invalid_revision'
)


# Organization slug validator
slug_validator = RegexValidator(
    regex=r'^[a-z0-9-]{3,50}$',
    message=_(
        'Slug must be 3-50 characters and contain only lowercase letters, '
        'numbers, and hyphens.'
    ),
    code='invalid_slug'
)


def validate_no_sql_injection(value):
    """
    Validate that input doesn't contain SQL injection patterns.
    
    Args:
        value: Input to validate
    
    Raises:
        ValidationError: If SQL injection pattern detected
    """
    if not isinstance(value, str):
        return
    
    # SQL keywords that shouldn't appear in normal input
    dangerous_patterns = [
        r'\bUNION\b.*\bSELECT\b',
        r'\bDROP\b.*\bTABLE\b',
        r'\bINSERT\b.*\bINTO\b',
        r'\bDELETE\b.*\bFROM\b',
        r'\bUPDATE\b.*\bSET\b',
        r"'.*OR.*'.*=.*'",
        r'--',
        r'\/\*',
        r'\*\/',
    ]
    
    value_upper = value.upper()
    for pattern in dangerous_patterns:
        if re.search(pattern, value_upper, re.IGNORECASE):
            raise ValidationError(
                _('Input contains invalid characters or patterns.'),
                code='sql_injection'
            )


def validate_no_xss(value):
    """
    Validate that input doesn't contain XSS attack patterns.
    
    Args:
        value: Input to validate
    
    Raises:
        ValidationError: If XSS pattern detected
    """
    if not isinstance(value, str):
        return
    
    dangerous_patterns = [
        r'<script[^>]*>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe[^>]*>',
        r'<object[^>]*>',
        r'<embed[^>]*>',
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, value, re.IGNORECASE):
            raise ValidationError(
                _('Input contains potentially dangerous content.'),
                code='xss_attempt'
            )


def validate_no_path_traversal(value):
    """
    Validate that input doesn't contain path traversal patterns.
    
    Args:
        value: Input to validate
    
    Raises:
        ValidationError: If path traversal pattern detected
    """
    if not isinstance(value, str):
        return
    
    dangerous_patterns = [
        r'\.\.',
        r'%2e%2e',
        r'\.\./',
        r'\.\.\\',
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, value, re.IGNORECASE):
            raise ValidationError(
                _('Input contains invalid path characters.'),
                code='path_traversal'
            )


def validate_filename(value):
    """
    Validate filename for security.
    
    Args:
        value: Filename to validate
    
    Raises:
        ValidationError: If filename is invalid
    """
    if not value or not isinstance(value, str):
        raise ValidationError(_('Filename is required.'), code='required')
    
    # Check length
    if len(value) > 255:
        raise ValidationError(
            _('Filename is too long (maximum 255 characters).'),
            code='max_length'
        )
    
    # Check for path traversal
    if '..' in value or '/' in value or '\\' in value:
        raise ValidationError(
            _('Filename contains invalid characters.'),
            code='invalid_chars'
        )
    
    # Check for null bytes
    if '\x00' in value:
        raise ValidationError(
            _('Filename contains null bytes.'),
            code='null_bytes'
        )
    
    # Check for control characters
    if any(ord(c) < 32 for c in value):
        raise ValidationError(
            _('Filename contains control characters.'),
            code='control_chars'
        )
    
    # Validate extension exists
    if '.' not in value:
        raise ValidationError(
            _('Filename must have an extension.'),
            code='no_extension'
        )


def validate_cad_file_extension(value):
    """
    Validate CAD file extension.
    
    Args:
        value: Filename to validate
    
    Raises:
        ValidationError: If extension is not allowed
    """
    allowed_extensions = [
        '.step', '.stp',  # STEP files
        '.iges', '.igs',  # IGES files
        '.stl',           # STL files
        '.obj',           # OBJ files
        '.dxf',           # DXF files
        '.dwg',           # DWG files
    ]
    
    if not value or not isinstance(value, str):
        raise ValidationError(_('Filename is required.'), code='required')
    
    ext = '.' + value.lower().split('.')[-1]
    
    if ext not in allowed_extensions:
        raise ValidationError(
            _(f'File type not allowed. Allowed types: {", ".join(allowed_extensions)}'),
            code='invalid_extension'
        )


def validate_file_size(file_obj, max_size_mb=500):
    """
    Validate file size.
    
    Args:
        file_obj: File object to validate
        max_size_mb: Maximum size in MB
    
    Raises:
        ValidationError: If file is too large
    """
    if not hasattr(file_obj, 'size'):
        return
    
    max_size_bytes = max_size_mb * 1024 * 1024
    
    if file_obj.size > max_size_bytes:
        raise ValidationError(
            _(f'File size exceeds {max_size_mb}MB limit.'),
            code='file_too_large'
        )


def validate_json_structure(value, required_fields=None):
    """
    Validate JSON structure.
    
    Args:
        value: JSON string or dict to validate
        required_fields: List of required field names
    
    Raises:
        ValidationError: If JSON is invalid
    """
    # Parse if string
    if isinstance(value, str):
        try:
            data = json.loads(value)
        except json.JSONDecodeError as e:
            raise ValidationError(
                _(f'Invalid JSON: {str(e)}'),
                code='invalid_json'
            )
    elif isinstance(value, dict):
        data = value
    else:
        raise ValidationError(
            _('Value must be JSON string or dictionary.'),
            code='invalid_type'
        )
    
    # Check required fields
    if required_fields:
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise ValidationError(
                _(f'Missing required fields: {", ".join(missing_fields)}'),
                code='missing_fields'
            )


def validate_email_domain(value, allowed_domains=None, blocked_domains=None):
    """
    Validate email domain.
    
    Args:
        value: Email address to validate
        allowed_domains: List of allowed domains (whitelist)
        blocked_domains: List of blocked domains (blacklist)
    
    Raises:
        ValidationError: If domain is not allowed or is blocked
    """
    if not value or '@' not in value:
        raise ValidationError(_('Invalid email address.'), code='invalid_email')
    
    domain = value.split('@')[1].lower()
    
    # Check whitelist
    if allowed_domains and domain not in allowed_domains:
        raise ValidationError(
            _(f'Email domain not allowed. Allowed domains: {", ".join(allowed_domains)}'),
            code='domain_not_allowed'
        )
    
    # Check blacklist
    if blocked_domains and domain in blocked_domains:
        raise ValidationError(
            _('Email domain is blocked.'),
            code='domain_blocked'
        )


def validate_ip_address(value):
    """
    Validate IP address format (IPv4 or IPv6).
    
    Args:
        value: IP address string
    
    Raises:
        ValidationError: If IP address is invalid
    """
    import ipaddress
    
    try:
        ipaddress.ip_address(value)
    except ValueError:
        raise ValidationError(
            _('Invalid IP address format.'),
            code='invalid_ip'
        )


def validate_classification_level(value):
    """
    Validate security classification level.
    
    Args:
        value: Classification level
    
    Raises:
        ValidationError: If classification is invalid
    """
    valid_levels = ['UNCLASSIFIED', 'CUI', 'CONFIDENTIAL', 'SECRET', 'TOP_SECRET']
    
    if value not in valid_levels:
        raise ValidationError(
            _(f'Invalid classification level. Valid levels: {", ".join(valid_levels)}'),
            code='invalid_classification'
        )


def validate_itar_controlled(value, user):
    """
    Validate ITAR access for user.
    
    Args:
        value: Boolean indicating if item is ITAR controlled
        user: User requesting access
    
    Raises:
        ValidationError: If user doesn't have ITAR clearance
    """
    if value and not getattr(user, 'has_itar_clearance', False):
        raise ValidationError(
            _('You do not have ITAR clearance to access this item.'),
            code='itar_clearance_required'
        )


def validate_organization_quota(organization, file_size_bytes):
    """
    Validate organization storage quota.
    
    Args:
        organization: Organization object
        file_size_bytes: Size of file to upload in bytes
    
    Raises:
        ValidationError: If quota would be exceeded
    """
    current_usage_gb = organization.get_storage_used_gb()
    max_storage_gb = organization.max_storage_gb
    
    new_usage_gb = current_usage_gb + (file_size_bytes / (1024 ** 3))
    
    if new_usage_gb > max_storage_gb:
        raise ValidationError(
            _(f'Storage quota exceeded. Current: {current_usage_gb:.2f}GB, '
              f'Max: {max_storage_gb}GB'),
            code='quota_exceeded'
        )


def validate_api_rate_limit(user, endpoint, max_requests=100, window_seconds=3600):
    """
    Validate API rate limit for user/endpoint.
    
    Args:
        user: User making the request
        endpoint: API endpoint being called
        max_requests: Maximum requests allowed
        window_seconds: Time window in seconds
    
    Raises:
        ValidationError: If rate limit exceeded
    """
    from django.core.cache import cache
    import time
    
    cache_key = f'rate_limit_{user.id}_{endpoint}'
    requests = cache.get(cache_key, [])
    now = time.time()
    
    # Remove old requests
    requests = [ts for ts in requests if now - ts < window_seconds]
    
    if len(requests) >= max_requests:
        raise ValidationError(
            _(f'Rate limit exceeded. Maximum {max_requests} requests per {window_seconds} seconds.'),
            code='rate_limit_exceeded'
        )
    
    # Add current request
    requests.append(now)
    cache.set(cache_key, requests, window_seconds)


class SecureInputValidator:
    """
    Comprehensive input validator combining multiple checks.
    """
    
    @staticmethod
    def validate_user_input(value, field_name='input'):
        """
        Validate general user input.
        
        Args:
            value: Input to validate
            field_name: Field name for error messages
        
        Raises:
            ValidationError: If input is invalid
        """
        if not value:
            return  # Allow empty values (use required=True in serializer)
        
        # Check for security issues
        validate_no_sql_injection(value)
        validate_no_xss(value)
        validate_no_path_traversal(value)
        
        # Check length
        if len(str(value)) > 10000:
            raise ValidationError(
                _(f'{field_name} is too long (maximum 10000 characters).'),
                code='max_length'
            )
    
    @staticmethod
    def validate_file_upload(file_obj, allowed_extensions=None):
        """
        Validate file upload comprehensively.
        
        Args:
            file_obj: File object to validate
            allowed_extensions: List of allowed extensions
        
        Raises:
            ValidationError: If file is invalid
        """
        # Validate filename
        validate_filename(file_obj.name)
        
        # Validate size
        validate_file_size(file_obj)
        
        # Validate extension
        if allowed_extensions:
            ext = '.' + file_obj.name.lower().split('.')[-1]
            if ext not in allowed_extensions:
                raise ValidationError(
                    _(f'File type not allowed. Allowed types: {", ".join(allowed_extensions)}'),
                    code='invalid_extension'
                )
        
        # Check for null bytes in file content (first 1KB)
        file_obj.seek(0)
        sample = file_obj.read(1024)
        if b'\x00' in sample:
            file_obj.seek(0)
            raise ValidationError(
                _('File contains invalid content.'),
                code='invalid_content'
            )
        file_obj.seek(0)
    
    @staticmethod
    def validate_metadata(metadata):
        """
        Validate metadata dictionary.
        
        Args:
            metadata: Metadata dict to validate
        
        Raises:
            ValidationError: If metadata is invalid
        """
        if not isinstance(metadata, dict):
            raise ValidationError(
                _('Metadata must be a dictionary.'),
                code='invalid_type'
            )
        
        # Check size
        metadata_str = json.dumps(metadata)
        if len(metadata_str) > 50000:  # 50KB limit
            raise ValidationError(
                _('Metadata is too large (maximum 50KB).'),
                code='metadata_too_large'
            )
        
        # Validate each value
        for key, value in metadata.items():
            if isinstance(value, str):
                SecureInputValidator.validate_user_input(value, field_name=f'metadata.{key}')
