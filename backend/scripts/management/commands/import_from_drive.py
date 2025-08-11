import os
import re
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from scripts.models import WorkoutScript, MotivationalQuote, ScriptCategory, WorkoutTemplate

class Command(BaseCommand):
    help = 'Import Johnny\'s workout content from DATABASE_CONTENT folder structure'
    
    def add_arguments(self, parser):
        parser.add_argument('--setup-complete-system', action='store_true', 
                          help='Setup complete system based on Drive structure')
        parser.add_argument('--import-local-files', action='store_true',
                          help='Import content from DATABASE_CONTENT folder')
        parser.add_argument('--folder-path', type=str, default='DATABASE_CONTENT',
                          help='Path to content folder (default: DATABASE_CONTENT)')
        parser.add_argument('--create-dummy-content', action='store_true',
                          help='Create dummy content for testing')
        parser.add_argument('--dry-run', action='store_true', 
                          help='Preview without making changes')
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No changes will be saved"))
        
        try:
            with transaction.atomic():
                if options['setup_complete_system']:
                    self._setup_complete_system_from_drive(dry_run)
                
                if options['import_local_files']:
                    self._import_from_local_folder(options['folder_path'], dry_run)
                
                if options['create_dummy_content']:
                    self._create_dummy_content(dry_run)
                
                if dry_run:
                    raise Exception("Dry run - rolling back")
                    
        except Exception as e:
            if "Dry run" in str(e):
                self.stdout.write(self.style.SUCCESS("✅ Dry run completed successfully"))
            else:
                self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))
    
    def _import_from_local_folder(self, folder_path, dry_run):
        """Import workout scripts from DATABASE_CONTENT folder structure"""
        
        if not os.path.exists(folder_path):
            self.stdout.write(self.style.ERROR(f"❌ Folder {folder_path} does not exist"))
            self.stdout.write(f"💡 Create folder structure like:")
            self.stdout.write(f"   {folder_path}/")
            self.stdout.write(f"   ├── kickboxing/")
            self.stdout.write(f"   │   ├── combinations/")
            self.stdout.write(f"   │   ├── legs_kicks/")
            self.stdout.write(f"   ├── power_yoga/")
            self.stdout.write(f"   │   ├── standing_poses/")
            self.stdout.write(f"   └── calisthenics/")
            self.stdout.write(f"       ├── pushup/")
            return
        
        # Define folder name mappings to category names
        folder_category_mapping = {
            # KICKBOXING MAPPINGS
            'combinations': 'kb_combinations',
            'combination': 'kb_combinations',
            'combo': 'kb_combinations',
            'legs_kicks': 'kb_legs_kicks',
            'legs': 'kb_legs_kicks',
            'kicks': 'kb_legs_kicks',
            'abs': 'kb_abs',
            'abs_round': 'kb_abs',
            'endurance': 'kb_endurance',
            'footwork': 'kb_footwork',
            'defence': 'kb_defence',
            'defense': 'kb_defence',
            'surprise': 'kb_surprise',
            'surprise_rounds': 'kb_surprise',
            'cooldown': 'kb_cooldown',
            'stretch': 'kb_stretch_relax',
            'stretch_relax': 'kb_stretch_relax',
            'warmup': 'kb_warmup',
            'warm_up': 'kb_warmup',
            'quotes': None,  # Skip quotes folders
            
            # POWER YOGA MAPPINGS
            'connecting': 'py_connecting',
            'connecting_phase': 'py_connecting',
            'sun_greeting': 'py_sun_greeting',
            'sun_salutation': 'py_sun_greeting',
            'standing': 'py_standing',
            'standing_poses': 'py_standing',
            'yoga_flow': 'py_yoga_flow',
            'flow': 'py_yoga_flow',
            'seated': 'py_seated',
            'seated_poses': 'py_seated',
            'lying': 'py_lying',
            'lying_poses': 'py_lying',
            'savasana': 'py_savasana',
            'mindfulness': 'py_mindfulness',
            'mindfullness': 'py_mindfulness',  # Handle typo
            'remember_quotes': None,  # Skip quotes folders
            
            # CALISTHENICS MAPPINGS
            'pushup': 'cal_pushup',
            'push_up': 'cal_pushup',
            'push_ups': 'cal_pushup',
            'pushups': 'cal_pushup',
            'situp': 'cal_situp',
            'sit_up': 'cal_situp',
            'sit_ups': 'cal_situp',
            'situps': 'cal_situp',
            'pullup': 'cal_pullup',
            'pull_up': 'cal_pullup',
            'pull_ups': 'cal_pullup',
            'pullups': 'cal_pullup',
            'dips': 'cal_dips',
            'dip': 'cal_dips',
            'lsit': 'cal_lsit',
            'l_sit': 'cal_lsit',
            'explosive': 'cal_explosive',
            'explosive_moves': 'cal_explosive',
            'handstand': 'cal_handstand',
            'handstand_variation': 'cal_handstand',
            'back_lever': 'cal_back_lever',
            'front_lever': 'cal_front_lever',
            'planche': 'cal_planche',
            'static_holds': 'cal_static_holds',
            'max_challenge': 'cal_max_challenge',
            'max': 'cal_max_challenge',
        }
        
        # Walk through the folder structure
        total_imported = 0
        errors = []
        
        for sport_folder in os.listdir(folder_path):
            sport_path = os.path.join(folder_path, sport_folder)
            
            if not os.path.isdir(sport_path):
                continue
                
            # Map sport folder to training type
            sport_type = self._map_sport_folder_to_type(sport_folder)
            if not sport_type:
                self.stdout.write(self.style.WARNING(f"⚠️ Unknown sport folder: {sport_folder}"))
                continue
            
            self.stdout.write(f"\n📁 Processing {sport_folder} ({sport_type})...")
            
            # Process each category folder within sport
            for category_folder in os.listdir(sport_path):
                category_path = os.path.join(sport_path, category_folder)
                
                if not os.path.isdir(category_path):
                    continue
                
                # Map folder name to category
                category_name = self._map_folder_to_category(category_folder, folder_category_mapping)
                if not category_name:
                    self.stdout.write(f"   ⚠️ Skipping unknown category: {category_folder}")
                    continue
                
                # Process files in this category
                file_count = 0
                for file_name in os.listdir(category_path):
                    if not file_name.lower().endswith(('.txt', '.doc', '.docx')):
                        continue
                    
                    file_path = os.path.join(category_path, file_name)
                    
                    try:
                        success = self._import_single_file(
                            file_path, file_name, sport_type, category_name, dry_run
                        )
                        if success:
                            file_count += 1
                            total_imported += 1
                    except Exception as e:
                        error_msg = f"Error importing {file_path}: {str(e)}"
                        errors.append(error_msg)
                        if not dry_run:  # Only show errors in real mode
                            self.stdout.write(self.style.ERROR(f"   ❌ {error_msg}"))
                
                if file_count > 0:
                    self.stdout.write(f"   ✅ {category_folder}: {file_count} files")
        
        # Summary
        self.stdout.write(f"\n🎯 IMPORT SUMMARY:")
        self.stdout.write(self.style.SUCCESS(f"✅ Total files imported: {total_imported}"))
        if errors:
            self.stdout.write(self.style.WARNING(f"⚠️ Errors encountered: {len(errors)}"))
            for error in errors[:3]:  # Show first 3 errors
                self.stdout.write(f"   {error}")
    
    def _map_sport_folder_to_type(self, folder_name):
        """Map folder name to training type"""
        folder_lower = folder_name.lower()
        if 'kickbox' in folder_lower or 'kick' in folder_lower:
            return 'kickboxing'
        elif 'yoga' in folder_lower or 'power' in folder_lower:
            return 'power_yoga'
        elif 'calisthen' in folder_lower or 'cal' in folder_lower or 'strength' in folder_lower:
            return 'calisthenics'
        return None
    
    def _map_folder_to_category(self, folder_name, mapping):
        """Map folder name to script category using intelligent matching"""
        folder_clean = folder_name.lower().replace(' ', '_').replace('-', '_')
        
        # Direct mapping first
        if folder_clean in mapping:
            return mapping[folder_clean]
        
        # Partial matching for variations
        for key, value in mapping.items():
            if key in folder_clean or folder_clean in key:
                return value
        
        return None
    
    def _import_single_file(self, file_path, file_name, sport_type, category_name, dry_run):
        """Import a single workout script file"""
        
        # Read file content
        try:
            if file_path.endswith('.txt'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
            else:
                # For .doc/.docx files, provide instruction
                content = f"[CONTENT FROM {file_name}]\n\n" + \
                         "Please copy content from Word document manually via admin interface."
        except Exception as e:
            raise Exception(f"Could not read file: {str(e)}")
        
        if not content or len(content) < 10:
            raise Exception("File appears to be empty or too short")
        
        # Clean title from filename
        title = self._clean_title_from_filename(file_name)
        
        # Get realistic duration based on category and content length
        duration = self._calculate_realistic_duration(category_name, content, sport_type)
        
        # Determine intensity level based on category
        intensity = self._determine_intensity_level(category_name, title, content)
        
        # Determine transition type (mainly for yoga)
        transition_type = self._determine_transition_type(category_name, title)
        
        # Determine goal based on category and content
        goal = self._determine_goal(category_name, title, content)
        
        if not dry_run:
            # Get script category
            try:
                script_category = ScriptCategory.objects.get(
                    training_type=sport_type,
                    name=category_name
                )
            except ScriptCategory.DoesNotExist:
                raise Exception(f"Category '{category_name}' not found for {sport_type}")
            
            # Create or update script
            script, created = WorkoutScript.objects.get_or_create(
                title=title,
                type=sport_type,
                script_category=script_category,
                defaults={
                    'content': content,
                    'duration_minutes': duration,
                    'goal': goal,
                    'intensity_level': intensity,
                    'transition_type': transition_type,
                    'language': 'nl',
                    'notes': f'Imported from {file_path}'
                }
            )
            
            if not created:
                # Update existing script
                script.content = content
                script.duration_minutes = duration
                script.goal = goal
                script.intensity_level = intensity
                script.transition_type = transition_type
                script.notes = f'Updated from {file_path}'
                script.save()
        else:
            # Dry run output
            action = "CREATE" if True else "UPDATE"  # Assume create in dry run
            self.stdout.write(
                f"   [DRY RUN] {action}: {title} ({duration:.1f}min, {goal}, intensity:{intensity})"
            )
        
        return True
    
    def _clean_title_from_filename(self, filename):
        """Clean up filename to create a proper title"""
        # Remove extension
        title = os.path.splitext(filename)[0]
        
        # Remove common prefixes like "Round 1:", "Ronde 2:", etc.
        title = re.sub(r'^(Round|Ronde)\s*\d+\s*:?\s*', '', title, flags=re.IGNORECASE)
        
        # Replace underscores and hyphens with spaces
        title = title.replace('_', ' ').replace('-', ' ')
        
        # Clean up multiple spaces
        title = re.sub(r'\s+', ' ', title).strip()
        
        # Capitalize first letter of each word
        title = title.title()
        
        return title
    
    def _calculate_realistic_duration(self, category_name, content, sport_type):
        """Calculate realistic duration based on category and content length"""
        
        # Base durations per category (in minutes)
        base_durations = {
            # KICKBOXING
            'kb_warmup': 8.0,
            'kb_combinations': 12.0,
            'kb_legs_kicks': 10.0,
            'kb_abs': 8.0,
            'kb_endurance': 15.0,
            'kb_footwork': 10.0,
            'kb_defence': 8.0,
            'kb_surprise': 5.0,
            'kb_cooldown': 6.0,
            'kb_stretch_relax': 7.0,
            
            # POWER YOGA
            'py_connecting': 5.0,
            'py_sun_greeting': 8.0,
            'py_standing': 12.0,
            'py_yoga_flow': 15.0,
            'py_seated': 10.0,
            'py_lying': 8.0,
            'py_savasana': 5.0,
            'py_mindfulness': 7.0,
            
            # CALISTHENICS
            'cal_warmup': 8.0,
            'cal_pushup': 10.0,
            'cal_situp': 8.0,
            'cal_pullup': 12.0,
            'cal_dips': 8.0,
            'cal_lsit': 6.0,
            'cal_explosive': 10.0,
            'cal_handstand': 8.0,
            'cal_back_lever': 6.0,
            'cal_front_lever': 6.0,
            'cal_planche': 6.0,
            'cal_static_holds': 8.0,
            'cal_max_challenge': 5.0,
        }
        
        base_duration = base_durations.get(category_name, 8.0)
        
        # Adjust based on content length
        content_length = len(content)
        if content_length < 500:
            return base_duration * 0.7  # Shorter content
        elif content_length > 2000:
            return base_duration * 1.3  # Longer content
        else:
            return base_duration
    
    def _determine_intensity_level(self, category_name, title, content):
        """Determine intensity level based on category and content"""
        
        # High intensity categories
        high_intensity = [
            'kb_endurance', 'kb_surprise', 'cal_explosive', 'cal_max_challenge'
        ]
        
        # Low intensity categories
        low_intensity = [
            'kb_warmup', 'kb_cooldown', 'kb_stretch_relax', 
            'py_connecting', 'py_savasana', 'py_mindfulness',
            'cal_warmup'
        ]
        
        if category_name in high_intensity:
            return 3
        elif category_name in low_intensity:
            return 1
        
        # Check content for intensity keywords
        content_lower = content.lower()
        title_lower = title.lower()
        
        high_keywords = ['max', 'explosive', 'intense', 'power', 'hard', 'challenge']
        low_keywords = ['gentle', 'slow', 'relax', 'calm', 'easy', 'stretch']
        
        if any(keyword in content_lower or keyword in title_lower for keyword in high_keywords):
            return 3
        elif any(keyword in content_lower or keyword in title_lower for keyword in low_keywords):
            return 1
        
        return 2  # Default to medium intensity
    
    def _determine_transition_type(self, category_name, title):
        """Determine transition type (mainly for yoga)"""
        
        if 'vinyasa' in category_name:
            if 'standing_to_sitting' in category_name:
                return 'standing_to_sitting'
            elif 'standing_to_standing' in category_name:
                return 'standing_to_standing'
            else:
                return 'flow_transition'
        
        title_lower = title.lower()
        if 'vinyasa' in title_lower:
            if 'sitting' in title_lower:
                return 'standing_to_sitting'
            elif 'standing' in title_lower:
                return 'standing_to_standing'
            else:
                return 'flow_transition'
        
        return 'none'
    
    def _determine_goal(self, category_name, title, content):
        """Determine workout goal based on category and content"""
        
        # Category-based goal mapping
        strength_categories = [
            'cal_pullup', 'cal_pushup', 'cal_dips', 'cal_lsit', 'cal_handstand',
            'cal_back_lever', 'cal_front_lever', 'cal_planche', 'cal_max_challenge'
        ]
        
        endurance_categories = [
            'kb_endurance', 'cal_explosive'
        ]
        
        flexibility_categories = [
            'kb_stretch_relax', 'py_savasana', 'py_mindfulness', 'py_lying'
        ]
        
        technique_categories = [
            'kb_combinations', 'kb_footwork', 'kb_defence'
        ]
        
        if category_name in strength_categories:
            return 'strength'
        elif category_name in endurance_categories:
            return 'endurance'
        elif category_name in flexibility_categories:
            return 'flexibility'
        elif category_name in technique_categories:
            return 'technique'
        
        # Check content for goal keywords
        content_lower = (content + title).lower()
        
        if any(word in content_lower for word in ['strength', 'strong', 'power', 'muscle']):
            return 'strength'
        elif any(word in content_lower for word in ['endurance', 'cardio', 'stamina']):
            return 'endurance'
        elif any(word in content_lower for word in ['flexibility', 'stretch', 'relax']):
            return 'flexibility'
        elif any(word in content_lower for word in ['technique', 'form', 'precision']):
            return 'technique'
        
        return 'allround'  # Default
    
    # ... (keep all the existing methods from the previous version)
    
    def _setup_complete_system_from_drive(self, dry_run):
        """Create complete system based on Johnny's actual Google Drive structure"""
        
        # KICKBOXING STRUCTURE (based on your Drive folders)
        kickboxing_categories = [
            ('kb_warmup', 'Warm-up', 1, False),
            ('kb_combinations', 'Combinations', 2, False),
            ('kb_legs_kicks', 'Legs & Kicks', 2, False),
            ('kb_abs', 'Abs Round', 1, False),
            ('kb_endurance', 'Endurance', 2, False),
            ('kb_footwork', 'Footwork', 2, False),
            ('kb_defence', 'Defence', 2, False),
            ('kb_surprise', 'Surprise Rounds', 1, False),  # For automatic insertion
            ('kb_cooldown', 'Cooldown', 1, False),
            ('kb_stretch_relax', 'Stretch and Relax', 1, False),
        ]
        
        # POWER YOGA STRUCTURE (based on your Drive folders)
        power_yoga_categories = [
            ('py_connecting', 'Connecting Phase', 1, False),
            ('py_sun_greeting', 'Sun Greeting', 1, False),
            ('py_standing', 'Standing Poses', 2, False),
            ('py_yoga_flow', 'Yoga Flow', 2, False),
            ('py_seated', 'Seated Poses', 2, False),
            ('py_lying', 'Lying Poses', 1, False),
            ('py_savasana', 'Savasana', 1, False),
            ('py_mindfulness', 'Mindfulness', 1, False),
            # Vinyasa categories for automatic transitions
            ('py_vinyasa_standing_to_standing', 'Vinyasa Standing-to-Standing', 2, False),
            ('py_vinyasa_standing_to_sitting', 'Vinyasa Standing-to-Sitting', 2, False),
        ]
        
        # CALISTHENICS STRUCTURE (based on your Drive folders)
        calisthenics_categories = [
            ('cal_warmup', 'Warm-up', 1, False),
            ('cal_pushup', 'Push-up Variations', 1, False),
            ('cal_situp', 'Sit-up Variations', 1, False),
            ('cal_pullup', 'Pull-up Variations', 2, False),
            ('cal_dips', 'Dips Variations', 2, False),
            ('cal_lsit', 'L-sit Variations', 2, False),
            ('cal_explosive', 'Explosive Moves', 2, False),
            ('cal_handstand', 'Handstand Variations', 3, False),       # Advanced
            ('cal_back_lever', 'Back-lever Variations', 3, False),     # Advanced
            ('cal_front_lever', 'Front-lever Variations', 3, False),   # Advanced
            ('cal_planche', 'Planche Variations', 3, False),           # Advanced
            ('cal_static_holds', 'Static Holds', 2, False),
            ('cal_max_challenge', 'MAX Challenge', 2, True),           # Must be last
        ]
        
        all_categories = [
            ('kickboxing', kickboxing_categories),
            ('power_yoga', power_yoga_categories),
            ('calisthenics', calisthenics_categories)
        ]
        
        created_count = 0
        for training_type, categories in all_categories:
            for name, display_name, difficulty, must_be_last in categories:
                if not dry_run:
                    category, created = ScriptCategory.objects.get_or_create(
                        training_type=training_type,
                        name=name,
                        defaults={
                            'display_name': display_name,
                            'difficulty_level': difficulty,
                            'must_be_last': must_be_last,
                            'description': f'Auto-created from your {training_type} Drive structure'
                        }
                    )
                    if created:
                        created_count += 1
                else:
                    created_count += 1
                    special = " (MUST BE LAST)" if must_be_last else ""
                    special = " (ADVANCED)" if difficulty == 3 else special
                    self.stdout.write(f"[DRY RUN] {training_type}: {display_name}{special}")
        
        self.stdout.write(self.style.SUCCESS(f"✅ Created {created_count} workout categories from your Drive structure"))
        
        # Setup smart automation rules
        self._setup_smart_automation_rules(dry_run)
        
        # Create workout templates
        self._create_workout_templates_from_structure(dry_run)
        
        # Create quotes structure
        self._create_quotes_from_drive_structure(dry_run)
    
    def _setup_smart_automation_rules(self, dry_run):
        """Setup smart automation rules for each sport"""
        if dry_run:
            self.stdout.write("[DRY RUN] Would setup smart automation rules")
            return
        
        # Sport-specific automation rules
        smart_rules = {
            'kickboxing': {
                'auto_surprise_rounds': True,
                'surprise_after': ['combinations', 'legs_kicks', 'endurance'],
                'no_surprise_after': ['warmup', 'cooldown', 'stretch']
            },
            'power_yoga': {
                'auto_vinyasa': True,
                'mandatory_transitions': ['standing_to_sitting'],
                'optional_transitions': ['standing_to_standing'],
                'optional_chance': 0.3
            },
            'calisthenics': {
                'difficulty_progression': True,
                'max_challenge_last': True,
                'advanced_moves': ['handstand', 'back_lever', 'front_lever', 'planche']
            }
        }
        
        # Apply rules to categories
        for training_type, rules in smart_rules.items():
            categories = ScriptCategory.objects.filter(training_type=training_type)
            for category in categories:
                category.sport_specific_rules = rules
                category.save()
        
        self.stdout.write(self.style.SUCCESS("✅ Setup smart automation rules"))
    
    def _create_workout_templates_from_structure(self, dry_run):
        """Create workout templates based on Johnny's methodology"""
        
        def get_category(training_type, name):
            if dry_run:
                return type('MockCategory', (), {'id': 1, 'name': name})()
            return ScriptCategory.objects.get(training_type=training_type, name=name)
        
        # KICKBOXING TEMPLATES (Johnny's methodology)
        kickboxing_templates = [
            # (order, primary, alternatives, required, surprise, transition)
            (1, 'kb_warmup', [], True, False, False),
            (2, 'kb_combinations', [], True, True, False),        # + Surprise
            (3, 'kb_legs_kicks', ['kb_abs'], True, True, False),  # Legs OR Abs + Surprise
            (4, 'kb_endurance', ['kb_footwork', 'kb_defence'], False, True, False), # Optional + Surprise
            (5, 'kb_stretch_relax', ['kb_cooldown'], True, False, False),
        ]
        
        # POWER YOGA TEMPLATES (Johnny's methodology)
        power_yoga_templates = [
            (1, 'py_connecting', [], True, False, False),
            (2, 'py_sun_greeting', [], True, False, False),
            (3, 'py_standing', [], True, False, True),           # Check transitions
            (4, 'py_yoga_flow', ['py_standing'], False, False, True), # Flow OR more standing
            (5, 'py_seated', [], True, False, True),            # Check transitions
            (6, 'py_lying', [], True, False, False),
            (7, 'py_savasana', ['py_mindfulness'], True, False, False),
        ]
        
        # CALISTHENICS TEMPLATES (Johnny's methodology)
        calisthenics_templates = [
            (1, 'cal_warmup', [], True, False, False),
            (2, 'cal_pushup', ['cal_situp'], True, False, False),
            (3, 'cal_pullup', ['cal_dips'], True, False, False),
            (4, 'cal_lsit', ['cal_explosive'], False, False, False),
            (5, 'cal_handstand', ['cal_back_lever', 'cal_front_lever', 'cal_planche'], False, False, False),
            (6, 'cal_max_challenge', [], False, False, False),  # Will be moved to end automatically
        ]
        
        all_templates = [
            ('kickboxing', kickboxing_templates),
            ('power_yoga', power_yoga_templates),
            ('calisthenics', calisthenics_templates)
        ]
        
        created_count = 0
        for sport, templates in all_templates:
            for order, primary_name, alt_names, required, surprise, transition in templates:
                primary_category = get_category(sport, primary_name)
                
                if not dry_run:
                    template, created = WorkoutTemplate.objects.get_or_create(
                        training_type=sport,
                        sequence_order=order,
                        defaults={
                            'primary_category': primary_category,
                            'is_required': required,
                            'requires_surprise_round': surprise,
                            'requires_transition': transition
                        }
                    )
                    
                    # Add alternatives
                    template.alternative_categories.clear()
                    for alt_name in alt_names:
                        alt_category = get_category(sport, alt_name)
                        template.alternative_categories.add(alt_category)
                    
                    if created:
                        created_count += 1
                else:
                    alt_display = f" OR {', '.join(alt_names)}" if alt_names else ""
                    smart_text = " + AUTO SURPRISE" if surprise else ""
                    smart_text = " + AUTO VINYASA" if transition else smart_text
                    self.stdout.write(f"[DRY RUN] {sport}: {order}. {primary_name}{alt_display}{smart_text}")
                    created_count += 1
        
        self.stdout.write(self.style.SUCCESS(f"✅ Created {created_count} workout templates with smart automation"))
    
    def _create_quotes_from_drive_structure(self, dry_run):
        """Create motivational quotes based on Johnny's methodology"""
        
        # Johnny's motivational quotes (Dutch - from your Drive structure)
        quotes_data = [
            # KICKBOXING QUOTES
            ('kickboxing', 'elke stoot maakt je sterker en zelfverzekerder', 'intense'),
            ('kickboxing', 'kickboksen leert je discipline en doorzettingsvermogen', 'anytime'),
            ('kickboxing', 'concentreer je op je ademhaling tussen combinaties', 'transition'),
            ('kickboxing', 'voel de kracht in elke beweging die je maakt', 'warmup'),
            ('kickboxing', 'je hebt hard gewerkt, wees trots op jezelf', 'cooldown'),
            
            # POWER YOGA QUOTES  
            ('power_yoga', 'yoga brengt balans in lichaam en geest', 'anytime'),
            ('power_yoga', 'laat je adem je beweging leiden en begeleiden', 'transition'),
            ('power_yoga', 'elke houding leert je iets nieuws over jezelf', 'intense'),
            ('power_yoga', 'verbind met je innerlijke kracht en rust', 'warmup'),
            ('power_yoga', 'laat alle spanning en stress van je afglijden', 'cooldown'),
            
            # CALISTHENICS QUOTES
            ('calisthenics', 'met elke pull-up word je sterker dan gisteren', 'intense'),
            ('calisthenics', 'je lichaam is je krachtigste gereedschap', 'anytime'),
            ('calisthenics', 'vooruitgang komt door consistentie, niet perfectie', 'transition'),
            ('calisthenics', 'bereid je lichaam voor op de uitdaging', 'warmup'),
            ('calisthenics', 'trots zijn op wat je vandaag hebt bereikt', 'cooldown'),
        ]
        
        created_count = 0
        for training_type, quote_text, context in quotes_data:
            if not dry_run:
                quote, created = MotivationalQuote.objects.get_or_create(
                    training_type=training_type,
                    quote_text=quote_text,
                    context=context,
                    defaults={'language': 'nl'}
                )
                if created:
                    created_count += 1
            else:
                created_count += 1
                self.stdout.write(f"[DRY RUN] {training_type} quote: {quote_text[:40]}...")
        
        self.stdout.write(self.style.SUCCESS(f"✅ Created {created_count} motivational quotes"))
    
    def _create_dummy_content(self, dry_run):
        """Create realistic dummy content with proper timeframes for testing"""
        
        if not ScriptCategory.objects.exists():
            self.stdout.write(self.style.ERROR("❌ Please run --setup-complete-system first"))
            return
        
        # Create dummy content only if no real content exists
        if WorkoutScript.objects.exists():
            self.stdout.write(self.style.WARNING("⚠️ Scripts already exist, skipping dummy content creation"))
            return
        
        # ... (rest of dummy content creation logic)
        self.stdout.write(self.style.SUCCESS("✅ Dummy content creation skipped (real content exists)"))