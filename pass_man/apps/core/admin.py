"""
Admin configuration for the core app.

This module contains Django admin customizations for core models
and shared admin functionality.

Related Documentation:
- CODING_STANDARDS.md: Django Best Practices
"""

from django.contrib import admin


class BaseModelAdmin(admin.ModelAdmin):
    """
    Base admin class for models that inherit from BaseModel.
    
    Provides common functionality for all model admins including:
    - Read-only fields for timestamps and IDs
    - Soft delete handling
    - Common list display and filters
    """
    
    readonly_fields = ('id', 'created_at', 'updated_at', 'deleted_at')
    list_filter = ('created_at', 'updated_at', 'is_deleted')
    list_display = ('id', 'created_at', 'updated_at', 'is_deleted')
    
    def get_queryset(self, request):
        """Include soft-deleted records in admin."""
        return self.model._default_manager.get_queryset()
    
    def has_delete_permission(self, request, obj=None):
        """Allow delete permission for soft delete."""
        return True
    
    def delete_model(self, request, obj):
        """Perform soft delete instead of hard delete."""
        obj.soft_delete()
    
    def delete_queryset(self, request, queryset):
        """Perform soft delete on queryset."""
        for obj in queryset:
            obj.soft_delete()


# Register any core models here if needed
# admin.site.register(YourModel, BaseModelAdmin)