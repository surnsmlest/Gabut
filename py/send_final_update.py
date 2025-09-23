#!/usr/bin/env python3
import os
import sys

def send_batch_summary(batch_name):
    """Kirim summary akhir untuk batch"""
    try:
        with open('translation_progress.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        batch_files = [line for line in lines if batch_name.lower() in line.lower() or any(x in line for x in ['COMPLETED:', 'FAILED:'])]
        
        completed = [line for line in batch_files if 'COMPLETED:' in line]
        failed = [line for line in batch_files if 'FAILED:' in line]
        
        message = f"✅ **{batch_name} COMPLETED**\n"
        message += f"Berhasil: {len(completed)} file\n"
        if failed:
            message += f"Gagal: {len(failed)} file\n"
        
        # Rata-rata success rate
        if completed:
            success_rates = []
            for comp in completed:
                parts = comp.split(':')
                if len(parts) >= 3:
                    try:
                        rate = float(parts[2].replace('%', ''))
                        success_rates.append(rate)
                    except:
                        pass
            
            if success_rates:
                avg_rate = sum(success_rates) / len(success_rates)
                message += f"Avg Success Rate: {avg_rate:.1f}%\n"
        
        os.system(f'python3 py/telegram_notify.py "BATCH SUMMARY" "{message}"')
        
    except Exception as e:
        print(f"Error sending summary: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        send_batch_summary(sys.argv[1])