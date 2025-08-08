from django.contrib import admin
from django.utils.html import format_html
from .models import WorkoutSession, SessionScript

class SessionScriptInline(admin.TabularInline):
    model = SessionScript
    extra = 0
    readonly_fields = ['workout_script', 'sequence_order', 'is_sport_addition']

@admin.register(WorkoutSession)
class WorkoutSessionAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'training_type', 'goal', 'total_duration', 
        'time_status_display', 'script_count', 'sport_additions', 'created_at'
    ]
    list_filter = ['training_type', 'goal', 'is_used', 'created_at']
    search_fields = ['title', 'notes']
    readonly_fields = ['created_at', 'time_status', 'sport_logic_summary']
    inlines = [SessionScriptInline]
    
    fieldsets = (
        ('Workout Information', {
            'fields': ('title', 'training_type', 'goal', 'total_duration', 'time_status'),
            'description': 'Basic information about this generated workout.'
        }),
        ('Generation Settings', {
            'fields': ('target_duration', 'time_flexibility'),
            'description': 'Duration targets and flexibility settings used.'
        }),
        ('Smart Automation Applied', {
            'fields': ('sport_logic_summary', 'sport_additions_applied'),
            'classes': ('collapse',),
            'description': 'What smart features were automatically applied.'
        }),
        ('Generated Content', {
            'fields': ('compiled_script',),
            'classes': ('collapse',),
            'description': 'The complete generated workout script.'
        }),
        ('Your Usage', {
            'fields': ('is_used', 'notes'),
            'description': 'Track whether you\'ve used this workout and add notes.'
        }),
    )
    
    def time_status_display(self, obj):
        status = obj.get_time_status()
        if 'Perfect' in status:
            return format_html('<span style="color: green;">✅ {}</span>', status)
        elif 'Short' in status:
            return format_html('<span style="color: orange;">⚠️ {}</span>', status)
        elif 'Long' in status:
            return format_html('<span style="color: red;">❌ {}</span>', status)
        return status
    time_status_display.short_description = 'Time Status'
    
    def script_count(self, obj):
        return obj.session_scripts.count()
    script_count.short_description = 'Scripts'
    
    def sport_additions(self, obj):
        return obj.session_scripts.filter(is_sport_addition=True).count()
    sport_additions.short_description = 'Smart Additions'