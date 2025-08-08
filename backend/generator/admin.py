from django.contrib import admin
from .models import WorkoutSession, SessionScript

class SessionScriptInline(admin.TabularInline):
    model = SessionScript
    extra = 0
    readonly_fields = ['workout_script', 'sequence_order']

@admin.register(WorkoutSession)
class WorkoutSessionAdmin(admin.ModelAdmin):
    list_display = ['title', 'training_type', 'goal', 'total_duration', 'time_status', 'created_at']
    list_filter = ['training_type', 'goal', 'created_at']
    search_fields = ['title']
    readonly_fields = ['created_at', 'time_status']
    inlines = [SessionScriptInline]
    
    def time_status(self, obj):
        return obj.get_time_status()
    time_status.short_description = 'Time Status'