import os
from django.core.management.base import BaseCommand
from django.db import transaction
from scripts.models import WorkoutScript, MotivationalQuote, ScriptCategory, WorkoutTemplate

class Command(BaseCommand):
    help = 'Setup Johnny\'s workout templates based on his methodology (system categories auto-created via migration)'
    
    def add_arguments(self, parser):
        parser.add_argument('--setup-complete-system', action='store_true',
                          help='Setup workout templates following Johnny\'s rules')
        parser.add_argument('--dry-run', action='store_true',
                          help='Preview without making changes')
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No changes will be saved"))
        
        try:
            with transaction.atomic():
                if options['setup_complete_system']:
                    self._setup_johnny_workout_system(dry_run)
                
                if dry_run:
                    raise Exception("Dry run - rolling back")
                    
        except Exception as e:
            if "Dry run" in str(e):
                self.stdout.write(self.style.SUCCESS("✅ Dry run completed successfully"))
            else:
                self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))
    
    def _setup_johnny_workout_system(self, dry_run):
        """Setup Johnny's complete workout system following his methodology"""
        
        self.stdout.write(self.style.SUCCESS("🎯 SETTING UP JOHNNY'S WORKOUT SYSTEM"))
        self.stdout.write("✅ System categories already created via migration")
        
        # Verify system categories exist
        if not dry_run:
            system_categories = ScriptCategory.objects.filter(is_system_category=True)
            if system_categories.count() < 4:
                self.stdout.write(self.style.ERROR("❌ System categories missing! Please run: python manage.py migrate"))
                return
            
            self.stdout.write(f"🔒 Found {system_categories.count()} system categories:")
            for cat in system_categories:
                self.stdout.write(f"   ✅ {cat.name} → {cat.display_name} ({cat.training_type})")
        
        # STEP 1: Create regular categories based on Johnny's Drive structure
        self._create_regular_categories(dry_run)
        
        # STEP 2: Create templates following Johnny's methodology
        self._create_johnny_workout_templates(dry_run)
        
        # STEP 3: Show system summary
        if not dry_run:
            self._show_johnny_system_summary()
    
    def _create_regular_categories(self, dry_run):
        """Create regular workout categories based on Johnny's Google Drive structure"""
        
        self.stdout.write("\n📁 CREATING REGULAR CATEGORIES (Based on Johnny's Drive)")
        self.stdout.write("=" * 60)
        
        # JOHNNY'S ACTUAL DRIVE STRUCTURE
        
        # KICKBOXING: Based on actual Drive folders
        kickboxing_categories = [
            ('kb_warmup', 'Warmup'),
            ('kb_cooldown', 'Cooldown / Shadow Boxing'),  # Johnny uses cooldown as warmup too
            ('kb_footwork', 'Footwork'),
            ('kb_combinations', 'Combinations'),
            ('kb_legs_kicks', 'Legs & Kicks'),
            ('kb_abs', 'Abs Round'),
            ('kb_endurance', 'Endurance'),
            ('kb_defence', 'Defence'),
            ('kb_stretch_relax', 'Stretch and Relax'),
            # kb_surprise already created as system category
        ]
        
        # POWER YOGA: Based on actual Drive + client requests
        power_yoga_categories = [
            ('py_connecting', 'Connecting Phase'),
            ('py_sun_greeting', 'Sun Greeting'),
            ('py_standing', 'Standing Poses'),
            ('py_yoga_flow', 'Yoga Flow'),
            ('py_seated', 'Seated Poses'),
            ('py_lying', 'Lying Poses'),
            ('py_savasana', 'Savasana'),
            ('py_mindfulness', 'Mindfulness'),  # Client requested addition
            # py_vinyasa_s2s and py_vinyasa_s2sit already created as system categories
        ]
        
        # CALISTHENICS: Based on actual Drive + client additions
        calisthenics_categories = [
            ('cal_warmup', 'Warmup'),
            ('cal_pushup', 'Push-up Variations'),
            ('cal_situp', 'Sit-up Variations'),
            ('cal_pullup', 'Pull-up Variations'),
            ('cal_dips', 'Dips Variations'),
            ('cal_lsit', 'L-sit Variations'),
            ('cal_explosive', 'Explosive Moves'),
            ('cal_handstand', 'Handstand Variations'),
            ('cal_back_lever', 'Back-lever Variations'),
            ('cal_front_lever', 'Front-lever Variations'),
            ('cal_planche', 'Planche Variations'),
            ('cal_static_holds', 'Static Holds'),
            # cal_max_challenge already created as system category
        ]
        
        all_categories = [
            ('kickboxing', kickboxing_categories),
            ('power_yoga', power_yoga_categories),
            ('calisthenics', calisthenics_categories)
        ]
        
        created_count = 0
        
        for training_type, categories in all_categories:
            self.stdout.write(f"\n🎯 Creating {training_type} categories...")
            
            for name, display_name in categories:
                if not dry_run:
                    category, created = ScriptCategory.objects.get_or_create(
                        training_type=training_type,
                        name=name,
                        defaults={
                            'display_name': display_name,
                            'description': f'Based on Johnny\'s {training_type} methodology',
                            'is_system_category': False,
                            'is_active': True
                        }
                    )
                    if created:
                        created_count += 1
                        self.stdout.write(f"   ✅ Created: {display_name}")
                    else:
                        self.stdout.write(f"   ⏭️ Exists: {display_name}")
                else:
                    created_count += 1
                    self.stdout.write(f"   [DRY RUN] {display_name}")
        
        self.stdout.write(self.style.SUCCESS(f"\n✅ Created {created_count} regular categories"))
    
    def _create_johnny_workout_templates(self, dry_run):
        """Create workout templates following Johnny's methodology and rules"""
        
        self.stdout.write(self.style.SUCCESS("\n🏗️ CREATING JOHNNY'S WORKOUT TEMPLATES"))
        self.stdout.write("✅ Following Johnny's methodology for each sport")
        
        def get_category(training_type, name):
            if dry_run:
                return type('MockCategory', (), {'id': 1, 'name': name, 'display_name': name})()
            return ScriptCategory.objects.get(training_type=training_type, name=name)
        
        # JOHNNY'S KICKBOXING METHODOLOGY
        self.stdout.write(f"\n🥊 KICKBOXING TEMPLATES (Johnny's Rules)")
        self.stdout.write("📋 Rule: Surprise rounds after core training sections")
        kickboxing_templates = [
            # (order, primary, alternatives, required, add_surprise_after, notes)
            (1, 'kb_warmup', ['kb_cooldown'], True, False, "Start: Warmup OR Shadow Boxing"),
            (2, 'kb_combinations', [], True, True, "Core: Combinations + AUTO-SURPRISE"),
            (3, 'kb_legs_kicks', ['kb_abs'], True, True, "Power: Legs/Kicks OR Abs + AUTO-SURPRISE"),
            (4, 'kb_endurance', ['kb_footwork', 'kb_defence'], False, True, "Optional: Endurance/Footwork/Defence + AUTO-SURPRISE"),
            (5, 'kb_stretch_relax', [], True, False, "End: Stretch and Relax (no surprise)"),
        ]
        
        # JOHNNY'S POWER YOGA METHODOLOGY  
        self.stdout.write(f"\n🧘‍♀️ POWER YOGA TEMPLATES (Johnny's Rules)")
        self.stdout.write("📋 Rule: Vinyasa transitions between pose changes")
        power_yoga_templates = [
            # (order, primary, alternatives, required, add_vinyasa_after, vinyasa_type, notes)
            (1, 'py_connecting', [], True, False, None, "Opening: Breath connection"),
            (2, 'py_sun_greeting', [], True, False, None, "Warmup: Sun salutations"),
            (3, 'py_standing', [], True, True, 'standing_to_standing', "Standing poses + AUTO-VINYASA S→S"),
            (4, 'py_yoga_flow', ['py_standing'], False, True, 'standing_to_standing', "Flow OR More standing + AUTO-VINYASA S→S"),
            (5, 'py_standing', [], False, True, 'standing_to_sitting', "Final standing + AUTO-VINYASA S→Sit"),
            (6, 'py_seated', [], True, False, None, "Seated poses (no more transitions back up)"),
            (7, 'py_lying', [], True, False, None, "Lying poses"),
            (8, 'py_savasana', ['py_mindfulness'], True, False, None, "End: Savasana OR Mindfulness"),
        ]
        
        # JOHNNY'S CALISTHENICS METHODOLOGY
        self.stdout.write(f"\n💪 CALISTHENICS TEMPLATES (Johnny's Rules)")
        self.stdout.write("📋 Rule: MAX challenge at end, progression through difficulty")
        calisthenics_templates = [
            # (order, primary, alternatives, required, add_max_after, notes)
            (1, 'cal_warmup', [], True, False, "Start: Joint mobility"),
            (2, 'cal_pushup', ['cal_situp'], True, False, "Basic: Push-ups OR Sit-ups"),
            (3, 'cal_pullup', ['cal_dips'], True, False, "Strength: Pull-ups OR Dips"),
            (4, 'cal_lsit', ['cal_explosive'], False, False, "Intermediate: L-sit OR Explosive"),
            (5, 'cal_handstand', ['cal_back_lever', 'cal_front_lever', 'cal_planche'], False, False, "Advanced: Choose one advanced move"),
            (6, 'cal_static_holds', [], False, True, "Conditioning + AUTO-MAX CHALLENGE"),
            (7, 'cal_max_challenge', [], True, False, "DIRECT: MAX challenge (ultimate test)"),
        ]
        
        created_count = 0
        
        # Create kickboxing templates
        for order, primary_name, alt_names, required, add_surprise, notes in kickboxing_templates:
            primary_category = get_category('kickboxing', primary_name)
            
            if not dry_run:
                template, created = WorkoutTemplate.objects.get_or_create(
                    training_type='kickboxing',
                    sequence_order=order,
                    defaults={
                        'primary_category': primary_category,
                        'is_required': required,
                        'add_surprise_round_after': add_surprise,
                        'is_active': True,
                    }
                )
                
                # Add alternatives
                template.alternative_categories.clear()
                for alt_name in alt_names:
                    alt_category = get_category('kickboxing', alt_name)
                    template.alternative_categories.add(alt_category)
                
                if created:
                    created_count += 1
                    self.stdout.write(f"   ✅ Step {order}: {notes}")
                else:
                    self.stdout.write(f"   ⏭️ Step {order}: {notes} (exists)")
            else:
                created_count += 1
                self.stdout.write(f"   [DRY RUN] Step {order}: {notes}")
        
        # Create power yoga templates
        for order, primary_name, alt_names, required, add_vinyasa, vinyasa_type, notes in power_yoga_templates:
            primary_category = get_category('power_yoga', primary_name)
            
            if not dry_run:
                template, created = WorkoutTemplate.objects.get_or_create(
                    training_type='power_yoga',
                    sequence_order=order,
                    defaults={
                        'primary_category': primary_category,
                        'is_required': required,
                        'add_vinyasa_transition_after': add_vinyasa,
                        'vinyasa_type': vinyasa_type,
                        'is_active': True,
                    }
                )
                
                # Add alternatives
                template.alternative_categories.clear()
                for alt_name in alt_names:
                    alt_category = get_category('power_yoga', alt_name)
                    template.alternative_categories.add(alt_category)
                
                if created:
                    created_count += 1
                    self.stdout.write(f"   ✅ Step {order}: {notes}")
                else:
                    self.stdout.write(f"   ⏭️ Step {order}: {notes} (exists)")
            else:
                created_count += 1
                self.stdout.write(f"   [DRY RUN] Step {order}: {notes}")
        
        # Create calisthenics templates
        for order, primary_name, alt_names, required, add_max, notes in calisthenics_templates:
            primary_category = get_category('calisthenics', primary_name)
            
            if not dry_run:
                template, created = WorkoutTemplate.objects.get_or_create(
                    training_type='calisthenics',
                    sequence_order=order,
                    defaults={
                        'primary_category': primary_category,
                        'is_required': required,
                        'add_max_challenge_after': add_max,
                        'is_active': True,
                    }
                )
                
                # Add alternatives
                template.alternative_categories.clear()
                for alt_name in alt_names:
                    alt_category = get_category('calisthenics', alt_name)
                    template.alternative_categories.add(alt_category)
                
                if created:
                    created_count += 1
                    self.stdout.write(f"   ✅ Step {order}: {notes}")
                else:
                    self.stdout.write(f"   ⏭️ Step {order}: {notes} (exists)")
            else:
                created_count += 1
                self.stdout.write(f"   [DRY RUN] Step {order}: {notes}")
        
        self.stdout.write(self.style.SUCCESS(f"\n✅ Created {created_count} Johnny-methodology templates"))
    
    def _show_johnny_system_summary(self):
        """Show summary of Johnny's complete workout system"""
        self.stdout.write(self.style.SUCCESS("\n🎯 JOHNNY'S WORKOUT SYSTEM READY"))
        
        self.stdout.write("\n🏆 Johnny's Sport Methodologies:")
        self.stdout.write("   🥊 Kickboxing: Surprise rounds after core training (combos, power, endurance)")
        self.stdout.write("   🧘‍♀️ Power Yoga: Smart vinyasa transitions between pose changes")  
        self.stdout.write("   💪 Calisthenics: Difficulty progression with MAX challenge finale")
        
        self.stdout.write("\n🔒 System Categories (Auto-Protected):")
        self.stdout.write("   🎯 kb_surprise - Auto-inserted after intense kickboxing sections")
        self.stdout.write("   💪 cal_max_challenge - Auto-placed or direct-placed at workout end")
        self.stdout.write("   🌊 py_vinyasa_s2s - Auto-inserted for standing-to-standing flows")
        self.stdout.write("   🌊 py_vinyasa_s2sit - Auto-inserted for standing-to-sitting transitions")
        
        self.stdout.write("\n📋 Template Logic:")
        self.stdout.write("   ✅ OR Logic: 'Combinations OR Footwork' - system picks one")
        self.stdout.write("   ✅ Required vs Optional: Johnny controls what's essential")
        self.stdout.write("   ✅ Smart Timing: AUTO-additions appear exactly where Johnny wants")
        self.stdout.write("   ✅ Sequence Control: Order numbers control workout flow")
        
        self.stdout.write("\n🚀 Next Steps:")
        self.stdout.write("   1. Import scripts: python manage.py import_scripts --folder-path DATABASE_CONTENT")
        self.stdout.write("   2. Import quotes: python manage.py import_quotes --folder-path DATABASE_CONTENT")
        self.stdout.write("   3. Customize templates: http://localhost:8000/admin/scripts/workouttemplate/")
        self.stdout.write("   4. Generate workouts: API endpoints ready")
        
        self.stdout.write("\n💡 Johnny's Control:")
        self.stdout.write("   ✏️ Can customize display names: 'Surprise Rounds' → 'Power Bursts'")
        self.stdout.write("   ✏️ Can enable/disable template steps via checkboxes")
        self.stdout.write("   ✏️ Can modify alternative categories for OR logic")
        self.stdout.write("   ✏️ Can adjust sequence order to change workout flow")
        self.stdout.write("   🚫 Cannot delete system categories (protected)")
        self.stdout.write("   🚫 Cannot change system category names (readonly)")
    
    def _create_dummy_content(self, dry_run):
        """Create dummy content that follows Johnny's methodology"""
        
        if not ScriptCategory.objects.exists():
            self.stdout.write(self.style.ERROR("❌ Please run --setup-complete-system first"))
            return
        
        if WorkoutScript.objects.exists():
            self.stdout.write(self.style.WARNING("⚠️ Scripts already exist, skipping dummy content creation"))
            return
        
        self.stdout.write(self.style.SUCCESS("📝 Creating dummy content following Johnny's methodology..."))
        
        # JOHNNY-STYLE dummy scripts
        dummy_scripts = [
            # KICKBOXING SCRIPTS (Following Johnny's style)
            {
                'title': 'Dynamic Shadow Boxing Warmup',
                'category': 'kb_warmup',
                'duration': 8.0,
                'content': '''Welcome to your Foxing Fit kickboxing session. Time to wake up your warrior.

[pause strong]

Start with gentle shadow boxing. Light jabs, easy crosses. Feel your body awakening.

[pause weak]

[Onthoud,...] will be replaced with motivational quote

Increase the pace gradually. Your body is preparing for battle.''',
                'goal': 'allround',
            },
            {
                'title': 'Fire Combinations',
                'category': 'kb_combinations',
                'duration': 12.0,
                'content': '''Time for combination mastery. This is where technique meets explosive power.

[pause strong]

Basic 1-2: Jab-Cross. Sharp, precise, devastating.

[pause weak]

Add the hook: 1-2-3. Feel the flow, the rhythm of destruction.

[pause strong]

[Onthoud,...] will be replaced with motivational quote

Now move! Side to side, in and out. Combinations with footwork - this is real fighting.''',
                'goal': 'technique',
            },
            {
                'title': 'Lightning Surprise Burst',
                'category': 'kb_surprise',
                'duration': 4.0,
                'content': '''🎯 JOHNNY'S SURPRISE ROUND

[pause strong]

MAXIMUM INTENSITY! Everything you've got for 30 seconds!

[pause weak]

This is where champions are made. Push beyond your limits!

This surprise round appears exactly where Johnny configured it!''',
                'goal': 'endurance',
            },
            
            # POWER YOGA SCRIPTS (Following Johnny's style)
            {
                'title': 'Breath and Intention',
                'category': 'py_connecting',
                'duration': 5.0,
                'content': '''Welcome to your Foxing Fit Power Yoga journey. Let's connect with intention.

[pause strong]

Close your eyes if comfortable. Feel your breath, your heartbeat.

[pause weak]

[Onthoud,...] will be replaced with motivational quote

Set your intention for this practice. What do you want to cultivate today?''',
                'goal': 'flexibility',
            },
            {
                'title': 'Warrior Flow Power',
                'category': 'py_standing',
                'duration': 15.0,
                'content': '''Standing in your power. These are the poses that build strength and determination.

[pause strong]

Warrior I: Feel your foundation, reach for the sky.

[pause weak]

Warrior II: Open your heart, gaze forward with focus.

[pause strong]

[Onthoud,...] will be replaced with motivational quote

This is where yoga becomes powerful. Hold with intention.''',
                'goal': 'strength',
            },
            {
                'title': 'Flowing Vinyasa S→S',
                'category': 'py_vinyasa_s2s',
                'duration': 3.0,
                'content': '''🌊 JOHNNY'S VINYASA TRANSITION

[pause strong]

Flowing with breath from one standing pose to another.

[pause weak]

This transition appears exactly where Johnny configured it!

Move with grace, move with power.''',
                'goal': 'flexibility',
            },
            {
                'title': 'Graceful Vinyasa S→Sit',
                'category': 'py_vinyasa_s2sit',
                'duration': 3.5,
                'content': '''🌊 JOHNNY'S VINYASA TRANSITION

[pause strong]

Graceful transition from standing to seated practice.

[pause weak]

This transition appears exactly where Johnny configured it!

Flow like water, strong like a mountain.''',
                'goal': 'flexibility',
            },
            
            # CALISTHENICS SCRIPTS (Following Johnny's style)
            {
                'title': 'Body Preparation Protocol',
                'category': 'cal_warmup',
                'duration': 8.0,
                'content': '''Welcome to Foxing Fit Calisthenics. Your body is your only equipment.

[pause strong]

Joint rotations: Neck, shoulders, hips, ankles. Wake up every connection.

[pause weak]

[Onthoud,...] will be replaced with motivational quote

Dynamic stretching: Leg swings, arm circles. Your body is your temple.''',
                'goal': 'allround',
            },
            {
                'title': 'Push-up Mastery Progression',
                'category': 'cal_pushup',
                'duration': 10.0,
                'content': '''Time to master the fundamental push-up. Simple, but not easy.

[pause strong]

Standard push-ups first. Perfect form, full range of motion.

[pause weak]

[Onthoud,...] will be replaced with motivational quote

Now variations: Wide grip, diamond, decline. Each one challenges you differently.''',
                'goal': 'strength',
            },
            {
                'title': 'Ultimate MAX Challenge',
                'category': 'cal_max_challenge',
                'duration': 5.0,
                'content': '''💪 JOHNNY'S MAX CHALLENGE

[pause strong]

This is it. Your ultimate test. Everything you've trained for leads to this moment.

[pause weak]

Maximum effort, maximum heart, maximum determination.

This MAX challenge appears exactly where Johnny configured it!

Show yourself what you're truly capable of.''',
                'goal': 'strength',
            }
        ]
        
        created_count = 0
        special_rounds_created = 0
        
        for script_data in dummy_scripts:
            is_special = self._is_special_category(script_data['category'])
            
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
                            'language': 'nl',
                            'notes': 'Johnny-style dummy content for testing methodology'
                        }
                    )
                    if created:
                        created_count += 1
                        if is_special:
                            special_rounds_created += 1
                        special_indicator = self._get_special_indicator(script_data['category'])
                        self.stdout.write(f"   ✅ {script_data['title']} ({script_data['duration']}min) {special_indicator}")
                except ScriptCategory.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"⚠️ Category {script_data['category']} not found"))
            else:
                created_count += 1
                if is_special:
                    special_rounds_created += 1
                special_indicator = self._get_special_indicator(script_data['category'])
                self.stdout.write(f"   [DRY RUN] {script_data['title']} {special_indicator}")
        
        self.stdout.write(self.style.SUCCESS(f"\n✅ Created {created_count} Johnny-style workout scripts"))
        self.stdout.write(self.style.SUCCESS(f"🎯 Created {special_rounds_created} special round scripts"))
        
    
    def _is_special_category(self, category_name):
        """Check if category is a special system category"""
        special_categories = ['kb_surprise', 'cal_max_challenge', 'py_vinyasa_s2s', 'py_vinyasa_s2sit']
        return category_name in special_categories
    
    def _get_special_indicator(self, category_name):
        """Get indicator for special categories"""
        indicators = {
            'kb_surprise': '🎯 (Johnny\'s auto-surprise system)',
            'py_vinyasa_s2s': '🌊 (Johnny\'s auto-vinyasa system)', 
            'py_vinyasa_s2sit': '🌊 (Johnny\'s auto-vinyasa system)',
            'cal_max_challenge': '💪 (Johnny\'s auto-MAX system)',
        }
        return indicators.get(category_name, '')