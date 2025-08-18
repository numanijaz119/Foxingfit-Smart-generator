import random
from django.utils import timezone
from django.db.models import Avg, Q
from scripts.models import WorkoutScript, WorkoutTemplate, MotivationalQuote, ScriptCategory
from .models import WorkoutSession, SessionScript
from .quote_processor import QuoteProcessor
from .branding import FoxingFitBranding

class SportSpecificLogicMixin:
    """
    Base mixin providing sport-specific intelligence for workout generation
    
    Developer Notes:
    - This is the foundation class that routes sport-specific logic
    - Each sport has its own mixin that inherits from this
    - Provides common methods for special rounds and sport detection
    - Used by IntelligentWorkoutGenerator to apply sport-specific post-processing
    """
    
    def apply_sport_specific_intelligence(self, selected_scripts, training_type, goal):
        """
        Route to appropriate sport-specific logic based on training type
        This is the main entry point for sport-specific post-processing
        """
        if training_type == 'kickboxing':
            return self.apply_kickboxing_intelligence(selected_scripts, goal)
        elif training_type == 'power_yoga':
            return self.apply_power_yoga_intelligence(selected_scripts, goal)
        elif training_type == 'calisthenics':
            return self.apply_calisthenics_intelligence(selected_scripts, goal)
        
        return selected_scripts  # No sport-specific logic, return as-is
    
    def find_special_round_script(self, training_type, script_category):
        """
        Find a script for the special round category (surprise, MAX challenge, vinyasa)
        Powers the automatic special round insertion
        """
        if not script_category:
            return None
            
        special_scripts = WorkoutScript.objects.filter(
            type=training_type,
            script_category=script_category,
            is_active=True
        ).exclude(id__in=self.used_script_ids)
        
        if special_scripts.exists():
            # Use freshness algorithm to prefer unused special rounds
            special_scripts_list = list(special_scripts)
            special_scripts_list.sort(key=lambda s: s.get_freshness_score(), reverse=True)
            selected = special_scripts_list[0]
            selected.mark_selected()
            self.used_script_ids.add(selected.id)
            return selected
        
        return None
    
    def track_sport_addition(self, addition_type, count=1):
        """Track sport-specific additions for metadata"""
        if not hasattr(self, 'sport_additions'):
            self.sport_additions = {}
        
        if addition_type not in self.sport_additions:
            self.sport_additions[addition_type] = 0
        self.sport_additions[addition_type] += count

class KickboxingIntelligenceMixin(SportSpecificLogicMixin):
    """
    Kickboxing-specific logic: Automatic surprise round insertion based on ADMIN TEMPLATE CHOICES
    
    Developer Notes:
    - Implements Johnny's surprise round methodology
    - Respects admin template configuration (add_surprise_round_after=True)
    - No automatic guessing - admin has full control via templates
    - Uses the auto-detected kb_surprise category for content
    """
    
    def apply_kickboxing_intelligence(self, selected_scripts, goal):
        """
        Process selected scripts and add surprise rounds based on ADMIN TEMPLATE CONFIGURATION
        
        IMPORTANT: Surprise rounds are ONLY added where admin configured them in templates,
        not based on automatic category pattern detection. Admin has full control.
        """
        # Simply return scripts as-is since template processing already added
        # surprise rounds where admin specified via add_surprise_round_after=True
        return selected_scripts

class PowerYogaIntelligenceMixin(SportSpecificLogicMixin):
    """
    Power Yoga-specific logic: ADMIN-CONTROLLED vinyasa transitions
    
    Developer Notes:
    - Respects admin template configuration (add_vinyasa_transition_after=True)
    - No automatic detection - admin has full control via templates
    - Vinyasa transitions are added where admin specifies, not based on pose patterns
    """
    
    def apply_power_yoga_intelligence(self, selected_scripts, goal):
        """
        Process selected scripts respecting ADMIN TEMPLATE CONFIGURATION for vinyasa
        
        IMPORTANT: Vinyasa transitions are ONLY added where admin configured them in templates,
        not based on automatic pose sequence detection. Admin has full control.
        """
        # Simply return scripts as-is since template processing already added
        # vinyasa transitions where admin specified via add_vinyasa_transition_after=True
        return selected_scripts

