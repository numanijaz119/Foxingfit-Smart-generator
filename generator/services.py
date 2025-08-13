import random
from django.utils import timezone
from django.db.models import Avg, Q
from scripts.models import WorkoutScript, WorkoutTemplate, MotivationalQuote, ScriptCategory
from .models import WorkoutSession, SessionScript

class SportSpecificGeneratorMixin:
    """
    Base mixin providing sport-specific intelligence for workout generation
    
    Developer Notes:
    - This is the foundation class that routes sport-specific logic
    - Each sport has its own mixin that inherits from this
    - Provides common methods for surprise rounds, vinyasa, and sport detection
    - Used by FlexibleWorkoutGenerator to apply sport-specific post-processing
    """
    
    def _apply_sport_specific_logic(self, selected_scripts, training_type, goal):
        """
        Route to appropriate sport-specific logic based on training type
        This is the main entry point for sport-specific post-processing
        """
        if training_type == 'kickboxing':
            return self._apply_kickboxing_logic(selected_scripts, goal)
        elif training_type == 'power_yoga':
            return self._apply_power_yoga_logic(selected_scripts, goal)
        elif training_type == 'calisthenics':
            return self._apply_calisthenics_logic(selected_scripts, goal)
        
        return selected_scripts  # No sport-specific logic, return as-is
    
    def _get_surprise_round_script(self, training_type):
        """
        Get a surprise round script for kickboxing automatic insertion
        Powers the automatic surprise round feature
        """
        surprise_scripts = WorkoutScript.objects.filter(
            type=training_type,
            script_category__name__icontains='surprise',
            is_active=True
        ).exclude(id__in=self.used_script_ids)
        
        if surprise_scripts.exists():
            # Use freshness algorithm to prefer unused surprise rounds
            surprise_scripts = list(surprise_scripts)
            surprise_scripts.sort(key=lambda s: s.get_freshness_score(), reverse=True)
            selected = surprise_scripts[0]
            selected.mark_selected()
            self.used_script_ids.add(selected.id)
            return selected
        
        return None
    
    def _get_vinyasa_transition_script(self, training_type, transition_type):
        """
        Get a vinyasa transition script for power yoga automatic insertion
        Powers the automatic vinyasa transition feature
        """
        # Look for specific transition type first
        vinyasa_scripts = WorkoutScript.objects.filter(
            type=training_type,
            transition_type=transition_type,
            is_active=True
        ).exclude(id__in=self.used_script_ids)
        
        if not vinyasa_scripts.exists():
            # Fallback to general vinyasa scripts
            vinyasa_scripts = WorkoutScript.objects.filter(
                type=training_type,
                script_category__name__icontains='vinyasa',
                is_active=True
            ).exclude(id__in=self.used_script_ids)
        
        if vinyasa_scripts.exists():
            selected = random.choice(vinyasa_scripts)
            selected.mark_selected()
            self.used_script_ids.add(selected.id)
            return selected
        
        return None

class KickboxingGeneratorMixin(SportSpecificGeneratorMixin):
    """
    Kickboxing-specific logic: Automatic surprise round insertion
    
    Developer Notes:
    - Implements Johnny's surprise round methodology
    - Adds surprise rounds after core training sections (combos, power, legs)
    - Skips surprise rounds for warmup and cooldown sections
    - Uses the surprise round script category for content
    """
    
    def _apply_kickboxing_logic(self, selected_scripts, goal):
        """
        Add surprise rounds after core kickboxing sections
        This implements Johnny's "surprise round glue" between main sections
        """
        enhanced_scripts = []
        
        for i, script in enumerate(selected_scripts):
            # Always add the main script first
            enhanced_scripts.append(script)
            
            # Check if this script's category requires a surprise round after it
            if script.script_category.requires_surprise_round():
                surprise_round = self._get_surprise_round_script('kickboxing')
                if surprise_round:
                    enhanced_scripts.append(surprise_round)
                    # Developer note: surprise_round is already marked as selected in _get_surprise_round_script
        
        return enhanced_scripts

