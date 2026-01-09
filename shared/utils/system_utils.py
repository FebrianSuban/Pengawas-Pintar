"""
System utilities untuk Windows/Linux
"""
import platform
import socket
import os
from typing import Optional


class SystemUtils:
    """Utilities untuk system operations"""
    
    @staticmethod
    def get_computer_name() -> str:
        """Get computer name"""
        return socket.gethostname()
    
    @staticmethod
    def get_local_ip() -> str:
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    @staticmethod
    def is_windows() -> bool:
        """Check if running on Windows"""
        return platform.system() == "Windows"
    
    @staticmethod
    def is_admin() -> bool:
        """Check if running as admin/root"""
        if SystemUtils.is_windows():
            try:
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            except:
                return False
        else:
            return os.geteuid() == 0
    
    @staticmethod
    def block_shortcuts(block: bool = True):
        """Block keyboard shortcuts (Windows only)"""
        if not SystemUtils.is_windows():
            return
        
        # This requires low-level keyboard hook
        # Implementation depends on specific requirements
        pass
    
    @staticmethod
    def prevent_task_manager(block: bool = True):
        """Prevent Task Manager access (Windows only)"""
        if not SystemUtils.is_windows():
            return
        
        # This requires registry modification or group policy
        # Implementation depends on specific requirements
        pass
    
    @staticmethod
    def lock_screen():
        """Lock the screen"""
        if SystemUtils.is_windows():
            import ctypes
            ctypes.windll.user32.LockWorkStation()
        else:
            os.system("gnome-screensaver-command -l")
