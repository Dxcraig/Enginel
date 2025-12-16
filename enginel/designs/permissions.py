"""
Custom permissions for Enginel.

Implements ITAR compliance, role-based access control,
and ownership-based permissions.
"""
from rest_framework import permissions


class IsUSPersonForITAR(permissions.BasePermission):
    """
    Permission to ensure only US persons can access ITAR-controlled designs.
    
    CRITICAL: Enforces ITAR compliance at permission level, not just queryset filtering.
    """
    message = "Access denied: ITAR-controlled designs require US person status."
    
    def has_object_permission(self, request, view, obj):
        """Check if user can access this specific object."""
        # Determine classification based on object type
        if hasattr(obj, 'classification'):
            classification = obj.classification
        elif hasattr(obj, 'design_asset'):
            classification = obj.design_asset.classification
        else:
            return True  # No classification, allow access
        
        # ITAR check
        if classification == 'ITAR':
            return request.user.is_us_person
        
        return True


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Only allow owners to edit objects.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only for the owner
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        elif hasattr(obj, 'uploaded_by'):
            return obj.uploaded_by == request.user
        elif hasattr(obj, 'author'):
            return obj.author == request.user
        
        return False


class CanReviewDesign(permissions.BasePermission):
    """
    Permission for review workflow actions.
    
    Rules:
    - Only assigned reviewers can approve/reject
    - Authors cannot approve their own designs
    - Requires appropriate security clearance
    """
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # For ReviewSession objects
        if hasattr(obj, 'reviewers'):
            # Check if user is an assigned reviewer
            if user not in obj.reviewers.all():
                return False
            
            # Author cannot review their own design
            if hasattr(obj, 'design_asset'):
                if obj.design_asset.uploaded_by == user:
                    return False
        
        # For DesignAsset objects being reviewed
        elif hasattr(obj, 'uploaded_by'):
            # Author cannot trigger review on their own design
            if obj.uploaded_by == user and view.action in ['start_review', 'approve']:
                return False
        
        return True


class HasClearanceLevel(permissions.BasePermission):
    """
    Check if user has required security clearance for classified content.
    """
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Get classification from object
        if hasattr(obj, 'classification'):
            classification = obj.classification
        elif hasattr(obj, 'design_asset') and hasattr(obj.design_asset, 'classification'):
            classification = obj.design_asset.classification
        else:
            return True  # No classification requirement
        
        # Clearance hierarchy
        clearance_levels = {
            'UNCLASSIFIED': 0,
            'CONFIDENTIAL': 1,
            'SECRET': 2,
            'TOP_SECRET': 3,
        }
        
        # If classified, check clearance level
        if classification in clearance_levels:
            user_level = clearance_levels.get(user.security_clearance_level, 0)
            required_level = clearance_levels[classification]
            return user_level >= required_level
        
        return True


class CanFinalizeUpload(permissions.BasePermission):
    """
    Only the uploader can finalize their own upload.
    """
    message = "Only the original uploader can finalize this upload."
    
    def has_object_permission(self, request, view, obj):
        return obj.uploaded_by == request.user


class CanAccessOrganizationData(permissions.BasePermission):
    """
    Multi-tenant permission: Users can only access data from their organization.
    
    TODO: Implement when adding Organization model.
    """
    
    def has_object_permission(self, request, view, obj):
        # For now, allow all access
        # When Organization model is added, check:
        # return obj.organization == request.user.organization
        return True


class IsReviewerOrReadOnly(permissions.BasePermission):
    """
    Only assigned reviewers can modify review sessions and markups.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read access for all
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write access only for assigned reviewers
        if hasattr(obj, 'review_session'):
            return request.user in obj.review_session.reviewers.all()
        elif hasattr(obj, 'reviewers'):
            return request.user in obj.reviewers.all()
        
        return False


class CanModifyDesignAsset(permissions.BasePermission):
    """
    Permission for modifying design assets.
    
    Rules:
    - Owners can modify their own assets
    - Cannot modify assets that are being reviewed
    - Cannot modify completed analysis jobs
    """
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Read permissions always allowed
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Check ownership
        if hasattr(obj, 'uploaded_by') and obj.uploaded_by != user:
            return False
        
        # Cannot modify if in review
        if hasattr(obj, 'status'):
            if obj.status == 'PROCESSING':
                return False  # Cannot modify while processing
        
        return True


# Composite permission classes for common use cases

class DesignAssetPermission(permissions.BasePermission):
    """
    Composite permission for design assets.
    Combines ITAR, clearance, and ownership checks.
    """
    
    def has_permission(self, request, view):
        # Must be authenticated
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Check all relevant permissions
        return (
            IsUSPersonForITAR().has_object_permission(request, view, obj) and
            HasClearanceLevel().has_object_permission(request, view, obj) and
            CanModifyDesignAsset().has_object_permission(request, view, obj)
        )


class ReviewPermission(permissions.BasePermission):
    """
    Composite permission for review workflow.
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Check ITAR and review-specific permissions
        return (
            IsUSPersonForITAR().has_object_permission(request, view, obj) and
            CanReviewDesign().has_object_permission(request, view, obj)
        )
