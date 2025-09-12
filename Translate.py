#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PO MULTILINE PARSER TESTER v1.0
Testing state machine logic for multiline msgid handling
Focus: Parse multiline strings & simple logging
"""

import re
import os
import time
import subprocess
from datetime import datetime
from collections import defaultdict

class POMultilineTester:
    def __init__(self):
        self.source_lang = "en"
        self.target_lang = "id"
        self.log_file = None
        
        # 4-layer mapping system (simplified for testing)
        self.tag_map = defaultdict(str)
        self.var_map = defaultdict(str)
        self.emotion_map = defaultdict(str)
        self.bracket_map = defaultdict(str)
        
        self.tag_counter = 1
        self.var_counter = 1
        self.emotion_counter = 1
        self.bracket_counter = 1
        
        # Statistics
        self.stats = {
            'success': 0,
            'failed': 0,
            'errors': 0,
            'skipped': 0,
            'total_entries': 0
        }

    def init_log_file(self, input_file):
        """Initialize simple log file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.splitext(input_file)[0]
        self.log_file = f"{base_name}_test_log_{timestamp}.txt"
        
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write("=== PO MULTILINE TRANSLATION LOG ===\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Input: {input_file}\n")
            f.write(f"Language: {self.source_lang} -> {self.target_lang}\n")
            f.write("=" * 50 + "\n\n")

    def log_translation(self, line_range, status, original_text, translated_text="", error_msg=""):
        """Log translation result"""
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"LINE {line_range} | STATUS: {status}\n")
            f.write(f"ORIGINAL: {original_text}\n")
            if translated_text and translated_text != original_text:
                f.write(f"RESULT  : {translated_text}\n")
            if error_msg:
                f.write(f"ERROR   : {error_msg}\n")
            f.write("-" * 40 + "\n\n")

    def scan_markup(self, content):
        """Quick scan for markup patterns"""
        # Reset counters
        self.tag_counter = 1
        self.var_counter = 1
        self.emotion_counter = 1
        self.bracket_counter = 1
        
        # Clear maps
        self.tag_map.clear()
        self.var_map.clear()
        self.emotion_map.clear()
        self.bracket_map.clear()
        
        # Scan patterns
        patterns = [
            (r'\{([^{}]+)\}', self.tag_map, 'tag_counter'),
            (r'\[([^\[\]]+)\]', self.var_map, 'var_counter'),
            (r'\(([^()]+)\)', self.emotion_map, 'emotion_counter'),
            (r'<([^<>]+)>', self.bracket_map, 'bracket_counter')
        ]
        
        for pattern, map_dict, counter_name in patterns:
            for match in set(re.findall(pattern, content)):
                # Skip digits for emotions (avoid math expressions)
                if counter_name == 'emotion_counter' and match.replace('.', '').replace(',', '').isdigit():
                    continue
                    
                if match not in map_dict:
                    counter_value = getattr(self, counter_name)
                    map_dict[match] = str(counter_value)
                    setattr(self, counter_name, counter_value + 1)

    def protect_text(self, text):
        """Apply 4-layer protection"""
        protected = text
        
        # Protection replacements
        replacements = [
            (r'\{([^{}]+)\}', lambda m: f"{{{self.tag_map.get(m.group(1), '?')}}}"),
            (r'\[([^\[\]]+)\]', lambda m: f"[{self.var_map.get(m.group(1), '?')}]"),
            (r'\(([^()]+)\)', lambda m: f"({self.emotion_map.get(m.group(1), m.group(1))})"),
            (r'<([^<>]+)>', lambda m: f"<{self.bracket_map.get(m.group(1), '?')}>")
        ]
        
        for pattern, replacement in replacements:
            protected = re.sub(pattern, replacement, protected)
        
        # Protect escape sequences
        escape_map = {
            '\\n': '<!NEWLINE!>',
            '\\t': '<!TAB!>',
            '\\"': '<!QUOTE!>',
            '\\\\': '<!BACKSLASH!>',
            '\\r': '<!CARRIAGE!>'
        }
        
        for old, new in escape_map.items():
            protected = protected.replace(old, new)
        
        return protected

    def translate_text(self, text):
        """Simple translation using translate-shell"""
        if not text or not text.strip():
            return text, "Empty input"
        
        # Check if command only
        if text.strip().startswith('@') or 'res://' in text or text.endswith(('.png', '.jpg', '.mp3')):
            return text, "Command skipped"
        
        try:
            # Escape for shell
            escaped_text = text.replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'")
            
            # Translate command
            cmd = f'trans -brief -no-ansi {self.source_lang}:{self.target_lang} "{escaped_text}"'
            
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=20,
                encoding='utf-8'
            )
            
            if result.returncode != 0:
                return text, "Translation command failed"
            
            translated = result.stdout.strip()
            
            if not translated:
                return text, "Empty translation result"
            
            # Restore escape sequences
            restore_map = {
                '<!NEWLINE!>': '\\n',
                '<!TAB!>': '\\t',
                '<!QUOTE!>': '\\"',
                '<!BACKSLASH!>': '\\\\',
                '<!CARRIAGE!>': '\\r'
            }
            
            for old, new in restore_map.items():
                translated = translated.replace(old, new)
            
            return translated, None
            
        except subprocess.TimeoutExpired:
            return text, "Translation timeout"
        except Exception as e:
            return text, f"Error: {str(e)}"

    def extract_quoted_text(self, line):
        """Extract text from quoted line: '"text"' -> 'text'"""
        line = line.strip()
        if line.startswith('"') and line.endswith('"'):
            return line[1:-1]  # Remove surrounding quotes
        return ""

    def split_translated_text(self, translated_text, original_lines, max_line_length=80):
        """Split translated text back into multiple lines matching original structure"""
        if not translated_text:
            return []
        
        # Simple approach: try to maintain similar line count
        target_line_count = len(original_lines)
        
        if target_line_count == 1:
            return [f'"{translated_text}"']
        
        # Split into words
        words = translated_text.split()
        if not words:
            return [f'"{translated_text}"']
        
        # Distribute words across lines
        lines = []
        words_per_line = max(1, len(words) // target_line_count)
        
        for i in range(0, len(words), words_per_line):
            line_words = words[i:i + words_per_line]
            line_text = ' '.join(line_words)
            
            # Add space at end if not last line (for continuation)
            if i + words_per_line < len(words):
                line_text += ' '
            
            lines.append(f'"{line_text}"')
        
        # If we have too many lines, merge some
        while len(lines) > target_line_count and len(lines) > 1:
            # Merge last two lines
            last_line = lines.pop()
            lines[-1] = lines[-1][:-1] + last_line[1:]  # Remove quotes and merge
        
        return lines

    def process_po_file(self, input_file):
        """Main processing with state machine"""
        print(f"🔍 Testing multiline parser for: {input_file}")
        
        if not os.path.exists(input_file):
            print(f"❌ File not found: {input_file}")
            return False
        
        # Initialize log
        self.init_log_file(input_file)
        
        # Read file
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Quick markup scan
        content = ''.join(lines)
        self.scan_markup(content)
        
        total_markup = len(self.tag_map) + len(self.var_map) + len(self.emotion_map) + len(self.bracket_map)
        print(f"📋 Found {total_markup} markup patterns")
        
        # State machine variables
        mode = 'normal'
        multiline_start_line = 0
        multiline_lines = []
        multiline_text = ""
        processed_lines = []
        
        print(f"🚀 Processing {len(lines)} lines...")
        
        for i, line in enumerate(lines, 1):
            original_line = line.rstrip()
            
            if mode == 'normal':
                # Normal mode: look for single line msgid or multiline start
                if original_line.strip().startswith('msgid "') and not original_line.strip() == 'msgid ""':
                    # Single line msgid
                    print(f"📝 Line {i}: Single line msgid")
                    msgid_match = re.search(r'msgid\s+"([^"]*)"', original_line)
                    if msgid_match:
                        original_text = msgid_match.group(1)
                        if original_text.strip():
                            # Protect and translate
                            protected_text = self.protect_text(original_text)
                            translated_text, error = self.translate_text(protected_text)
                            
                            if error:
                                self.log_translation(str(i), "ERROR", original_text, "", error)
                                self.stats['failed'] += 1
                                processed_lines.append(line)
                            else:
                                self.log_translation(str(i), "SUCCESS", original_text, translated_text)
                                self.stats['success'] += 1
                                processed_lines.append(line)
                                # Next line should be msgstr, we'll handle that separately
                        else:
                            processed_lines.append(line)
                    else:
                        processed_lines.append(line)
                
                elif original_line.strip() == 'msgid ""':
                    # Start multiline mode
                    print(f"🔄 Line {i}: Multiline msgid start")
                    mode = 'multiline'
                    multiline_start_line = i
                    multiline_lines = [line]
                    multiline_text = ""
                
                else:
                    # Regular line (comments, msgstr, etc.)
                    processed_lines.append(line)
            
            elif mode == 'multiline':
                # Multiline mode: collect text lines until msgstr
                if original_line.strip().startswith('"') and original_line.strip().endswith('"'):
                    # Text line in multiline msgid
                    text_part = self.extract_quoted_text(original_line)
                    multiline_text += text_part
                    multiline_lines.append(line)
                    print(f"📄 Line {i}: Collecting text part: '{text_part[:30]}...'")
                
                elif original_line.strip().startswith('msgstr ""'):
                    # End of multiline msgid - trigger translation
                    print(f"✅ Line {i}: Multiline msgid complete ({multiline_start_line}-{i-1})")
                    
                    # Add all collected lines
                    processed_lines.extend(multiline_lines)
                    
                    if multiline_text.strip():
                        # Protect and translate
                        protected_text = self.protect_text(multiline_text)
                        translated_text, error = self.translate_text(protected_text)
                        
                        line_range = f"{multiline_start_line+1}-{i-1}"
                        
                        if error:
                            self.log_translation(line_range, "ERROR", multiline_text, "", error)
                            self.stats['failed'] += 1
                            # Keep original msgstr ""
                            processed_lines.append(line)
                        else:
                            self.log_translation(line_range, "SUCCESS", multiline_text, translated_text)
                            self.stats['success'] += 1
                            
                            # Split translated text into multiple lines
                            original_text_lines = [l for l in multiline_lines if l.strip().startswith('"')]
                            translated_lines = self.split_translated_text(translated_text, original_text_lines)
                            
                            # Add msgstr ""
                            processed_lines.append(line)
                            
                            # Add translated lines
                            for trans_line in translated_lines:
                                processed_lines.append(trans_line + '\n')
                    else:
                        # Empty multiline
                        processed_lines.append(line)
                        self.stats['skipped'] += 1
                    
                    # Reset for normal mode
                    mode = 'normal'
                    multiline_lines = []
                    multiline_text = ""
                    self.stats['total_entries'] += 1
                
                else:
                    # Unexpected line in multiline mode - treat as regular
                    print(f"⚠️ Line {i}: Unexpected line in multiline mode: {original_line.strip()}")
                    processed_lines.append(line)
        
        # Save output file
        output_file = f"{os.path.splitext(input_file)[0]}_test_output.po"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.writelines(processed_lines)
        
        # Print summary
        print(f"\n📊 TESTING RESULTS:")
        print(f"✅ Success: {self.stats['success']}")
        print(f"❌ Failed: {self.stats['failed']}")
        print(f"⏩ Skipped: {self.stats['skipped']}")
        print(f"📄 Output: {output_file}")
        print(f"📋 Log: {self.log_file}")
        
        return True

def main():
    print("=" * 60)
    print("🧪 PO MULTILINE PARSER TESTER v1.0")
    print("Testing state machine logic for multiline msgid handling")
    print("=" * 60)
    
    # Get input file
    po_files = [f for f in os.listdir('.') if f.endswith('.po')]
    
    if not po_files:
        print("❌ No .po files found in current directory!")
        return
    
    print(f"\nFound {len(po_files)} .po file(s):")
    for i, file in enumerate(po_files, 1):
        size = os.path.getsize(file) // 1024
        print(f"[{i}] {file} ({size} KB)")
    
    try:
        choice = int(input(f"\nSelect file [1-{len(po_files)}]: "))
        if 1 <= choice <= len(po_files):
            selected_file = po_files[choice - 1]
            
            tester = POMultilineTester()
            
            # Optional: change languages
            source = input(f"Source language (default: {tester.source_lang}): ").strip()
            if source:
                tester.source_lang = source
            
            target = input(f"Target language (default: {tester.target_lang}): ").strip()
            if target:
                tester.target_lang = target
            
            print(f"\n🚀 Starting test with {tester.source_lang} -> {tester.target_lang}")
            
            success = tester.process_po_file(selected_file)
            
            if success:
                print(f"\n✅ Test completed! Check the output and log files.")
            else:
                print(f"\n❌ Test failed!")
        else:
            print("❌ Invalid selection!")
    
    except (ValueError, KeyboardInterrupt):
        print("\n👋 Test cancelled!")

if __name__ == "__main__":
    main()
