from django.contrib import admin
from .models import WorkoutScript, WorkoutTemplate, MotivationalQuote, ScriptCategory

@admin.register(ScriptCategory)
class ScriptCategoryAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'training_type', 'difficulty_level', 'must_be_last', 'is_active']
    list_filter = ['training_type', 'difficulty_level', 'must_be_last', 'is_active']
    search_fields = ['display_name', 'name', 'description']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('display_name', 'training_type', 'name', 'description'),
            'description': 'What this workout section is called and what it\'s for.'
        }),
        ('Smart Settings', {
            'fields': ('difficulty_level', 'must_be_last'),
            'description': 'Settings that help the system organize workouts intelligently.'
        }),
        ('Management', {
            'fields': ('is_active',),
            'description': 'Control whether this section appears in the system.'
        }),
    )

@admin.register(WorkoutScript)
class WorkoutScriptAdmin(admin.ModelAdmin):
    list_display = ['title', 'type', 'script_category', 'goal', 'duration_minutes', 'times_selected', 'is_active']
    list_filter = ['type', 'script_category__training_type', 'goal', 'intensity_level', 'is_active']
    search_fields = ['title', 'content']
    readonly_fields = ['times_selected', 'last_selected', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'type', 'script_category', 'goal', 'language'),
            'description': 'Essential details about this workout script.'
        }),
        ('Content & Timing', {
            'fields': ('content', 'duration_minutes'),
            'description': 'The actual script text and how long it takes to speak.'
        }),
        ('Smart Features', {
            'fields': ('intensity_level', 'transition_type'),
            'description': 'Settings that help the system use this script intelligently.'
        }),
        ('Management', {
            'fields': ('is_active', 'notes'),
            'description': 'Control this script and add your personal notes.'
        }),
        ('Automatic Tracking', {
            'fields': ('times_selected', 'last_selected'),
            'classes': ('collapse',),
            'description': 'Usage statistics tracked automatically for variety.'
        }),
    )

@admin.register(MotivationalQuote)
class MotivationalQuoteAdmin(admin.ModelAdmin):
    list_display = ['quote_preview', 'training_type', 'target_category_display', 'is_exercise_specific', 'times_used', 'is_active']
    list_filter = ['training_type', 'is_exercise_specific', 'target_category__training_type', 'is_active']
    search_fields = ['quote_text']
    readonly_fields = ['times_used', 'last_used', 'is_exercise_specific']
    
    fieldsets = (
        ('Quote Content', {
            'fields': ('training_type', 'quote_text', 'language'),
            'description': 'The motivational quote and what sport it\'s for.'
        }),
        ('Exercise Targeting', {
            'fields': ('target_category',),
            'description': 'Link to specific exercise (leave blank for general quotes).'
        }),
        ('Management', {
            'fields': ('is_active',),
            'description': 'Quote settings and status.'
        }),
        ('Automatic Tracking', {
            'fields': ('is_exercise_specific', 'times_used', 'last_used'),
            'classes': ('collapse',),
            'description': 'System-managed fields (read-only).'
        }),
    )
    
    def quote_preview(self, obj):
        return obj.quote_text[:50] + "..." if len(obj.quote_text) > 50 else obj.quote_text
    quote_preview.short_description = 'Quote Preview'
    
    def target_category_display(self, obj):
        return obj.target_category.display_name if obj.target_category else "General"
    target_category_display.short_description = 'Target Exercise'
    
    def get_form(self, request, obj=None, **kwargs):
        """Filter target_category choices based on training_type"""
        form = super().get_form(request, obj, **kwargs)
        if 'target_category' in form.base_fields:
            if obj:  # Editing existing quote
                form.base_fields['target_category'].queryset = ScriptCategory.objects.filter(
                    training_type=obj.training_type,
                    is_active=True
                ).order_by('display_name')
            else:  # Creating new quote
                form.base_fields['target_category'].queryset = ScriptCategory.objects.filter(
                    is_active=True
                ).order_by('training_type', 'display_name')
        return form

@admin.register(WorkoutTemplate)
class WorkoutTemplateAdmin(admin.ModelAdmin):
    list_display = ['training_type', 'sequence_order', 'primary_category', 'alternatives_preview', 'requires_surprise_round', 'requires_transition', 'is_required']
    list_filter = ['training_type', 'requires_surprise_round', 'requires_transition', 'is_required']
    ordering = ['training_type', 'sequence_order']
    
    filter_horizontal = ['alternative_categories']
    
    fieldsets = (
        ('Workout Structure', {
            'fields': ('training_type', 'sequence_order', 'primary_category', 'alternative_categories', 'is_required'),
            'description': 'Define the basic structure of workouts for this sport.'
        }),
        ('Smart Automation', {
            'fields': ('requires_surprise_round', 'requires_transition', 'transition_script_category', 'sequence_priority'),
            'description': 'Automatic features that will be applied during workout generation.'
        }),
        ('Time Management', {
            'fields': ('min_duration', 'max_duration', 'preferred_duration'),
            'classes': ('collapse',),
            'description': 'Time constraints for this workout section.'
        }),
    )
    
    def alternatives_preview(self, obj):
        alternatives = obj.alternative_categories.all()[:3]
        alt_names = [alt.display_name for alt in alternatives]
        preview = ", ".join(alt_names)
        if obj.alternative_categories.count() > 3:
            preview += f" (+{obj.alternative_categories.count() - 3} more)"
        return preview or "None"
    alternatives_preview.short_description = 'Alternative Options'