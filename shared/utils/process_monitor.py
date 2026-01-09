"""
Monitor untuk proses yang berjalan
"""
import psutil
import platform
from typing import List, Set, Dict
import threading
import time


class ProcessMonitor:
    """Monitor untuk proses aplikasi"""
    
    def __init__(self, allowed_apps: List[str] = None, blocked_apps: List[str] = None):
        """
        Initialize process monitor
        
        Args:
            allowed_apps: List aplikasi yang diizinkan (whitelist)
            blocked_apps: List aplikasi yang diblokir (blacklist)
        """
        self.allowed_apps = set(allowed_apps or [])
        self.blocked_apps = set(blocked_apps or [])
        self.is_running = False
        self.monitoring_thread = None
        self.check_interval = 2.0
        
        # Callbacks
        self.violation_callback = None
        
        # Tracked processes
        self.tracked_processes: Dict[str, psutil.Process] = {}
    
    def set_violation_callback(self, callback):
        """Set callback untuk violation"""
        self.violation_callback = callback
    
    def start(self):
        """Start monitoring"""
        if self.is_running:
            return
        
        self.is_running = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
    
    def stop(self):
        """Stop monitoring"""
        self.is_running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=2)
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                self._check_processes()
                time.sleep(self.check_interval)
            except Exception as e:
                print(f"Error in process monitoring: {e}")
                time.sleep(1)
    
    def _check_processes(self):
        """Check semua proses yang berjalan"""
        current_processes = {}
        
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                proc_info = proc.info
                proc_name = proc_info['name'].lower()
                
                # Check blocked apps
                if self._is_blocked(proc_name):
                    if self.violation_callback:
                        self.violation_callback({
                            'type': 'application_blocked',
                            'process_name': proc_name,
                            'pid': proc_info['pid'],
                            'description': f"Aplikasi terlarang terdeteksi: {proc_name}"
                        })
                    
                    # Kill process
                    try:
                        proc.kill()
                    except:
                        pass
                
                # Track process
                current_processes[proc_name] = proc
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        self.tracked_processes = current_processes
    
    def _is_blocked(self, proc_name: str) -> bool:
        """Check if process is blocked"""
        # Check blacklist
        if self.blocked_apps:
            for blocked in self.blocked_apps:
                if blocked.lower() in proc_name:
                    return True
        
        # Check whitelist (jika ada whitelist, hanya yang di whitelist yang diizinkan)
        if self.allowed_apps:
            is_allowed = False
            for allowed in self.allowed_apps:
                if allowed.lower() in proc_name:
                    is_allowed = True
                    break
            if not is_allowed:
                return True
        
        return False
    
    def get_running_processes(self) -> List[Dict]:
        """Get list of running processes"""
        processes = []
        for name, proc in self.tracked_processes.items():
            try:
                processes.append({
                    'name': name,
                    'pid': proc.pid,
                    'status': proc.status()
                })
            except:
                pass
        return processes
    
    def kill_process(self, pid: int) -> bool:
        """Kill process by PID"""
        try:
            proc = psutil.Process(pid)
            proc.kill()
            return True
        except:
            return False
    
    def kill_process_by_name(self, name: str) -> bool:
        """Kill process by name"""
        killed = False
        for proc_name, proc in self.tracked_processes.items():
            if name.lower() in proc_name.lower():
                try:
                    proc.kill()
                    killed = True
                except:
                    pass
        return killed
