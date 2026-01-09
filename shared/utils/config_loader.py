"""
Utility untuk load konfigurasi
"""
import json
import os
from typing import Dict, Any


class ConfigLoader:
    """Loader untuk file konfigurasi"""
    
    @staticmethod
    def load_config(config_path: str, template_path: str = None) -> Dict[str, Any]:
        """
        Load konfigurasi dari file
        
        Args:
            config_path: Path ke file config
            template_path: Path ke template (optional)
        
        Returns:
            Dict konfigurasi
        """
        # Jika config tidak ada, gunakan template
        if not os.path.exists(config_path) and template_path:
            if os.path.exists(template_path):
                # Copy template
                import shutil
                os.makedirs(os.path.dirname(config_path), exist_ok=True)
                shutil.copy(template_path, config_path)
        
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        elif template_path and os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {}
    
    @staticmethod
    def save_config(config_path: str, config: Dict[str, Any]):
        """Save konfigurasi ke file"""
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
