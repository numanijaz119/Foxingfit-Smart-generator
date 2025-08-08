from django.contrib import admin
from .models import WorkoutScript, WorkoutTemplate, MotivationalQuote, ScriptCategory

@admin.register(ScriptCategory)
class ScriptCategoryAdmin(admin.ModelAdmin):
    """
    Johnny can manage script categories himself
    """
    list_display = ['display_name', 'training_type', 'name', 'is_active']
    list_filter = ['training_type', 'is_active']
    search_fields = ['display_name', 'name', 'description']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('display_name', 'training_type', 'name')
        }),
        ('Details', {
            'fields': ('description', 'is_active')
        }),
    )

@admin.register(WorkoutScript)
class WorkoutScriptAdmin(admin.ModelAdmin):
    list_display = ['title', 'type', 'script_category', 'goal', 'duration_minutes', 'times_selected', 'is_active']
    list_filter = ['type', 'script_category__training_type', 'goal', 'language', 'is_active']
    search_fields = ['title', 'content']
    readonly_fields = ['times_selected', 'last_selected', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'type', 'script_category', 'goal', 'language')
        }),
        ('Content', {
            'fields': ('content', 'duration_minutes')
        }),
        ('System', {
            'fields': ('is_active', 'notes'),
        }),
        ('Engine Stats', {
            'fields': ('times_selected', 'last_selected'),
            'classes': ('collapse',)
        }),
    )
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter script categories by training type"""
        if db_field.name == "script_category":
            kwargs["queryset"] = ScriptCategory.objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(MotivationalQuote)
class MotivationalQuoteAdmin(admin.ModelAdmin):
    """
    Johnny's motivational quotes management
    """
    list_display = ['training_type', 'quote_preview', 'context', 'times_used', 'is_active']
    list_filter = ['training_type', 'context', 'language', 'is_active']
    search_fields = ['quote_text']
    
    fieldsets = (
        ('Quote Information', {
            'fields': ('training_type', 'quote_text', 'context', 'language')
        }),
        ('System', {
            'fields': ('is_active', 'times_used', 'last_used'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['times_used', 'last_used']
    
    def quote_preview(self, obj):
        return obj.quote_text[:50] + "..." if len(obj.quote_text) > 50 else obj.quote_text
    quote_preview.short_description = 'Quote Preview'

@admin.register(WorkoutTemplate)
class WorkoutTemplateAdmin(admin.ModelAdmin):
    """
    Johnny's flexible workout templates with OR logic
    """
    list_display = ['training_type', 'sequence_order', 'primary_category', 'alternatives_preview', 'is_required']
    list_filter = ['training_type', 'is_required']
    ordering = ['training_type', 'sequence_order']
    
    filter_horizontal = ['alternative_categories']  # Nice interface for many-to-many
    
    def alternatives_preview(self, obj):
        alternatives = obj.alternative_categories.all()[:3]
        alt_names = [alt.display_name for alt in alternatives]
        preview = ", ".join(alt_names)
        if obj.alternative_categories.count() > 3:
            preview += f" (+{obj.alternative_categories.count() - 3} more)"
        return preview or "None"
    alternatives_preview.short_description = 'Alternatives'
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter categories by training type"""
        if db_field.name == "primary_category":
            kwargs["queryset"] = ScriptCategory.objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """Filter alternative categories by training type"""
        if db_field.name == "alternative_categories":
            kwargs["queryset"] = ScriptCategory.objects.filter(is_active=True)
        return super().formfield_for_manytomany(db_field, request, **kwargs)
