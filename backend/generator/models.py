from django.db import models
from scripts.models import WorkoutScript

class WorkoutSession(models.Model):
    """
    Generated workout sessions with flexible timing
    """
    training_type = models.CharField(max_length=15, choices=WorkoutScript.TRAINING_TYPES)
    title = models.CharField(max_length=200)
    total_duration = models.FloatField()
    target_duration = models.FloatField(default=60.0)  # Johnny's target (60 min)
    time_flexibility = models.FloatField(default=5.0)  # Johnny's ±5 min flexibility
    goal = models.CharField(max_length=15, choices=WorkoutScript.GOALS)
    
    # Generated content
    compiled_script = models.TextField(help_text="Final compiled script with motivational quotes")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    is_used = models.BooleanField(default=False, help_text="Did Johnny use this workout?")
    notes = models.TextField(blank=True, help_text="Johnny's notes about this workout")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Workout Session"
        verbose_name_plural = "Workout Sessions"
    
    def get_time_status(self):
        """Get time status description"""
        min_duration = self.target_duration - self.time_flexibility
        max_duration = self.target_duration + self.time_flexibility
        
        if self.total_duration < min_duration:
            return f"Short ({self.total_duration:.1f} min - target {self.target_duration:.0f}±{self.time_flexibility:.0f})"
        elif self.total_duration > max_duration:
            return f"Long ({self.total_duration:.1f} min - target {self.target_duration:.0f}±{self.time_flexibility:.0f})"
        else:
            return f"Perfect ({self.total_duration:.1f} min)"
    
    def __str__(self):
        return f"{self.get_training_type_display()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

class SessionScript(models.Model):
    """
    Individual scripts in a generated workout session
    """
    workout_session = models.ForeignKey(WorkoutSession, on_delete=models.CASCADE, related_name='session_scripts')
    workout_script = models.ForeignKey(WorkoutScript, on_delete=models.CASCADE)
    sequence_order = models.IntegerField()
    
    class Meta:
        ordering = ['sequence_order']
        verbose_name = "Session Script"
        verbose_name_plural = "Session Scripts"