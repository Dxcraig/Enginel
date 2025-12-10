from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, DesignAsset, AssemblyNode


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Admin interface for CustomUser with compliance fields."""
    
    list_display = [
        'username', 
        'email', 
        'is_us_person', 
        'security_clearance_level', 
        'organization',
        'is_staff'
    ]
    
    list_filter = [
        'is_us_person', 
        'security_clearance_level', 
        'is_staff', 
        'is_active'
    ]
    
    search_fields = ['username', 'email', 'organization']
    
    # Add our custom fields to the edit form
    fieldsets = UserAdmin.fieldsets + (
        ('Compliance & Security', {
            'fields': (
                'is_us_person', 
                'security_clearance_level', 
                'organization', 
                'phone_number'
            )
        }),
    )
    
    # Add our custom fields to the add user form
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Compliance & Security', {
            'fields': (
                'is_us_person', 
                'security_clearance_level', 
                'organization', 
                'phone_number'
            )
        }),
    )


@admin.register(DesignAsset)
class DesignAssetAdmin(admin.ModelAdmin):
    """Admin interface for DesignAsset with filtering and search."""
    
    list_display = [
        'filename', 
        'part_number', 
        'classification', 
        'status', 
        'created_by', 
        'created_at'
    ]
    
    list_filter = [
        'classification', 
        'status', 
        'is_valid_geometry',
        'created_at'
    ]
    
    search_fields = [
        'filename', 
        'part_number', 
        'description',
        's3_key'
    ]
    
    readonly_fields = [
        'id', 
        'created_at', 
        'updated_at', 
        'file_hash'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'filename', 
                'part_number', 
                'revision', 
                'description',
                'tags'
            )
        }),
        ('File Details', {
            'fields': (
                's3_key', 
                'file_size', 
                'file_hash',
                'units'
            )
        }),
        ('Classification & Ownership', {
            'fields': (
                'classification', 
                'created_by'
            )
        }),
        ('Processing Status', {
            'fields': (
                'status', 
                'processing_error', 
                'is_valid_geometry'
            )
        }),
        ('Extracted Data', {
            'fields': (
                'metadata', 
                'validation_report'
            ),
            'classes': ('collapse',)  # Collapsed by default
        }),
        ('Timestamps', {
            'fields': (
                'id',
                'created_at', 
                'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    # Custom action to mark designs as completed
    actions = ['mark_as_completed']
    
    def mark_as_completed(self, request, queryset):
        """Admin action to manually mark designs as completed."""
        updated = queryset.update(status='COMPLETED')
        self.message_user(request, f'{updated} design(s) marked as completed.')
    mark_as_completed.short_description = 'Mark selected as COMPLETED'


@admin.register(AssemblyNode)
class AssemblyNodeAdmin(admin.ModelAdmin):
    """Admin interface for BOM tree nodes."""
    
    list_display = [
        'name', 
        'part_number', 
        'node_type', 
        'quantity', 
        'design_asset',
        'depth'
    ]
    
    list_filter = [
        'node_type', 
        'design_asset'
    ]
    
    search_fields = [
        'name', 
        'part_number',
        'reference_designator'
    ]
    
    readonly_fields = [
        'path', 
        'depth', 
        'numchild'
    ]
    
    fieldsets = (
        ('BOM Information', {
            'fields': (
                'design_asset',
                'name', 
                'part_number', 
                'node_type',
                'quantity',
                'reference_designator'
            )
        }),
        ('Physical Properties', {
            'fields': (
                'mass', 
                'volume'
            )
        }),
        ('Tree Structure (Read-Only)', {
            'fields': (
                'path', 
                'depth', 
                'numchild'
            ),
            'classes': ('collapse',)
        }),
        ('Additional Data', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )


# Note: LogEntry (AuditLog) is automatically registered by django-auditlog
# No need to manually register it here