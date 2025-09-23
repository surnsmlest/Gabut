#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REN'PY BATCH TRANSLATOR v6.0 (MODIFIED FOR BATCH PROCESSING)
- Process all .rpy files in specified folder
- Flexible filename handling
- Improved output naming system
- Progress tracking for Telegram notifications
"""

import re
import os
import sys
import time
import subprocess
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# ================ CONFIG ================
BATCH_FOLDER = sys.argv[1] if len(sys.argv) > 1 else "batch_kecil"  # Folder containing .rpy files
BAHASA_ASAL = "en"                  # Source language
BAHASA_TUJUAN = "id"                # Target language  
JEDA_TERJEMAH = 0.3                 # Delay between translations (seconds)
LOG_LEVEL = "ERROR"                 # Options: ALL, ERROR, SUMMARY
OUTPUT_FOLDER = "output_tl"         # Output folder for translated files
# ========================================

class RenPyBatchTranslator:
    def __init__(self, input_file):
        self.input_file = input_file
        self.filename_base = Path(input_file).stem  # filename without extension
        self.output_file = self._generate_output_name()
        self.mapping_file = self._generate_mapping_name()
        self.log_file = self._generate_log_name()
        self.tag_map = defaultdict(str)
        self.var_map = defaultdict(str)
        self.tag_counter = 1
        self.var_counter = 1
        self.total_lines = 0

        # Logging counters
        self.translation_stats = {
            'success': 0,
            'failed': 0,
            'empty_input': 0,
            'empty_output': 0,
            'errors': 0,
            'skipped_code': 0,
            'total_processed': 0
        }

        # Ren'Py keywords yang TIDAK boleh ditranslate
        self.skip_keywords = [
            'show ', 'scene ', 'play ', 'stop ', 'queue ',
            'image ', 'define ', 'transform ', 'screen ',
            'jump ', 'call ', 'return', 'menu:', 'if ',
            'python:', 'init ', 'label ', 'with ',
            'hide ', 'at ', 'as ', '$', 'pause',
            'nvl ', 'window ', 'voice ', 'sound ',
            'music ', 'audio ', 'renpy.', 'camera '
        ]

    def _generate_output_name(self):
        """Generate output filename: original_name_lang.rpy"""
        return os.path.join(OUTPUT_FOLDER, f"{self.filename_base}_{BAHASA_TUJUAN}.rpy")

    def _generate_mapping_name(self):
        """Generate mapping filename: filename_mapping.txt"""
        return f"{self.filename_base}_mapping.txt"

    def _generate_log_name(self):
        """Generate log filename: filename_log.txt"""
        return f"{self.filename_base}_log.txt"

    def _write_progress(self, status, success_rate=0):
        """Tulis progress ke file untuk dibaca GitHub Actions"""
        progress_file = "translation_progress.txt"
        try:
            with open(progress_file, 'a', encoding='utf-8') as f:
                if status == "started":
                    f.write(f"🔄 STARTED:{self.filename_base}\n")
                elif status == "completed":
                    f.write(f"✅ COMPLETED:{self.filename_base}:{success_rate:.1f}%\n")
                elif status == "failed":
                    f.write(f"❌ FAILED:{self.filename_base}\n")
        except Exception as e:
            print(f"⚠️  Error writing progress: {e}")

    def _init_log_file(self):
        if LOG_LEVEL == "SUMMARY":
            return
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write("=== REN'PY TRANSLATION LOG v6.0 ===\n")
            f.write(f"Tanggal: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Input: {self.input_file}\n")
            f.write(f"Output: {self.output_file}\n")
            f.write(f"Bahasa: {BAHASA_ASAL} -> {BAHASA_TUJUAN}\n")
            f.write(f"Log Level: {LOG_LEVEL}\n")
            f.write("="*50 + "\n\n")

    def _log_translation(self, line_num, status, original_text, translated_text="", error_msg="", context=""):
        if LOG_LEVEL == "SUMMARY":
            return
        elif LOG_LEVEL == "ERROR" and status == "SUCCESS":
            return
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"BARIS {line_num} | STATUS: {status}\n")
            if context:
                f.write(f"CONTEXT: {context.strip()}\n")
            f.write(f"ASLI   : '{original_text}'\n")
            if translated_text and translated_text != original_text:
                f.write(f"HASIL  : '{translated_text}'\n")
            if error_msg:
                f.write(f"ERROR  : {error_msg}\n")
            f.write("-" * 40 + "\n\n")

    def _protect_escapes(self, text):
        replacements = {
            '\\n': '<!NEWLINE!>',
            '\\t': '<!TAB!>',
            '\\"': '<!QUOTE!>',
            '\\\\': '<!BACKSLASH!>',
            '\\r': '<!CARRIAGE!>',
            '\\{': '<!LEFTBRACE!>',
            '\\}': '<!RIGHTBRACE!>'
        }
        protected = text
        for old, new in replacements.items():
            protected = protected.replace(old, new)
        return protected

    def _restore_escapes(self, text):
        replacements = {
            '<!NEWLINE!>': '\\n',
            '<!TAB!>': '\\t',
            '<!QUOTE!>': '\\"',
            '<!BACKSLASH!>': '\\\\',
            '<!CARRIAGE!>': '\\r',
            '<!LEFTBRACE!>': '\\{',
            '<!RIGHTBRACE!>': '\\}'
        }
        restored = text
        for old, new in replacements.items():
            restored = restored.replace(old, new)
        # Clean up extra spaces around tags
        restored = re.sub(r'\{\s+', '{', restored)
        restored = re.sub(r'\s+\}', '}', restored)
        return restored

    def _should_translate(self, line, text_match):
        """
        MODIFIED: Translate ALL text inside quotes unless it's Ren'Py code/filename/path!
        """
        before_quote = line[:text_match.start()].strip().lower()

        # Skip jika ada keyword Ren'Py di awal baris
        for keyword in self.skip_keywords:
            if before_quote.startswith(keyword.lower()):
                return False

        # Skip jika ada tanda $ (Python code)
        if '$' in before_quote:
            return False

        # Skip jika di dalam menu options yang pendek
        if before_quote.endswith(':'):
            return False

        # Skip jika ini adalah block old
        if before_quote.endswith('old'):
            return False

        # Skip jika hanya path/filename
        text_content = text_match.group(1)
        if (text_content.endswith(('.png', '.jpg', '.mp3', '.ogg', '.wav')) or
            '/' in text_content or '\\' in text_content):
            return False

        # Translate ALL other texts, including one word, long sentences, etc
        return True

    def _scan_tags_and_vars(self):
        with open(self.input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Scan tags
        tag_pattern = r'\{([^{}]+)\}'
        for tag in set(re.findall(tag_pattern, content)):
            if tag not in self.tag_map:
                self.tag_map[tag] = str(self.tag_counter)
                self.tag_counter += 1
        
        # Scan variables
        var_pattern = r'\[([^\[\]]+)\]'
        for var in set(re.findall(var_pattern, content)):
            if var not in self.var_map:
                self.var_map[var] = str(self.var_counter)
                self.var_counter += 1

        # Simpan mapping
        with open(self.mapping_file, 'w', encoding='utf-8') as f:
            f.write("=== TAG MAPPING ===\n")
            for tag, num in sorted(self.tag_map.items(), key=lambda x: int(x[1])):
                f.write(f"{{{num}}} = {{{tag}}}\n")
            f.write("\n=== VARIABLE MAPPING ===\n")
            for var, num in sorted(self.var_map.items(), key=lambda x: int(x[1])):
                f.write(f"[{num}] = [{var}]\n")
            f.write("\n=== DASH MAPPING ===\n")
            f.write("© = -\n")
            f.write("® = –\n") 
            f.write("™ = —\n")
        print(f"📋 {self.filename_base}: Ditemukan {len(self.tag_map)} tags, {len(self.var_map)} variables")

    def _do_translation(self, text):
        try:
            escaped_text = text.replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'")
            cmd = f'trans -brief -no-ansi {BAHASA_ASAL}:{BAHASA_TUJUAN} "{escaped_text}"'
            result = subprocess.run(
                cmd,
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=25,
                encoding='utf-8'
            )
            if result.returncode != 0:
                return None, result.stderr.strip() if result.stderr else "Translation command failed"
            translated = result.stdout.strip()
            if not translated:
                return None, "Empty translation result"
            return translated, None
        except subprocess.TimeoutExpired:
            return None, "Translation timeout (25s)"
        except Exception as e:
            return None, f"Unexpected error: {str(e)}"

    def _translate_text(self, text, line_num, context=""):
        self.translation_stats['total_processed'] += 1

        # Check empty input
        if not text or not text.strip():
            self.translation_stats['empty_input'] += 1
            self._log_translation(line_num, "EMPTY_INPUT", text, context=context)
            return text

        # Protect escape sequences
        protected_text = self._protect_escapes(text)

        # Translate
        translated, error = self._do_translation(protected_text)

        if error:
            if "timeout" in error.lower():
                self.translation_stats['errors'] += 1
                self._log_translation(line_num, "TIMEOUT", text, error_msg=error, context=context)
            else:
                self.translation_stats['failed'] += 1
                self._log_translation(line_num, "FAILED", text, error_msg=error, context=context)
            return text

        if not translated:
            self.translation_stats['empty_output'] += 1
            self._log_translation(line_num, "EMPTY_OUTPUT", text, context=context)
            return text

        # Restore escape sequences
        final_text = self._restore_escapes(translated)

        # Success
        self.translation_stats['success'] += 1
        self._log_translation(line_num, "SUCCESS", text, final_text, context=context)
        return final_text

    def _process_line(self, line, line_num):
        original_line = line.rstrip()
        if (not original_line.strip() or 
            original_line.strip().startswith('#') or
            original_line.strip().startswith('$')):
            return line

        processed_line = original_line
        # Ganti variabel dengan placeholder
        processed_line = re.sub(
            r'\[([^\[\]]+)\]', 
            lambda m: f"[{self.var_map.get(m.group(1), '?')}]", 
            processed_line
        )
        # Ganti tag dengan placeholder
        processed_line = re.sub(
            r'\{([^{}]+)\}', 
            lambda m: f"{{{self.tag_map.get(m.group(1), '?')}}}", 
            processed_line
        )
        # Ganti dash characters dengan simbol khusus
        processed_line = processed_line.replace('-', '©')
        processed_line = processed_line.replace('–', '®')
        processed_line = processed_line.replace('—', '™')

        def smart_translate_match(match):
            text = match.group(1)
            # Translate ALL, except Ren'Py keywords/filename/path
            if not self._should_translate(processed_line, match):
                self.translation_stats['skipped_code'] += 1
                self._log_translation(line_num, "SKIPPED_CODE", text, context=original_line)
                return f'"{text}"'  # Return as-is
            translated = self._translate_text(text, line_num, context=original_line)
            return f'"{translated}"'

        final_line = re.sub(r'"([^"]*)"', smart_translate_match, processed_line)
        return final_line + '\n'

    def _write_summary_log(self):
        success_rate = (self.translation_stats['success'] / max(1, self.translation_stats['total_processed'])) * 100
        summary_text = f"""
{'='*60}
RINGKASAN TERJEMAHAN {self.filename_base}
{'='*60}
✅ Berhasil ditranslate : {self.translation_stats['success']}
⏩ Skip (Ren'Py code)   : {self.translation_stats['skipped_code']}
❌ Gagal/Error         : {self.translation_stats['failed'] + self.translation_stats['errors']}
📝 Input kosong         : {self.translation_stats['empty_input']}
📄 Output kosong        : {self.translation_stats['empty_output']}
📊 Total diproses       : {self.translation_stats['total_processed']}
📋 Total baris file     : {self.total_lines}
🎯 Success Rate         : {success_rate:.1f}%
"""
        if LOG_LEVEL != "SUMMARY":
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(summary_text)
        print(summary_text)
        return success_rate

    def _check_dependencies(self):
        try:
            result = subprocess.run("trans --version", shell=True, capture_output=True, timeout=5)
            if result.returncode != 0:
                print("❌ translate-shell tidak ditemukan!")
                print("📥 Install dengan: npm install -g translate-shell")
                return False
            return True
        except:
            print("❌ Error checking translate-shell dependency")
            return False

    def _validate_output(self):
        try:
            with open(self.output_file, 'r', encoding='utf-8') as f:
                content = f.read()
            issues = []
            quote_count = content.count('"')
            if quote_count % 2 != 0:
                issues.append("⚠️ Unmatched quotes detected")
            if content.count('{') != content.count('}'):
                issues.append("⚠️ Unmatched curly brackets")
            if content.count('[') != content.count(']'):
                issues.append("⚠️ Unmatched square brackets")
                
            if issues:
                print(f"\n🚨 SYNTAX WARNINGS for {self.filename_base}:")
                for issue in issues:
                    print(f"   {issue}")
            else:
                print(f"\n✅ Syntax validation passed for {self.filename_base}!")
        except Exception as e:
            print(f"\n⚠️ Could not validate syntax for {self.filename_base}: {e}")

    def translate_single_file(self):
        """Translate single .rpy file"""
        print(f"📂 Processing: {self.input_file}")
        
        # Tulis progress started
        self._write_progress("started")
        
        if not os.path.exists(self.input_file):
            print(f"❌ File tidak ditemukan: {self.input_file}")
            self._write_progress("failed")
            return False
            
        if not self._check_dependencies():
            self._write_progress("failed")
            return False
            
        # Create output folder
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)
        
        self._init_log_file()
        print(f"🔍 {self.filename_base}: Scanning tags dan variabel...")
        self._scan_tags_and_vars()
        
        print(f"🚀 {self.filename_base}: Memulai terjemahan...")
        
        with open(self.input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        self.total_lines = len(lines)
        
        results = []
        start_time = time.time()
        
        for i, line in enumerate(lines, 1):
            processed = self._process_line(line, i)
            results.append(processed)
            
            if i % 50 == 0 or i == self.total_lines:  # Update progress every 50 lines
                percent = (i / self.total_lines) * 100
                success_rate = (self.translation_stats['success'] / max(1, self.translation_stats['total_processed'])) * 100
                elapsed = time.time() - start_time
                eta = (elapsed / i) * (self.total_lines - i) if i > 0 else 0
                print(f"\r📊 {self.filename_base}: {percent:.1f}% | {i}/{self.total_lines} | Success: {success_rate:.0f}% | ETA: {eta:.0f}s", end='')
            
            if JEDA_TERJEMAH > 0:
                time.sleep(JEDA_TERJEMAH)
        
        # Save results
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.writelines(results)
            print(f"\n✅ {self.filename_base}: File berhasil disimpan!")
        except Exception as e:
            print(f"\n❌ {self.filename_base}: Error menyimpan file: {e}")
            self._write_progress("failed")
            return False
        
        self._validate_output()
        success_rate = self._write_summary_log()
        
        # Tulis progress completed dengan success rate
        self._write_progress("completed", success_rate)
        
        return True

def process_batch_folder(batch_folder):
    """Process all .rpy files in batch folder"""
    print(f"\n{'='*60}")
    print(f"🎮 REN'PY BATCH TRANSLATOR v6.0")
    print(f"📂 Processing folder: {batch_folder}")
    print(f"🌐 {BAHASA_ASAL} -> {BAHASA_TUJUAN}")
    print(f"{'='*60}")
    
    # Check if batch folder exists
    if not os.path.exists(batch_folder):
        print(f"❌ Folder tidak ditemukan: {batch_folder}")
        return
    
    # Get all .rpy files
    rpy_files = [f for f in os.listdir(batch_folder) if f.endswith('.rpy')]
    
    if not rpy_files:
        print(f"❌ Tidak ada file .rpy ditemukan di {batch_folder}")
        return
    
    print(f"📋 Ditemukan {len(rpy_files)} file .rpy")
    print("-" * 60)
    
    # Process each file
    success_count = 0
    failed_count = 0
    
    for filename in sorted(rpy_files):
        filepath = os.path.join(batch_folder, filename)
        translator = RenPyBatchTranslator(filepath)
        
        try:
            if translator.translate_single_file():
                success_count += 1
            else:
                failed_count += 1
        except Exception as e:
            print(f"\n❌ Error processing {filename}: {e}")
            failed_count += 1
        
        print("-" * 60)
    
    # Final summary
    total_files = len(rpy_files)
    print(f"\n🎯 BATCH PROCESSING SUMMARY:")
    print(f"✅ Berhasil: {success_count}/{total_files}")
    print(f"❌ Gagal: {failed_count}/{total_files}")
    print(f"📁 Output folder: {OUTPUT_FOLDER}")
    
    if success_count > 0:
        print(f"\n🎉 Translation completed!")
        print(f"📦 Check {OUTPUT_FOLDER}/ for translated files")
    else:
        print(f"\n❌ No files were successfully translated")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 translate.py <batch_folder>")
        print("Example: python3 translate.py batch_kecil")
        sys.exit(1)
    
    batch_folder = sys.argv[1]
    process_batch_folder(batch_folder)