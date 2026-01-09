"""
Main entry point untuk Admin Application
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtWidgets import QApplication
from admin_app.app import AdminApp


def main():
    """Main function"""
    app = QApplication(sys.argv)
    
    # Create admin application
    admin_app = AdminApp()
    admin_app.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
