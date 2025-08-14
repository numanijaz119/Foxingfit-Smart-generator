import os
import re
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from scripts.models import WorkoutScript, ScriptCategory

# For DOCX file reading
try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

class Command(BaseCommand):
    help = 'Import Johnny\'s workout scripts from DATABASE_CONTENT folder structure with DOCX support'
    
    def add_arguments(self, parser):
        parser.add_argument('--folder-path', type=str, default='DATABASE_CONTENT',
                          help='Path to content folder (default: DATABASE_CONTENT)')
        parser.add_argument('--dry-run', action='store_true', 
                          help='Preview without making changes')
        parser.add_argument('--update-existing', action='store_true',
                          help='Update existing scripts if found')
        parser.add_argument('--install-docx', action='store_true',
                          help='Show instructions to install python-docx')
    
    def handle(self, *args, **options):
        # Check if python-docx is available
        if options['install_docx']:
            self._show_docx_installation_instructions()
            return
            
        if not DOCX_AVAILABLE:
            self.stdout.write(self.style.ERROR("❌ python-docx not installed!"))
            self.stdout.write("Run: python manage.py import_from_drive --install-docx")
            return
        
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No changes will be saved"))
        
        try:
            with transaction.atomic():
                self._import_from_local_folder(
                    options['folder_path'], 
                    dry_run, 
                    options['update_existing']
                )
                
                if dry_run:
                    raise Exception("Dry run - rolling back")
                    
        except Exception as e:
            if "Dry run" in str(e):
                self.stdout.write(self.style.SUCCESS("✅ Dry run completed successfully"))
            else:
                self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))
    
    def _show_docx_installation_instructions(self):
        """Show installation instructions for python-docx"""
        self.stdout.write(self.style.SUCCESS("📋 DOCX SUPPORT INSTALLATION"))
        self.stdout.write("")
        self.stdout.write("To read DOCX files, install python-docx:")
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("pip install python-docx"))
        self.stdout.write("")
        self.stdout.write("Or if using pipenv:")
        self.stdout.write(self.style.SUCCESS("pipenv install python-docx"))
        self.stdout.write("")
        self.stdout.write("Or add to requirements.txt:")
        self.stdout.write("python-docx==0.8.11")
    
    def _import_from_local_folder(self, folder_path, dry_run, update_existing):
        """Import workout scripts from DATABASE_CONTENT folder structure"""
        
        if not os.path.exists(folder_path):
            self.stdout.write(self.style.ERROR(f"❌ Folder {folder_path} does not exist"))
            self._show_folder_structure_example(folder_path)
            return
        
        # Define folder name mappings to category names based on EXACT Drive structure
        folder_category_mapping = {
            # KICKBOXING MAPPINGS (based on actual Drive folders)
            'warmup': 'kb_warmup',
            'warm-up': 'kb_warmup',
            'warm up': 'kb_warmup',
            'combinations': 'kb_combinations',
            'combinations (empty)': 'kb_combinations',
            'combo': 'kb_combinations',
            'combos': 'kb_combinations',
            'legs & kicks': 'kb_legs_kicks',
            'legs & kicks ': 'kb_legs_kicks',  # Handle trailing space
            'legs and kicks': 'kb_legs_kicks',
            'legs': 'kb_legs_kicks',
            'kicks': 'kb_legs_kicks',
            'abs round': 'kb_abs',
            'abs': 'kb_abs',
            'footwork': 'kb_footwork',
            'footwork (empty)': 'kb_footwork',
            'defence': 'kb_defence',
            'defence (empty)': 'kb_defence',
            'defense': 'kb_defence',
            'suprise rounds': 'kb_surprise',    # Note: Drive has typo "Suprise"
            'surprise rounds': 'kb_surprise',   # Handle both spellings
            'surprise': 'kb_surprise',
            'cooldown': 'kb_cooldown',
            'cooldown (empty)': 'kb_cooldown',
            'cool-down': 'kb_cooldown',
            'cool down': 'kb_cooldown',
            'endurance': 'kb_endurance',
            'endurance (empty)': 'kb_endurance',
            'stretch and relax': 'kb_stretch_relax',
            'stretch': 'kb_stretch_relax',
            'relax': 'kb_stretch_relax',
            'stretching': 'kb_stretch_relax',
            'quotes': None,  # Skip quotes folders
            
            # POWER YOGA MAPPINGS (based on actual Drive folders)
            'connecting phase': 'py_connecting',
            'connecting': 'py_connecting',
            'sun greeting': 'py_sun_greeting',
            'sun salutation': 'py_sun_greeting',
            'sun': 'py_sun_greeting',
            'standing poses': 'py_standing',
            'standing': 'py_standing',
            'yoga flow': 'py_yoga_flow',
            'flow': 'py_yoga_flow',
            'seated poses': 'py_seated',
            'seated': 'py_seated',
            'sitting poses': 'py_seated',
            'sitting': 'py_seated',
            'lying poses': 'py_lying',
            'lying': 'py_lying',
            'savasana': 'py_savasana',
            'mindfullness': 'py_mindfulness',  # Handle typo from Drive
            'mindfulness': 'py_mindfulness',   # Correct spelling
            'remember quotes': None,  # Skip quotes folders
            
            # CALISTHENICS MAPPINGS (based on actual Drive folders)
            'max challenge': 'cal_max_challenge',
            'max': 'cal_max_challenge',
            'challenge': 'cal_max_challenge',
            'explosive moves': 'cal_explosive',
            'explosive': 'cal_explosive',
            'l-sit variation': 'cal_lsit',
            'l-sit': 'cal_lsit',
            'lsit': 'cal_lsit',
            'l sit': 'cal_lsit',
            'dips variation': 'cal_dips',
            'dips': 'cal_dips',
            'dip': 'cal_dips',
            'handstand variation': 'cal_handstand',
            'handstand variation (empty)': 'cal_handstand',
            'handstand': 'cal_handstand',
            'back-lever variation': 'cal_back_lever',
            'back-lever': 'cal_back_lever',
            'back lever': 'cal_back_lever',
            'front-lever variation': 'cal_front_lever',
            'front-lever': 'cal_front_lever',
            'front lever': 'cal_front_lever',
            'planche variation': 'cal_planche',
            'planche': 'cal_planche',
            'static holds': 'cal_static_holds',
            'static holds (empty)': 'cal_static_holds',
            'static': 'cal_static_holds',
            'holds': 'cal_static_holds',
            'push-up variation': 'cal_pushup',
            'pushup variation': 'cal_pushup',
            'push-up': 'cal_pushup',
            'pushup': 'cal_pushup',
            'push up': 'cal_pushup',
            'pushups': 'cal_pushup',
            'push-ups': 'cal_pushup',
            'sit-up variation': 'cal_situp',
            'situp variation': 'cal_situp',
            'sit-up': 'cal_situp',
            'situp': 'cal_situp',
            'sit up': 'cal_situp',
            'situps': 'cal_situp',
            'sit-ups': 'cal_situp',
            'pull-up variation': 'cal_pullup',
            'pullup variation': 'cal_pullup',
            'pull-up': 'cal_pullup',
            'pullup': 'cal_pullup',
            'pull up': 'cal_pullup',
            'pullups': 'cal_pullup',
            'pull-ups': 'cal_pullup',
            'quotes': None,  # Skip quotes folders
        }
        
        # Walk through the folder structure
        total_imported = 0
        total_updated = 0
        total_skipped = 0
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
            sport_file_count = 0
            for category_folder in os.listdir(sport_path):
                category_path = os.path.join(sport_path, category_folder)
                
                if not os.path.isdir(category_path):
                    continue
                
                # Map folder name to category using EXACT Drive names
                category_name = self._map_folder_to_category(category_folder, folder_category_mapping, sport_type)
                if not category_name:
                    self.stdout.write(f"   ⚠️ Skipping unknown/quotes category: {category_folder}")
                    continue
                
                self.stdout.write(f"   📂 Processing category: {category_folder} -> {category_name}")
                
                # Process files in this category
                category_file_count = 0
                files_in_category = []
                
                # List all files in this category
                try:
                    files_in_category = [f for f in os.listdir(category_path) 
                                       if f.lower().endswith(('.docx', '.txt'))]
                except PermissionError:
                    self.stdout.write(f"   ❌ Permission denied accessing: {category_path}")
                    continue
                
                if not files_in_category:
                    self.stdout.write(f"   📁 Empty category: {category_folder} (no .docx/.txt files)")
                    continue
                
                self.stdout.write(f"   📄 Found {len(files_in_category)} files in {category_folder}")
                
                for file_name in files_in_category:
                    file_path = os.path.join(category_path, file_name)
                    
                    try:
                        result = self._import_single_file(
                            file_path, file_name, sport_type, category_name, dry_run, update_existing
                        )
                        if result == 'created':
                            category_file_count += 1
                            total_imported += 1
                        elif result == 'updated':
                            category_file_count += 1
                            total_updated += 1
                        elif result == 'skipped':
                            total_skipped += 1
                    except Exception as e:
                        error_msg = f"Error importing {file_path}: {str(e)}"
                        errors.append(error_msg)
                        self.stdout.write(self.style.ERROR(f"   ❌ {error_msg}"))
                
                if category_file_count > 0:
                    self.stdout.write(f"   ✅ {category_folder}: {category_file_count} files processed")
                    sport_file_count += category_file_count
                else:
                    self.stdout.write(f"   ⏭️ {category_folder}: No files processed")
            
            if sport_file_count > 0:
                self.stdout.write(f"📊 {sport_folder} total: {sport_file_count} files processed")
        
        # Summary
        self.stdout.write(f"\n🎯 IMPORT SUMMARY:")
        self.stdout.write(self.style.SUCCESS(f"✅ New files imported: {total_imported}"))
        if total_updated > 0:
            self.stdout.write(self.style.SUCCESS(f"🔄 Files updated: {total_updated}"))
        if total_skipped > 0:
            self.stdout.write(self.style.WARNING(f"⏭️ Files skipped (already exist): {total_skipped}"))
        if errors:
            self.stdout.write(self.style.WARNING(f"⚠️ Errors encountered: {len(errors)}"))
            for error in errors[:5]:  # Show first 5 errors
                self.stdout.write(f"   {error}")
    
    def _show_folder_structure_example(self, folder_path):
        """Show example folder structure"""
        self.stdout.write(f"💡 Create folder structure like:")
        self.stdout.write(f"   {folder_path}/")
        self.stdout.write(f"   ├── Kickboxing/")
        self.stdout.write(f"   │   ├── Combinations/")
        self.stdout.write(f"   │   │   ├── Fire breath. (3_25).docx")
        self.stdout.write(f"   │   │   └── Advanced Combinations (12_45).docx")
        self.stdout.write(f"   │   ├── Legs & Kicks/")
        self.stdout.write(f"   ├── Power Yoga/")
        self.stdout.write(f"   │   ├── Standing Poses/")
        self.stdout.write(f"   │   │   └── Warrior Flow (15_20).docx")
        self.stdout.write(f"   └── Calisthenics/")
        self.stdout.write(f"       ├── Dips variation/")
        self.stdout.write(f"       │   └── Progressive Dips (10_15).docx")
    
    def _map_sport_folder_to_type(self, folder_name):
        """Map folder name to training type"""
        folder_lower = folder_name.lower().strip()
        if 'kickbox' in folder_lower:
            return 'kickboxing'
        elif 'yoga' in folder_lower or 'power' in folder_lower:
            return 'power_yoga'
        elif 'calisthen' in folder_lower:
            return 'calisthenics'
        return None
    
    def _map_folder_to_category(self, folder_name, mapping, sport_type=None):
        """Map folder name to script category using EXACT Drive matching with sport-specific warmup handling"""
        folder_clean = folder_name.lower().strip()
        
        # Handle sport-specific warmup mapping first
        if any(word in folder_clean for word in ['warmup', 'warm-up', 'warm up']):
            if sport_type == 'kickboxing':
                return 'kb_warmup'
            elif sport_type == 'calisthenics':
                return 'cal_warmup'
            elif sport_type == 'power_yoga':
                return 'py_connecting'  # Power yoga uses connecting phase as warmup
        
        # Direct mapping first (exact match)
        if folder_clean in mapping:
            mapped_value = mapping[folder_clean]
            # Skip warmup entries in mapping since we handle them above
            if mapped_value and not mapped_value.endswith('_warmup'):
                return mapped_value
        
        # Handle variations and partial matches
        for key, value in mapping.items():
            if value is None:  # Skip None values (quotes folders)
                continue
            # Skip warmup entries since we handle them above
            if value and value.endswith('_warmup'):
                continue
            if key in folder_clean or folder_clean in key:
                return value
        
        # Smart fallback: try to infer category from common words
        return self._infer_category_from_folder_name(folder_clean, sport_type)
    
    def _infer_category_from_folder_name(self, folder_name, sport_type=None):
        """Infer category from folder name using common patterns with sport context"""
        folder_lower = folder_name.lower()
        
        # Handle warmup with sport context
        if any(word in folder_lower for word in ['warmup', 'warm-up', 'warm up']):
            if sport_type == 'kickboxing':
                return 'kb_warmup'
            elif sport_type == 'calisthenics':
                return 'cal_warmup'
            elif sport_type == 'power_yoga':
                return 'py_connecting'
            else:
                return 'warmup_generic'  # Fallback
        
        # KICKBOXING patterns
        elif any(word in folder_lower for word in ['combo', 'combination']):
            return 'kb_combinations'
        elif any(word in folder_lower for word in ['leg', 'kick']):
            return 'kb_legs_kicks'
        elif any(word in folder_lower for word in ['abs', 'core']):
            return 'kb_abs'
        elif any(word in folder_lower for word in ['footwork', 'foot']):
            return 'kb_footwork'
        elif any(word in folder_lower for word in ['defence', 'defense']):
            return 'kb_defence'
        elif any(word in folder_lower for word in ['surprise', 'suprise']):
            return 'kb_surprise'
        elif any(word in folder_lower for word in ['cooldown', 'cool-down', 'cool down']):
            return 'kb_cooldown'
        elif any(word in folder_lower for word in ['endurance', 'cardio']):
            return 'kb_endurance'
        elif any(word in folder_lower for word in ['stretch', 'relax']):
            return 'kb_stretch_relax'
        
        # POWER YOGA patterns
        elif any(word in folder_lower for word in ['connecting', 'connect']):
            return 'py_connecting'
        elif any(word in folder_lower for word in ['sun', 'greeting', 'salutation']):
            return 'py_sun_greeting'
        elif any(word in folder_lower for word in ['standing', 'stand']):
            return 'py_standing'
        elif any(word in folder_lower for word in ['flow', 'vinyasa']):
            return 'py_yoga_flow'
        elif any(word in folder_lower for word in ['seated', 'sitting', 'sit']):
            return 'py_seated'
        elif any(word in folder_lower for word in ['lying', 'lie', 'supine']):
            return 'py_lying'
        elif any(word in folder_lower for word in ['savasana', 'corpse']):
            return 'py_savasana'
        elif any(word in folder_lower for word in ['mindfulness', 'mindfullness', 'meditation']):
            return 'py_mindfulness'
        
        # CALISTHENICS patterns
        elif any(word in folder_lower for word in ['max', 'challenge']):
            return 'cal_max_challenge'
        elif any(word in folder_lower for word in ['explosive', 'plyometric']):
            return 'cal_explosive'
        elif any(word in folder_lower for word in ['l-sit', 'lsit', 'l sit']):
            return 'cal_lsit'
        elif any(word in folder_lower for word in ['dip']):
            return 'cal_dips'
        elif any(word in folder_lower for word in ['handstand']):
            return 'cal_handstand'
        elif any(word in folder_lower for word in ['back', 'lever']) and 'back' in folder_lower:
            return 'cal_back_lever'
        elif any(word in folder_lower for word in ['front', 'lever']) and 'front' in folder_lower:
            return 'cal_front_lever'
        elif any(word in folder_lower for word in ['planche']):
            return 'cal_planche'
        elif any(word in folder_lower for word in ['static', 'hold', 'isometric']):
            return 'cal_static_holds'
        elif any(word in folder_lower for word in ['push', 'pushup']):
            return 'cal_pushup'
        elif any(word in folder_lower for word in ['sit', 'situp', 'crunch']) and ('up' in folder_lower or 'crunch' in folder_lower):
            return 'cal_situp'
        elif any(word in folder_lower for word in ['pull', 'pullup']):
            return 'cal_pullup'
        
        # Skip quotes and other non-exercise folders
        elif any(word in folder_lower for word in ['quote', 'remember', 'notes']):
            return None
        elif any(word in folder_lower for word in ['stretch', 'relax']):
            return 'kb_stretch_relax'
        
        # POWER YOGA patterns
        elif any(word in folder_lower for word in ['connecting', 'connect']):
            return 'py_connecting'
        elif any(word in folder_lower for word in ['sun', 'greeting', 'salutation']):
            return 'py_sun_greeting'
        elif any(word in folder_lower for word in ['standing', 'stand']):
            return 'py_standing'
        elif any(word in folder_lower for word in ['flow', 'vinyasa']):
            return 'py_yoga_flow'
        elif any(word in folder_lower for word in ['seated', 'sitting', 'sit']):
            return 'py_seated'
        elif any(word in folder_lower for word in ['lying', 'lie', 'supine']):
            return 'py_lying'
        elif any(word in folder_lower for word in ['savasana', 'corpse']):
            return 'py_savasana'
        elif any(word in folder_lower for word in ['mindfulness', 'mindfullness', 'meditation']):
            return 'py_mindfulness'
        
        # CALISTHENICS patterns
        elif any(word in folder_lower for word in ['max', 'challenge']):
            return 'cal_max_challenge'
        elif any(word in folder_lower for word in ['explosive', 'plyometric']):
            return 'cal_explosive'
        elif any(word in folder_lower for word in ['l-sit', 'lsit', 'l sit']):
            return 'cal_lsit'
        elif any(word in folder_lower for word in ['dip']):
            return 'cal_dips'
        elif any(word in folder_lower for word in ['handstand']):
            return 'cal_handstand'
        elif any(word in folder_lower for word in ['back', 'lever']) and 'back' in folder_lower:
            return 'cal_back_lever'
        elif any(word in folder_lower for word in ['front', 'lever']) and 'front' in folder_lower:
            return 'cal_front_lever'
        elif any(word in folder_lower for word in ['planche']):
            return 'cal_planche'
        elif any(word in folder_lower for word in ['static', 'hold', 'isometric']):
            return 'cal_static_holds'
        elif any(word in folder_lower for word in ['push', 'pushup']):
            return 'cal_pushup'
        elif any(word in folder_lower for word in ['sit', 'situp', 'crunch']) and ('up' in folder_lower or 'crunch' in folder_lower):
            return 'cal_situp'
        elif any(word in folder_lower for word in ['pull', 'pullup']):
            return 'cal_pullup'
        
        # Skip quotes and other non-exercise folders
        elif any(word in folder_lower for word in ['quote', 'remember', 'notes']):
            return None
        
        # If no pattern matches, return None (will be skipped with warning)
        return None
    
    def _import_single_file(self, file_path, file_name, sport_type, category_name, dry_run, update_existing):
        """Import a single workout script file"""
        
        # Extract duration from filename FIRST (this is the key fix)
        duration = self._extract_duration_from_filename(file_name)
        
        # Clean title from filename (remove duration and Round prefixes)
        title = self._clean_title_from_filename(file_name)
        
        # Read file content based on file type
        content = self._read_file_content(file_path, file_name)
        
        if not content or len(content.strip()) < 10:
            content = self._create_placeholder_content(file_name, duration)
        
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
                raise Exception(f"Category '{category_name}' not found for {sport_type}. Please run setup-complete-system first.")
            
            # Check if script already exists
            existing_script = WorkoutScript.objects.filter(
                title=title,
                type=sport_type,
                script_category=script_category
            ).first()
            
            if existing_script:
                if update_existing:
                    # Update existing script
                    existing_script.content = content
                    existing_script.duration_minutes = duration
                    existing_script.goal = goal
                    existing_script.intensity_level = intensity
                    existing_script.transition_type = transition_type
                    existing_script.notes = f'Updated from {file_path}'
                    existing_script.save()
                    return 'updated'
                else:
                    return 'skipped'
            else:
                # Create new script
                WorkoutScript.objects.create(
                    title=title,
                    type=sport_type,
                    script_category=script_category,
                    content=content,
                    duration_minutes=duration,
                    goal=goal,
                    intensity_level=intensity,
                    transition_type=transition_type,
                    language='nl',
                    notes=f'Imported from {file_path}'
                )
                return 'created'
        else:
            # Dry run output
            content_preview = content[:100] + "..." if len(content) > 100 else content
            self.stdout.write(
                f"   [DRY RUN] CREATE: {title} ({duration:.2f}min, {goal}, intensity:{intensity}, category:{category_name})"
            )
            self.stdout.write(f"     Content preview: {content_preview}")
            return 'created'
    
    def _read_file_content(self, file_path, file_name):
        """Read content from DOCX or TXT file"""
        try:
            if file_path.lower().endswith('.docx'):
                return self._read_docx_content(file_path)
            elif file_path.lower().endswith('.txt'):
                return self._read_txt_content(file_path)
            else:
                return ""
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"   ⚠️ Could not read {file_name}: {str(e)}"))
            return ""
    
    def _read_docx_content(self, file_path):
        """Read content from DOCX file using python-docx"""
        try:
            doc = docx.Document(file_path)
            content_parts = []
            
            for paragraph in doc.paragraphs:
                text = paragraph.text.strip()
                if text:
                    content_parts.append(text)
            
            content = '\n\n'.join(content_parts)
            
            # Clean up the content
            content = self._clean_docx_content(content)
            
            return content
            
        except Exception as e:
            raise Exception(f"Failed to read DOCX file: {str(e)}")
    
    def _read_txt_content(self, file_path):
        """Read content from TXT file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            return content
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read().strip()
                return content
            except Exception as e:
                raise Exception(f"Failed to read TXT file with UTF-8 or Latin-1 encoding: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to read TXT file: {str(e)}")
    
    def _clean_docx_content(self, content):
        """Clean up content extracted from DOCX"""
        if not content:
            return ""
        
        # Remove excessive newlines
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # Remove leading/trailing whitespace
        content = content.strip()
        
        # Add pause markers if they don't exist (basic heuristic)
        if '[pause' not in content.lower():
            # Add pause markers at the end of sentences and paragraphs
            content = re.sub(r'\.(\s*\n)', '.\n\n[pause weak]\n', content)
            content = re.sub(r'\n\n(?!\[pause)', '\n\n[pause strong]\n\n', content)
        
        return content
    
    def _create_placeholder_content(self, filename, duration):
        """Create placeholder content when file cannot be read"""
        return f"""[FILE: {filename}]
