"""
Participant Application - Main application class
"""
import sys
import os
import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QLabel, QPushButton, QSystemTrayIcon,
                               QMenu, QMessageBox, QDialog, QLineEdit, QTextEdit, QStyle)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QObject
from PySide6.QtGui import QIcon, QAction

# Import shared modules
from shared.networking.client import ProctoringClient
from shared.networking.protocol import Message, MessageType
from shared.ai_detection.detection_manager import DetectionManager
from shared.utils.process_monitor import ProcessMonitor
from shared.utils.config_loader import ConfigLoader
from shared.utils.system_utils import SystemUtils
from shared.utils.evidence_capture import EvidenceCapture
from shared.database.database_manager import DatabaseManager
from shared.database.models import ViolationType, ViolationSeverity


class NetworkThread(QThread):
    """Thread untuk network operations"""
    message_received = Signal(object)
    connected = Signal(bool)
    
    def __init__(self, client: ProctoringClient):
        super().__init__()
        self.client = client
        self.running = False
    
    def run(self):
        """Run network thread"""
        self.running = True
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Start client
        name = SystemUtils.get_computer_name()
        ip = SystemUtils.get_local_ip()
        loop.run_until_complete(
            self.client.start(name, ip, SystemUtils.get_computer_name())
        )
    
    def stop(self):
        """Stop network thread"""
        self.running = False
        self.client.stop()


