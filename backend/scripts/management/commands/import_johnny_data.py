import csv
from django.core.management.base import BaseCommand
from django.db import transaction
from scripts.models import WorkoutScript, MotivationalQuote, ScriptCategory, WorkoutTemplate

class Command(BaseCommand):
    help = 'Import Johnny\'s scripts and setup his workout templates'
    
    def add_arguments(self, parser):
        parser.add_argument('--scripts-csv', type=str, help='CSV file with workout scripts')
        parser.add_argument('--quotes-csv', type=str, help='CSV file with motivational quotes')
        parser.add_argument('--create-default-structure', action='store_true', 
                          help='Create default workout templates')
        parser.add_argument('--dry-run', action='store_true')
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be saved"))
        
        try:
            with transaction.atomic():
                # Create initial script categories
                if options['create_default_structure']:
                    self._create_script_categories(dry_run)
                    self._create_workout_templates(dry_run)
                    self._create_sample_quotes(dry_run)
                
                # Import scripts
                if options['scripts_csv']:
                    self._import_scripts(options['scripts_csv'], dry_run)
                
                # Import quotes
                if options['quotes_csv']:
                    self._import_quotes(options['quotes_csv'], dry_run)
                
                if dry_run:
                    raise Exception("Dry run - rolling back transaction")
                    
        except Exception as e:
            if "Dry run" in str(e):
                self.stdout.write(self.style.SUCCESS("Dry run completed successfully"))
            else:
                self.stdout.write(self.style.ERROR(f"Error: {e}"))
    
    def _create_script_categories(self, dry_run):
        """Create Johnny's expanded script categories"""
        script_categories_data = [
            # Kickboxing - Johnny's expanded list
            ('kickboxing', 'kb_warmup', 'Warm-up'),
            ('kickboxing', 'kb_combination_building', 'Combination Building'),
            ('kickboxing', 'kb_just_combinations', 'Just Combinations'),
            ('kickboxing', 'kb_knockout_power', 'Knockout Power'),
            ('kickboxing', 'kb_reaction_time', 'Reaction Time'),
            ('kickboxing', 'kb_endurance', 'Endurance Round'),
            ('kickboxing', 'kb_legs_kicks', 'Legs & Kicks'),
            ('kickboxing', 'kb_abs', 'Abs Round'),
            ('kickboxing', 'kb_cooldown', 'Cooldown/Shadow Boxing'),
            ('kickboxing', 'kb_footwork', 'Footwork'),
            ('kickboxing', 'kb_surprise', 'Surprise Rounds'),
            ('kickboxing', 'kb_defence', 'Defence'),
            ('kickboxing', 'kb_stretch_relax', 'Stretch and Relax'),
            
            # Power Yoga - including mindfulness
            ('power_yoga', 'py_connecting', 'Connecting Phase'),
            ('power_yoga', 'py_sun_greeting', 'Sun Greeting'),
            ('power_yoga', 'py_standing', 'Standing Poses'),
            ('power_yoga', 'py_flow', 'Yoga Flow'),
            ('power_yoga', 'py_seated', 'Seated Poses'),
            ('power_yoga', 'py_lying', 'Lying Poses'),
            ('power_yoga', 'py_savasana', 'Savasana (Ending/Relaxation)'),
            ('power_yoga', 'py_mindfulness', 'Mindfulness'),
            
            # Calisthenics - Johnny's expanded list
            ('calisthenics', 'cal_warmup', 'Warm-up'),
            ('calisthenics', 'cal_pushup', 'Push-up Variations'),
            ('calisthenics', 'cal_situp', 'Sit-up Variations'),
            ('calisthenics', 'cal_pullup', 'Pull-up Variations'),
            ('calisthenics', 'cal_dips', 'Dips Variations'),
            ('calisthenics', 'cal_lsit', 'L-sit Variations'),
            ('calisthenics', 'cal_explosive', 'Explosive Moves'),
            ('calisthenics', 'cal_max_challenge', 'Max Challenge'),
            ('calisthenics', 'cal_handstand', 'Handstand Variations'),
            ('calisthenics', 'cal_back_lever', 'Back-lever Variations'),
            ('calisthenics', 'cal_front_lever', 'Front-lever Variations'),
            ('calisthenics', 'cal_planche', 'Planche Variations'),
            ('calisthenics', 'cal_static_holds', 'Static Holds'),
        ]
        
        created_count = 0
        for training_type, name, display_name in script_categories_data:
            if not dry_run:
                category, created = ScriptCategory.objects.get_or_create(
                    training_type=training_type,
                    name=name,
                    defaults={'display_name': display_name}
                )
                if created:
                    created_count += 1
            else:
                created_count += 1
                self.stdout.write(f"[DRY RUN] Would create: {training_type} - {display_name}")
        
        self.stdout.write(
            self.style.SUCCESS(f"Created {created_count} script categories")
        )
    
    def _create_workout_templates(self, dry_run):
        """Create Johnny's flexible workout templates"""
        
        def get_or_create_category(training_type, name):
            if dry_run:
                return type('MockCategory', (), {'id': 1, 'name': name})()
            return ScriptCategory.objects.get(training_type=training_type, name=name)
        
        # Kickboxing template with Johnny's OR logic
        kickboxing_templates = [
            (1, 'kb_warmup', [], True),  # Required
            (2, 'kb_combination_building', ['kb_just_combinations'], False),  # Combo building OR just combos
            (3, 'kb_knockout_power', ['kb_reaction_time', 'kb_endurance'], False),  # Power OR reaction OR endurance
            (4, 'kb_legs_kicks', ['kb_abs'], False),  # Legs OR abs
            (5, 'kb_stretch_relax', [], True),  # Required
        ]
        
        created_count = 0
        for order, primary_name, alt_names, required in kickboxing_templates:
            primary_category = get_or_create_category('kickboxing', primary_name)
            
            if not dry_run:
                template, created = WorkoutTemplate.objects.get_or_create(
                    training_type='kickboxing',
                    sequence_order=order,
                    defaults={
                        'primary_category': primary_category,
                        'is_required': required
                    }
                )
                
                # Add alternatives
                for alt_name in alt_names:
                    alt_category = get_or_create_category('kickboxing', alt_name)
                    template.alternative_categories.add(alt_category)
                
                if created:
                    created_count += 1
            else:
                alt_display = f" OR {', '.join(alt_names)}" if alt_names else ""
                self.stdout.write(f"[DRY RUN] Would create template: {order}. {primary_name}{alt_display}")
                created_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f"Created {created_count} workout templates for Kickboxing")
        )
    
    def _create_sample_quotes(self, dry_run):
        """Create sample motivational quotes"""
        sample_quotes = [
            # Kickboxing
            ('kickboxing', 'Kickboxing is training your mind to get stronger', 'intense'),
            ('kickboxing', 'Every punch makes you more confident', 'anytime'),
            ('kickboxing', 'Focus on your breathing between combinations', 'transition'),
            
            # Power Yoga
            ('power_yoga', 'Power Yoga is good for your balance', 'anytime'),
            ('power_yoga', 'Let your breath guide your movement', 'transition'),
            ('power_yoga', 'Every pose is a chance to find your center', 'intense'),
            
            # Calisthenics
            ('calisthenics', 'with every pull up you\'re getting stronger', 'intense'),
            ('calisthenics', 'Your body is your only equipment', 'anytime'),
            ('calisthenics', 'Progress comes from consistency, not perfection', 'transition'),
        ]
        
        created_count = 0
        for training_type, quote_text, context in sample_quotes:
            if not dry_run:
                quote, created = MotivationalQuote.objects.get_or_create(
                    training_type=training_type,
                    quote_text=quote_text,
                    context=context
                )
                if created:
                    created_count += 1
            else:
                created_count += 1
                self.stdout.write(f"[DRY RUN] Would create quote: {quote_text}")
        
        self.stdout.write(
            self.style.SUCCESS(f"Created {created_count} sample motivational quotes")
        )
    
    def _import_scripts(self, csv_file, dry_run):
        """Import workout scripts from CSV"""
        imported_count = 0
        errors = []
        
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row_num, row in enumerate(reader, 1):
                try:
                    # Map CSV columns to model fields
                    title = row.get('title', '').strip()
                    training_type = row.get('type', '').strip().lower()
                    script_category_name = row.get('script_category', '').strip()
                    goal = row.get('goal', 'allround').strip().lower()
                    content = row.get('content', '').strip()
                    duration_str = row.get('duration', '5.0').strip()
                    
                    # Parse duration
                    if ':' in duration_str:
                        parts = duration_str.split(':')
                        duration = int(parts[0]) + int(parts[1]) / 60
                    else:
                        duration = float(duration_str)
                    
                    # Validate required fields
                    if not all([title, training_type, script_category_name, content]):
                        raise ValueError("Missing required fields")
                    
                    if not dry_run:
                        # Get script category
                        script_category = ScriptCategory.objects.get(
                            training_type=training_type,
                            name=script_category_name
                        )
                        
                        WorkoutScript.objects.create(
                            title=title,
                            type=training_type,
                            script_category=script_category,
                            goal=goal,
                            content=content,
                            duration_minutes=duration,
                            notes=f"Imported from CSV: {csv_file}"
                        )
                    
                    imported_count += 1
                    
                    if dry_run:
                        self.stdout.write(f"[DRY RUN] Would import: {title}")
                
                except Exception as e:
                    error_msg = f"Row {row_num}: {str(e)}"
                    errors.append(error_msg)
                    self.stdout.write(self.style.ERROR(error_msg))
        
        self.stdout.write(
            self.style.SUCCESS(f"Imported {imported_count} workout scripts")
        )
        
        if errors:
            self.stdout.write(
                self.style.WARNING(f"Encountered {len(errors)} errors")
            )
    
    def _import_quotes(self, csv_file, dry_run):
        """Import motivational quotes from CSV"""
        imported_count = 0
        
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                training_type = row.get('training_type', '').strip().lower()
                quote_text = row.get('quote_text', '').strip()
                context = row.get('context', 'anytime').strip().lower()
                
                if training_type and quote_text:
                    if not dry_run:
                        MotivationalQuote.objects.create(
                            training_type=training_type,
                            quote_text=quote_text,
                            context=context
                        )
                    imported_count += 1
                    
                    if dry_run:
                        self.stdout.write(f"[DRY RUN] Would import quote: {quote_text[:50]}...")
        
        self.stdout.write(
            self.style.SUCCESS(f"Imported {imported_count} motivational quotes")
        )