Duration: {duration:.2f} minutes

⚠️ CONTENT COULD NOT BE READ AUTOMATICALLY

📋 TO COMPLETE THIS SCRIPT:
1. Open the original file: {filename}
2. Copy the workout content manually
3. Edit this script in the Django admin
4. Replace this placeholder with the actual workout content
5. Add [pause strong] and [pause weak] markers as needed

💡 Remember to include:
- Clear exercise instructions
- Breathing cues
- Motivational elements
- Proper pause markers for voice recording

This script was automatically imported from: {filename}
"""
    
    def _extract_duration_from_filename(self, filename):
        """
        Extract duration from filename with improved parsing
        
        Expected patterns:
        - "Fire breath. (3_25).docx" -> 3 minutes 25 seconds = 3.417 minutes
        - "Exercise name (8_30).docx" -> 8 minutes 30 seconds = 8.5 minutes
        - "Exercise name (0_45).docx" -> 0 minutes 45 seconds = 0.75 minutes
        - "Exercise name (15_00).docx" -> 15 minutes 0 seconds = 15.0 minutes
        """
        # Remove extension first
        name_without_ext = os.path.splitext(filename)[0]
        
        self.stdout.write(f"   🔍 Analyzing filename: {name_without_ext}")
        
        # Pattern 1: (MM_SS) format - PRIMARY FORMAT
        # Matches: (3_25), (8_30), (0_45), (15_00), etc.
        underscore_pattern = r'\((\d{1,2})_(\d{2})\)'
        match = re.search(underscore_pattern, name_without_ext)
        
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            
            # Validate seconds (should be 0-59)
            if seconds > 59:
                self.stdout.write(f"   ⚠️ Invalid seconds value: {seconds}, treating as 59")
                seconds = 59
            
            total_minutes = minutes + (seconds / 60.0)
            self.stdout.write(f"   ⏱️ Found underscore time pattern: ({minutes}_{seconds:02d}) = {minutes}m {seconds}s = {total_minutes:.3f} minutes")
            return total_minutes
        
        # Pattern 2: (MM:SS) format - legacy colon format
        colon_pattern = r'\((\d{1,2}):(\d{2})\)'
        match = re.search(colon_pattern, name_without_ext)
        
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            
            # Validate seconds
            if seconds > 59:
                seconds = 59
            
            total_minutes = minutes + (seconds / 60.0)
            self.stdout.write(f"   ⏱️ Found colon time pattern: ({minutes}:{seconds:02d}) = {minutes}m {seconds}s = {total_minutes:.3f} minutes")
            return total_minutes
        
        # Pattern 3: (XX seconds) or (XX seconden) format
        seconds_pattern = r'\((\d+)\s*(seconds?|seconden?|sec)\s*\)'
        match = re.search(seconds_pattern, name_without_ext, re.IGNORECASE)
        
        if match:
            seconds = int(match.group(1))
            total_minutes = seconds / 60.0
            self.stdout.write(f"   ⏱️ Found seconds pattern: {seconds} seconds = {total_minutes:.3f} minutes")
            return total_minutes
        
        # Pattern 4: (XX min) format
        minutes_pattern = r'\((\d+)\s*min(?:utes?)?\s*\)'
        match = re.search(minutes_pattern, name_without_ext, re.IGNORECASE)
        
        if match:
            minutes = int(match.group(1))
            self.stdout.write(f"   ⏱️ Found minutes pattern: {minutes} minutes")
            return float(minutes)
        
        # Pattern 5: Single number in parentheses (assume minutes if reasonable)
        single_number_pattern = r'\((\d{1,2})\)'
        match = re.search(single_number_pattern, name_without_ext)
        
        if match:
            number = int(match.group(1))
            if number <= 60:  # Assume minutes if 60 or less
                self.stdout.write(f"   ⏱️ Found single number pattern (assuming minutes): {number} minutes")
                return float(number)
        
        # If no duration found, use category defaults
        default_duration = self._get_default_duration_for_category(filename, name_without_ext)
        self.stdout.write(f"   ⚠️ No time pattern found, using default: {default_duration} minutes")
        return default_duration
    
    def _get_default_duration_for_category(self, filename, clean_name):
        """Get default duration based on filename patterns and category"""
        filename_lower = filename.lower()
        clean_lower = clean_name.lower()
        
        # Default durations based on common patterns
        if 'quote' in filename_lower:
            return 0.083  # 5 seconds
        elif any(word in clean_lower for word in ['warmup', 'warm-up', 'warm up']):
            return 8.0
        elif any(word in clean_lower for word in ['cooldown', 'cool-down', 'stretch', 'relax']):
            return 6.0
        elif any(word in clean_lower for word in ['max', 'challenge']):
            return 5.0
        elif any(word in clean_lower for word in ['surprise', 'suprise']):
            return 4.0
        elif any(word in clean_lower for word in ['connecting', 'savasana']):
            return 5.0
        elif any(word in clean_lower for word in ['sun', 'greeting', 'salutation']):
            return 8.0
        elif any(word in clean_lower for word in ['flow', 'yoga', 'standing', 'seated', 'lying']):
            return 12.0
        elif any(word in clean_lower for word in ['endurance', 'cardio']):
            return 15.0
        elif any(word in clean_lower for word in ['combination', 'combo']):
            return 12.0
        elif any(word in clean_lower for word in ['legs', 'kicks', 'abs']):
            return 10.0
        elif any(word in clean_lower for word in ['handstand', 'lever', 'planche']):
            return 8.0
        else:
            return 10.0  # Default 10 minutes
    
    def _clean_title_from_filename(self, filename):
        """Clean up filename to create a proper title"""
        # Remove extension
        title = os.path.splitext(filename)[0]
        
        # Remove ALL duration patterns first
        title = re.sub(r'\(\d{1,2}_\d{2}\)', '', title)  # Remove (MM_SS)
        title = re.sub(r'\(\d{1,2}:\d{2}\)', '', title)  # Remove (MM:SS)
        title = re.sub(r'\(\d+\s*(seconds?|seconden?|sec)\s*\)', '', title, flags=re.IGNORECASE)  # Remove (XX seconds)
        title = re.sub(r'\(\d+\s*min(?:utes?)?\s*\)', '', title, flags=re.IGNORECASE)  # Remove (XX min)
        title = re.sub(r'\(\d{1,4}\)', '', title)  # Remove any remaining numbers in parentheses
        
        # Remove common prefixes like "Round 1:", "Ronde 2:", etc.
        title = re.sub(r'^(Round|Ronde)\s*\d+\s*:?\s*', '', title, flags=re.IGNORECASE)
        
        # Replace underscores and hyphens with spaces
        title = title.replace('_', ' ').replace('-', ' ')
        
        # Remove extra periods and spaces
        title = re.sub(r'\.+', '.', title)  # Multiple periods to single
        title = title.rstrip('.')  # Remove trailing periods
        
        # Clean up multiple spaces and trim
        title = re.sub(r'\s+', ' ', title).strip()
        
        # Capitalize first letter of each word
        title = title.title()
        
        return title
    
    def _determine_intensity_level(self, category_name, title, content):
        """Determine intensity level based on category and content"""
        
        # High intensity categories
        high_intensity = [
            'kb_endurance', 'kb_surprise', 'cal_explosive', 'cal_max_challenge'
        ]
        
        # WARMUP patterns - need to determine sport context
        low_intensity = [
            'kb_cooldown', 'kb_stretch_relax', 'kb_warmup',  # Added kb_warmup
            'py_connecting', 'py_savasana', 'py_mindfulness',
            'cal_warmup'  # Added cal_warmup
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