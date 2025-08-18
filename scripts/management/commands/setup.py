import os
from django.core.management.base import BaseCommand
from django.db import transaction
from scripts.models import WorkoutScript, MotivationalQuote, ScriptCategory, WorkoutTemplate

class Command(BaseCommand):
    help = 'Setup Johnny\'s complete workout system with full admin control for all sports'
    
    def add_arguments(self, parser):
        parser.add_argument('--setup-complete-system', action='store_true',
                          help='Setup complete system with admin control for all sports')
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
                    self._setup_complete_admin_control_system(dry_run)
                
                if options['create_dummy_content']:
                    self._create_dummy_content(dry_run)
                
                if dry_run:
                    raise Exception("Dry run - rolling back")
                    
        except Exception as e:
            if "Dry run" in str(e):
                self.stdout.write(self.style.SUCCESS("✅ Dry run completed successfully"))
            else:
                self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))
    
    def _setup_complete_admin_control_system(self, dry_run):
        """Setup complete system with full admin control for all sports"""
        
        self.stdout.write(self.style.SUCCESS("🎯 Setting up COMPLETE ADMIN CONTROL SYSTEM"))
        self.stdout.write("✅ Johnny will have full control over special round placement")
        
        # COMPLETE CATEGORIES - Regular exercises + admin-controlled special categories
        
        # KICKBOXING: Regular categories + admin-controlled surprise rounds
        kickboxing_categories = [
            ('kb_warmup', 'Warmup'),
            ('kb_cooldown', 'Cooldown / Shadow Boxing'),
            ('kb_footwork', 'Footwork'),
            ('kb_combinations', 'Combinations'),
            ('kb_legs_kicks', 'Legs & Kicks'),
            ('kb_abs', 'Abs Round'),
            ('kb_endurance', 'Endurance'),
            ('kb_defence', 'Defence'),
            ('kb_stretch_relax', 'Stretch and Relax'),
            # ADMIN-CONTROLLED: Surprise round category
            ('kb_surprise', 'Surprise Rounds'),
        ]
        
        # POWER YOGA: Regular categories + admin-controlled vinyasa transitions  
        power_yoga_categories = [
            ('py_connecting', 'Connecting Phase'),
            ('py_sun_greeting', 'Sun Greeting'),
            ('py_standing', 'Standing Poses'),
            ('py_yoga_flow', 'Yoga Flow'),
            ('py_seated', 'Seated Poses'),
            ('py_lying', 'Lying Poses'),
            ('py_savasana', 'Savasana'),
            ('py_mindfulness', 'Mindfulness'),
            # ADMIN-CONTROLLED: Vinyasa transition categories
            ('py_vinyasa_s2s', 'Vinyasa Standing-to-Standing'),
            ('py_vinyasa_s2sit', 'Vinyasa Standing-to-Sitting'),
        ]
        
        # CALISTHENICS: Regular categories + admin-controlled MAX challenge
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
            # ADMIN-CONTROLLED: MAX challenge category
            ('cal_max_challenge', 'MAX Challenge'),
        ]
        
        all_categories = [
            ('kickboxing', kickboxing_categories),
            ('power_yoga', power_yoga_categories),
            ('calisthenics', calisthenics_categories)
        ]
        
        created_count = 0
        special_categories_created = 0
        
        for training_type, categories in all_categories:
            self.stdout.write(f"\n📁 Creating {training_type} categories...")
            
            for name, display_name in categories:
                is_special = self._is_admin_controlled_category(name)
                special_indicator = self._get_admin_control_indicator(name)
                
                if not dry_run:
                    category, created = ScriptCategory.objects.get_or_create(
                        training_type=training_type,
                        name=name,
                        defaults={
                            'display_name': display_name,
                            'description': f'Auto-created {training_type} category for admin control system'
                        }
                    )
                    if created:
                        created_count += 1
                        if is_special:
                            special_categories_created += 1
                        self.stdout.write(f"   ✅ Created: {display_name} {special_indicator}")
                    else:
                        self.stdout.write(f"   ⏭️ Exists: {display_name} {special_indicator}")
                else:
                    created_count += 1
                    if is_special:
                        special_categories_created += 1
                    self.stdout.write(f"   [DRY RUN] {display_name} {special_indicator}")
        
        self.stdout.write(self.style.SUCCESS(f"\n✅ Created {created_count} categories"))
        self.stdout.write(self.style.SUCCESS(f"🎯 Created {special_categories_created} admin-controlled special categories"))
        
        # Create admin control templates
        self._create_admin_control_templates(dry_run)
    
    def _is_admin_controlled_category(self, category_name):
        """Check if category is admin-controlled special category"""
        admin_controlled = ['kb_surprise', 'py_vinyasa_s2s', 'py_vinyasa_s2sit', 'cal_max_challenge']
        return category_name in admin_controlled
    
    def _get_admin_control_indicator(self, category_name):
        """Get indicator for admin-controlled categories"""
        indicators = {
            'kb_surprise': '🎯 (Admin controls via template checkboxes)',
            'py_vinyasa_s2s': '🌊 (Admin controls via template checkboxes)', 
            'py_vinyasa_s2sit': '🌊 (Admin controls via template checkboxes)',
            'cal_max_challenge': '💪 (Admin controls via template checkboxes)',
        }
        return indicators.get(category_name, '')
    
    def _create_admin_control_templates(self, dry_run):
        """Create workout templates with full admin control configuration"""
        
        self.stdout.write(self.style.SUCCESS("\n🏗️ Creating workout templates with FULL ADMIN CONTROL"))
        self.stdout.write("✅ Johnny can control ALL special rounds via template checkboxes")
        
        def get_category(training_type, name):
            if dry_run:
                return type('MockCategory', (), {'id': 1, 'name': name, 'display_name': name})()
            return ScriptCategory.objects.get(training_type=training_type, name=name)
        
        # KICKBOXING TEMPLATES - Full admin control over surprise rounds
        self.stdout.write(f"\n🥊 Creating Kickboxing templates with admin-controlled surprise rounds...")
        kickboxing_templates = [
            # (order, primary, alternatives, required, add_surprise_after)
            (1, 'kb_warmup', ['kb_cooldown'], True, False),  # Warmup OR Cooldown
            (2, 'kb_combinations', [], True, True),  # Combinations + ADMIN-CONTROLLED SURPRISE
            (3, 'kb_legs_kicks', ['kb_abs'], True, True),  # Legs/Kicks OR Abs + ADMIN-CONTROLLED SURPRISE  
            (4, 'kb_endurance', ['kb_footwork', 'kb_defence'], False, True), # Optional + ADMIN-CONTROLLED SURPRISE
            (5, 'kb_stretch_relax', [], True, False),  # Final stretch (no surprise)
        ]
        
        # POWER YOGA TEMPLATES - Full admin control over vinyasa
        self.stdout.write(f"\n🧘‍♀️ Creating Power Yoga templates with admin-controlled vinyasa...")
        power_yoga_templates = [
            # (order, primary, alternatives, required, add_vinyasa_after, vinyasa_type)
            (1, 'py_connecting', [], True, False, None),
            (2, 'py_sun_greeting', [], True, False, None),
            (3, 'py_standing', [], True, True, 'standing_to_standing'),  # ADMIN-CONTROLLED VINYASA S→S
            (4, 'py_yoga_flow', ['py_standing'], False, True, 'standing_to_standing'),  # ADMIN-CONTROLLED VINYASA S→S
            (5, 'py_standing', [], False, True, 'standing_to_sitting'),  # ADMIN-CONTROLLED VINYASA S→Sit
            (6, 'py_seated', [], True, False, None),  # No transitions back to standing
            (7, 'py_lying', [], True, False, None),
            (8, 'py_savasana', ['py_mindfulness'], True, False, None),
        ]
        
        # CALISTHENICS TEMPLATES - Full admin control over MAX challenge
        self.stdout.write(f"\n💪 Creating Calisthenics templates with admin-controlled MAX challenge...")
        calisthenics_templates = [
            # (order, primary, alternatives, required, add_max_after)
            (1, 'cal_warmup', [], True, False),
            (2, 'cal_pushup', ['cal_situp'], True, False),
            (3, 'cal_pullup', ['cal_dips'], True, False),
            (4, 'cal_lsit', ['cal_explosive'], False, False),
            (5, 'cal_handstand', ['cal_back_lever', 'cal_front_lever', 'cal_planche'], False, True), # ADMIN-CONTROLLED MAX
            (6, 'cal_static_holds', [], False, False),
            (7, 'cal_max_challenge', [], True, False),  # Direct placement option
        ]
        
        created_count = 0
        admin_control_count = 0
        
        # Create kickboxing templates
        for order, primary_name, alt_names, required, add_surprise in kickboxing_templates:
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
                    if add_surprise:
                        admin_control_count += 1
                    alt_display = f" OR {', '.join(alt_names)}" if alt_names else ""
                    admin_text = " + ADMIN-CONTROLLED SURPRISE" if add_surprise else ""
                    self.stdout.write(f"   ✅ Step {order}: {primary_name}{alt_display}{admin_text}")
                else:
                    self.stdout.write(f"   ⏭️ Step {order}: {primary_name} (exists)")
            else:
                created_count += 1
                if add_surprise:
                    admin_control_count += 1
                alt_display = f" OR {', '.join(alt_names)}" if alt_names else ""
                admin_text = " + ADMIN-CONTROLLED SURPRISE" if add_surprise else ""
                self.stdout.write(f"   [DRY RUN] Step {order}: {primary_name}{alt_display}{admin_text}")
        
        # Create power yoga templates
        for order, primary_name, alt_names, required, add_vinyasa, vinyasa_type in power_yoga_templates:
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
                    if add_vinyasa:
                        admin_control_count += 1
                    alt_display = f" OR {', '.join(alt_names)}" if alt_names else ""
                    admin_text = f" + ADMIN-CONTROLLED VINYASA ({vinyasa_type})" if add_vinyasa and vinyasa_type else ""
                    self.stdout.write(f"   ✅ Step {order}: {primary_name}{alt_display}{admin_text}")
                else:
                    self.stdout.write(f"   ⏭️ Step {order}: {primary_name} (exists)")
            else:
                created_count += 1
                if add_vinyasa:
                    admin_control_count += 1
                alt_display = f" OR {', '.join(alt_names)}" if alt_names else ""
                admin_text = f" + ADMIN-CONTROLLED VINYASA ({vinyasa_type})" if add_vinyasa and vinyasa_type else ""
                self.stdout.write(f"   [DRY RUN] Step {order}: {primary_name}{alt_display}{admin_text}")
        
        # Create calisthenics templates
        for order, primary_name, alt_names, required, add_max in calisthenics_templates:
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
                    if add_max:
                        admin_control_count += 1
                    alt_display = f" OR {', '.join(alt_names)}" if alt_names else ""
                    admin_text = " + ADMIN-CONTROLLED MAX" if add_max else ""
                    admin_text = " (DIRECT PLACEMENT OPTION)" if primary_name == 'cal_max_challenge' else admin_text
                    self.stdout.write(f"   ✅ Step {order}: {primary_name}{alt_display}{admin_text}")
                else:
                    self.stdout.write(f"   ⏭️ Step {order}: {primary_name} (exists)")
            else:
                created_count += 1
                if add_max:
                    admin_control_count += 1
                alt_display = f" OR {', '.join(alt_names)}" if alt_names else ""
                admin_text = " + ADMIN-CONTROLLED MAX" if add_max else ""
                admin_text = " (DIRECT PLACEMENT OPTION)" if primary_name == 'cal_max_challenge' else admin_text
                self.stdout.write(f"   [DRY RUN] Step {order}: {primary_name}{alt_display}{admin_text}")
        
        self.stdout.write(self.style.SUCCESS(f"\n✅ Created {created_count} workout templates"))
        self.stdout.write(self.style.SUCCESS(f"🎯 Configured {admin_control_count} admin-controlled special round placements"))
        
        # Show admin control summary
        if not dry_run:
            self._show_admin_control_summary()
    
    def _show_admin_control_summary(self):
        """Show comprehensive summary of admin control system"""
        self.stdout.write(self.style.SUCCESS("\n🎯 COMPLETE ADMIN CONTROL SYSTEM READY"))
        
        self.stdout.write("\n📋 Johnny's Control Powers:")
        self.stdout.write("   🥊 Kickboxing: Full control over surprise round placement")
        self.stdout.write("   🧘‍♀️ Power Yoga: Full control over vinyasa transition placement")  
        self.stdout.write("   💪 Calisthenics: Full control over MAX challenge placement")
        
        self.stdout.write("\n🎯 How Admin Control Works:")
        self.stdout.write("   ✅ Template checkboxes control WHERE special rounds appear")
        self.stdout.write("   ✅ System auto-finds special categories by name patterns")
        self.stdout.write("   ✅ Intelligent warnings guide optimal placement")
        self.stdout.write("   ✅ Warnings don't block - Johnny has final say")
        
        self.stdout.write("\n🔧 Auto-Detection Patterns:")
        self.stdout.write("   'surprise' in name → kb_surprise category")
        self.stdout.write("   'vinyasa' + 's2s' → py_vinyasa_s2s category")
        self.stdout.write("   'vinyasa' + 's2sit' → py_vinyasa_s2sit category")
        self.stdout.write("   'max' + 'challenge' → cal_max_challenge category")
        
        self.stdout.write("\n🚀 Next Steps:")
        self.stdout.write("   1. Import scripts: python manage.py import_scripts --folder-path DATABASE_CONTENT")
        self.stdout.write("   2. Import quotes: python manage.py import_quotes --folder-path DATABASE_CONTENT")
        self.stdout.write("   3. Configure templates: http://localhost:8000/admin/scripts/workouttemplate/")
        self.stdout.write("   4. Generate workouts: Use API or admin interface")
        
        self.stdout.write("\n💡 Template Configuration Tips:")
        self.stdout.write("   - Check 'add_surprise_round_after' for intense kickboxing steps")
        self.stdout.write("   - Check 'add_vinyasa_transition_after' for yoga pose changes")
        self.stdout.write("   - Check 'add_max_challenge_after' for calisthenics climax")
        self.stdout.write("   - Watch for warnings but make your own decisions")
    
    def _create_dummy_content(self, dry_run):
        """Create dummy content with admin-controlled special rounds for testing"""
        
        if not ScriptCategory.objects.exists():
            self.stdout.write(self.style.ERROR("❌ Please run --setup-complete-system first"))
            return
        
        if WorkoutScript.objects.exists():
            self.stdout.write(self.style.WARNING("⚠️ Scripts already exist, skipping dummy content creation"))
            return
        
        self.stdout.write(self.style.SUCCESS("📝 Creating dummy content for admin control system..."))
        
        # Enhanced dummy scripts including admin-controlled special rounds
        dummy_scripts = [
            # KICKBOXING SCRIPTS
            {
                'title': 'Dynamic Kickboxing Warmup',
                'category': 'kb_warmup',
                'duration': 7.5,
                'content': '''Welcome to your kickboxing session. Let's properly warm up your body.

[pause strong]

Start with arm circles, forward and backward. Feel your shoulders opening up.

[pause weak]

Your body is warming up, ready for the real training ahead.''',
                'goal': 'allround',
            },
            {
                'title': 'Power Combination Training',
                'category': 'kb_combinations',
                'duration': 12.5,
                'content': '''Time for combination work. This is where technique meets power.

[pause strong]

Start with the basic 1-2: jab-cross. Feel the snap in your punches.

[pause weak]

[Onthoud,...] will be replaced with motivational quote

Let's add some movement. Side to side, in and out.''',
                'goal': 'technique',
            },
            {
                'title': 'Lightning Fast Surprise',
                'category': 'kb_surprise',
                'duration': 4.0,
                'content': '''🎯 ADMIN-CONTROLLED SURPRISE ROUND

[pause strong]

Maximum intensity for the next 30 seconds. Everything you've got!

[pause weak]

This surprise round appears exactly where Johnny configured it in templates!''',
                'goal': 'endurance',
            },
            
            # POWER YOGA SCRIPTS
            {
                'title': 'Breath Connection Opening',
                'category': 'py_connecting',
                'duration': 5.0,
                'content': '''Welcome to your power yoga practice. Let's begin by connecting with our breath.

[pause strong]

[Onthoud,...] will be replaced with motivational quote''',
                'goal': 'flexibility',
            },
            {
                'title': 'Warrior Flow Sequence',
                'category': 'py_standing',
                'duration': 14.0,
                'content': '''Time for our standing warrior sequence. Feel your strength and stability.

[pause strong]

Step your left foot back into Warrior I. Arms reaching up to the sky.''',
                'goal': 'strength',
            },
            {
                'title': 'Standing to Sitting Flow',
                'category': 'py_vinyasa_s2sit',
                'duration': 3.5,
                'content': '''🌊 ADMIN-CONTROLLED VINYASA TRANSITION

[pause strong]

Flowing transition from standing to seated poses.

This vinyasa appears exactly where Johnny configured it in templates!''',
                'goal': 'flexibility',
            },
            {
                'title': 'Standing to Standing Flow',
                'category': 'py_vinyasa_s2s',
                'duration': 3.0,
                'content': '''🌊 ADMIN-CONTROLLED VINYASA TRANSITION

[pause strong]

Dynamic flow between standing poses.

This vinyasa appears exactly where Johnny configured it in templates!''',
                'goal': 'flexibility',
            },
            
            # CALISTHENICS SCRIPTS
            {
                'title': 'Joint Mobility Warmup',
                'category': 'cal_warmup',
                'duration': 8.0,
                'content': '''Let's prepare your body for calisthenics training.

[pause strong]

[Onthoud,...] will be replaced with motivational quote''',
                'goal': 'allround',
            },
            {
                'title': 'Progressive Push-up Training',
                'category': 'cal_pushup',
                'duration': 10.0,
                'content': '''Let's work on push-up variations to build upper body strength.

[pause strong]

[Onthoud,...] will be replaced with motivational quote''',
                'goal': 'strength',
            },
            {
                'title': 'Ultimate MAX Challenge',
                'category': 'cal_max_challenge',
                'duration': 5.0,
                'content': '''💪 ADMIN-CONTROLLED MAX CHALLENGE

[pause strong]

Time for the ultimate challenge. This is where you prove your limits.

This MAX challenge appears exactly where Johnny configured it in templates!''',
                'goal': 'strength',
            }
        ]
        
        created_count = 0
        special_rounds_created = 0
        
        for script_data in dummy_scripts:
            is_special = self._is_admin_controlled_category(script_data['category'])
            
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
                            'notes': 'Dummy content for admin control system testing'
                        }
                    )
                    if created:
                        created_count += 1
                        if is_special:
                            special_rounds_created += 1
                        special_indicator = self._get_admin_control_indicator(script_data['category'])
                        self.stdout.write(f"   ✅ {script_data['title']} ({script_data['duration']}min) {special_indicator}")
                except ScriptCategory.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"⚠️ Category {script_data['category']} not found"))
            else:
                created_count += 1
                if is_special:
                    special_rounds_created += 1
                special_indicator = self._get_admin_control_indicator(script_data['category'])
                self.stdout.write(f"   [DRY RUN] {script_data['title']} {special_indicator}")
        
        self.stdout.write(self.style.SUCCESS(f"\n✅ Created {created_count} dummy workout scripts"))
        self.stdout.write(self.style.SUCCESS(f"🎯 Created {special_rounds_created} admin-controlled special round scripts"))
        
        # Create dummy quotes
        if not dry_run:
            self._create_dummy_quotes()
    
    def _create_dummy_quotes(self):
        """Create dummy motivational quotes for testing"""
        dummy_quotes = [
            # General quotes
            ('kickboxing', 'elke stoot maakt je sterker', None),
            ('power_yoga', 'je adem is je anker', None),
            ('calisthenics', 'je lichaam is je gym', None),
            
            # Exercise-specific quotes
            ('kickboxing', 'perfecte combinaties komen van perfecte herhaling', 'kb_combinations'),
            ('power_yoga', 'in balans vind je kracht', 'py_standing'),
            ('calisthenics', 'elke push-up brengt je dichter bij perfectie', 'cal_pushup'),
        ]
        
        created_quotes = 0
        for training_type, quote_text, category_name in dummy_quotes:
            target_category = None
            if category_name:
                try:
                    target_category = ScriptCategory.objects.get(name=category_name)
                except ScriptCategory.DoesNotExist:
                    continue
            
            quote, created = MotivationalQuote.objects.get_or_create(
                training_type=training_type,
                quote_text=quote_text,
                defaults={
                    'target_category': target_category,
                    'language': 'nl'
                }
            )
            if created:
                created_quotes += 1
        
        if created_quotes > 0:
            self.stdout.write(self.style.SUCCESS(f"✅ Created {created_quotes} dummy motivational quotes"))