class ParticipantApp(QMainWindow):
    """Main participant application"""
    
    def __init__(self):
        super().__init__()
        
        # Load config
        config_path = Path("config/participant_config.json")
        template_path = Path("config/participant_config_template.json")
        self.config = ConfigLoader.load_config(str(config_path), str(template_path))
        
        # Initialize components
        # Selalu tampilkan dialog registrasi untuk validasi
        self.participant_id = ''
        self.participant_name = ''
        
        # Tampilkan dialog registrasi (akan memvalidasi dengan server)
        self._show_registration_dialog()
        
        # Pastikan ID dan nama sudah diisi dan valid
        if not self.participant_id or not self.participant_name:
            QMessageBox.critical(
                None, "Error", 
                "ID dan Nama peserta harus diisi dan divalidasi dengan server!\n\n"
                "Pastikan:\n"
                "1. Server admin sudah berjalan\n"
                "2. Sesi ujian sudah dimulai\n"
                "3. ID dan Nama sesuai dengan yang didaftarkan di admin"
            )
            sys.exit(1)
        
        # Setup UI
        self._setup_ui()
        self._setup_tray_icon()
        
        # Initialize monitoring
        self._init_monitoring()
        
        # Setup timers
        self._setup_timers()
        
        # State
        self.is_locked = False
        self.permission_active = False
        
        # Prevent closing
        self.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)
    
    def _show_registration_dialog(self):
        """Show registration dialog dengan validasi server"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Registrasi Peserta")
        dialog.setModal(True)
        
        layout = QVBoxLayout()
        
        info_label = QLabel("Masukkan ID dan Nama sesuai dengan yang didaftarkan oleh pengawas:")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        id_label = QLabel("ID Peserta:")
        id_input = QLineEdit()
        layout.addWidget(id_label)
        layout.addWidget(id_input)
        
        name_label = QLabel("Nama:")
        name_input = QLineEdit()
        layout.addWidget(name_label)
        layout.addWidget(name_input)
        
        status_label = QLabel("")
        status_label.setStyleSheet("color: red;")
        layout.addWidget(status_label)
        
        # Button layout
        button_layout = QHBoxLayout()
        button = QPushButton("Daftar")
        cancel_button = QPushButton("Batal")
        
        def cancel_and_exit():
            reply = QMessageBox.question(
                dialog, "Konfirmasi",
                "Anda yakin ingin keluar? Anda harus memasukkan ID dan Nama yang valid untuk menggunakan aplikasi.",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                sys.exit(0)
        
        cancel_button.clicked.connect(cancel_and_exit)
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(button)
        
        def validate_and_accept():
            participant_id = id_input.text().strip()
            name = name_input.text().strip()
            
            if not participant_id or not name:
                status_label.setText("ID dan Nama harus diisi!")
                return
            
            # Disable button saat validasi
            button.setEnabled(False)
            status_label.setText("Memvalidasi dengan server...")
            status_label.setStyleSheet("color: blue;")
            
            # Validasi dengan server
            server_config = self.config.get('admin_server', {})
            server_host = server_config.get('host', 'localhost')
            server_port = server_config.get('port', 8765)
            
            try:
                import urllib.request
                import urllib.parse
                url = f"http://{server_host}:{server_port}/validate_participant/{urllib.parse.quote(participant_id)}?name={urllib.parse.quote(name)}"
                
                with urllib.request.urlopen(url, timeout=10) as response:
                    result = json.loads(response.read().decode())
                    
                    if result.get('valid'):
                        self.participant_id = participant_id
                        self.participant_name = name
                        
                        # Save to config
                        self.config['participant']['id'] = self.participant_id
                        self.config['participant']['name'] = self.participant_name
                        ConfigLoader.save_config("config/participant_config.json", self.config)
                        
                        status_label.setText("Validasi berhasil!")
                        status_label.setStyleSheet("color: green;")
                        QMessageBox.information(dialog, "Berhasil", "Registrasi berhasil! Anda dapat terhubung ke server.")
                        dialog.accept()
                    else:
                        status_label.setText(result.get('message', 'Validasi gagal!'))
                        status_label.setStyleSheet("color: red;")
                        button.setEnabled(True)
            except urllib.error.URLError as e:
                error_msg = str(e)
                if "timed out" in error_msg.lower() or "timeout" in error_msg.lower():
                    status_label.setText(f"Error: Server tidak merespons. Pastikan server admin sudah berjalan di {server_host}:{server_port}")
                elif "Connection refused" in error_msg or "No connection" in error_msg:
                    status_label.setText(f"Error: Tidak dapat terhubung ke server. Pastikan server admin berjalan di {server_host}:{server_port}")
                else:
                    status_label.setText(f"Error: {error_msg}")
                status_label.setStyleSheet("color: red;")
                button.setEnabled(True)
            except Exception as e:
                status_label.setText(f"Error: {str(e)}")
                status_label.setStyleSheet("color: red;")
                button.setEnabled(True)
        
        button.clicked.connect(validate_and_accept)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        
        # Set dialog agar tidak bisa ditutup tanpa validasi (hilangkan tombol X)
        dialog.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint)
        
        # Prevent closing without validation
        original_close = dialog.closeEvent
        def closeEvent(event):
            if not self.participant_id or not self.participant_name:
                QMessageBox.warning(
                    dialog, "Peringatan",
                    "Anda harus memasukkan ID dan Nama yang valid untuk melanjutkan!\n\nGunakan tombol 'Batal' jika ingin keluar."
                )
                event.ignore()
            else:
                if original_close:
                    original_close(event)
                else:
                    event.accept()
        
        dialog.closeEvent = closeEvent
        
        # Show dialog dan tunggu sampai validasi berhasil
        dialog.exec()
    
    def _setup_ui(self):
        """Setup UI"""
        self.setWindowTitle("Aplikasi Peserta Ujian")
        self.setMinimumSize(400, 300)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # Participant info
        participant_info = f"ID: {self.participant_id} | Nama: {self.participant_name}"
        participant_label = QLabel(participant_info)
        participant_label.setStyleSheet("font-weight: bold; font-size: 12px; padding: 5px;")
        layout.addWidget(participant_label)
        
        # Status label
        self.status_label = QLabel("Status: Menghubungkan...")
        layout.addWidget(self.status_label)
        
        # Exam info
        self.exam_label = QLabel("Sesi Ujian: -")
        layout.addWidget(self.exam_label)
        
        # Permission button
        self.permission_button = QPushButton("Minta Izin Keluar")
        self.permission_button.clicked.connect(self._request_permission)
        layout.addWidget(self.permission_button)
        
        # Lock message
        self.lock_label = QLabel("")
        self.lock_label.setStyleSheet("color: red; font-weight: bold;")
        self.lock_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lock_label)
        
        # Hide window if configured
        if not self.config.get('ui', {}).get('show_taskbar', False):
            self.hide()
    
    def _setup_tray_icon(self):
        """Setup system tray icon"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        
        self.tray_icon = QSystemTrayIcon(self)
        # Menggunakan SP_DesktopIcon sebagai pengganti SP_ComputerIcon yang tidak tersedia di PySide6
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DesktopIcon))
        
        tray_menu = QMenu()
        
        show_action = QAction("Tampilkan", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        exit_action = QAction("Keluar", self)
        exit_action.triggered.connect(self._attempt_exit)
        tray_menu.addAction(exit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._tray_icon_activated)
        self.tray_icon.show()
    
    def _tray_icon_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
    
    def _init_monitoring(self):
        """Initialize monitoring components"""
        # Network client
        server_config = self.config.get('admin_server', {})
        server_url = f"ws://{server_config.get('host', 'localhost')}:{server_config.get('port', 8765)}"
        
        self.client = ProctoringClient(server_url, self.participant_id)
        self._setup_client_handlers()
        
        # Network thread
        self.network_thread = NetworkThread(self.client)
        self.network_thread.message_received.connect(self._handle_server_message)
        self.network_thread.connected.connect(self._on_connection_changed)
        self.network_thread.start()
        
        # AI Detection
        # Note: Config akan diupdate dari server
        self.detection_manager = DetectionManager({})
        self.detection_manager.set_violation_callback(self._on_violation_detected)
        self.detection_manager.start()
        
        # Process Monitor
        exam_rules = self.config.get('exam_rules', {})
        self.process_monitor = ProcessMonitor(
            allowed_apps=exam_rules.get('allowed_applications', []),
            blocked_apps=exam_rules.get('blocked_applications', [])
        )
        self.process_monitor.set_violation_callback(self._on_process_violation)
        self.process_monitor.start()
        
        # Evidence capture
        self.evidence_capture = EvidenceCapture("evidence")
        
        # Database (optional, untuk local logging)
        self.db_manager = DatabaseManager("data/participant.db")
    
    def _setup_client_handlers(self):
        """Setup client message handlers"""
        def handle_register_ack(msg):
            data = msg.data
            if data.get('status') == 'rejected':
                self._show_warning(data.get('message', 'Registrasi ditolak!'))
                self.status_label.setText("Status: Registrasi Ditolak")
            elif data.get('status') == 'registered':
                self.status_label.setText("Status: Terhubung")
                QMessageBox.information(self, "Berhasil", "Registrasi berhasil!")
        
        def handle_warning(msg):
            self._show_warning(msg.data.get('message', 'Peringatan!'))
        
        def handle_lock(msg):
            self._lock_screen()
        
        def handle_unlock(msg):
            self._unlock_screen()
        
        def handle_permission_response(msg):
            self._handle_permission_response(msg.data)
        
        def handle_emergency_lock(msg):
            self._lock_screen()
            self._show_warning("EMERGENCY LOCK - Semua komputer dikunci!")
        
        def handle_config_update(msg):
            self._update_config(msg.data)
        
        self.client.register_handler(MessageType.REGISTER_ACK, handle_register_ack)
        self.client.register_handler(MessageType.WARNING, handle_warning)
        self.client.register_handler(MessageType.LOCK, handle_lock)
        self.client.register_handler(MessageType.UNLOCK, handle_unlock)
        self.client.register_handler(MessageType.PERMISSION_RESPONSE, handle_permission_response)
        self.client.register_handler(MessageType.EMERGENCY_LOCK, handle_emergency_lock)
        self.client.register_handler(MessageType.CONFIG_UPDATE, handle_config_update)
    
    def _setup_timers(self):
        """Setup timers"""
        # Heartbeat timer
        self.heartbeat_timer = QTimer()
        self.heartbeat_timer.timeout.connect(self._send_heartbeat)
        self.heartbeat_timer.start(5000)  # Every 5 seconds
        
        # Detection timer
        self.detection_timer = QTimer()
        self.detection_timer.timeout.connect(self._check_detections)
        detection_interval = self.config.get('monitoring', {}).get('camera_check_interval', 1.0)
        self.detection_timer.start(int(detection_interval * 1000))
    
    def _send_heartbeat(self):
        """Send heartbeat to server"""
        if self.client.is_connected:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.client.send_heartbeat())
            else:
                loop.run_until_complete(self.client.send_heartbeat())
    
    def _check_detections(self):
        """Check AI detections"""
        if not self.client.is_connected:
            return
        
        detections = self.detection_manager.get_all_detections()
        
        # Send violations
        loop = asyncio.get_event_loop()
        for violation in detections.get('violations', []):
            if loop.is_running():
                asyncio.create_task(
                    self.client.send_violation_report(
                        violation['type'],
                        violation['severity'],
                        violation['description']
                    )
                )
            else:
                loop.run_until_complete(
                    self.client.send_violation_report(
                        violation['type'],
                        violation['severity'],
                        violation['description']
                    )
                )
    
    def _on_violation_detected(self, violation: Dict):
        """Handle violation dari AI detection"""
        # Capture evidence
        violation_id = f"violation_{datetime.utcnow().timestamp()}"
        evidence = self.evidence_capture.capture_violation_evidence(
            violation_id, violation['type']
        )
        
        # Send to server
        if self.client.is_connected:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    self.client.send_violation_report(
                        violation['type'],
                        violation.get('severity', 'medium'),
                        violation.get('description', '')
                    )
                )
            else:
                loop.run_until_complete(
                    self.client.send_violation_report(
                        violation['type'],
                        violation.get('severity', 'medium'),
                        violation.get('description', '')
                    )
                )
    
    def _on_process_violation(self, violation: Dict):
        """Handle violation dari process monitor"""
        # Send to server
        if self.client.is_connected:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    self.client.send_violation_report(
                        violation['type'],
                        'high',
                        violation.get('description', '')
                    )
                )
            else:
                loop.run_until_complete(
                    self.client.send_violation_report(
                        violation['type'],
                        'high',
                        violation.get('description', '')
                    )
                )
    
    def _handle_server_message(self, message: Message):
        """Handle message dari server"""
        # Messages are handled by client handlers
        pass
    
    def _on_connection_changed(self, connected: bool):
        """Handle connection status change"""
        if connected:
            self.status_label.setText("Status: Terhubung")
        else:
            self.status_label.setText("Status: Terputus")
    
    def _show_warning(self, message: str):
        """Show warning message"""
        QMessageBox.warning(self, "Peringatan", message)
    
    def _lock_screen(self):
        """Lock the screen"""
        self.is_locked = True
        self.lock_label.setText("KOMPUTER DIKUNCI")
        SystemUtils.lock_screen()
    
    def _unlock_screen(self):
        """Unlock the screen"""
        self.is_locked = False
        self.lock_label.setText("")
    
    def _request_permission(self):
        """Request permission untuk leave seat"""
        if self.client.is_connected:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    self.client.send_permission_request('leave_seat', 10, "Minta izin keluar")
                )
            else:
                loop.run_until_complete(
                    self.client.send_permission_request('leave_seat', 10, "Minta izin keluar")
                )
            self.permission_button.setText("Menunggu persetujuan...")
            self.permission_button.setEnabled(False)
    
    def _handle_permission_response(self, data: Dict):
        """Handle permission response"""
        if data.get('approved'):
            self.permission_active = True
            expires_at = datetime.fromisoformat(data.get('expires_at'))
            self.detection_manager.set_permission_active(True, expires_at)
            self.permission_button.setText("Izin aktif")
            QTimer.singleShot(int(data.get('duration_minutes', 10)) * 60 * 1000,
                            self._permission_expired)
        else:
            self.permission_button.setText("Minta Izin Keluar")
            self.permission_button.setEnabled(True)
            QMessageBox.information(self, "Izin Ditolak", "Izin Anda ditolak oleh pengawas.")
    
    def _permission_expired(self):
        """Handle permission expiration"""
        self.permission_active = False
        self.detection_manager.set_permission_active(False, None)
        self.permission_button.setText("Minta Izin Keluar")
        self.permission_button.setEnabled(True)
    
    def _update_config(self, config: Dict):
        """Update config dari server"""
        # Update exam rules
        if 'exam_rules' in config:
            exam_rules = config['exam_rules']
            self.process_monitor.allowed_apps = set(exam_rules.get('allowed_applications', []))
            self.process_monitor.blocked_apps = set(exam_rules.get('blocked_applications', []))
        
        # Update AI detection config
        if 'ai_proctoring' in config:
            self.detection_manager.config = config['ai_proctoring']
    
    def _attempt_exit(self):
        """Attempt to exit (will be blocked if unauthorized)"""
        # This is a violation - report it
        if self.client.is_connected:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    self.client.send_violation_report(
                        'process_termination_attempt',
                        'critical',
                        'Percobaan menutup aplikasi peserta'
                    )
                )
            else:
                loop.run_until_complete(
                    self.client.send_violation_report(
                        'process_termination_attempt',
                        'critical',
                        'Percobaan menutup aplikasi peserta'
                    )
                )
        
        # Show warning
        QMessageBox.warning(
            self,
            "Akses Ditolak",
            "Anda tidak diizinkan menutup aplikasi ini selama ujian berlangsung."
        )
    
    def closeEvent(self, event):
        """Handle close event"""
        # Block closing
        self._attempt_exit()
        event.ignore()
    
    def __del__(self):
        """Cleanup"""
        if hasattr(self, 'detection_manager'):
            self.detection_manager.stop()
        if hasattr(self, 'process_monitor'):
            self.process_monitor.stop()
        if hasattr(self, 'network_thread'):
            self.network_thread.stop()
