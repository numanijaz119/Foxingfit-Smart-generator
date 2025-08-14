import os
import re
from django.core.management.base import BaseCommand
from django.db import transaction
from scripts.models import MotivationalQuote

# For DOCX file reading
try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

class Command(BaseCommand):
    help = 'Import motivational quotes from DOCX files in DATABASE_CONTENT quotes folders'
    
    def add_arguments(self, parser):
        parser.add_argument('--folder-path', type=str, default='DATABASE_CONTENT',
                          help='Path to content folder (default: DATABASE_CONTENT)')
        parser.add_argument('--dry-run', action='store_true', 
                          help='Preview without making changes')
        parser.add_argument('--update-existing', action='store_true',
                          help='Update existing quotes if found')
        parser.add_argument('--install-docx', action='store_true',
                          help='Show instructions to install python-docx')
    
    def handle(self, *args, **options):
        # Check if python-docx is available
        if options['install_docx']:
            self._show_docx_installation_instructions()
            return
            
        if not DOCX_AVAILABLE:
            self.stdout.write(self.style.ERROR("❌ python-docx not installed!"))
            self.stdout.write("Run: python manage.py import_quotes --install-docx")
            return
        
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No changes will be saved"))
        
        try:
            with transaction.atomic():
                self._import_quotes_from_folders(
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
    
    def _import_quotes_from_folders(self, folder_path, dry_run, update_existing):
        """Import quotes from DATABASE_CONTENT quotes folders"""
        
        if not os.path.exists(folder_path):
            self.stdout.write(self.style.ERROR(f"❌ Folder {folder_path} does not exist"))
            return
        
        # Track imports
        total_imported = 0
        total_updated = 0
        total_skipped = 0
        errors = []
        
        # Process each sport folder
        for sport_folder in os.listdir(folder_path):
            sport_path = os.path.join(folder_path, sport_folder)
            
            if not os.path.isdir(sport_path):
                continue
                
            # Map sport folder to training type
            sport_type = self._map_sport_folder_to_type(sport_folder)
            if not sport_type:
                self.stdout.write(self.style.WARNING(f"⚠️ Unknown sport folder: {sport_folder}"))
                continue
            
            self.stdout.write(f"\n📁 Processing {sport_folder} ({sport_type}) quotes...")
            
            # Look for quotes folders within sport folder
            quotes_folders_found = 0
            for category_folder in os.listdir(sport_path):
                category_path = os.path.join(sport_path, category_folder)
                
                if not os.path.isdir(category_path):
                    continue
                
                # Check if this is a quotes folder
                if self._is_quotes_folder(category_folder):
                    quotes_folders_found += 1
                    self.stdout.write(f"   📂 Found quotes folder: {category_folder}")
                    
                    # Process all DOCX files in quotes folder
                    docx_files = [f for f in os.listdir(category_path) 
                                 if f.lower().endswith('.docx')]
                    
                    if not docx_files:
                        self.stdout.write(f"   📁 No DOCX files found in {category_folder}")
                        continue
                    
                    self.stdout.write(f"   📄 Found {len(docx_files)} DOCX files")
                    
                    for docx_file in docx_files:
                        file_path = os.path.join(category_path, docx_file)
                        
                        try:
                            results = self._process_quotes_file(
                                file_path, docx_file, sport_type, dry_run, update_existing
                            )
                            total_imported += results['imported']
                            total_updated += results['updated']
                            total_skipped += results['skipped']
                            
                        except Exception as e:
                            error_msg = f"Error processing {file_path}: {str(e)}"
                            errors.append(error_msg)
                            self.stdout.write(self.style.ERROR(f"   ❌ {error_msg}"))
            
            if quotes_folders_found == 0:
                self.stdout.write(f"   ⚠️ No quotes folders found in {sport_folder}")
        
        # Summary
        self.stdout.write(f"\n🎯 QUOTES IMPORT SUMMARY:")
        self.stdout.write(self.style.SUCCESS(f"✅ New quotes imported: {total_imported}"))
        if total_updated > 0:
            self.stdout.write(self.style.SUCCESS(f"🔄 Quotes updated: {total_updated}"))
        if total_skipped > 0:
            self.stdout.write(self.style.WARNING(f"⏭️ Quotes skipped (already exist): {total_skipped}"))
        if errors:
            self.stdout.write(self.style.WARNING(f"⚠️ Errors encountered: {len(errors)}"))
    
    def _map_sport_folder_to_type(self, folder_name):
        """Map sport folder name to training type"""
        folder_lower = folder_name.lower().strip()
        if 'kickbox' in folder_lower:
            return 'kickboxing'
        elif 'yoga' in folder_lower or 'power' in folder_lower:
            return 'power_yoga'
        elif 'calisthen' in folder_lower:
            return 'calisthenics'
        return None
    
    def _is_quotes_folder(self, folder_name):
        """Check if folder contains quotes based on name"""
        folder_lower = folder_name.lower().strip()
        quotes_keywords = ['quote', 'quotes', 'remember', 'onthoud', 'motivational']
        return any(keyword in folder_lower for keyword in quotes_keywords)
    
    def _process_quotes_file(self, file_path, file_name, sport_type, dry_run, update_existing):
        """Process a single DOCX file and extract quotes"""
        
        self.stdout.write(f"   📖 Processing: {file_name}")
        
        # Read DOCX content
        try:
            quotes_text = self._read_docx_content(file_path)
        except Exception as e:
            raise Exception(f"Failed to read DOCX file: {str(e)}")
        
        if not quotes_text:
            self.stdout.write(f"   ⚠️ No content found in {file_name}")
            return {'imported': 0, 'updated': 0, 'skipped': 0}
        
        # Extract quotes starting with "Onthoud"
        quotes = self._extract_quotes_from_text(quotes_text)
        
        if not quotes:
            self.stdout.write(f"   ⚠️ No quotes starting with 'Onthoud' found in {file_name}")
            return {'imported': 0, 'updated': 0, 'skipped': 0}
        
        self.stdout.write(f"   💬 Found {len(quotes)} quotes in {file_name}")
        
        # Process each quote
        results = {'imported': 0, 'updated': 0, 'skipped': 0}
        
        for i, quote_text in enumerate(quotes, 1):
            try:
                # Determine context for this quote
                context = self._determine_quote_context(quote_text, file_name)
                
                # Clean quote text
                clean_quote = self._clean_quote_text(quote_text)
                
                if not clean_quote:
                    continue
                
                # Import/update quote
                result = self._import_single_quote(
                    clean_quote, sport_type, context, dry_run, update_existing, file_name
                )
                results[result] += 1
                
                if dry_run:
                    self.stdout.write(f"   [DRY RUN] Quote {i}: {clean_quote[:80]}... -> {context}")
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"   ❌ Error processing quote {i}: {str(e)}"))
        
        return results
    
    def _read_docx_content(self, file_path):
        """Read content from DOCX file"""
        try:
            doc = docx.Document(file_path)
            content_parts = []
            
            for paragraph in doc.paragraphs:
                text = paragraph.text.strip()
                if text:
                    content_parts.append(text)
            
            return '\n'.join(content_parts)
            
        except Exception as e:
            raise Exception(f"Failed to read DOCX file: {str(e)}")
    
    def _extract_quotes_from_text(self, text):
        """Extract quotes that start with 'Onthoud' from text"""
        quotes = []
        
        # Split text into lines and process
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and section headers
            if not line:
                continue
                
            if line.startswith('**Part') or line.startswith('PART') or 'seconds' in line.lower():
                continue
            
            # Look for lines that start with Onthoud (case insensitive)
            if line.lower().startswith('onthoud'):
                # Extract the quote part after Onthoud
                quote_text = self._extract_single_quote_from_line(line)
                if quote_text and len(quote_text.strip()) > 5:
                    quotes.append(quote_text)
        
        return quotes
    
    def _extract_single_quote_from_line(self, line):
        """Extract a single quote from a line containing Onthoud"""
        
        # Simple approach: find where the actual quote starts
        quote_content = None
        
        # Method 1: Look for [pause weak] and extract what comes after
        if '[pause weak]' in line:
            parts = line.split('[pause weak]', 1)
            if len(parts) == 2:
                quote_content = parts[1].strip()
        
        # Method 2: Look for comma after Onthoud and extract what comes after
        elif line.lower().startswith('onthoud,'):
            parts = line.split(',', 1)
            if len(parts) == 2:
                quote_content = parts[1].strip()
        
        # Method 3: Look for period after Onthoud and extract what comes after  
        elif line.lower().startswith('onthoud.'):
            parts = line.split('.', 1)
            if len(parts) == 2:
                quote_content = parts[1].strip()
        
        # Method 4: Simple fallback - take everything after "onthoud "
        elif line.lower().startswith('onthoud '):
            quote_content = line[8:].strip()  # Skip "onthoud "
        
        if quote_content:
            # Clean up the extracted content
            # Remove any remaining [pause ...] markers
            quote_content = re.sub(r'\[pause\s+\w+\]', '', quote_content)
            # Remove any remaining [...] markers
            quote_content = re.sub(r'\[.*?\]', '', quote_content)
            # Clean up multiple spaces
            quote_content = re.sub(r'\s+', ' ', quote_content)
            
            return quote_content.strip()
        
        return None
    
    def _clean_quote_text(self, quote_text):
        """Clean quote text by removing formatting"""
        
        clean_text = quote_text.strip()
        
        # Remove trailing punctuation if it's just a period
        if clean_text.endswith('.') and not clean_text.endswith('...'):
            clean_text = clean_text[:-1]
        
        # Ensure the quote starts with lowercase
        if clean_text and clean_text[0].isupper() and len(clean_text) > 1:
            first_word = clean_text.split()[0] if clean_text.split() else ""
            # Keep proper nouns uppercase
            if first_word.lower() not in ['nederland', 'johnny', 'yoga']:
                clean_text = clean_text[0].lower() + clean_text[1:]
        
        return clean_text
    
    def _determine_quote_context(self, quote_text, file_name):
        """Determine the context for a quote based on content"""
        
        quote_lower = quote_text.lower()
        
        # High intensity keywords
        intense_keywords = [
            'kracht', 'sterker', 'hard', 'uitdaging', 'challenge',
            'vechten', 'slaan', 'gevecht', 'power', 'explosive'
        ]
        
        # Warmup keywords
        warmup_keywords = [
            'begin', 'start', 'voorbereid', 'prepare', 'warming', 'warm', 'klaar'
        ]
        
        # Cooldown keywords
        cooldown_keywords = [
            'rust', 'ontspan', 'relax', 'kalm', 'trots', 'gedaan', 'zweet'
        ]
        
        # Transition keywords  
        transition_keywords = [
            'focus', 'concentreer', 'ademhaling', 'adem', 'balans', 'ritme'
        ]
        
        # Check quote content for context clues
        if any(keyword in quote_lower for keyword in intense_keywords):
            return 'intense'
        elif any(keyword in quote_lower for keyword in warmup_keywords):
            return 'warmup'
        elif any(keyword in quote_lower for keyword in cooldown_keywords):
            return 'cooldown'
        elif any(keyword in quote_lower for keyword in transition_keywords):
            return 'transition'
        
        return 'anytime'
    
    def _import_single_quote(self, quote_text, sport_type, context, dry_run, update_existing, source_file):
        """Import or update a single motivational quote"""
        
        if not dry_run:
            # Check if quote already exists
            existing_quote = MotivationalQuote.objects.filter(
                training_type=sport_type,
                quote_text=quote_text
            ).first()
            
            if existing_quote:
                if update_existing:
                    existing_quote.context = context
                    existing_quote.save()
                    return 'updated'
                else:
                    return 'skipped'
            else:
                # Create new quote
                MotivationalQuote.objects.create(
                    training_type=sport_type,
                    quote_text=quote_text,
                    context=context,
                    language='nl'
                )
                return 'imported'
        else:
            # Dry run
            existing_quote = MotivationalQuote.objects.filter(
                training_type=sport_type,
                quote_text=quote_text
            ).exists()
            
            if existing_quote:
                return 'skipped' if not update_existing else 'updated'
            else:
                return 'imported'