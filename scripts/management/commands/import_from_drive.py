import os
import re
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from scripts.models import WorkoutScript, MotivationalQuote, ScriptCategory, WorkoutTemplate

class Command(BaseCommand):
    help = 'Setup Johnny\'s workout system with categories, templates and quotes'
    
    def add_arguments(self, parser):
        parser.add_argument('--setup-complete-system', action='store_true', 
                          help='Setup complete system based on Drive structure')
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
                
                if options['create_dummy_content']:
                    self._create_dummy_content(dry_run)
                
                if dry_run:
                    raise Exception("Dry run - rolling back")
                    
        except Exception as e:
            if "Dry run" in str(e):
                self.stdout.write(self.style.SUCCESS("✅ Dry run completed successfully"))
            else:
                self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))
    
    def _setup_complete_system_from_drive(self, dry_run):
        """Create complete system based on Johnny's actual Google Drive structure and client specifications"""
        
        # KICKBOXING STRUCTURE (based on client corrections and Drive folders)
        kickboxing_categories = [
            # Note: cooldown can be used for warmup/shadow boxing too
            ('kb_cooldown', 'Cooldown', 1, False),  # Client: "cooldown: thats where I create shadow boxing in(or as warmup"
            ('kb_footwork', 'Footwork', 2, False),  # Client: "footwork."
            ('kb_combinations', 'Combinations', 2, False),  # Client: "just: Combinations."
            ('kb_legs_kicks', 'Legs & Kicks', 2, False),  # From Drive structure
            ('kb_abs', 'Abs Round', 1, False),  # From Drive structure
            ('kb_endurance', 'Endurance', 2, False),  # From Drive structure
            ('kb_defence', 'Defence', 2, False),  # Client: "defence."
            ('kb_surprise', 'Surprise Rounds', 1, False),  # Client: "Surprise rounds." + For automatic insertion
            ('kb_stretch_relax', 'Stretch and Relax', 1, False),  # From Drive structure
        ]
        
        # POWER YOGA STRUCTURE (client said "pretty good add mindfullness, please.")
        power_yoga_categories = [
            ('py_connecting', 'Connecting Phase', 1, False),
            ('py_sun_greeting', 'Sun Greeting', 1, False),
            ('py_standing', 'Standing Poses', 2, False),
            ('py_yoga_flow', 'Yoga Flow', 2, False),
            ('py_seated', 'Seated Poses', 2, False),
            ('py_lying', 'Lying Poses', 1, False),
            ('py_savasana', 'Savasana', 1, False),
            ('py_mindfulness', 'Mindfulness', 1, False),  # Client requested addition
            # Vinyasa categories for automatic transitions
            ('py_vinyasa_standing_to_standing', 'Vinyasa Standing-to-Standing', 2, False),
            ('py_vinyasa_standing_to_sitting', 'Vinyasa Standing-to-Sitting', 2, False),
        ]
        
        # CALISTHENICS STRUCTURE (based on client additions and Drive folders)
        calisthenics_categories = [
            # Basic exercises
            ('cal_pushup', 'Push-up Variations', 1, False),  # Implied from original list
            ('cal_situp', 'Sit-up Variations', 1, False),  # Implied from original list
            ('cal_pullup', 'Pull-up Variations', 2, False),  # Implied from original list
            ('cal_dips', 'Dips Variations', 2, False),  # Client: "Dips Variations" (from Drive)
            ('cal_lsit', 'L-sit Variations', 2, False),  # Implied from original list
            ('cal_explosive', 'Explosive Moves', 2, False),  # Implied from original list
            # Advanced moves (client additions)
            ('cal_handstand', 'Handstand Variations', 3, False),  # Client: "handstand variations."
            ('cal_back_lever', 'Back-lever Variations', 3, False),  # Client: "back-lever variations."
            ('cal_front_lever', 'Front-lever Variations', 3, False),  # Client: "front-lever variations."
            ('cal_planche', 'Planche Variations', 3, False),  # Client: "planche variations."
            ('cal_static_holds', 'Static Holds', 2, False),  # Client: "static holds."
            ('cal_max_challenge', 'Max Challenge', 2, True),  # Must be last
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
                'no_surprise_after': ['cooldown', 'stretch']
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
        """Create workout templates based on client specifications and Johnny's methodology"""
        
        def get_category(training_type, name):
            if dry_run:
                return type('MockCategory', (), {'id': 1, 'name': name})()
            return ScriptCategory.objects.get(training_type=training_type, name=name)
        
        # KICKBOXING TEMPLATES (updated based on client specifications)
        kickboxing_templates = [
            # (order, primary, alternatives, required, surprise, transition)
            (1, 'kb_cooldown', [], True, False, False),  # Can be warmup/shadow boxing
            (2, 'kb_combinations', [], True, True, False),  # + Surprise
            (3, 'kb_legs_kicks', ['kb_abs'], True, True, False),  # Legs OR Abs + Surprise
            (4, 'kb_endurance', ['kb_footwork', 'kb_defence'], False, True, False), # Optional + Surprise
            (5, 'kb_stretch_relax', [], True, False, False),
        ]
        
        # POWER YOGA TEMPLATES (client approved with mindfulness addition)
        power_yoga_templates = [
            (1, 'py_connecting', [], True, False, False),
            (2, 'py_sun_greeting', [], True, False, False),
            (3, 'py_standing', [], True, False, True),           # Check transitions
            (4, 'py_yoga_flow', ['py_standing'], False, False, True), # Flow OR more standing
            (5, 'py_seated', [], True, False, True),            # Check transitions
            (6, 'py_lying', [], True, False, False),
            (7, 'py_savasana', ['py_mindfulness'], True, False, False),  # Savasana OR mindfulness
        ]
        
        # CALISTHENICS TEMPLATES (based on client additions)
        calisthenics_templates = [
            (1, 'cal_pushup', ['cal_situp'], True, False, False),  # Push-up OR Sit-up
            (2, 'cal_pullup', ['cal_dips'], True, False, False),   # Pull-up OR Dips
            (3, 'cal_lsit', ['cal_explosive'], False, False, False), # L-sit OR Explosive
            (4, 'cal_handstand', ['cal_back_lever', 'cal_front_lever', 'cal_planche'], False, False, False), # Advanced moves
            (5, 'cal_static_holds', [], False, False, False),     # Optional static holds
            (6, 'cal_max_challenge', [], False, False, False),    # Will be moved to end automatically
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
            ('kickboxing', 'focus op je techniek, niet alleen op kracht', 'anytime'),
            ('kickboxing', 'verdediging is net zo belangrijk als aanval', 'transition'),
            
            # POWER YOGA QUOTES  
            ('power_yoga', 'yoga brengt balans in lichaam en geest', 'anytime'),
            ('power_yoga', 'laat je adem je beweging leiden en begeleiden', 'transition'),
            ('power_yoga', 'elke houding leert je iets nieuws over jezelf', 'intense'),
            ('power_yoga', 'verbind met je innerlijke kracht en rust', 'warmup'),
            ('power_yoga', 'laat alle spanning en stress van je afglijden', 'cooldown'),
            ('power_yoga', 'mindfulness begint met bewuste ademhaling', 'anytime'),
            ('power_yoga', 'vind je centrum in elke pose', 'transition'),
            
            # CALISTHENICS QUOTES
            ('calisthenics', 'met elke pull-up word je sterker dan gisteren', 'intense'),
            ('calisthenics', 'je lichaam is je krachtigste gereedschap', 'anytime'),
            ('calisthenics', 'vooruitgang komt door consistentie, niet perfectie', 'transition'),
            ('calisthenics', 'bereid je lichaam voor op de uitdaging', 'warmup'),
            ('calisthenics', 'trots zijn op wat je vandaag hebt bereikt', 'cooldown'),
            ('calisthenics', 'handstand training vergt geduld en moed', 'anytime'),
            ('calisthenics', 'statische houding versterkt lichaam en geest', 'transition'),
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
        
        self.stdout.write("📝 Creating realistic dummy workout scripts...")
        
        # Dummy scripts with realistic durations and content
        dummy_scripts = [
            # KICKBOXING SCRIPTS
            {
                'title': 'Shadow Boxing Warmup',
                'category': 'kb_cooldown',
                'duration': 8.0,
                'content': '''Welcome to your kickboxing session. Let's start with some shadow boxing to warm up your body.

[pause strong]

Begin with light movements. Throw some gentle jabs, feeling your shoulders warming up.

[pause weak]

Add some crosses now. Remember to rotate your hip for power.

[pause strong]

Keep moving, keep breathing. You're preparing your body for the real workout ahead.''',
                'goal': 'allround',
                'intensity': 1
            },
            {
                'title': 'Basic Combinations Training',
                'category': 'kb_combinations',
                'duration': 12.5,
                'content': '''Time for combination work. This is where technique meets power.

[pause strong]

Start with the basic 1-2: jab-cross. Feel the snap in your punches.

[pause weak]

Now add a hook: jab-cross-hook. Keep your guard up between combinations.

[pause strong]

**Onthoud, [elke combinatie maakt je sneller en sterker]**

Let's add some movement. Side to side, in and out.''',
                'goal': 'technique',
                'intensity': 2
            },
            
            # POWER YOGA SCRIPTS
            {
                'title': 'Breath Connection',
                'category': 'py_connecting',
                'duration': 5.0,
                'content': '''Welcome to your power yoga practice. Let's begin by connecting with our breath.

[pause strong]

Find a comfortable seated position. Close your eyes if that feels good.

[pause weak]

Take a deep breath in through your nose... and slowly exhale through your mouth.

[pause strong]

**Onthoud, [je adem is je anker in elke beweging]**''',
                'goal': 'flexibility',
                'intensity': 1
            },
            {
                'title': 'Warrior Flow Sequence',
                'category': 'py_standing',
                'duration': 14.0,
                'content': '''Time for our standing warrior sequence. Feel your strength and stability.

[pause strong]

Step your left foot back into Warrior I. Arms reaching up to the sky.

[pause weak]

Open to Warrior II. Strong legs, relaxed shoulders.

[pause strong]

Flow into reverse warrior. Let your back hand rest on your back leg.

[pause weak]

Return to Warrior II and hold. Feel your power.''',
                'goal': 'strength',
                'intensity': 2
            },
            
            # CALISTHENICS SCRIPTS
            {
                'title': 'Push-up Progression',
                'category': 'cal_pushup',
                'duration': 10.0,
                'content': '''Let's work on push-up variations to build upper body strength.

[pause strong]

Start with standard push-ups. Focus on perfect form.

[pause weak]

Keep your core tight, body in a straight line from head to heels.

[pause strong]

If you need to modify, drop to your knees. No shame in building strength gradually.

[pause weak]

**Onthoud, [elke push-up brengt je dichter bij je doel]**''',
                'goal': 'strength',
                'intensity': 2
            },
            {
                'title': 'Handstand Progression Training',
                'category': 'cal_handstand',
                'duration': 8.0,
                'content': '''Advanced handstand training. This requires patience and practice.

[pause strong]

Start against the wall. Walk your feet up slowly.

[pause weak]

Feel the weight in your hands. Keep your core engaged.

[pause strong]

Don't rush this movement. Handstands take time to master.

[pause weak]

**Onthoud, [geduld en oefening leiden tot meesterschap]**''',
                'goal': 'strength',
                'intensity': 3
            }
        ]
        
        created_count = 0
        for script_data in dummy_scripts:
            if not dry_run:
                try:
                    category = ScriptCategory.objects.get(name=script_data['category'])
                    script, created = WorkoutScript.objects.get_or_create(
                        title=script_data['title'],
                        type=category.training_type,
                        script_category=category,
                        defaults={
                            'content': script_data['content'],
                            'duration_minutes': script_data['duration'],
                            'goal': script_data['goal'],
                            'intensity_level': script_data['intensity'],
                            'transition_type': 'none',
                            'language': 'nl',
                            'notes': 'Dummy content for testing'
                        }
                    )
                    if created:
                        created_count += 1
                except ScriptCategory.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"⚠️ Category {script_data['category']} not found"))
            else:
                created_count += 1
                self.stdout.write(f"[DRY RUN] CREATE: {script_data['title']} ({script_data['duration']}min)")
        
        self.stdout.write(self.style.SUCCESS(f"✅ Created {created_count} dummy workout scripts"))