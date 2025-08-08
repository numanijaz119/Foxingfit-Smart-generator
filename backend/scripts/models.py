from django.db import models
from django.utils import timezone

class ScriptCategory(models.Model):
    """
    Dynamic script categories that Johnny can manage himself
    This allows him to add new sections.
    """
    TRAINING_TYPES = [
        ('kickboxing', 'Kickboxing Heavybag'),
        ('power_yoga', 'Power Yoga'),
        ('calisthenics', 'Calisthenics'),
    ]
    
    # Core fields
    name = models.CharField(max_length=50, help_text="Internal name (e.g., 'kb_footwork')")
    display_name = models.CharField(max_length=100, help_text="Display name (e.g., 'Footwork Training')")
    training_type = models.CharField(max_length=15, choices=TRAINING_TYPES)
    
    # user customization
    description = models.TextField(blank=True, help_text="What this section is for")
    is_active = models.BooleanField(default=True)
    
    # System fields
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['name', 'training_type']
        ordering = ['training_type', 'display_name']
        verbose_name = "Script Category"
        verbose_name_plural = "Script Categories"
    
    def __str__(self):
        return f"{self.get_training_type_display()} - {self.display_name}"

class WorkoutScript(models.Model):
    
    TRAINING_TYPES = [
        ('kickboxing', 'Kickboxing Heavybag'),
        ('power_yoga', 'Power Yoga'),
        ('calisthenics', 'Calisthenics'),
    ]
    
    GOALS = [
        ('allround', 'All-round'),
        ('endurance', 'Endurance'),
        ('strength', 'Strength'),
        ('flexibility', 'Flexibility'),
        ('technique', 'Technique'),
    ]
    
    # Languages (future expansion)
    LANGUAGES = [
        ('nl', 'Dutch'),
        ('en', 'English'),
    ]
    
    # Core fields
    title = models.CharField(max_length=200)
    type = models.CharField(max_length=15, choices=TRAINING_TYPES, db_index=True)
    script_category = models.ForeignKey(ScriptCategory, on_delete=models.CASCADE, db_index=True)
    goal = models.CharField(max_length=15, choices=GOALS, db_index=True)
    
    # Content
    content = models.TextField(help_text="Script content with [pause strong]/[pause weak] markers")
    
    # Duration (user exact format: "8:30 min")
    duration_minutes = models.FloatField(help_text="Duration when spoken (e.g., 8.5 for 8:30)")
    
    # Language support (future feature)
    language = models.CharField(max_length=2, choices=LANGUAGES, default='nl')
    
    # Engine efficiency tracking 
    times_selected = models.IntegerField(default=0, help_text="For engine variety logic")
    last_selected = models.DateTimeField(null=True, blank=True)
    
    # System fields
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Admin notes (not user-facing)
    notes = models.TextField(blank=True, help_text="Admin notes for Johnny")
    
    class Meta:
        ordering = ['type', 'script_category__display_name', 'title']
        indexes = [
            models.Index(fields=['type', 'script_category', 'goal']),
            models.Index(fields=['times_selected', 'last_selected']),  # For engine efficiency
        ]
        verbose_name = "Workout Script"
        verbose_name_plural = "Workout Scripts"
    
    def mark_selected(self):
        """Track selection for engine efficiency (not user analytics)"""
        self.times_selected += 1
        self.last_selected = timezone.now()
        self.save(update_fields=['times_selected', 'last_selected'])
    
    def get_freshness_score(self):
        """Engine efficiency: prefer blocks not used recently"""
        if not self.last_selected:
            return 1.0  # Never used = most fresh
        
        days_since = (timezone.now() - self.last_selected).days
        if days_since >= 14:
            return 1.0
        elif days_since >= 7:
            return 0.8
        elif days_since >= 3:
            return 0.6
        else:
            return 0.3  # Recently used = less fresh
    
    def __str__(self):
        return f"{self.get_type_display()} - {self.title}"

class MotivationalQuote(models.Model):
    TRAINING_TYPES = WorkoutScript.TRAINING_TYPES
    
    USAGE_CONTEXT = [
        ('warmup', 'During Warm-up'),
        ('intense', 'High Intensity Moments'),
        ('transition', 'Between Workout Parts'),
        ('cooldown', 'Cool Down'),
        ('anytime', 'Any Time'),
    ]
    
    # Basic fields
    training_type = models.CharField(max_length=15, choices=TRAINING_TYPES)
    quote_text = models.TextField(help_text="The content inside [...] brackets (without 'Remember, ')")
    context = models.CharField(max_length=15, choices=USAGE_CONTEXT, default='anytime')
    language = models.CharField(max_length=2, choices=WorkoutScript.LANGUAGES, default='nl')
    
    # Simple usage tracking for variety
    times_used = models.IntegerField(default=0)
    last_used = models.DateTimeField(null=True, blank=True)
    
    # System fields
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['training_type', 'context']
        verbose_name = "Motivational Quote"
        verbose_name_plural = "Motivational Quotes"
    
    def mark_used(self):
        """Track usage for variety in quote selection"""
        self.times_used += 1
        self.last_used = timezone.now()
        self.save(update_fields=['times_used', 'last_used'])
    
    def get_formatted_quote(self):
        """Returns the quote in user format: Remember, [quote_text]"""
        return f"Remember, [{self.quote_text}]"
    
    def __str__(self):
        return f"{self.get_training_type_display()} - {self.quote_text[:50]}..."

class WorkoutTemplate(models.Model):
    """
    user flexible workout structure rules
    Supports OR logic: "combo building OR just combos"
    """
    training_type = models.CharField(max_length=15, choices=WorkoutScript.TRAINING_TYPES)
    sequence_order = models.IntegerField()
    primary_category = models.ForeignKey(ScriptCategory, on_delete=models.CASCADE, related_name='primary_templates')
    
    # OR logic
    alternative_categories = models.ManyToManyField(
        ScriptCategory, 
        blank=True, 
        related_name='alternative_templates',
        help_text="Alternative categories for OR logic (e.g., 'just combos' as alternative to 'combo building')"
    )
    
    # Logic rules
    is_required = models.BooleanField(default=True, help_text="Must be included in every workout")
    
    # time flexibility
    min_duration = models.FloatField(null=True, blank=True)
    max_duration = models.FloatField(null=True, blank=True)
    preferred_duration = models.FloatField(null=True, blank=True, help_text="Ideal duration for this part")
    
    class Meta:
        unique_together = ['training_type', 'sequence_order']
        ordering = ['training_type', 'sequence_order']
        verbose_name = "Workout Template"
        verbose_name_plural = "Workout Templates"
    
    def get_all_possible_categories(self):
        """Get primary category + all alternatives"""
        categories = [self.primary_category]
        categories.extend(self.alternative_categories.all())
        return categories
    
    def __str__(self):
        alternatives = list(self.alternative_categories.values_list('display_name', flat=True))
        alt_text = f" OR {', '.join(alternatives)}" if alternatives else ""
        return f"{self.get_training_type_display()} - Step {self.sequence_order}: {self.primary_category.display_name}{alt_text}"