class CalisthenicsIntelligenceMixin(SportSpecificLogicMixin):
    """
    Calisthenics-specific logic: ADMIN-CONTROLLED MAX challenge + logical exercise ordering
    
    Developer Notes:
    - Respects admin template configuration (add_max_challenge_after=True)
    - No automatic MAX challenge placement - admin has full control via templates
    - Maintains logical exercise ordering for safety (warmup first, etc.)
    """
    
    def apply_calisthenics_intelligence(self, selected_scripts, goal):
        """
        Apply calisthenics-specific ordering while respecting ADMIN TEMPLATE CONFIGURATION
        
        IMPORTANT: MAX challenge placement is ONLY done where admin configured it in templates,
        not automatically moved to end. Admin has full control over placement.
        """
        # Apply logical exercise ordering for safety (warmup first, basic before advanced)
        # But respect admin decisions about MAX challenge placement
        ordered_scripts = self.apply_logical_exercise_ordering(selected_scripts)
        
        # Track if any reordering was applied for analytics
        if len(ordered_scripts) != len(selected_scripts) or ordered_scripts != selected_scripts:
            self.track_sport_addition('difficulty_reordered')
        
        return ordered_scripts
    
    def apply_logical_exercise_ordering(self, scripts):
        """
        Apply logical ordering to calisthenics exercises for safety
        Warmup first, then basic exercises, then advanced exercises
        Does NOT move MAX challenge - respects admin placement
        """
        warmup_scripts = []
        basic_scripts = []
        advanced_scripts = []
        special_scripts = []  # Keep MAX challenge and other specials in original position
        
        for script in scripts:
            category_name = script.script_category.name.lower()
            
            if 'warmup' in category_name:
                warmup_scripts.append(script)
            elif script.is_max_challenge():
                # Keep MAX challenge in admin-specified position
                special_scripts.append((len(warmup_scripts + basic_scripts + advanced_scripts), script))
            elif any(advanced_term in category_name for advanced_term in 
                    ['handstand', 'lever', 'planche']):
                advanced_scripts.append(script)
            else:
                basic_scripts.append(script)
        
        # Combine in logical order, inserting special scripts at original positions
        ordered_base = warmup_scripts + basic_scripts + advanced_scripts
        
        # Insert special scripts back at their original relative positions
        for position, special_script in special_scripts:
            ordered_base.insert(min(position, len(ordered_base)), special_script)
        
        return ordered_base

