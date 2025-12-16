"""
Audit logging utilities for Enginel.

Provides helpers and decorators for CMMC-compliant audit trails.
"""
from functools import wraps
from django.utils import timezone
from .models import AuditLog


def get_client_ip(request):
    """Extract client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_audit_event(user, action, resource_type, resource_id, request=None, changes=None):
    """
    Create an audit log entry.
    
    Args:
        user: Django User object who performed the action
        action: One of CREATE, READ, UPDATE, DELETE, DOWNLOAD, UPLOAD
        resource_type: Model name (e.g., 'DesignAsset', 'ReviewSession')
        resource_id: UUID of the resource
        request: HttpRequest object (optional, for IP/user agent)
        changes: Dict with before/after values for updates (optional)
    
    Returns:
        AuditLog instance
    """
    audit_data = {
        'actor_id': user.id,
        'actor_username': user.username,
        'action': action,
        'resource_type': resource_type,
        'resource_id': resource_id,
        'changes': changes or {},
    }
    
    if request:
        audit_data['ip_address'] = get_client_ip(request)
        audit_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
    
    return AuditLog.objects.create(**audit_data)


def audit_action(action, resource_type_attr='__class__.__name__', resource_id_attr='id'):
    """
    Decorator to automatically log audit events for view methods.
    
    Usage:
        @audit_action('DOWNLOAD', resource_type_attr='__class__.__name__')
        def download_file(self, request, pk=None):
            ...
    
    Args:
        action: Audit action type (CREATE, READ, UPDATE, DELETE, DOWNLOAD, UPLOAD)
        resource_type_attr: Attribute path to get resource type (default: model class name)
        resource_id_attr: Attribute path to get resource ID (default: 'id')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            # Execute the view
            response = view_func(self, request, *args, **kwargs)
            
            # Log audit event if successful (2xx status code)
            if hasattr(response, 'status_code') and 200 <= response.status_code < 300:
                try:
                    # Get the resource instance
                    resource = self.get_object() if hasattr(self, 'get_object') else None
                    
                    if resource:
                        # Extract resource type
                        if resource_type_attr == '__class__.__name__':
                            resource_type = resource.__class__.__name__
                        else:
                            resource_type = getattr(resource, resource_type_attr)
                        
                        # Extract resource ID
                        resource_id = getattr(resource, resource_id_attr)
                        
                        # Create audit log
                        log_audit_event(
                            user=request.user,
                            action=action,
                            resource_type=resource_type,
                            resource_id=resource_id,
                            request=request
                        )
                except Exception as e:
                    # Don't fail the request if audit logging fails
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to create audit log: {e}")
            
            return response
        return wrapper
    return decorator


def track_model_changes(instance, old_values, new_values, user, request=None):
    """
    Track changes to model fields for UPDATE audit logs.
    
    Args:
        instance: Model instance being updated
        old_values: Dict of field names to old values
        new_values: Dict of field names to new values
        user: User performing the update
        request: HttpRequest (optional)
    
    Returns:
        AuditLog instance
    """
    changes = {
        'before': old_values,
        'after': new_values,
        'changed_fields': [k for k in old_values if old_values[k] != new_values.get(k)]
    }
    
    return log_audit_event(
        user=user,
        action='UPDATE',
        resource_type=instance.__class__.__name__,
        resource_id=instance.id,
        request=request,
        changes=changes
    )


class AuditLogMixin:
    """
    Mixin for ViewSets to automatically log CREATE/UPDATE/DELETE operations.
    
    Usage:
        class MyViewSet(AuditLogMixin, viewsets.ModelViewSet):
            audit_resource_type = 'MyModel'  # Optional, defaults to model name
    """
    
    def perform_create(self, serializer):
        """Override to log CREATE operations."""
        instance = serializer.save()
        
        # Log creation
        try:
            resource_type = getattr(self, 'audit_resource_type', instance.__class__.__name__)
            log_audit_event(
                user=self.request.user,
                action='CREATE',
                resource_type=resource_type,
                resource_id=instance.id,
                request=self.request,
                changes={'created_fields': list(serializer.validated_data.keys())}
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to create audit log for CREATE: {e}")
        
        return instance
    
    def perform_update(self, serializer):
        """Override to log UPDATE operations."""
        # Capture old values
        instance = serializer.instance
        old_values = {}
        for field in serializer.validated_data.keys():
            old_values[field] = str(getattr(instance, field, None))
        
        # Perform update
        instance = serializer.save()
        
        # Capture new values
        new_values = {}
        for field in serializer.validated_data.keys():
            new_values[field] = str(getattr(instance, field, None))
        
        # Log update
        try:
            track_model_changes(instance, old_values, new_values, self.request.user, self.request)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to create audit log for UPDATE: {e}")
        
        return instance
    
    def perform_destroy(self, instance):
        """Override to log DELETE operations."""
        resource_type = getattr(self, 'audit_resource_type', instance.__class__.__name__)
        resource_id = instance.id
        
        # Capture snapshot before deletion
        snapshot = {}
        for field in instance._meta.fields:
            snapshot[field.name] = str(getattr(instance, field.name, None))
        
        # Perform deletion
        instance.delete()
        
        # Log deletion
        try:
            log_audit_event(
                user=self.request.user,
                action='DELETE',
                resource_type=resource_type,
                resource_id=resource_id,
                request=self.request,
                changes={'deleted_snapshot': snapshot}
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to create audit log for DELETE: {e}")
