#!/usr/bin/env python3
import os
import sys

def read_progress():
    """Baca progress file dan format untuk Telegram"""
    try:
        with open('translation_progress.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        completed = [line for line in lines if 'COMPLETED:' in line]
        in_progress = [line for line in lines if 'STARTED:' in line and not any(c['file'] in line for c in completed)]
        failed = [line for line in lines if 'FAILED:' in line]
        
        return completed, in_progress, failed
    except:
        return [], [], []

def format_progress_message(batch_name):
    completed, in_progress, failed = read_progress()
    
    total_files = len(completed) + len(in_progress) + len(failed)
    if total_files == 0:
        return None
    
    progress_percent = (len(completed) / total_files) * 100
    
    message = f"📊 **{batch_name}**\n"
    message += f"Progress: {progress_percent:.1f}% ({len(completed)}/{total_files} file)\n\n"
    
    # Tampilkan 5 file terakhir yang selesai
    if completed:
        message += "✅ **File Selesai:**\n"
        for comp in completed[-5:]:  # 5 file terakhir
            parts = comp.strip().replace('✅ COMPLETED:', '').split(':')
            if len(parts) >= 2:
                filename = parts[0]
                success_rate = parts[1]
                message += f"• {filename} ({success_rate})\n"
        message += "\n"
    
    # File sedang proses
    if in_progress:
        message += "🔄 **Sedang Diproses:**\n"
        for prog in in_progress[-3:]:  # 3 file terakhir
            filename = prog.strip().replace('🔄 STARTED:', '')
            message += f"• {filename}\n"
    
    return message

if __name__ == "__main__":
    if len(sys.argv) > 1:
        batch_name = sys.argv[1]
        message = format_progress_message(batch_name)
        if message:
            # Kirim via telegram_notify.py
            os.system(f'python3 py/telegram_notify.py "PROGRESS UPDATE" "{message}"')