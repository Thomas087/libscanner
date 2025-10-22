from django.contrib import admin
from django.utils.html import format_html
from .models import GovernmentDocument, NegativeKeyword


@admin.register(GovernmentDocument)
class GovernmentDocumentAdmin(admin.ModelAdmin):
    """Admin interface for GovernmentDocument model."""
    
    list_display = [
        'title_short', 
        'prefecture_name',
        'region_name',
        'date_updated', 
        'is_recent_display',
        'is_icpe_display',
        'link_display', 
        'created_at'
    ]
    
    list_filter = [
        'is_icpe',
        'prefecture_name',
        'region_name',
        'date_updated',
        'created_at',
        'updated_at',
    ]
    
    search_fields = [
        'title',
        'description',
        'link',
        'prefecture_name',
        'region_name',
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'link_display',
        'is_recent_display',
        'is_icpe_display',
    ]
    
    fieldsets = (
        ('Document Information', {
            'fields': ('title', 'description', 'link_display')
        }),
        ('Prefecture Information', {
            'fields': ('prefecture_name', 'prefecture_code', 'region_name')
        }),
        ('Dates', {
            'fields': ('date_updated', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_icpe', 'is_recent_display', 'is_icpe_display'),
            'classes': ('collapse',)
        }),
    )
    
    list_per_page = 25
    ordering = ['-date_updated']
    
    def title_short(self, obj):
        """Display truncated title for list view."""
        if len(obj.title) > 60:
            return f"{obj.title[:60]}..."
        return obj.title
    title_short.short_description = "Title"
    title_short.admin_order_field = "title"
    
    def link_display(self, obj):
        """Display link as clickable URL."""
        if obj.link:
            return format_html(
                '<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>',
                obj.link,
                "View Document"
            )
        return "No link"
    link_display.short_description = "Link"
    
    def is_recent_display(self, obj):
        """Display if document is recent with color coding."""
        is_recent = obj.is_recent()
        if is_recent:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Recent</span>'
            )
        else:
            return format_html(
                '<span style="color: orange;">Older</span>'
            )
    is_recent_display.short_description = "Recent"
    is_recent_display.admin_order_field = "date_updated"
    
    def is_icpe_display(self, obj):
        """Display ICPE status with color coding."""
        if obj.is_icpe:
            return format_html(
                '<span style="color: #d63384; font-weight: bold;">🔒 ICPE</span>'
            )
        else:
            return format_html(
                '<span style="color: #6c757d;">General</span>'
            )
    is_icpe_display.short_description = "ICPE Status"
    is_icpe_display.admin_order_field = "is_icpe"
    
    def get_queryset(self, request):
        """Optimize queryset for admin."""
        return super().get_queryset(request).select_related()
    
    def has_add_permission(self, request):
        """Allow adding documents manually."""
        return True
    
    def has_change_permission(self, request, obj=None):
        """Allow editing documents."""
        return True
    
    def has_delete_permission(self, request, obj=None):
        """Allow deleting documents."""
        return True


@admin.register(NegativeKeyword)
class NegativeKeywordAdmin(admin.ModelAdmin):
    """Admin interface for NegativeKeyword model."""
    
    list_display = [
        'keyword',
        'created_at',
        'updated_at'
    ]
    
    list_filter = [
        'created_at',
        'updated_at',
    ]
    
    search_fields = [
        'keyword',
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        ('Keyword Information', {
            'fields': ('keyword',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    list_per_page = 25
    ordering = ['keyword']
    
    def get_queryset(self, request):
        """Optimize queryset for admin."""
        return super().get_queryset(request)
    
    def has_add_permission(self, request):
        """Allow adding negative keywords manually."""
        return True
    
    def has_change_permission(self, request, obj=None):
        """Allow editing negative keywords."""
        return True
    
    def has_delete_permission(self, request, obj=None):
        """Allow deleting negative keywords."""
        return True
