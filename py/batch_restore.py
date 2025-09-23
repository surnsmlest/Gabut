#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BATCH RESTORE SCRIPT FOR GITHUB ACTIONS
- Scan translated .rpy files in output_tl/id/
- Scan mapping .txt files 
- Match and restore files automatically
- Organize output in proper structure
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime

# ============== CONFIG ==============
INPUT_DIR = "output_tl"  # Folder hasil translate
MAPPING_DIR = "."        # Folder mapping files (root)
OUTPUT_DIR = "id"        # Output final structure
# ====================================

def log_message(message, level="INFO"):
    """Log message with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] [{level}] {message}")

def create_output_structure():
    """Create output directory structure"""
    directories = [
        f"{OUTPUT_DIR}",
        f"{OUTPUT_DIR}/mapping", 
        f"{OUTPUT_DIR}/log",
        f"{OUTPUT_DIR}/restored"
    ]
    
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        log_message(f"Created directory: {dir_path}")

def scan_translated_files():
    """Scan for translated .rpy files in output_tl/"""
    translated_files = []
    
    # Scan di output_tl/ untuk file .rpy
    if os.path.exists(INPUT_DIR):
        for file in os.listdir(INPUT_DIR):
            if file.endswith('.rpy'):
                translated_files.append(file)
    
    log_message(f"Found {len(translated_files)} translated .rpy files")
    return sorted(translated_files)

def scan_mapping_files():
    """Scan for mapping .txt files"""
    mapping_files = []
    
    # Scan di root directory untuk file _mapping.txt
    for file in os.listdir(MAPPING_DIR):
        if file.endswith('_mapping.txt'):
            mapping_files.append(file)
    
    log_message(f"Found {len(mapping_files)} mapping files")
    return sorted(mapping_files)

def extract_base_name(filename):
    """Extract base name from filename
    A_id.rpy -> A
    A_mapping.txt -> A
    """
    if filename.endswith('_id.rpy'):
        return filename.replace('_id.rpy', '')
    elif filename.endswith('_mapping.txt'):
        return filename.replace('_mapping.txt', '')
    else:
        # Fallback for other patterns
        return Path(filename).stem.split('_')[0]

def load_mapping_file(map_file):
    """Load enhanced mapping file with TAG/VARIABLE/EMOTION/DASH support"""
    mappings = {
        'tag': {},      # {1} = {something}
        'variable': {}, # [1] = [something] 
        'emotion': {},  # (1) = (something)
        'bracket': {},  # <1> = <something>
        'dash': {}      # © = -, ® = –, ™ = —
    }
    
    try:
        with open(map_file, 'r', encoding='utf-8') as f:
            current_section = None
            
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Detect sections
                if "TAG MAPPING" in line.upper():
                    current_section = 'tag'
                    continue
                elif "VARIABLE MAPPING" in line.upper():
                    current_section = 'variable'  
                    continue
                elif "EMOTION MAPPING" in line.upper():
                    current_section = 'emotion'
                    continue
                elif "BRACKET MAPPING" in line.upper():
                    current_section = 'bracket'
                    continue
                elif "DASH MAPPING" in line.upper():
                    current_section = 'dash'
                    continue
                elif line.startswith('==='):
                    continue
                
                # Parse mappings based on current section
                if current_section == 'tag':
                    # {1} = {something}
                    if match := re.match(r'\{(\d+)\}\s*=\s*\{(.+)\}', line):
                        mappings['tag'][match.group(1)] = match.group(2)
                        
                elif current_section == 'variable':
                    # [1] = [something]
                    if match := re.match(r'\[(\d+)\]\s*=\s*\[(.+)\]', line):
                        mappings['variable'][match.group(1)] = match.group(2)
                        
                elif current_section == 'emotion':
                    # (1) = (something)
                    if match := re.match(r'\((\d+)\)\s*=\s*\((.+)\)', line):
                        mappings['emotion'][match.group(1)] = match.group(2)
                
                elif current_section == 'dash':
                    # © = -, ® = –, ™ = —
                    if match := re.match(r'(©|®|™)\s*=\s*(.)', line):
                        mappings['dash'][match.group(1)] = match.group(2)
    
    except Exception as e:
        log_message(f"Error loading mapping {map_file}: {e}", "ERROR")
    
    return mappings

def apply_mappings(content, mappings):
    """Apply all mappings to content"""
    # Apply TAG mappings: {1} → {something}
    def replace_tag(match):
        num = match.group(1)
        replacement = mappings['tag'].get(num, f'UNKNOWN_TAG_{num}')
        return f"{{{replacement}}}"
    
    content = re.sub(r'\{(\d+)\}', replace_tag, content)
    
    # Apply VARIABLE mappings: [1] → [something]
    def replace_var(match):
        num = match.group(1)
        replacement = mappings['variable'].get(num, f'UNKNOWN_VAR_{num}')
        return f"[{replacement}]"
    
    content = re.sub(r'\[(\d+)\]', replace_var, content)
    
    # Apply EMOTION mappings: (1) → (something)  
    def replace_emotion(match):
        num = match.group(1)
        replacement = mappings['emotion'].get(num, f'UNKNOWN_EMOTION_{num}')
        return f"({replacement})"
    
    content = re.sub(r'\((\d+)\)', replace_emotion, content)
    
    # Apply DASH mappings: © → -, ® → –, ™ → —
    for symbol, replacement in mappings['dash'].items():
        content = content.replace(symbol, replacement)
    
    return content

def restore_single_file(rpy_file, mapping_file, output_name):
    """Restore single file with mapping"""
    try:
        # Load mappings
        mappings = load_mapping_file(mapping_file)
        
        # Count total mappings
        total_mappings = sum(len(m) for m in mappings.values())
        if total_mappings == 0:
            log_message(f"No mappings found in {mapping_file}", "WARNING")
            return False
        
        # Read translated file
        input_path = os.path.join(INPUT_DIR, rpy_file)
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_length = len(content)
        
        # Apply mappings
        restored_content = apply_mappings(content, mappings)
        
        # Save restored file
        output_path = os.path.join(OUTPUT_DIR, "restored", output_name)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(restored_content)
        
        # Log statistics
        tag_count = len(mappings['tag'])
        var_count = len(mappings['variable']) 
        emotion_count = len(mappings['emotion'])
        dash_count = len(mappings['dash'])
        
        log_message(f"Restored {rpy_file} → {output_name}")
        log_message(f"  Mappings applied: Tags={tag_count}, Vars={var_count}, Emotions={emotion_count}, Dashes={dash_count}")
        log_message(f"  Size: {original_length:,} → {len(restored_content):,} chars")
        
        return True
        
    except Exception as e:
        log_message(f"Error restoring {rpy_file}: {e}", "ERROR")
        return False

def move_support_files():
    """Move mapping and log files to organized structure"""
    moved_mappings = 0
    moved_logs = 0
    
    # Move mapping files
    for file in os.listdir(MAPPING_DIR):
        if file.endswith('_mapping.txt'):
            src = os.path.join(MAPPING_DIR, file)
            dst = os.path.join(OUTPUT_DIR, "mapping", file)
            try:
                os.rename(src, dst)
                moved_mappings += 1
            except Exception as e:
                log_message(f"Error moving {file}: {e}", "ERROR")
    
    # Move log files
    for file in os.listdir(MAPPING_DIR):
        if file.endswith('_log.txt'):
            src = os.path.join(MAPPING_DIR, file)
            dst = os.path.join(OUTPUT_DIR, "log", file)
            try:
                os.rename(src, dst)
                moved_logs += 1
            except Exception as e:
                log_message(f"Error moving {file}: {e}", "ERROR")
    
    # Move remaining .rpy files from output_tl to id/
    if os.path.exists(INPUT_DIR):
        moved_rpy = 0
        for file in os.listdir(INPUT_DIR):
            if file.endswith('.rpy'):
                src = os.path.join(INPUT_DIR, file)
                # Remove _id suffix for final name
                final_name = file.replace('_id.rpy', '.rpy') if file.endswith('_id.rpy') else file
                dst = os.path.join(OUTPUT_DIR, final_name)
                try:
                    os.rename(src, dst)
                    moved_rpy += 1
                except Exception as e:
                    log_message(f"Error moving {file}: {e}", "ERROR")
        
        log_message(f"Moved {moved_rpy} translated .rpy files to {OUTPUT_DIR}/")
    
    log_message(f"Organized files: {moved_mappings} mappings, {moved_logs} logs")

def create_restore_report(processed_files, successful_restores):
    """Create restoration report"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'total_files_found': len(processed_files),
        'successful_restores': successful_restores,
        'failed_restores': len(processed_files) - successful_restores,
        'success_rate': f"{(successful_restores/len(processed_files)*100):.1f}%" if processed_files else "0%",
        'processed_files': processed_files
    }
    
    # Save JSON report
    report_path = os.path.join(OUTPUT_DIR, "restore_report.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # Save text summary
    summary_path = os.path.join(OUTPUT_DIR, "restore_summary.txt")
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(f"BATCH RESTORE SUMMARY\n")
        f.write(f"====================\n")
        f.write(f"Timestamp: {report['timestamp']}\n")
        f.write(f"Total files: {report['total_files_found']}\n")
        f.write(f"Successful: {report['successful_restores']}\n")
        f.write(f"Failed: {report['failed_restores']}\n")
        f.write(f"Success rate: {report['success_rate']}\n\n")
        
        f.write("PROCESSED FILES:\n")
        for file_info in processed_files:
            status = "✅" if file_info['success'] else "❌"
            f.write(f"{status} {file_info['rpy_file']} → {file_info['output_name']}\n")
    
    log_message(f"Restore report saved: {report_path}")
    return report

def update_progress(current, total):
    """Update progress file for GitHub Actions monitoring"""
    try:
        progress_text = f"Restoring: {current}/{total} files ({current/total*100:.1f}%)"
        with open('restore_progress.txt', 'w', encoding='utf-8') as f:
            f.write(progress_text)
    except Exception as e:
        log_message(f"Error updating progress: {e}", "ERROR")

def main():
    """Main batch restore function"""
    log_message("=== BATCH RESTORE STARTED ===")
    
    # Create output structure
    create_output_structure()
    
    # Scan files
    translated_files = scan_translated_files()
    mapping_files = scan_mapping_files()
    
    if not translated_files:
        log_message("No translated .rpy files found!", "ERROR")
        return
    
    if not mapping_files:
        log_message("No mapping files found!", "ERROR") 
        return
    
    # Create mapping lookup
    mapping_lookup = {}
    for mapping_file in mapping_files:
        base_name = extract_base_name(mapping_file)
        mapping_lookup[base_name] = mapping_file
    
    log_message(f"Created mapping lookup for {len(mapping_lookup)} base names")
    
    # Process each translated file
    processed_files = []
    successful_restores = 0
    
    for i, rpy_file in enumerate(translated_files, 1):
        update_progress(i, len(translated_files))
        
        base_name = extract_base_name(rpy_file)
        log_message(f"[{i}/{len(translated_files)}] Processing: {rpy_file} (base: {base_name})")
        
        # Find corresponding mapping file
        if base_name in mapping_lookup:
            mapping_file = mapping_lookup[base_name]
            output_name = f"{base_name}.rpy"  # Final name without _id
            
            log_message(f"  Found mapping: {mapping_file}")
            log_message(f"  Output will be: {output_name}")
            
            # Restore file
            success = restore_single_file(rpy_file, mapping_file, output_name)
            
            processed_files.append({
                'rpy_file': rpy_file,
                'mapping_file': mapping_file,
                'output_name': output_name,
                'success': success
            })
            
            if success:
                successful_restores += 1
        else:
            log_message(f"  No mapping found for base name: {base_name}", "WARNING")
            processed_files.append({
                'rpy_file': rpy_file,
                'mapping_file': None,
                'output_name': None,
                'success': False
            })
    
    # Move support files
    move_support_files()
    
    # Create report
    report = create_restore_report(processed_files, successful_restores)
    
    # Final summary
    log_message("=== BATCH RESTORE COMPLETED ===")
    log_message(f"Total processed: {len(processed_files)}")
    log_message(f"Successful restores: {successful_restores}")
    log_message(f"Success rate: {report['success_rate']}")
    
    # Update final progress
    with open('restore_progress.txt', 'w', encoding='utf-8') as f:
        f.write(f"COMPLETED: {successful_restores}/{len(processed_files)} files restored")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log_message("Operation cancelled by user", "WARNING")
    except Exception as e:
        log_message(f"Critical error: {e}", "ERROR")
        raise