class PowerYogaGeneratorMixin(SportSpecificGeneratorMixin):
    """
    Power Yoga-specific logic: Automatic vinyasa transition insertion
    
    Developer Notes:
    - Implements Johnny's vinyasa flow methodology  
    - Mandatory transitions: Standing-to-Sitting (always inserted)
    - Optional transitions: Standing-to-Standing (30% chance for variety)
    - Uses transition_type metadata to select appropriate vinyasa scripts
    """
    
    def _apply_power_yoga_logic(self, selected_scripts, goal):
        """
        Add vinyasa transitions between power yoga sections based on position changes
        This creates the flowing yoga experience Johnny wants
        """
        enhanced_scripts = []
        
        for i, script in enumerate(selected_scripts):
            # Always add the main script first
            enhanced_scripts.append(script)
            
            # Check if we need a transition to the next script
            if i < len(selected_scripts) - 1:
                current_category = script.script_category.name
                next_category = selected_scripts[i + 1].script_category.name
                
                # MANDATORY: Standing to Sitting transition
                if ('standing' in current_category and 'seated' in next_category):
                    vinyasa = self._get_vinyasa_transition_script('power_yoga', 'standing_to_sitting')
                    if vinyasa:
                        enhanced_scripts.append(vinyasa)
                
                # OPTIONAL: Standing to Standing transition (30% chance for flow variety)
                elif ('standing' in current_category and 'standing' in next_category):
                    if random.random() < 0.3:  # 30% chance for variety
                        vinyasa = self._get_vinyasa_transition_script('power_yoga', 'standing_to_standing')
                        if vinyasa:
                            enhanced_scripts.append(vinyasa)
        
        return enhanced_scripts

class CalisthenicsGeneratorMixin(SportSpecificGeneratorMixin):
    """
    Calisthenics-specific logic: Difficulty progression and MAX challenge placement
    
    Developer Notes:
    - Implements proper difficulty progression for safety
    - Ensures MAX challenge scripts are always placed at the end
    - Prevents advanced movements from appearing too early in workouts
    - Uses difficulty_level and must_be_last metadata for intelligent ordering
    """
    
    def _apply_calisthenics_logic(self, selected_scripts, goal):
        """
        Apply difficulty progression and ensure MAX challenge placement at end
        This ensures safe progression and proper challenge placement
        """
        # Separate MAX challenge scripts from regular scripts
        max_challenge_scripts = []
        regular_scripts = []
        
        for script in selected_scripts:
            if script.script_category.must_be_last:
                max_challenge_scripts.append(script)
            else:
                regular_scripts.append(script)
        
        # Sort regular scripts by difficulty level (beginner → intermediate → advanced)
        regular_scripts.sort(key=lambda s: s.script_category.difficulty_level)
        
        # Combine: regular scripts first, then MAX challenge scripts at end
        return regular_scripts + max_challenge_scripts

