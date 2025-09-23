#!/usr/bin/env python3
"""
RenPy Translation Manager
Scan file .rpy di folder tl dan split berdasarkan jumlah line
"""

import os
import shutil
import sys
from pathlib import Path

# Konfigurasi - bisa diubah via command line arguments
TL_FOLDER = sys.argv[1] if len(sys.argv) > 1 else "tl"
OUTPUT_FOLDERS = {
    "kecil": "batch_kecil",
    "sedang": "batch_sedang", 
    "besar": "batch_besar",
    "super": "batch_super"
}

# Threshold untuk kategorisasi (jumlah lines) - UPDATED
THRESHOLD = {
    "kecil": (1, 799),        # 1-799 lines
    "sedang": (800, 2499),    # 800-2499 lines
    "besar": (2500, 4999),    # 2500-4999 lines
    "super": (5000, float('inf'))  # 5000+ lines
}

def count_lines(file_path):
    """Hitung jumlah baris dalam file"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for _ in f)
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return 0

def create_output_folders():
    """Buat folder output dan bersihkan jika sudah ada"""
    for category, folder_name in OUTPUT_FOLDERS.items():
        folder_path = Path(folder_name)
        if folder_path.exists():
            print(f"🗑️  Cleaning existing folder: {folder_name}")
            shutil.rmtree(folder_path)
        
        folder_path.mkdir(exist_ok=True)
        print(f"📁 Created folder: {folder_name}")

def categorize_file(line_count):
    """Kategorisasi file berdasarkan jumlah baris"""
    if line_count == 0:
        return "kosong"
    
    for category, (min_lines, max_lines) in THRESHOLD.items():
        if min_lines <= line_count <= max_lines:
            return category
    
    return "unknown"

def copy_file_to_batch(source_path, category):
    """Copy file ke folder batch yang sesuai"""
    if category == "kosong":
        return False  # Skip file kosong
    
    if category not in OUTPUT_FOLDERS:
        print(f"❌ Unknown category: {category}")
        return False
    
    destination_folder = OUTPUT_FOLDERS[category]
    destination_path = Path(destination_folder) / source_path.name
    
    try:
        shutil.copy2(source_path, destination_path)
        return True
    except Exception as e:
        print(f"❌ Error copying {source_path}: {e}")
        return False

def scan_and_split():
    """Main function: scan dan split file"""
    print("🚀 Starting RenPy Translation Manager...")
    print(f"📂 Scanning folder: {TL_FOLDER}")
    
    # Cek apakah folder tl ada
    tl_path = Path(TL_FOLDER)
    if not tl_path.exists():
        print(f"❌ Folder {TL_FOLDER} tidak ditemukan!")
        sys.exit(1)
    
    # Buat folder output
    create_output_folders()
    
    # Scan semua file .rpy
    rpy_files = list(tl_path.glob("*.rpy"))
    
    if not rpy_files:
        print(f"❌ Tidak ada file .rpy ditemukan di folder {TL_FOLDER}")
        sys.exit(1)
    
    print(f"📊 Ditemukan {len(rpy_files)} file .rpy")
    print("-" * 70)
    
    # Statistik - UPDATED untuk include super
    stats = {
        "kosong": 0,
        "kecil": 0,
        "sedang": 0,
        "besar": 0,
        "super": 0,
        "total_lines": 0
    }
    
    # Process setiap file
    for file_path in sorted(rpy_files):
        line_count = count_lines(file_path)
        category = categorize_file(line_count)
        
        # Status icon - UPDATED
        icons = {
            "kosong": "⚪",
            "kecil": "🟢", 
            "sedang": "🟠",
            "besar": "🔴",
            "super": "🔥"
        }
        
        icon = icons.get(category, "❓")
        
        print(f"{icon} {file_path.name:30} | {line_count:5} lines | {category.upper()}")
        
        # Copy ke folder batch (kecuali file kosong)
        if copy_file_to_batch(file_path, category):
            stats[category] += 1
            stats["total_lines"] += line_count
        elif category == "kosong":
            stats["kosong"] += 1
    
    # Print summary - UPDATED
    print("-" * 70)
    print("📈 SUMMARY:")
    print(f"⚪ Kosong (skip):         {stats['kosong']:3} files")
    print(f"🟢 Kecil (1-799):        {stats['kecil']:3} files")
    print(f"🟠 Sedang (800-2499):    {stats['sedang']:3} files")
    print(f"🔴 Besar (2500-4999):    {stats['besar']:3} files")
    print(f"🔥 Super (5000+):        {stats['super']:3} files")
    print(f"📝 Total lines:          {stats['total_lines']:,}")
    print("-" * 70)
    
    # Cek hasil di setiap folder
    print("📁 BATCH FOLDERS:")
    for category, folder_name in OUTPUT_FOLDERS.items():
        folder_path = Path(folder_name)
        file_count = len(list(folder_path.glob("*.rpy")))
        print(f"   {folder_name:15} | {file_count:3} files")
    
    total_processed = stats['kecil'] + stats['sedang'] + stats['besar'] + stats['super']
    print(f"\n✅ Selesai! {total_processed} file siap diterjemahkan")
    
    # Buat summary file untuk workflow
    create_summary_file(stats)

def create_summary_file(stats):
    """Buat file summary untuk dibaca workflow"""
    summary_data = {
        "total_files": stats['kecil'] + stats['sedang'] + stats['besar'] + stats['super'],
        "total_lines": stats['total_lines'],
        "categories": {
            "kecil": stats['kecil'],
            "sedang": stats['sedang'], 
            "besar": stats['besar'],
            "super": stats['super']
        }
    }
    
    # Tulis ke file text sederhana - UPDATED
    with open("manager_summary.txt", "w") as f:
        f.write(f"TOTAL_FILES={summary_data['total_files']}\n")
        f.write(f"TOTAL_LINES={summary_data['total_lines']}\n")
        f.write(f"KECIL_FILES={summary_data['categories']['kecil']}\n")
        f.write(f"SEDANG_FILES={summary_data['categories']['sedang']}\n")
        f.write(f"BESAR_FILES={summary_data['categories']['besar']}\n")
        f.write(f"SUPER_FILES={summary_data['categories']['super']}\n")
    
    print("📄 Summary saved to: manager_summary.txt")

if __name__ == "__main__":
    try:
        scan_and_split()
    except KeyboardInterrupt:
        print("\n⚠️  Process dibatalkan oleh user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)