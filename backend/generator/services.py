import random
from django.utils import timezone
from django.db.models import Avg
from scripts.models import WorkoutScript, WorkoutTemplate, MotivationalQuote, ScriptCategory
from .models import WorkoutSession, SessionScript

class FlexibleWorkoutGenerator:
    """
    Johnny's intelligent workout generator with OR logic and time constraints
    """
    
    def __init__(self):
        self.selected_scripts = []
        self.used_script_ids = set()
        self.target_duration = 60.0  # 1 hour
        self.time_flexibility = 5.0  # ± 5 minutes
        
    def generate_1hour_workout(self, training_type, goal='allround'):
        """
        Generate flexible 1-hour workout following Johnny's OR logic
        Target: 60 minutes ± 5 minutes (55-65 minutes total)
        """
        # Get template rules for this training type
        template_rules = WorkoutTemplate.objects.filter(
            training_type=training_type
        ).order_by('sequence_order')
        
        if not template_rules.exists():
            raise ValueError(f"No workout template defined for {training_type}")
        
        selected_scripts = []
        total_duration = 0
        min_duration = self.target_duration - self.time_flexibility  # 55 min
        max_duration = self.target_duration + self.time_flexibility  # 65 min
        
        # Follow template rules with OR logic
        for rule in template_rules:
            # Get all possible categories (primary + alternatives)
            possible_categories = rule.get_all_possible_categories()
            
            # Try each possible category until we find suitable scripts
            selected_category = None
            selected_script = None
            
            for category in possible_categories:
                script = self._select_script_for_category(category, goal, training_type)
                if script:
                    # Check if adding this script keeps us within time constraints
                    potential_total = total_duration + script.duration_minutes
                    remaining_required_time = self._estimate_remaining_required_time(
                        template_rules, rule.sequence_order, training_type, goal
                    )
                    
                    # Will we exceed max time?
                    if potential_total + remaining_required_time > max_duration:
                        continue  # Try next alternative
                    
                    # Select this script
                    selected_category = category
                    selected_script = script
                    break
            
            # If we found a suitable script, add it
            if selected_script:
                selected_scripts.append(selected_script)
                total_duration += selected_script.duration_minutes
                self.used_script_ids.add(selected_script.id)
                selected_script.mark_selected()
            elif rule.is_required:
                # This is a required part but we couldn't find anything
                fallback_script = self._find_fallback_script(training_type, goal, max_duration - total_duration)
                if fallback_script:
                    selected_scripts.append(fallback_script)
                    total_duration += fallback_script.duration_minutes
                    self.used_script_ids.add(fallback_script.id)
                    fallback_script.mark_selected()
        
        # Check if we're in acceptable time range
        if total_duration < min_duration:
            # Try to add filler content
            self._add_filler_content(selected_scripts, training_type, goal, min_duration - total_duration)
            total_duration = sum(script.duration_minutes for script in selected_scripts)
        
        if not selected_scripts:
            raise ValueError("No suitable scripts found for workout generation")
        
        # Create workout session record
        workout_session = WorkoutSession.objects.create(
            training_type=training_type,
            title=self._generate_title(training_type, goal),
            total_duration=total_duration,
            target_duration=self.target_duration,
            time_flexibility=self.time_flexibility,
            goal=goal,
            compiled_script=self._compile_script(selected_scripts, training_type)
        )
        
        # Save the scripts used
        for i, script in enumerate(selected_scripts):
            SessionScript.objects.create(
                workout_session=workout_session,
                workout_script=script,
                sequence_order=i + 1
            )
        
        return {
            'workout_session_id': workout_session.id,
            'title': workout_session.title,
            'training_type': training_type,
            'goal': goal,
            'total_duration': total_duration,
            'time_status': workout_session.get_time_status(),
            'scripts': [
                {
                    'title': script.title,
                    'script_category': script.script_category.display_name,
                    'duration': script.duration_minutes
                }
                for script in selected_scripts
            ],
            'compiled_script': workout_session.compiled_script
        }
    
    def _select_script_for_category(self, script_category, goal, training_type):
        """Select script for a specific script category"""
        candidates = WorkoutScript.objects.filter(
            type=training_type,
            script_category=script_category,
            goal__in=[goal, 'allround'],
            is_active=True
        ).exclude(id__in=self.used_script_ids)
        
        if not candidates.exists():
            return None
        
        # Smart selection: prefer fresh scripts but add randomization
        candidates_list = list(candidates)
        candidates_list.sort(key=lambda s: s.get_freshness_score(), reverse=True)
        
        # Select from top 3 fresh candidates for variety
        top_candidates = candidates_list[:3] if len(candidates_list) >= 3 else candidates_list
        return random.choice(top_candidates)
    
    def _estimate_remaining_required_time(self, template_rules, current_order, training_type, goal):
        """Estimate time needed for remaining required parts"""
        remaining_rules = template_rules.filter(
            sequence_order__gt=current_order,
            is_required=True
        )
        
        estimated_time = 0
        for rule in remaining_rules:
            # Get average duration for required parts
            possible_categories = rule.get_all_possible_categories()
            
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
            
            if category_count > 0:
                estimated_time += avg_duration / category_count
            else:
                estimated_time += 5.0  # Default estimate
        
        return estimated_time
    
    def _find_fallback_script(self, training_type, goal, max_remaining_time):
        """Find any suitable script when primary options fail"""
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
        """Add filler content if workout is too short"""
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
                
                if needed_time <= 1.0:  # Close enough
                    break
    
    def _compile_script(self, scripts, training_type):
        """Compile selected scripts into final script with motivational quotes"""
        script_parts = []
        
        # Add opening motivational quote
        opening_quote = self._get_motivational_quote(training_type, 'warmup')
        if opening_quote:
            script_parts.append(f"**{opening_quote}**\n\n")
        
        for i, script in enumerate(scripts):
            # Add script category header
            script_parts.append(f"\n## {script.script_category.display_name}\n")
            script_parts.append(f"<!-- {script.title} -->\n")
            
            # Add the actual content
            script_parts.append(script.content)
            
            # Add motivational quotes at strategic points
            if i < len(scripts) - 2:
                # Add quotes during intense sections
                if any(keyword in script.script_category.name.lower() 
                       for keyword in ['power', 'explosive', 'intense', 'max']):
                    motivational_quote = self._get_motivational_quote(training_type, 'intense')
                    if motivational_quote:
                        script_parts.append(f"\n\n**{motivational_quote}**\n")
                
                # Add transition quotes between different categories
                elif i > 0 and scripts[i-1].script_category != script.script_category:
                    motivational_quote = self._get_motivational_quote(training_type, 'transition')
                    if motivational_quote:
                        script_parts.append(f"\n\n**{motivational_quote}**\n")
            
            # Add pause between scripts
            script_parts.append("\n\n[pause strong] [pause strong]\n")
        
        # Add closing motivational quote
        closing_quote = self._get_motivational_quote(training_type, 'cooldown')
        if closing_quote:
            script_parts.append(f"\n**{closing_quote}**\n")
        
        return ''.join(script_parts)
    
    def _get_motivational_quote(self, training_type, context):
        """Get Johnny's motivational quote for insertion"""
        quotes = MotivationalQuote.objects.filter(
            training_type=training_type,
            context__in=[context, 'anytime'],
            is_active=True
        ).order_by('times_used', 'last_used')  # Prefer less used quotes
        
        if quotes.exists():
            selected_quote = quotes.first()
            selected_quote.mark_used()
            return selected_quote.get_formatted_quote()
        
        return None
    
    def _generate_title(self, training_type, goal):
        """Generate descriptive title"""
        type_names = dict(WorkoutScript.TRAINING_TYPES)
        goal_names = dict(WorkoutScript.GOALS)
        
        base_name = type_names.get(training_type, training_type)
        goal_name = goal_names.get(goal, goal)
        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M")
        
        return f"{base_name} - {goal_name} - {timestamp}"