class FlexibleWorkoutGenerator(
    KickboxingGeneratorMixin,
    PowerYogaGeneratorMixin, 
    CalisthenicsGeneratorMixin
):
    """
    Johnny's intelligent workout generator with sport-specific logic and custom duration support
    
    Developer Notes:
    - Main generator class that coordinates all sport-specific intelligence
    - Inherits from all sport-specific mixins for complete functionality
    - Follows this flow: Template-based generation → Sport-specific enhancement → Final compilation
    - Tracks script usage for variety and applies time constraints
    - Now supports custom target duration (30-60 minutes)
    """
    
    def __init__(self):
        """Initialize generator with tracking and constraints"""
        self.selected_scripts = []
        self.used_script_ids = set()        # Prevents duplicate script selection
        self.target_duration = 60.0         # Default target duration
        self.time_flexibility = 5.0         # ±5 minutes acceptable range
        
    def generate_1hour_workout(self, training_type, goal='allround'):
        """
        Generate flexible 1-hour workout with sport-specific intelligence (backward compatibility)
        
        Args:
            training_type: 'kickboxing', 'power_yoga', or 'calisthenics'
            goal: 'allround', 'strength', 'endurance', 'flexibility', 'technique'
        
        Returns:
            Dict with workout data including time status
        """
        return self.generate_workout_with_duration(training_type, goal, 60.0)
    
    def generate_workout_with_duration(self, training_type, goal='allround', target_duration=60.0):
        """
        Generate workout with custom duration and sport-specific intelligence
        
        Developer Flow:
        1. Set custom duration parameters
        2. Load workout template rules for sport
        3. Select scripts following OR logic and time constraints  
        4. Apply sport-specific enhancements (surprise rounds, vinyasa, ordering)
        5. Add filler content if needed to reach target duration
        6. Trim content if workout is too long
        7. Compile final script with motivational quotes
        8. Save workout session with metadata
        
        Args:
            training_type: 'kickboxing', 'power_yoga', or 'calisthenics'
            goal: 'allround', 'strength', 'endurance', 'flexibility', 'technique'
            target_duration: Target duration in minutes (15-120)
        
        Returns:
            Dict with workout data including time status
        """
        
        # STEP 1: Set custom duration parameters
        self.target_duration = float(target_duration)
        
        # Adjust time flexibility based on duration
        if self.target_duration <= 30:
            self.time_flexibility = 3.0    # ±3 minutes for short workouts
        elif self.target_duration <= 45:
            self.time_flexibility = 4.0    # ±4 minutes for medium workouts  
        else:
            self.time_flexibility = 5.0    # ±5 minutes for long workouts
        
        # STEP 2: Load template rules for this sport
        template_rules = WorkoutTemplate.objects.filter(
            training_type=training_type
        ).order_by('sequence_order', 'sequence_priority')
        
        if not template_rules.exists():
            raise ValueError(f"No workout template defined for {training_type}")
        
        selected_scripts = []
        total_duration = 0
        min_duration = self.target_duration - self.time_flexibility
        max_duration = self.target_duration + self.time_flexibility
        
        # STEP 3: Follow template rules with OR logic and time awareness
        for rule in template_rules:
            possible_categories = rule.get_all_possible_categories()
            
            # CALISTHENICS SPECIAL RULE: Don't start with advanced movements
            if training_type == 'calisthenics' and len(selected_scripts) < 2:
                # Filter out advanced movements for early workout sections
                possible_categories = [cat for cat in possible_categories 
                                     if cat.difficulty_level <= 2]
            
            selected_script = None
            for category in possible_categories:
                script = self._select_script_for_category(category, goal, training_type)
                if script:
                    # Time constraint check: Will this fit with remaining required time?
                    potential_total = total_duration + script.duration_minutes
                    remaining_required_time = self._estimate_remaining_required_time(
                        template_rules, rule.sequence_order, training_type, goal
                    )
                    
                    if potential_total + remaining_required_time <= max_duration:
                        selected_script = script
                        break  # Found a suitable script, use it
            
            # Add selected script to workout
            if selected_script:
                selected_scripts.append(selected_script)
                total_duration += selected_script.duration_minutes
                self.used_script_ids.add(selected_script.id)
                selected_script.mark_selected()  # Track usage for variety
            elif rule.is_required:
                # This is required but we couldn't find anything suitable, try fallback
                fallback_script = self._find_fallback_script(training_type, goal, max_duration - total_duration)
                if fallback_script:
                    selected_scripts.append(fallback_script)
                    total_duration += fallback_script.duration_minutes
                    self.used_script_ids.add(fallback_script.id)
                    fallback_script.mark_selected()
        
        # STEP 4: Apply sport-specific enhancements (surprise rounds, vinyasa, ordering)
        enhanced_scripts = self._apply_sport_specific_logic(selected_scripts, training_type, goal)
        
        # Recalculate duration after sport-specific additions
        total_duration = sum(script.duration_minutes for script in enhanced_scripts)
        
        # STEP 5: Add filler content if workout is too short
        if total_duration < min_duration:
            self._add_filler_content(enhanced_scripts, training_type, goal, min_duration - total_duration)
            total_duration = sum(script.duration_minutes for script in enhanced_scripts)
        
        # STEP 6: Trim content if workout is too long (NEW)
        if total_duration > max_duration:
            enhanced_scripts = self._trim_workout_content(enhanced_scripts, max_duration)
            total_duration = sum(script.duration_minutes for script in enhanced_scripts)
        
        if not enhanced_scripts:
            raise ValueError("No suitable scripts found for workout generation")
        
        # STEP 7: Create workout session record with metadata
        workout_session = WorkoutSession.objects.create(
            training_type=training_type,
            title=self._generate_title(training_type, goal, self.target_duration),  # Include duration
            total_duration=total_duration,
            target_duration=self.target_duration,  # Use custom target
            time_flexibility=self.time_flexibility,
            goal=goal,
            compiled_script=self._compile_script(enhanced_scripts, training_type),
            sport_additions_applied=self._get_sport_additions_summary(enhanced_scripts, training_type)
        )
        
        # STEP 8: Save the scripts used in this session
        for i, script in enumerate(enhanced_scripts):
            SessionScript.objects.create(
                workout_session=workout_session,
                workout_script=script,
                sequence_order=i + 1,
                is_sport_addition=script.is_surprise_round() or script.is_vinyasa_transition()
            )
        
        # Return comprehensive generation results
        return {
            'workout_session_id': workout_session.id,
            'title': workout_session.title,
            'training_type': training_type,
            'goal': goal,
            'total_duration': total_duration,
            'target_duration': self.target_duration,  # Include target in response
            'time_status': workout_session.get_time_status(),
            'scripts': [
                {
                    'title': script.title,
                    'script_category': script.script_category.display_name,
                    'duration': script.duration_minutes,
                    'is_sport_addition': script.is_surprise_round() or script.is_vinyasa_transition()
                }
                for script in enhanced_scripts
            ],
            'compiled_script': workout_session.compiled_script,
            'sport_specific_additions': self._get_sport_additions_summary(enhanced_scripts, training_type)
        }
    
    def _select_script_for_category(self, script_category, goal, training_type):
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
        
        if not candidates.exists():
            return None
        
        # Smart selection: Sort by freshness score, then add randomization
        candidates_list = list(candidates)
        candidates_list.sort(key=lambda s: s.get_freshness_score(), reverse=True)
        
        # Select from top 3 fresh candidates for variety while avoiding overuse
        top_candidates = candidates_list[:3] if len(candidates_list) >= 3 else candidates_list
        return random.choice(top_candidates)
    
    def _estimate_remaining_required_time(self, template_rules, current_order, training_type, goal):
        """
        Estimate time needed for remaining required template sections
        Prevents time constraint violations by predicting future requirements
        """
        remaining_rules = template_rules.filter(
            sequence_order__gt=current_order,
            is_required=True
        )
        
        estimated_time = 0
        for rule in remaining_rules:
            possible_categories = rule.get_all_possible_categories()
            
            # Calculate average duration for each possible category
            avg_duration = 0
            category_count = 0
            
            for category in possible_categories:
                category_avg = WorkoutScript.objects.filter(
                    type=training_type,
                    script_category=category,
                    goal__in=[goal, 'allround'],
                    is_active=True
                ).aggregate(avg_duration=Avg('duration_minutes'))['avg_duration']
                
                if category_avg:
                    avg_duration += category_avg
                    category_count += 1
            
            # Use average of averages, or fallback estimate
            if category_count > 0:
                estimated_time += avg_duration / category_count
            else:
                estimated_time += 5.0  # Fallback estimate when no data available
        
        return estimated_time
    
    def _find_fallback_script(self, training_type, goal, max_remaining_time):
        """
        Find any suitable script when primary category options fail
        Safety net for edge cases where specific categories have no available scripts
        """
        candidates = WorkoutScript.objects.filter(
            type=training_type,
            goal__in=[goal, 'allround'],
            duration_minutes__lte=max_remaining_time,
            is_active=True
        ).exclude(id__in=self.used_script_ids)
        
        if candidates.exists():
            return random.choice(candidates)
        return None
    
    def _add_filler_content(self, selected_scripts, training_type, goal, needed_time):
        """
        Add additional content if workout is shorter than target duration
        Ensures workouts meet the target duration
        """
        filler_candidates = WorkoutScript.objects.filter(
            type=training_type,
            goal__in=[goal, 'allround'],
            duration_minutes__lte=needed_time,
            is_active=True
        ).exclude(id__in=self.used_script_ids).order_by('duration_minutes')
        
        for candidate in filler_candidates:
            if candidate.duration_minutes <= needed_time:
                selected_scripts.append(candidate)
                needed_time -= candidate.duration_minutes
                self.used_script_ids.add(candidate.id)
                candidate.mark_selected()
                
                if needed_time <= 1.0:  # Close enough to target
                    break
    
    def _trim_workout_content(self, scripts, max_duration):
        """
        Remove optional content if workout is too long
        NEW: Handles cases where workout exceeds target duration
        """
        current_duration = sum(script.duration_minutes for script in scripts)
        
        if current_duration <= max_duration:
            return scripts
        
        # Identify required vs optional scripts
        required_scripts = []
        optional_scripts = []
        
        for script in scripts:
            # Sport additions and essential scripts are required
            if (script.is_surprise_round() or 
                script.is_vinyasa_transition() or 
                script.intensity_level >= 3 or
                'warmup' in script.script_category.name.lower() or
                'cooldown' in script.script_category.name.lower() or
                'stretch' in script.script_category.name.lower() or
                'savasana' in script.script_category.name.lower()):
                required_scripts.append(script)
            else:
                optional_scripts.append(script)
        
        # Start with required scripts
        trimmed_scripts = required_scripts[:]
        current_duration = sum(script.duration_minutes for script in trimmed_scripts)
        
        # Add back optional scripts that fit
        for optional_script in optional_scripts:
            if current_duration + optional_script.duration_minutes <= max_duration:
                trimmed_scripts.append(optional_script)
                current_duration += optional_script.duration_minutes
        
        # Reorder scripts logically after trimming
        return self._reorder_scripts_logically(trimmed_scripts)
    
    def _reorder_scripts_logically(self, scripts):
        """
        Reorder scripts in logical sequence after trimming
        Maintains warmup first, cooldown last, sport-specific rules
        """
        warmup_scripts = []
        main_scripts = []
        cooldown_scripts = []
        
        for script in scripts:
            category_name = script.script_category.name.lower()
            if ('warmup' in category_name or 
                'connecting' in category_name or
                'sun_greeting' in category_name):
                warmup_scripts.append(script)
            elif ('cooldown' in category_name or 
                  'stretch' in category_name or 
                  'savasana' in category_name or
                  'mindfulness' in category_name):
                cooldown_scripts.append(script)
            else:
                main_scripts.append(script)
        
        # Apply sport-specific ordering to main scripts
        if scripts and len(scripts) > 0:
            training_type = scripts[0].type
            if training_type == 'calisthenics':
                # Sort by difficulty level for calisthenics
                main_scripts.sort(key=lambda s: s.script_category.difficulty_level)
        
        return warmup_scripts + main_scripts + cooldown_scripts
    
    def _compile_script(self, scripts, training_type):
        """
        Compile selected scripts into final formatted script with motivational quotes
        Creates the final script output with sport-specific formatting and quote insertion
        """
        script_parts = []
        
        # Add opening motivational quote for workout start
        opening_quote = self._get_motivational_quote(training_type, 'warmup')
        if opening_quote:
            script_parts.append(f"**{opening_quote}**\n\n")
        
        for i, script in enumerate(scripts):
            # Add section headers with sport-specific styling
            section_type = "🎯 SURPRISE ROUND" if script.is_surprise_round() else ""
            section_type = "🌊 VINYASA TRANSITION" if script.is_vinyasa_transition() else section_type
            
            if section_type:
                script_parts.append(f"\n{section_type}\n")
            else:
                script_parts.append(f"\n## {script.script_category.display_name}\n")
            
            # Add script metadata comment
            script_parts.append(f"<!-- {script.title} -->\n")
            
            # Add the actual workout content
            script_parts.append(script.content)
            
            # Strategic motivational quote placement
            if i < len(scripts) - 2:  # Don't add quotes after last two scripts
                # Add quotes during high-intensity sections
                if script.intensity_level >= 3 or script.is_surprise_round():
                    motivational_quote = self._get_motivational_quote(training_type, 'intense')
                    if motivational_quote:
                        script_parts.append(f"\n\n**{motivational_quote}**\n")
                # Add quotes during category transitions
                elif i > 0 and scripts[i-1].script_category != script.script_category:
                    motivational_quote = self._get_motivational_quote(training_type, 'transition')
                    if motivational_quote:
                        script_parts.append(f"\n\n**{motivational_quote}**\n")
            
            # Add pause between scripts for pacing
            script_parts.append("\n\n[pause strong] [pause strong]\n")
        
        # Add closing motivational quote for workout end
        closing_quote = self._get_motivational_quote(training_type, 'cooldown')
        if closing_quote:
            script_parts.append(f"\n**{closing_quote}**\n")
        
        return ''.join(script_parts)
    
    def _get_motivational_quote(self, training_type, context):
        """
        Get contextually appropriate motivational quote with variety algorithm
        Uses usage tracking to ensure quote variety and prevent repetition
        """
        quotes = MotivationalQuote.objects.filter(
            training_type=training_type,
            context__in=[context, 'anytime'],  # Match specific context or any-time quotes
            is_active=True
        ).order_by('times_used', 'last_used')  # Prefer less used quotes first
        
        if quotes.exists():
            selected_quote = quotes.first()
            selected_quote.mark_used()  # Track usage for variety
            return selected_quote.get_formatted_quote()
        
        return None
    
    def _get_sport_additions_summary(self, scripts, training_type):
        """
        Create summary of sport-specific additions made during generation
        Provides metadata about what sport logic was applied for debugging and analytics
        """
        summary = {
            'surprise_rounds_added': 0,
            'vinyasa_transitions_added': 0,
            'difficulty_reordered': False,
            'max_challenge_moved_last': False
        }
        
        # Count sport-specific additions
        for script in scripts:
            if script.is_surprise_round():
                summary['surprise_rounds_added'] += 1
            if script.is_vinyasa_transition():
                summary['vinyasa_transitions_added'] += 1
        
        # Check for calisthenics-specific reordering
        if training_type == 'calisthenics':
            max_challenge_scripts = [s for s in scripts if s.script_category.must_be_last]
            if max_challenge_scripts:
                summary['max_challenge_moved_last'] = True
                
            # Check if difficulty progression was applied
            difficulty_levels = [s.script_category.difficulty_level for s in scripts[:-len(max_challenge_scripts)] if not s.script_category.must_be_last]
            if len(difficulty_levels) > 1 and difficulty_levels == sorted(difficulty_levels):
                summary['difficulty_reordered'] = True
        
        return summary
    
    def _generate_title(self, training_type, goal, target_duration=None):
        """Generate descriptive title for the workout session including duration"""
        type_names = dict(WorkoutScript.TRAINING_TYPES)
        goal_names = dict(WorkoutScript.GOALS)
        
        base_name = type_names.get(training_type, training_type)
        goal_name = goal_names.get(goal, goal)
        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M")
        
        # Include duration in title if provided
        if target_duration:
            duration_str = f" ({int(target_duration)}min)"
        else:
            duration_str = ""
        
        return f"{base_name} - {goal_name}{duration_str} - {timestamp}"