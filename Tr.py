#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PO MULTILINE TRANSLATE v2 + ProgressBar
- Translate msgid single-line & multiline ke msgstr otomatis
- Mapping tag/var/kurung/angle ke mapping.txt
- Jeda 0.3 detik setiap translate
- FIX: single-line msgid overwrite/replace msgstr lama, progress percent
"""

import re
import os
import time
import subprocess
from datetime import datetime
from collections import defaultdict

class POMultilineTranslator:
    def __init__(self):
        self.source_lang = "en"
        self.target_lang = "id"
        self.log_file = None
        
        self.tag_map = defaultdict(str)
        self.var_map = defaultdict(str)
        self.emotion_map = defaultdict(str)
        self.bracket_map = defaultdict(str)
        
        self.tag_counter = 1
        self.var_counter = 1
        self.emotion_counter = 1
        self.bracket_counter = 1
        
        self.stats = {
            'success': 0,
            'failed': 0,
            'errors': 0,
            'skipped': 0,
            'total_entries': 0
        }

    def init_log_file(self, input_file):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.splitext(input_file)[0]
        self.log_file = f"{base_name}_log_{timestamp}.txt"
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write("=== PO TRANSLATE LOG ===\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Input: {input_file}\n")
            f.write(f"Language: {self.source_lang} -> {self.target_lang}\n")
            f.write("=" * 40 + "\n\n")

    def log_translation(self, line_range, status, original_text, translated_text="", error_msg=""):
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"LINE {line_range} | STATUS: {status}\n")
            f.write(f"ORIGINAL: {original_text}\n")
            if translated_text and translated_text != original_text:
                f.write(f"RESULT  : {translated_text}\n")
            if error_msg:
                f.write(f"ERROR   : {error_msg}\n")
            f.write("-" * 30 + "\n")

    def scan_markup(self, content):
        self.tag_counter = 1
        self.var_counter = 1
        self.emotion_counter = 1
        self.bracket_counter = 1
        self.tag_map.clear()
        self.var_map.clear()
        self.emotion_map.clear()
        self.bracket_map.clear()
        patterns = [
            (r'\{([^{}]+)\}', self.tag_map, 'tag_counter'),
            (r'\[([^\[\]]+)\]', self.var_map, 'var_counter'),
            (r'\(([^()]+)\)', self.emotion_map, 'emotion_counter'),
            (r'<([^<>]+)>', self.bracket_map, 'bracket_counter')
        ]
        for pattern, map_dict, counter_name in patterns:
            for match in set(re.findall(pattern, content)):
                if counter_name == 'emotion_counter' and match.replace('.', '').replace(',', '').isdigit():
                    continue
                if match not in map_dict:
                    counter_value = getattr(self, counter_name)
                    map_dict[match] = str(counter_value)
                    setattr(self, counter_name, counter_value + 1)

    def protect_text(self, text):
        protected = text
        replacements = [
            (r'\{([^{}]+)\}', lambda m: f"{{{self.tag_map.get(m.group(1), '?')}}}"),
            (r'\[([^\[\]]+)\]', lambda m: f"[{self.var_map.get(m.group(1), '?')}]"),
            (r'\(([^()]+)\)', lambda m: f"({self.emotion_map.get(m.group(1), m.group(1))})"),
            (r'<([^<>]+)>', lambda m: f"<{self.bracket_map.get(m.group(1), '?')}>")
        ]
        for pattern, replacement in replacements:
            protected = re.sub(pattern, replacement, protected)
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
        if not text or not text.strip():
            return text, "Empty input"
        if text.strip().startswith('@') or 'res://' in text or text.endswith(('.png', '.jpg', '.mp3')):
            return text, "Command skipped"
        try:
            escaped_text = text.replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'")
            cmd = f'trans -brief -no-ansi {self.source_lang}:{self.target_lang} "{escaped_text}"'
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                encoding='utf-8'
            )
            time.sleep(0.3)
            if result.returncode != 0:
                return text, "Translation command failed"
            translated = result.stdout.strip()
            if not translated:
                return text, "Empty translation result"
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
        line = line.strip()
        if line.startswith('"') and line.endswith('"'):
            return line[1:-1]
        return ""

    def split_translated_text(self, translated_text, original_lines):
        if not translated_text:
            return []
        target_line_count = len(original_lines)
        if target_line_count <= 1:
            return [f'"{translated_text}"']
        words = translated_text.split()
        lines = []
        chunk_size = max(1, len(words) // target_line_count)
        idx = 0
        for l in range(target_line_count):
            if idx >= len(words):
                break
            # If last line, ambil semua sisa
            if l == target_line_count - 1:
                chunk = words[idx:]
            else:
                chunk = words[idx:idx + chunk_size]
            line_text = ' '.join(chunk)
            lines.append(f'"{line_text}"')
            idx += chunk_size
        # Gabungkan sisa jika line kurang
        if idx < len(words):
            lines[-1] = lines[-1][:-1] + ' ' + ' '.join(words[idx:]) + '"'
        return lines

    def export_mapping(self, input_file):
        mapping_file = f"{os.path.splitext(input_file)[0]}_mapping.txt"
        with open(mapping_file, 'w', encoding='utf-8') as f:
            f.write("=== TAG MAPPING ===\n")
            for k, v in sorted(self.tag_map.items(), key=lambda x: int(x[1])):
                f.write(f"{{{v}}} = {{{k}}}\n")
            f.write("\n=== VARIABLE MAPPING ===\n")
            for k, v in sorted(self.var_map.items(), key=lambda x: int(x[1])):
                f.write(f"[{v}] = [{k}]\n")
            f.write("\n=== EMOTION MAPPING ===\n")
            for k, v in sorted(self.emotion_map.items(), key=lambda x: int(x[1]) if x[1].isdigit() else 9999):
                f.write(f"({v}) = ({k})\n")
            f.write("\n=== BRACKET MAPPING ===\n")
            for k, v in sorted(self.bracket_map.items(), key=lambda x: int(x[1]) if x[1].isdigit() else 9999):
                f.write(f"<{v}> = <{k}>\n")

    def process_po_file(self, input_file):
        print(f"🔍 Processing: {input_file}")
        if not os.path.exists(input_file):
            print(f"❌ File not found: {input_file}")
            return False
        self.init_log_file(input_file)
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        content = ''.join(lines)
        self.scan_markup(content)
        # PHASE: Hitung total entry yang diterjemahkan (progress bar)
        total_entries = 0
        i = 0
        while i < len(lines):
            line = lines[i].rstrip()
            if line.strip().startswith('msgid "') and not line.strip() == 'msgid ""':
                total_entries += 1
            elif line.strip() == 'msgid ""':
                while i+1 < len(lines) and not lines[i+1].strip().startswith('msgstr ""'):
                    i += 1
                total_entries += 1
            i += 1
        done_entries = 0

        mode = 'normal'
        multiline_start_line = 0
        multiline_lines = []
        multiline_text = ""
        processed_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            original_line = line.rstrip()
            if mode == 'normal':
                if original_line.strip().startswith('msgid "') and not original_line.strip() == 'msgid ""':
                    msgid_match = re.search(r'msgid\s+"([^"]*)"', original_line)
                    if msgid_match:
                        original_text = msgid_match.group(1)
                        if original_text.strip():
                            done_entries += 1
                            percent = int((done_entries / total_entries) * 100)
                            print(f"Translating... {done_entries}/{total_entries} ({percent}%)", end="\r")
                            protected_text = self.protect_text(original_text)
                            translated_text, error = self.translate_text(protected_text)
                            if error:
                                self.log_translation(str(i+1), "ERROR", original_text, "", error)
                                self.stats['failed'] += 1
                                processed_lines.append(line)
                                if i+1 < len(lines) and lines[i+1].strip().startswith('msgstr'):
                                    i += 1
                                    processed_lines.append('msgstr ""\n')
                            else:
                                self.log_translation(str(i+1), "SUCCESS", original_text, translated_text)
                                self.stats['success'] += 1
                                processed_lines.append(line)
                                if i+1 < len(lines) and lines[i+1].strip().startswith('msgstr'):
                                    i += 1
                                processed_lines.append(f'msgstr "{translated_text}"\n')
                        else:
                            processed_lines.append(line)
                    else:
                        processed_lines.append(line)
                elif original_line.strip() == 'msgid ""':
                    mode = 'multiline'
                    multiline_start_line = i+1
                    multiline_lines = [line]
                    multiline_text = ""
                else:
                    processed_lines.append(line)
            elif mode == 'multiline':
                if original_line.strip().startswith('"') and original_line.strip().endswith('"'):
                    text_part = self.extract_quoted_text(original_line)
                    multiline_text += text_part
                    multiline_lines.append(line)
                elif original_line.strip().startswith('msgstr ""'):
                    processed_lines.extend(multiline_lines)
                    if multiline_text.strip():
                        done_entries += 1
                        percent = int((done_entries / total_entries) * 100)
                        print(f"Translating... {done_entries}/{total_entries} ({percent}%)", end="\r")
                        protected_text = self.protect_text(multiline_text)
                        translated_text, error = self.translate_text(protected_text)
                        line_range = f"{multiline_start_line+1}-{i}"
                        if error:
                            self.log_translation(line_range, "ERROR", multiline_text, "", error)
                            self.stats['failed'] += 1
                            processed_lines.append(line)
                        else:
                            self.log_translation(line_range, "SUCCESS", multiline_text, translated_text)
                            self.stats['success'] += 1
                            processed_lines.append(line)
                            original_text_lines = [l for l in multiline_lines if l.strip().startswith('"')]
                            translated_lines = self.split_translated_text(translated_text, original_text_lines)
                            for trans_line in translated_lines:
                                processed_lines.append(trans_line + '\n')
                    else:
                        processed_lines.append(line)
                        self.stats['skipped'] += 1
                    mode = 'normal'
                    multiline_lines = []
                    multiline_text = ""
                else:
                    processed_lines.append(line)
            i += 1
        print("\n")  # Munculkan baris baru setelah progress
        output_file = f"{os.path.splitext(input_file)[0]}_translated.po"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.writelines(processed_lines)
        self.export_mapping(input_file)
        print(f"✅ Output: {output_file}")
        print(f"📋 Log: {self.log_file}")
        print(f"🔗 Mapping: {os.path.splitext(input_file)[0]}_mapping.txt")
        return True

def main():
    print("=" * 50)
    print(" PO MULTILINE TRANSLATOR v2")
    print("=" * 50)
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
            translator = POMultilineTranslator()
            source = input(f"Source language (default: {translator.source_lang}): ").strip()
            if source:
                translator.source_lang = source
            target = input(f"Target language (default: {translator.target_lang}): ").strip()
            if target:
                translator.target_lang = target
            print(f"\n🚀 Start: {translator.source_lang} -> {translator.target_lang}")
            success = translator.process_po_file(selected_file)
            if success:
                print(f"\n✅ Done! Check output, log, and mapping.")
            else:
                print(f"\n❌ Failed!")
        else:
            print("❌ Invalid selection!")
    except (ValueError, KeyboardInterrupt):
        print("\n👋 Cancelled.")

if __name__ == "__main__":
    main()
