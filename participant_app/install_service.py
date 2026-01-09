"""
Script untuk install participant app sebagai Windows service
"""
import sys
import os
from pathlib import Path

if sys.platform != 'win32':
    print("Service installation hanya tersedia untuk Windows")
    sys.exit(1)

try:
    import win32serviceutil
    import win32service
    import servicemanager
except ImportError:
    print("pywin32 tidak terinstall. Install dengan: pip install pywin32")
    sys.exit(1)


class ParticipantService(win32serviceutil.ServiceFramework):
    """Windows service untuk participant app"""
    _svc_name_ = "PengawasPintarParticipant"
    _svc_display_name_ = "Pengawas Pintar - Participant"
    _svc_description_ = "Aplikasi peserta untuk sistem proctoring ujian"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32service.CreateEvent(None, 0, 0, None)
        self.app = None
    
    def SvcStop(self):
        """Stop service"""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32service.SetEvent(self.stop_event)
        if self.app:
            self.app.stop()
    
    def SvcDoRun(self):
        """Run service"""
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        
        try:
            from participant_app.app import ParticipantApp
            from PySide6.QtWidgets import QApplication
            
            app = QApplication(sys.argv)
            self.app = ParticipantApp()
            self.app.show()
            app.exec()
        except Exception as e:
            servicemanager.LogErrorMsg(f"Error running service: {e}")


if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(ParticipantService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(ParticipantService)
