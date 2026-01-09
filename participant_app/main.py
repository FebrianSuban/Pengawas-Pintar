"""
Main entry point untuk Participant Application
"""
import sys
import os
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtWidgets import QApplication
from participant_app.app import ParticipantApp


def main():
    """Main function"""
    app = QApplication(sys.argv)
    
    # Create participant application
    participant_app = ParticipantApp()
    participant_app.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