class IntelligentWorkoutGenerator(
    KickboxingIntelligenceMixin,
    PowerYogaIntelligenceMixin, 
    CalisthenicsIntelligenceMixin
):
    """
    Johnny's intelligent workout generator with sport-specific logic and flexible duration support
    
    Developer Notes:
    - Main generator class that coordinates all sport-specific intelligence
    - Inherits from all sport-specific mixins for complete functionality
    - Follows this flow: Template-based generation → Sport-specific enhancement → Final compilation
    - Tracks script usage for variety and applies time constraints
    - Supports custom target duration (15-120 minutes)
    - Uses proper descriptive naming for clarity
    """
    
    def __init__(self):
        """Initialize generator with tracking and constraints"""
        self.selected_scripts = []
        self.used_script_ids = set()        # Prevents duplicate script selection
        self.target_duration = 60.0         # Default target duration
        self.time_flexibility = 5.0         # ±5 minutes acceptable range
        self.sport_additions = {}           # Track sport-specific additions
        
    def generate_workout_with_custom_duration(self, training_type, goal='allround', target_duration=60.0):
        """
        Generate workout with custom duration and sport-specific intelligence
        
        This is the main public method for workout generation with full flexibility
        
        Args:
            training_type: 'kickboxing', 'power_yoga', or 'calisthenics'
            goal: 'allround', 'strength', 'endurance', 'flexibility', 'technique'
            target_duration: Target duration in minutes (15-120)
        
        Returns:
            Dict with workout data including time status and sport additions
        """
        
        # STEP 1: Set custom duration parameters and validate
        self.target_duration = float(target_duration)
        
        if self.target_duration < 15 or self.target_duration > 120:
            raise ValueError("Target duration must be between 15 and 120 minutes")
        
        # Adjust time flexibility based on duration
        if self.target_duration <= 30:
            self.time_flexibility = 3.0    # ±3 minutes for short workouts
        elif self.target_duration <= 45:
            self.time_flexibility = 4.0    # ±4 minutes for medium workouts  
        else:
            self.time_flexibility = 5.0    # ±5 minutes for long workouts
        
        # STEP 2: Load active template rules for this sport
        template_rules = WorkoutTemplate.objects.filter(
            training_type=training_type,
            is_active=True  # Only use active template steps
        ).order_by('sequence_order')
        
        if not template_rules.exists():
            raise ValueError(f"No active workout template defined for {training_type}")
        
        # STEP 3: Generate base workout following template rules
        # NOTE: Special rounds (surprise, vinyasa, MAX) are added HERE based on admin template config
        selected_scripts = self.generate_base_workout_from_templates(
            template_rules, training_type, goal
        )
        
        # STEP 4: Apply sport-specific post-processing (ordering, flow logic, etc.)
        # NOTE: This is for post-processing logic like calisthenics ordering, yoga flow detection
        # Special rounds are already added in step 3 based on admin configuration
        enhanced_scripts = self.apply_sport_specific_intelligence(
            selected_scripts, training_type, goal
        )
        
        # STEP 5: Apply duration management (filler content or trimming)
        final_scripts = self.apply_duration_management(
            enhanced_scripts, training_type, goal
        )
        
        if not final_scripts:
            raise ValueError("No suitable scripts found for workout generation")
        
        # STEP 6: Create and save workout session with metadata
        workout_session = self.create_workout_session_record(
            final_scripts, training_type, goal
        )
        
        # STEP 7: Return comprehensive generation results
        return self.compile_generation_results(workout_session, final_scripts, training_type)
    
    def generate_base_workout_from_templates(self, template_rules, training_type, goal):
        """
        Generate base workout following template rules with OR logic and ADMIN-CONTROLLED special rounds
        
        IMPORTANT: This is where surprise rounds are actually added, based on admin template configuration.
        The sport-specific intelligence mixins are for post-processing other logic.
        """
        selected_scripts = []
        total_duration = 0
        min_duration = self.target_duration - self.time_flexibility
        max_duration = self.target_duration + self.time_flexibility
        
        for template_rule in template_rules:
            # Get all possible categories for this template step (OR logic)
            possible_categories = template_rule.get_all_possible_categories()
            
            # Filter to only active categories
            possible_categories = [cat for cat in possible_categories if cat.is_active]
            
            if not possible_categories:
                continue  # Skip this template step if no active categories
            
            # Try to select a script from one of the possible categories
            selected_script = self.select_best_script_from_categories(
                possible_categories, goal, training_type, max_duration - total_duration
            )
            
            # Add selected script to workout
            if selected_script:
                selected_scripts.append(selected_script)
                total_duration += selected_script.duration_minutes
                self.used_script_ids.add(selected_script.id)
                selected_script.mark_selected()  # Track usage for variety
                
                # ADMIN-CONTROLLED SPECIAL ROUNDS: Process template checkbox settings
                # This is where admin template configuration is respected
                special_category = template_rule.get_special_round_category_to_add_after()
                if special_category and special_category.is_active:
                    special_script = self.find_special_round_script(training_type, special_category)
                    if special_script:
                        selected_scripts.append(special_script)
                        total_duration += special_script.duration_minutes
                        # Track what type of special round was added
                        if special_script.is_surprise_round():
                            self.track_sport_addition('surprise_rounds_added')
                        elif special_script.is_max_challenge():
                            self.track_sport_addition('max_challenge_added')
                        elif special_script.is_vinyasa_transition():
                            self.track_sport_addition('vinyasa_transitions_added')
                        
            elif template_rule.is_required:
                # This is required but we couldn't find anything suitable, try fallback
                fallback_script = self.find_fallback_script_for_training_type(
                    training_type, goal, max_duration - total_duration
                )
                if fallback_script:
                    selected_scripts.append(fallback_script)
                    total_duration += fallback_script.duration_minutes
                    self.used_script_ids.add(fallback_script.id)
                    fallback_script.mark_selected()
        
        return selected_scripts
    
    def select_best_script_from_categories(self, possible_categories, goal, training_type, max_remaining_duration):
        """
        Select best script from possible categories using freshness algorithm
        Uses goal matching and freshness scoring for intelligent variety
        """
        for category in possible_categories:
            script = self.select_best_script_for_category(
                category, goal, training_type, max_remaining_duration
            )
            if script:
                return script  # Found a suitable script, use it
        
        return None  # No suitable script found in any category
    
    def select_best_script_for_category(self, script_category, goal, training_type, max_duration=None):
        """
        Select best script for a specific category using freshness algorithm
        Uses goal matching and freshness scoring for intelligent variety
        """
        candidates = WorkoutScript.objects.filter(
            type=training_type,
            script_category=script_category,
            goal__in=[goal, 'allround'],  # Match specific goal or all-round scripts
            is_active=True
        ).exclude(id__in=self.used_script_ids)
        
        # Apply duration constraint if specified
        if max_duration is not None:
            candidates = candidates.filter(duration_minutes__lte=max_duration)
        
        if not candidates.exists():
            return None
        
        # Smart selection: Sort by freshness score, then add randomization
        candidates_list = list(candidates)
        candidates_list.sort(key=lambda s: s.get_freshness_score(), reverse=True)
        
        # Select from top 3 fresh candidates for variety while avoiding overuse
        top_candidates = candidates_list[:3] if len(candidates_list) >= 3 else candidates_list
        return random.choice(top_candidates)
    
    def find_fallback_script_for_training_type(self, training_type, goal, max_remaining_duration):
        """
        Find any suitable script when primary category options fail
        Safety net for edge cases where specific categories have no available scripts
        """
        candidates = WorkoutScript.objects.filter(
            type=training_type,
            goal__in=[goal, 'allround'],
            duration_minutes__lte=max_remaining_duration,
            is_active=True
        ).exclude(id__in=self.used_script_ids)
        
        if candidates.exists():
            return random.choice(candidates)
        return None
    
    def apply_duration_management(self, enhanced_scripts, training_type, goal):
        """
        Apply duration management: add filler content or trim if needed
        Ensures workouts meet the target duration within acceptable flexibility
        """
        total_duration = sum(script.duration_minutes for script in enhanced_scripts)
        min_duration = self.target_duration - self.time_flexibility
        max_duration = self.target_duration + self.time_flexibility
        
        # Add filler content if workout is too short
        if total_duration < min_duration:
            self.add_filler_content_to_workout(
                enhanced_scripts, training_type, goal, min_duration - total_duration
            )
        
        # Trim content if workout is too long
        elif total_duration > max_duration:
            enhanced_scripts = self.trim_workout_to_target_duration(
                enhanced_scripts, max_duration
            )
        
        return enhanced_scripts
    
    def add_filler_content_to_workout(self, selected_scripts, training_type, goal, needed_duration):
        """
        Add additional content if workout is shorter than target duration
        Ensures workouts meet the minimum target duration
        """
        filler_candidates = WorkoutScript.objects.filter(
            type=training_type,
            goal__in=[goal, 'allround'],
            duration_minutes__lte=needed_duration,
            is_active=True
        ).exclude(id__in=self.used_script_ids).order_by('duration_minutes')
        
        for candidate in filler_candidates:
            if candidate.duration_minutes <= needed_duration:
                selected_scripts.append(candidate)
                needed_duration -= candidate.duration_minutes
                self.used_script_ids.add(candidate.id)
                candidate.mark_selected()
                
                if needed_duration <= 1.0:  # Close enough to target
                    break
    
    def trim_workout_to_target_duration(self, scripts, max_duration):
        """
        Remove optional content if workout is too long
        Handles cases where workout exceeds target duration
        """
        current_duration = sum(script.duration_minutes for script in scripts)
        
        if current_duration <= max_duration:
            return scripts
        
        # Identify essential vs optional scripts
        essential_scripts = []
        optional_scripts = []
        
        for script in scripts:
            # Special rounds and essential scripts are kept
            if (script.is_surprise_round() or 
                script.is_max_challenge() or 
                script.is_vinyasa_transition() or
                self.is_essential_exercise_script(script)):
                essential_scripts.append(script)
            else:
                optional_scripts.append(script)
        
        # Start with essential scripts
        trimmed_scripts = essential_scripts[:]
        current_duration = sum(script.duration_minutes for script in trimmed_scripts)
        
        # Add back optional scripts that fit
        for optional_script in optional_scripts:
            if current_duration + optional_script.duration_minutes <= max_duration:
                trimmed_scripts.append(optional_script)
                current_duration += optional_script.duration_minutes
        
        # Reorder scripts logically after trimming
        return self.reorder_scripts_logically_for_sport(trimmed_scripts)
    
    def is_essential_exercise_script(self, script):
        """
        Determine if a script is essential and should not be trimmed
        Essential scripts include warmup, cooldown, and core exercises
        """
        category_name = script.script_category.name.lower()
        essential_patterns = [
            'warmup', 'warm-up', 'cooldown', 'cool-down', 
            'stretch', 'savasana', 'mindfulness', 'connecting'
        ]
        return any(pattern in category_name for pattern in essential_patterns)
    
    def reorder_scripts_logically_for_sport(self, scripts):
        """
        Reorder scripts in logical sequence after trimming
        Maintains warmup first, cooldown last, sport-specific rules
        """
        if not scripts:
            return scripts
            
        warmup_scripts = []
        main_scripts = []
        cooldown_scripts = []
        
        for script in scripts:
            category_name = script.script_category.name.lower()
            if self.is_warmup_script(script):
                warmup_scripts.append(script)
            elif self.is_cooldown_script(script):
                cooldown_scripts.append(script)
            else:
                main_scripts.append(script)
        
        # Apply sport-specific ordering to main scripts
        training_type = scripts[0].type
        if training_type == 'calisthenics':
            main_scripts = self.apply_logical_exercise_ordering(main_scripts)
        
        return warmup_scripts + main_scripts + cooldown_scripts
    
    def is_warmup_script(self, script):
        """Check if script is a warmup script"""
        category_name = script.script_category.name.lower()
        warmup_patterns = ['warmup', 'warm-up', 'connecting', 'sun_greeting']
        return any(pattern in category_name for pattern in warmup_patterns)
    
    def is_cooldown_script(self, script):
        """Check if script is a cooldown script"""
        category_name = script.script_category.name.lower()
        cooldown_patterns = ['cooldown', 'cool-down', 'stretch', 'relax', 'savasana', 'mindfulness']
        return any(pattern in category_name for pattern in cooldown_patterns)
    
    def create_workout_session_record(self, final_scripts, training_type, goal):
        """
        Create workout session record with metadata and script compilation
        Saves the complete workout session to database for tracking
        """
        total_duration = sum(script.duration_minutes for script in final_scripts)
        
        workout_session = WorkoutSession.objects.create(
            training_type=training_type,
            title=self.generate_descriptive_workout_title(training_type, goal, self.target_duration),
            total_duration=total_duration,
            target_duration=self.target_duration,
            time_flexibility=self.time_flexibility,
            goal=goal,
            compiled_script=self.compile_final_workout_script(final_scripts, training_type),
            sport_additions_applied=self.get_sport_additions_summary()
        )
        
        # Save the scripts used in this session with order and metadata
        for i, script in enumerate(final_scripts):
            SessionScript.objects.create(
                workout_session=workout_session,
                workout_script=script,
                sequence_order=i + 1,
                is_sport_addition=(script.is_surprise_round() or 
                                 script.is_max_challenge() or 
                                 script.is_vinyasa_transition())
            )
        
        return workout_session
    
    def compile_final_workout_script(self, scripts, training_type):
        """
        Compile scripts with Foxing Fit branding, round numbers, and intelligent quote replacement
        
        NEW: Adds round numbers in orange text format as requested by client
        
        1. Start with Foxing Fit opening (NO quotes at start)
        2. Process each script with proper round numbering and [Onthoud,..] placeholders
        3. End with Foxing Fit closing (NO quotes at end)
        """
        script_parts = []
        quote_processor = QuoteProcessor()
        round_counter = 1  # Track round numbers for orange text format
        
        # STEP 1: Add Foxing Fit opening
        opening_text = FoxingFitBranding.get_opening_text(training_type)
        script_parts.append(f"{opening_text}\n\n")
        
        # STEP 2: Process each script with proper formatting
        for i, script in enumerate(scripts):
            # ROUND NUMBER LOGIC: Main exercise scripts get round numbers in orange text
            if self.should_script_have_round_number(script):
                # Use enhanced branding for proper round number formatting
                round_header = FoxingFitBranding.format_round_header(
                    round_counter, 
                    script.title, 
                    'nl'  # Johnny prefers Dutch
                )
                script_parts.append(f"\n{round_header}\n\n")
                round_counter += 1
                
            else:
                # SPECIAL ROUND LOGIC: Special scripts get special indicators
                special_type = FoxingFitBranding.detect_special_round_type(script)
                if special_type:
                    special_header = FoxingFitBranding.format_special_round_header(
                        special_type, 
                        script.title
                    )
                    script_parts.append(f"\n{special_header}\n\n")
                else:
                    # NON-ROUND SCRIPTS: Warmup, cooldown, etc. get simple headers
                    script_parts.append(f"\n## {script.script_category.display_name}\n\n")
            
            # Add script metadata comment for admin/developer reference
            script_parts.append(f"<!-- {script.title} ({script.duration_minutes}min) -->\n")
            
            # Process script content with quote placeholder replacement ONLY
            processed_content = quote_processor.process_script_content(script, training_type)
            script_parts.append(processed_content)
            
            # Add pause between scripts for pacing and smooth transitions
            script_parts.append("\n\n[pause strong] [pause strong]\n")
        
        # STEP 3: Add Foxing Fit closing (NO quotes at end - Johnny's rule)
        closing_text = FoxingFitBranding.get_closing_text(training_type)
        script_parts.append(f"\n{closing_text}")
        
        return ''.join(script_parts)
    
    def should_script_have_round_number(self, script):
        """
        Determine if a script should get a round number in orange text
        
        CLIENT REQUIREMENT: Main exercise scripts need round numbers like "Ronde 1: Push-up Variatie"
        
        Rules:
        - Regular exercise scripts GET round numbers (combinations, push-ups, etc.)
        - Special scripts do NOT get round numbers (surprise, vinyasa, max challenge)
        - Warmup/cooldown scripts do NOT get round numbers
        """
        # Use enhanced branding logic for consistency
        return FoxingFitBranding.should_use_round_numbering(script.script_category.name)
    
    def get_script_section_type_indicator(self, script):
        """Get visual indicator for special script types"""
        if script.is_surprise_round():
            return "🎯 SURPRISE ROUND"
        elif script.is_max_challenge():
            return "💪 MAX CHALLENGE"
        elif script.is_vinyasa_transition():
            return "🌊 VINYASA TRANSITION"
        return None
    
    def get_sport_additions_summary(self):
        """
        Create summary of sport-specific additions made during generation
        Provides metadata about what sport logic was applied for analytics
        """
        summary = {
            'surprise_rounds_added': self.sport_additions.get('surprise_rounds_added', 0),
            'vinyasa_transitions_added': self.sport_additions.get('vinyasa_transitions_added', 0),
            'difficulty_reordered': self.sport_additions.get('difficulty_reordered', 0) > 0,
            'max_challenge_moved_last': self.sport_additions.get('max_challenge_moved_last', 0) > 0
        }
        return summary
    
    def generate_descriptive_workout_title(self, training_type, goal, target_duration):
        """Generate descriptive title for the workout session including duration"""
        type_names = dict(WorkoutScript.TRAINING_TYPES)
        goal_names = dict(WorkoutScript.GOALS)
        
        base_name = type_names.get(training_type, training_type)
        goal_name = goal_names.get(goal, goal)
        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M")
        
        # Include duration in title
        duration_str = f" ({int(target_duration)}min)"
        
        return f"{base_name} - {goal_name}{duration_str} - {timestamp}"
    
    def compile_generation_results(self, workout_session, final_scripts, training_type):
        """
        Compile comprehensive generation results for API response
        Returns complete workout data including metadata and timing analysis
        """
        return {
            'workout_session_id': workout_session.id,
            'title': workout_session.title,
            'training_type': training_type,
            'goal': workout_session.goal,
            'total_duration': workout_session.total_duration,
            'target_duration': self.target_duration,
            'time_status': workout_session.get_time_status(),
            'scripts': [
                {
                    'title': script.title,
                    'script_category': script.script_category.display_name,
                    'duration': script.duration_minutes,
                    'is_sport_addition': (script.is_surprise_round() or 
                                        script.is_max_challenge() or 
                                        script.is_vinyasa_transition())
                }
                for script in final_scripts
            ],
            'compiled_script': workout_session.compiled_script,
            'sport_specific_additions': self.get_sport_additions_summary()
        }

    # Backward compatibility method
    def generate_1hour_workout(self, training_type, goal='allround'):
        """
        Generate 1-hour workout (backward compatibility)
        Delegates to the main generation method with 60-minute target
        """
        return self.generate_workout_with_custom_duration(training_type, goal, 60.0)