"""
Script untuk inisialisasi proyek
Membuat direktori dan file konfigurasi yang diperlukan
"""
import os
import shutil
from pathlib import Path


def init_project():
    """Initialize project structure"""
    print("Menginisialisasi proyek Pengawas Pintar...")
    
    # Create directories
    directories = [
        "data",
        "logs",
        "evidence",
        "config"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"[OK] Created directory: {directory}/")
    
    # Copy config templates if they don't exist
    config_files = [
        ("config/admin_config_template.json", "config/admin_config.json"),
        ("config/participant_config_template.json", "config/participant_config.json")
    ]
    
    for template, target in config_files:
        if not os.path.exists(target) and os.path.exists(template):
            shutil.copy(template, target)
            print(f"[OK] Created config file: {target}")
        elif not os.path.exists(target):
            print(f"[WARNING] Template not found: {template}")
        else:
            print(f"[OK] Config file already exists: {target}")
    
    print("\n[OK] Inisialisasi selesai!")
    print("\nLangkah selanjutnya:")
    print("1. Edit config/admin_config.json untuk konfigurasi admin")
    print("2. Edit config/participant_config.json untuk konfigurasi participant")
    print("3. Jalankan admin app: python admin_app/main.py")
    print("4. Jalankan participant app: python participant_app/main.py")


if __name__ == "__main__":
    init_project()
