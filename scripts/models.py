from django.db import models
from django.utils import timezone
import re

class ScriptCategory(models.Model):
    """
    Dynamic script categories with sport-specific intelligence
    
    Developer Notes:
    - This model stores the different types of workout sections (warmup, combos, etc.)
    - Each category has sport-specific metadata for intelligent workout generation
    - The sport_specific_rules field allows flexible rule storage for future enhancements
    """
    TRAINING_TYPES = [
        ('kickboxing', 'Kickboxing Heavybag'),
        ('power_yoga', 'Power Yoga'),
        ('calisthenics', 'Calisthenics'),
    ]
    
    DIFFICULTY_LEVELS = [
        (1, 'Beginner'),
        (2, 'Intermediate'),
        (3, 'Advanced'),
    ]
    
    # Core identification fields
    name = models.CharField(
        max_length=50, 
        help_text="System name - don't change this once created"
    )
    display_name = models.CharField(
        max_length=100, 
        help_text="The name you see in workouts (e.g., 'Footwork Training')"
    )
    training_type = models.CharField(max_length=15, choices=TRAINING_TYPES)
    description = models.TextField(
        blank=True, 
        help_text="What this section is for - helps you organize your content"
    )
    
    # SPORT-SPECIFIC LOGIC FIELDS - These enable automatic sport intelligence
    difficulty_level = models.IntegerField(
        choices=DIFFICULTY_LEVELS, 
        default=1,
        help_text="How hard this section is - helps order exercises properly"
    )
    must_be_last = models.BooleanField(
        default=False,
        help_text="Always put this at the end (like MAX Challenge)"
    )
    sport_specific_rules = models.JSONField(
        default=dict,
        blank=True,
        help_text="Special rules for this category - usually left empty"
    )
    
    # System tracking fields
    is_active = models.BooleanField(
        default=True,
        help_text="Turn off to hide this category without deleting it"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['name', 'training_type']
        ordering = ['training_type', 'difficulty_level', 'display_name']
        verbose_name = "Script Category"
        verbose_name_plural = "Script Categories"
    
    # SPORT-SPECIFIC HELPER METHODS - These enable intelligent rule detection
    def is_advanced_movement(self):
        """Check if this is an advanced calisthenics movement requiring prerequisites"""
        advanced_movements = ['back_lever', 'front_lever', 'planche', 'handstand']
        return any(move in self.name.lower() for move in advanced_movements)
    
    def requires_surprise_round(self):
        """
        Check if this kickboxing category should get a surprise round after it
        Used by KickboxingGeneratorMixin to auto-insert surprise rounds
        """
        if self.training_type != 'kickboxing':
            return False
        
        # No surprise rounds for gentle sections
        no_surprise = ['warmup', 'cooldown', 'stretch']
        if any(term in self.name.lower() for term in no_surprise):
            return False
            
        return True  # All other kickboxing categories get surprise rounds
    
    def __str__(self):
        return f"{self.get_training_type_display()} - {self.display_name}"

class WorkoutScript(models.Model):
    """
    Johnny's individual workout scripts with enhanced metadata for sport intelligence
    
    Developer Notes:
    - These are the actual spoken content pieces that make up workouts
    - Enhanced with sport-specific metadata for intelligent selection and ordering
    - Auto-cleans titles on save to remove round numbers
    - Tracks usage for variety in selection algorithm
    """
    
    TRAINING_TYPES = ScriptCategory.TRAINING_TYPES
    
    GOALS = [
        ('allround', 'All-round'),
        ('endurance', 'Endurance'),
        ('strength', 'Strength'),
        ('flexibility', 'Flexibility'),
        ('technique', 'Technique'),
    ]
    
    LANGUAGES = [
        ('nl', 'Dutch'),
        ('en', 'English'),
    ]
    
    INTENSITY_LEVELS = [
        (1, 'Low'),
        (2, 'Medium'),
        (3, 'High'),
    ]
    
    TRANSITION_TYPES = [
        ('standing_to_standing', 'Standing to Standing'),
        ('standing_to_sitting', 'Standing to Sitting'),
        ('sitting_to_standing', 'Sitting to Standing'),
        ('flow_transition', 'General Flow'),
        ('none', 'No Transition'),
    ]
    
    # Core content fields
    title = models.CharField(
        max_length=200,
        help_text="Name for this script - 'Round 1:' will be removed automatically"
    )
    type = models.CharField(
        max_length=15, 
        choices=TRAINING_TYPES, 
        db_index=True,
        help_text="Which sport this script is for"
    )
    script_category = models.ForeignKey(
        ScriptCategory, 
        on_delete=models.CASCADE, 
        db_index=True,
        help_text="What type of exercise this is (warmup, combos, etc.)"
    )
    goal = models.CharField(
        max_length=15, 
        choices=GOALS, 
        db_index=True,
        help_text="What fitness goal this targets"
    )
    
    # Main content and timing
    content = models.TextField(
        help_text="The actual script text with [pause strong]/[pause weak] markers"
    )
    duration_minutes = models.FloatField(
        help_text="How long this takes to speak (from murf.ai timing)"
    )
    
    # SPORT-SPECIFIC METADATA - These fields enable intelligent sport logic
    intensity_level = models.IntegerField(
        choices=INTENSITY_LEVELS,
        default=2,
        help_text="How intense this script is - helps with flow decisions"
    )
    transition_type = models.CharField(
        max_length=20,
        choices=TRANSITION_TYPES,
        default='none',
        help_text="What kind of position change this provides (for yoga)"
    )
    
    # Language and localization
    language = models.CharField(
        max_length=2, 
        choices=LANGUAGES, 
        default='nl',
        help_text="Language for this script"
    )
    
    # USAGE TRACKING - These fields power the variety algorithm
    times_selected = models.IntegerField(
        default=0,
        help_text="How often this was used - system tracks automatically"
    )
    last_selected = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When this was last used - system tracks automatically"
    )
    
    # Management fields
    is_active = models.BooleanField(
        default=True,
        help_text="Turn off to hide this script without deleting it"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(
        blank=True, 
        help_text="Your personal notes about this script"
    )
    
    class Meta:
        ordering = ['type', 'script_category__display_name', 'title']
        indexes = [
            models.Index(fields=['type', 'script_category', 'goal']),
            models.Index(fields=['times_selected', 'last_selected']),
            models.Index(fields=['intensity_level', 'transition_type']),
        ]
        verbose_name = "Workout Script"
        verbose_name_plural = "Workout Scripts"
    
    def clean_title(self):
        """
        Remove round numbers from title during save
        Auto-cleans "Round 1:" or "Ronde 2:" prefixes from imported titles
        """
        self.title = re.sub(r'^(Round|Ronde)\s+\d+:\s*', '', self.title, flags=re.IGNORECASE).strip()
    
    def save(self, *args, **kwargs):
        """Override save to auto-clean titles"""
        self.clean_title()  # Always clean titles on save
        super().save(*args, **kwargs)
    
    # USAGE TRACKING METHODS - These power the variety and freshness system
    def mark_selected(self):
        """Track selection for engine efficiency and variety"""
        self.times_selected += 1
        self.last_selected = timezone.now()
        self.save(update_fields=['times_selected', 'last_selected'])
    
    def get_freshness_score(self):
        """
        Calculate freshness score for variety algorithm
        Returns 0.3-1.0 score, higher = fresher (less recently used)
        """
        if not self.last_selected:
            return 1.0  # Never used = most fresh
        
        days_since = (timezone.now() - self.last_selected).days
        if days_since >= 14:
            return 1.0      # Very fresh
        elif days_since >= 7:
            return 0.8      # Fresh
        elif days_since >= 3:
            return 0.6      # Somewhat fresh
        else:
            return 0.3      # Recently used = less fresh
    
    # SPORT-SPECIFIC DETECTION METHODS - Enable sport logic identification
    def is_surprise_round(self):
        """Check if this is a surprise round script for kickboxing"""
        return 'surprise' in self.script_category.name.lower()
    
    def is_vinyasa_transition(self):
        """Check if this is a vinyasa transition script for power yoga"""
        return 'vinyasa' in self.script_category.name.lower()
    
    def __str__(self):
        return f"{self.get_type_display()} - {self.title}"

class MotivationalQuote(models.Model):
    """
    Johnny's "Onthoud..." motivational quotes system
    
    Developer Notes:
    - These are the green text motivational insertions
    - Auto-formatted with "Onthoud, [quote_text]" pattern
    - Usage tracking prevents repetition within sessions
    """
    
    TRAINING_TYPES = WorkoutScript.TRAINING_TYPES
    
    USAGE_CONTEXT = [
        ('warmup', 'During Warm-up'),
        ('intense', 'High Intensity Moments'),
        ('transition', 'Between Workout Parts'),
        ('cooldown', 'Cool Down'),
        ('anytime', 'Any Time'),
    ]
    
    # Core quote fields
    training_type = models.CharField(
        max_length=15, 
        choices=TRAINING_TYPES,
        help_text="Which sport this motivational quote is for"
    )
    quote_text = models.TextField(
        help_text="The motivational text - 'Onthoud,' will be added automatically"
    )
    context = models.CharField(
        max_length=15, 
        choices=USAGE_CONTEXT, 
        default='anytime',
        help_text="When to use this quote during workouts"
    )
    language = models.CharField(
        max_length=2, 
        choices=WorkoutScript.LANGUAGES, 
        default='nl',
        help_text="Language for this quote"
    )
    
    # USAGE TRACKING - Prevents quote repetition and ensures variety
    times_used = models.IntegerField(
        default=0,
        help_text="How often this quote was used - system tracks automatically"
    )
    last_used = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When this quote was last used - system tracks automatically"
    )
    
    # Management
    is_active = models.BooleanField(
        default=True,
        help_text="Turn off to hide this quote without deleting it"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['training_type', 'context']
        verbose_name = "Motivational Quote"
        verbose_name_plural = "Motivational Quotes"
    
    # USAGE TRACKING METHODS - Power the quote variety system
    def mark_used(self):
        """Track usage for variety in quote selection"""
        self.times_used += 1
        self.last_used = timezone.now()
        self.save(update_fields=['times_used', 'last_used'])
    
    def get_formatted_quote(self):
        """Returns the quote in Johnny's standard format"""
        return f"Onthoud, [{self.quote_text}]"
    
    def __str__(self):
        return f"{self.get_training_type_display()} - {self.quote_text[:50]}..."

class WorkoutTemplate(models.Model):
    """
    Johnny's flexible workout structure rules with sport-specific logic
    
    Developer Notes:
    - Defines the order and rules for workout generation
    - Supports OR logic through alternative_categories
    - Contains sport-specific automation rules for surprise rounds, vinyasa, etc.
    - Powers the intelligent workout generation algorithm
    """
    
    # Core template structure
    training_type = models.CharField(
        max_length=15, 
        choices=WorkoutScript.TRAINING_TYPES,
        help_text="Which sport this template is for"
    )
    sequence_order = models.IntegerField(
        help_text="Order in workout (1 = first, 2 = second, etc.)"
    )
    primary_category = models.ForeignKey(
        ScriptCategory, 
        on_delete=models.CASCADE, 
        related_name='primary_templates',
        help_text="Main type of exercise for this step"
    )
    
    # OR LOGIC SUPPORT - Enables flexible "A OR B OR C" workout structures
    alternative_categories = models.ManyToManyField(
        ScriptCategory, 
        blank=True, 
        related_name='alternative_templates',
        help_text="Other exercise types that can be used instead (creates choice)"
    )
    
    # Basic generation rules
    is_required = models.BooleanField(
        default=True,
        help_text="Must be included in every workout (turn off for optional sections)"
    )
    
    # SPORT-SPECIFIC AUTOMATION RULES - These power the sport intelligence
    requires_surprise_round = models.BooleanField(
        default=False,
        help_text="Add a surprise round after this section (kickboxing only)"
    )
    requires_transition = models.BooleanField(
        default=False,
        help_text="Check if transition needed after this section (yoga flow)"
    )
    transition_script_category = models.ForeignKey(
        ScriptCategory,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='transition_templates',
        help_text="Which transition type to use (for yoga vinyasa)"
    )
    sequence_priority = models.IntegerField(
        default=0,
        help_text="Force certain order despite sequence_order (higher = later)"
    )
    
    # TIME CONSTRAINTS - Enable time-aware generation
    min_duration = models.FloatField(
        null=True, 
        blank=True,
        help_text="Minimum time for this section in minutes"
    )
    max_duration = models.FloatField(
        null=True, 
        blank=True,
        help_text="Maximum time for this section in minutes"
    )
    preferred_duration = models.FloatField(
        null=True, 
        blank=True,
        help_text="Ideal time for this section in minutes"
    )
    
    class Meta:
        unique_together = ['training_type', 'sequence_order']
        ordering = ['training_type', 'sequence_order', 'sequence_priority']
        verbose_name = "Workout Template"
        verbose_name_plural = "Workout Templates"
    
    # TEMPLATE HELPER METHODS - Support the generation algorithm
    def get_all_possible_categories(self):
        """Get primary category + all alternatives for OR logic"""
        categories = [self.primary_category]
        categories.extend(self.alternative_categories.all())
        return categories
    
    def should_add_surprise_round(self):
        """
        Check if this template step should trigger surprise round addition
        Used by KickboxingGeneratorMixin for automatic surprise round insertion
        """
        return (self.training_type == 'kickboxing' and 
                self.requires_surprise_round and
                self.primary_category.requires_surprise_round())
    
    def __str__(self):
        alternatives = list(self.alternative_categories.values_list('display_name', flat=True))
        alt_text = f" OR {', '.join(alternatives)}" if alternatives else ""
        return f"{self.get_training_type_display()} - Step {self.sequence_order}: {self.primary_category.display_name}{alt_text}"