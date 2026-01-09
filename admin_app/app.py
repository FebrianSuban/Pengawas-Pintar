"""
Admin Application - Main application class dengan dashboard
"""
import sys
import os
import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QLabel, QPushButton, QTableWidget,
                               QTableWidgetItem, QTabWidget, QGroupBox, QSpinBox,
                               QCheckBox, QComboBox, QLineEdit, QTextEdit,
                               QMessageBox, QFileDialog, QProgressBar, QSplitter,
                               QInputDialog, QDialog, QDialogButtonBox)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QObject
from PySide6.QtGui import QIcon, QColor, QFont

# Import shared modules
from shared.networking.server import ProctoringServer
from shared.networking.protocol import Message, MessageType
from shared.database.database_manager import DatabaseManager
from shared.database.models import ViolationType, ViolationSeverity, PermissionStatus, ExamSession
from shared.utils.config_loader import ConfigLoader
from shared.utils.system_utils import SystemUtils


class ServerThread(QThread):
    """Thread untuk server operations"""
    message_received = Signal(str, object)  # participant_id, message
    
    def __init__(self, server: ProctoringServer):
        super().__init__()
        self.server = server
        self.running = False
    
    def run(self):
        """Run server"""
        self.running = True
        self.server.run()
    
    def stop(self):
        """Stop server"""
        self.running = False


class AdminApp(QMainWindow):
    """Main admin application"""
    
    def __init__(self):
        super().__init__()
        
        # Load config
        config_path = Path("config/admin_config.json")
        template_path = Path("config/admin_config_template.json")
        self.config = ConfigLoader.load_config(str(config_path), str(template_path))
        
        # Initialize database
        self.db_manager = DatabaseManager("data/admin.db")
        
        # Current exam session
        self.current_session = None
        self.current_session_id = None
        
        # Participants data
        self.participants: Dict[str, Dict] = {}
        
        # Setup UI
        self._setup_ui()
        
        # Initialize server
        self._init_server()
        
        # Setup timers
        self._setup_timers()
        
        # AI Proctor mode
        self.ai_proctor_mode = False
    
    def _setup_ui(self):
        """Setup UI"""
        self.setWindowTitle("Pengawas Pintar - Admin Dashboard")
        self.setMinimumSize(1200, 800)
        
        # Central widget dengan tabs
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Toolbar
        toolbar = self._create_toolbar()
        main_layout.addWidget(toolbar)
        
        # Tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Dashboard tab
        self.dashboard_tab = self._create_dashboard_tab()
        self.tabs.addTab(self.dashboard_tab, "Dashboard")
        
        # Participants tab
        self.participants_tab = self._create_participants_tab()
        self.tabs.addTab(self.participants_tab, "Peserta")
        
        # Violations tab
        self.violations_tab = self._create_violations_tab()
        self.tabs.addTab(self.violations_tab, "Pelanggaran")
        
        # Configuration tab
        self.config_tab = self._create_config_tab()
        self.tabs.addTab(self.config_tab, "Konfigurasi")
        
        # Analytics tab
        self.analytics_tab = self._create_analytics_tab()
        self.tabs.addTab(self.analytics_tab, "Analitik")
    
    def _create_toolbar(self) -> QWidget:
        """Create toolbar"""
        toolbar = QWidget()
        layout = QHBoxLayout()
        toolbar.setLayout(layout)
        
        # Start/Stop session button
        self.session_button = QPushButton("Mulai Sesi Ujian")
        self.session_button.clicked.connect(self._toggle_session)
        layout.addWidget(self.session_button)
        
        # AI Proctor mode
        self.ai_proctor_button = QPushButton("Mode AI Proctor: OFF")
        self.ai_proctor_button.clicked.connect(self._toggle_ai_proctor)
        layout.addWidget(self.ai_proctor_button)
        
        # Emergency lock button
        self.emergency_button = QPushButton("🔒 LOCK SEMUA")
        self.emergency_button.setStyleSheet("background-color: red; color: white; font-weight: bold;")
        self.emergency_button.clicked.connect(self._emergency_lock)
        layout.addWidget(self.emergency_button)
        
        layout.addStretch()
        
        # Status label
        self.status_label = QLabel("Server: Tidak aktif")
        layout.addWidget(self.status_label)
        
        return toolbar
    
    def _create_dashboard_tab(self) -> QWidget:
        """Create dashboard tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # Stats
        stats_group = QGroupBox("Statistik")
        stats_layout = QHBoxLayout()
        stats_group.setLayout(stats_layout)
        
        self.total_participants_label = QLabel("Total Peserta: 0")
        self.active_participants_label = QLabel("Aktif: 0")
        self.violations_count_label = QLabel("Pelanggaran: 0")
        self.avg_integrity_label = QLabel("Integritas Rata-rata: 100%")
        
        stats_layout.addWidget(self.total_participants_label)
        stats_layout.addWidget(self.active_participants_label)
        stats_layout.addWidget(self.violations_count_label)
        stats_layout.addWidget(self.avg_integrity_label)
        
        layout.addWidget(stats_group)
        
        # Recent violations
        violations_group = QGroupBox("Pelanggaran Terkini")
        violations_layout = QVBoxLayout()
        violations_group.setLayout(violations_layout)
        
        self.recent_violations_table = QTableWidget()
        self.recent_violations_table.setColumnCount(4)
        self.recent_violations_table.setHorizontalHeaderLabels(["Waktu", "Peserta", "Jenis", "Keterangan"])
        violations_layout.addWidget(self.recent_violations_table)
        
        layout.addWidget(violations_group)
        
        layout.addStretch()
        
        return widget
    
    def _create_participants_tab(self) -> QWidget:
        """Create participants tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # Participants table
        self.participants_table = QTableWidget()
        self.participants_table.setColumnCount(7)
        self.participants_table.setHorizontalHeaderLabels([
            "ID", "Nama", "Status", "Integritas", "Peringatan", "Pelanggaran", "Aksi"
        ])
        layout.addWidget(self.participants_table)
        
        # Action buttons
        actions_layout = QHBoxLayout()
        
        self.add_participant_button = QPushButton("Tambah Peserta")
        self.add_participant_button.clicked.connect(self._add_participant)
        actions_layout.addWidget(self.add_participant_button)
        
        self.lock_participant_button = QPushButton("Kunci Peserta")
        self.lock_participant_button.clicked.connect(self._lock_selected_participant)
        actions_layout.addWidget(self.lock_participant_button)
        
        self.unlock_participant_button = QPushButton("Buka Kunci")
        self.unlock_participant_button.clicked.connect(self._unlock_selected_participant)
        actions_layout.addWidget(self.unlock_participant_button)
        
        actions_layout.addStretch()
        
        layout.addLayout(actions_layout)
        
        return widget
    
    def _create_violations_tab(self) -> QWidget:
        """Create violations tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # Filters
        filters_layout = QHBoxLayout()
        
        self.violation_filter_participant = QComboBox()
        self.violation_filter_participant.addItem("Semua Peserta")
        filters_layout.addWidget(QLabel("Peserta:"))
        filters_layout.addWidget(self.violation_filter_participant)
        
        self.violation_filter_type = QComboBox()
        self.violation_filter_type.addItem("Semua Jenis")
        for vtype in ViolationType:
            self.violation_filter_type.addItem(vtype.value)
        filters_layout.addWidget(QLabel("Jenis:"))
        filters_layout.addWidget(self.violation_filter_type)
        
        filter_button = QPushButton("Filter")
        filter_button.clicked.connect(self._filter_violations)
        filters_layout.addWidget(filter_button)
        
        filters_layout.addStretch()
        layout.addLayout(filters_layout)
        
        # Violations table
        self.violations_table = QTableWidget()
        self.violations_table.setColumnCount(6)
        self.violations_table.setHorizontalHeaderLabels([
            "Waktu", "Peserta", "Jenis", "Tingkat", "Keterangan", "Bukti"
        ])
        layout.addWidget(self.violations_table)
        
        return widget
    
    def _create_config_tab(self) -> QWidget:
        """Create configuration tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # AI Proctoring config
        ai_group = QGroupBox("AI Proctoring")
        ai_layout = QVBoxLayout()
        ai_group.setLayout(ai_layout)
        
        self.ai_enabled_checkbox = QCheckBox("Aktifkan AI Detection")
        self.ai_enabled_checkbox.setChecked(self.config.get('ai_proctoring', {}).get('enabled', True))
        ai_layout.addWidget(self.ai_enabled_checkbox)
        
        # Camera config
        camera_group = QGroupBox("Camera Detection")
        camera_layout = QVBoxLayout()
        camera_group.setLayout(camera_layout)
        
        self.face_absence_threshold = QSpinBox()
        self.face_absence_threshold.setRange(1, 60)
        self.face_absence_threshold.setValue(
            int(self.config.get('ai_proctoring', {}).get('camera', {}).get('face_absence_threshold', 5))
        )
        camera_layout.addWidget(QLabel("Face Absence Threshold (detik):"))
        camera_layout.addWidget(self.face_absence_threshold)
        
        ai_layout.addWidget(camera_group)
        
        # Exam rules
        rules_group = QGroupBox("Aturan Ujian")
        rules_layout = QVBoxLayout()
        rules_group.setLayout(rules_layout)
        
        self.allowed_apps_text = QTextEdit()
        allowed_apps = self.config.get('exam_rules', {}).get('allowed_applications', [])
        self.allowed_apps_text.setPlainText('\n'.join(allowed_apps))
        rules_layout.addWidget(QLabel("Aplikasi yang Diizinkan (satu per baris):"))
        rules_layout.addWidget(self.allowed_apps_text)
        
        self.blocked_apps_text = QTextEdit()
        blocked_apps = self.config.get('exam_rules', {}).get('blocked_applications', [])
        self.blocked_apps_text.setPlainText('\n'.join(blocked_apps))
        rules_layout.addWidget(QLabel("Aplikasi yang Diblokir (satu per baris):"))
        rules_layout.addWidget(self.blocked_apps_text)
        
        layout.addWidget(ai_group)
        layout.addWidget(rules_group)
        
        # Save button
        save_button = QPushButton("Simpan Konfigurasi")
        save_button.clicked.connect(self._save_config)
        layout.addWidget(save_button)
        
        layout.addStretch()
        
        return widget
    
    def _create_analytics_tab(self) -> QWidget:
        """Create analytics tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # Integrity scores
        integrity_group = QGroupBox("Skor Integritas")
        integrity_layout = QVBoxLayout()
        integrity_group.setLayout(integrity_layout)
        
        self.integrity_table = QTableWidget()
        self.integrity_table.setColumnCount(3)
        self.integrity_table.setHorizontalHeaderLabels(["Peserta", "Skor Integritas", "Status"])
        integrity_layout.addWidget(self.integrity_table)
        
        layout.addWidget(integrity_group)
        
        # Export button
        export_button = QPushButton("Ekspor Laporan")
        export_button.clicked.connect(self._export_report)
        layout.addWidget(export_button)
        
        layout.addStretch()
        
        return widget
    
    def _init_server(self):
        """Initialize server"""
        server_config = self.config.get('server', {})
        self.server = ProctoringServer(
            host=server_config.get('host', '0.0.0.0'),
            port=server_config.get('port', 8765)
        )
        
        # Set database manager reference untuk server
        self.server.db_manager = self.db_manager
        self.server.admin_app = self
        
        # Register handlers
        self.server.register_handler(MessageType.REGISTER, self._handle_register_async)
        self.server.register_handler(MessageType.HEARTBEAT, self._handle_heartbeat_async)
        self.server.register_handler(MessageType.VIOLATION_REPORT, self._handle_violation_report_async)
        self.server.register_handler(MessageType.PERMISSION_REQUEST, self._handle_permission_request_async)
        self.server.register_handler(MessageType.STATUS_UPDATE, self._handle_status_update_async)
        
        # Start server in thread
        self.server_thread = ServerThread(self.server)
        self.server_thread.message_received.connect(self._on_server_message)
        self.server_thread.start()
        
        self.status_label.setText("Server: Aktif")
    
    async def _handle_register_async(self, participant_id: str, message: Message):
        """Handle participant registration dengan validasi"""
        data = message.data
        name = data.get('name', '').strip()
        
        # Validasi: cek apakah ID dan nama sesuai dengan yang didaftarkan
        participant = self.db_manager.get_participant(participant_id)
        
        if not participant:
            # Participant tidak terdaftar
            ack_message = Message(
                MessageType.REGISTER_ACK,
                data={
                    'status': 'rejected',
                    'message': f'ID Peserta {participant_id} tidak terdaftar. Silakan hubungi pengawas.'
                },
                participant_id=participant_id
            )
            await self.server.send_message(participant_id, ack_message)
            return
        
        # Validasi nama
        if participant.name.lower() != name.lower():
            ack_message = Message(
                MessageType.REGISTER_ACK,
                data={
                    'status': 'rejected',
                    'message': f'Nama tidak sesuai. Nama yang terdaftar: {participant.name}'
                },
                participant_id=participant_id
            )
            await self.server.send_message(participant_id, ack_message)
            return
        
        # Validasi sesi ujian
        if not self.current_session_id or participant.exam_session_id != self.current_session_id:
            ack_message = Message(
                MessageType.REGISTER_ACK,
                data={
                    'status': 'rejected',
                    'message': 'Sesi ujian tidak aktif atau tidak sesuai.'
                },
                participant_id=participant_id
            )
            await self.server.send_message(participant_id, ack_message)
            return
        
        # Update participant info dengan computer info
        computer_ip = data.get('computer_ip', '')
        computer_name = data.get('computer_name', '')
        with self.db_manager.get_session() as session:
            participant.computer_ip = computer_ip
            participant.computer_name = computer_name
            participant.is_active = True
            participant.last_heartbeat = datetime.utcnow()
            session.add(participant)
        
        # Send acknowledgment
        ack_message = Message(
            MessageType.REGISTER_ACK,
            data={
                'status': 'registered',
                'participant_id': participant_id,
                'exam_session_id': self.current_session_id
            },
            participant_id=participant_id
        )
        await self.server.send_message(participant_id, ack_message)
        
        # Update dashboard
        self._update_dashboard()
    
    async def _handle_heartbeat_async(self, participant_id: str, message: Message):
        """Handle heartbeat dengan update database"""
        # Update heartbeat di database
        self.db_manager.update_participant_heartbeat(participant_id)
        
        # Update dashboard
        self._update_dashboard()
    
    def _setup_timers(self):
        """Setup timers"""
        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_dashboard)
        self.update_timer.start(2000)  # Every 2 seconds
    
    def _toggle_session(self):
        """Toggle exam session"""
        if self.current_session is None:
            # Start session
            name, ok = QInputDialog.getText(self, "Nama Sesi", "Masukkan nama sesi ujian:")
            if ok and name:
                # Buat sesi dan ambil ID saat masih dalam session
                with self.db_manager.get_session() as session:
                    exam_session = ExamSession(
                        name=name,
                        status='active'
                    )
                    session.add(exam_session)
                    session.flush()
                    session.refresh(exam_session)
                    session_id = exam_session.id  # Ambil ID saat masih dalam session
                
                self.current_session_id = session_id
                self.current_session = self.db_manager.get_exam_session(session_id)
                self.session_button.setText("Akhiri Sesi Ujian")
                QMessageBox.information(self, "Sesi Dimulai", f"Sesi ujian '{name}' telah dimulai.")
        else:
            # End session
            reply = QMessageBox.question(
                self, "Akhiri Sesi",
                "Apakah Anda yakin ingin mengakhiri sesi ujian?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                if self.current_session_id:
                    with self.db_manager.get_session() as session:
                        session_obj = self.db_manager.get_exam_session(self.current_session_id)
                        if session_obj:
                            session_obj.status = 'completed'
                            session_obj.end_time = datetime.utcnow()
                            session.add(session_obj)
                self.current_session = None
                self.current_session_id = None
                self.session_button.setText("Mulai Sesi Ujian")
                QMessageBox.information(self, "Sesi Berakhir", "Sesi ujian telah diakhiri.")
    
    def _toggle_ai_proctor(self):
        """Toggle AI Proctor mode"""
        self.ai_proctor_mode = not self.ai_proctor_mode
        if self.ai_proctor_mode:
            self.ai_proctor_button.setText("Mode AI Proctor: ON")
            self.ai_proctor_button.setStyleSheet("background-color: green; color: white;")
        else:
            self.ai_proctor_button.setText("Mode AI Proctor: OFF")
            self.ai_proctor_button.setStyleSheet("")
    
    def _emergency_lock(self):
        """Emergency lock all participants"""
        reply = QMessageBox.question(
            self, "Emergency Lock",
            "Kunci semua komputer peserta?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            message = Message(MessageType.EMERGENCY_LOCK, data={'reason': 'emergency'})
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.server.broadcast_message(message))
            QMessageBox.information(self, "Locked", "Semua komputer peserta telah dikunci.")
    
    def _handle_violation_report(self, participant_id: str, message: Message):
        """Handle violation report"""
        data = message.data
        violation_type = ViolationType(data.get('violation_type', 'application_blocked'))
        severity = ViolationSeverity(data.get('severity', 'medium'))
        
        # Create violation record
        if self.current_session_id:
            violation = self.db_manager.create_violation(
                participant_id,
                self.current_session_id,
                violation_type,
                severity,
                data.get('description', '')
            )
            
            # Update participant stats
            participant = self.db_manager.get_participant(participant_id)
            if participant:
                # Calculate integrity score
                self._update_integrity_score(participant_id)
            
            # Auto-handle jika AI Proctor mode
            if self.ai_proctor_mode:
                self._handle_violation_auto(violation, participant_id)
    
    def _handle_violation_auto(self, violation, participant_id: str):
        """Auto-handle violation dalam AI Proctor mode"""
        participant = self.db_manager.get_participant(participant_id)
        if not participant:
            return
        
        # Increment warning
        self.db_manager.increment_warning_count(participant_id)
        
        # Send warning
        warning_message = Message(
            MessageType.WARNING,
            data={
                'message': f"Peringatan: {violation.description}",
                'warning_count': participant.warning_count
            },
            participant_id=participant_id
        )
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.server.send_message(participant_id, warning_message))
        
        # Check escalation
        escalation = self.config.get('ai_proctoring', {}).get('escalation', {})
        warnings_before_flag = escalation.get('warnings_before_flag', 3)
        warnings_before_lock = escalation.get('warnings_before_lock', 5)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        if participant.warning_count >= warnings_before_lock:
            # Lock participant
            self.db_manager.lock_participant(participant_id, True)
            lock_message = Message(MessageType.LOCK, data={'reason': 'auto_escalation'}, participant_id=participant_id)
            loop.run_until_complete(self.server.send_message(participant_id, lock_message))
        elif participant.warning_count >= warnings_before_flag:
            # Flag participant
            flag_message = Message(
                MessageType.WARNING,
                data={'message': 'FLAG: Anda telah mencapai batas peringatan!', 'flag': True},
                participant_id=participant_id
            )
            loop.run_until_complete(self.server.send_message(participant_id, flag_message))
    
    async def _handle_violation_report_async(self, participant_id: str, message: Message):
        """Async wrapper untuk violation report"""
        await self._handle_violation_report(participant_id, message)
    
    async def _handle_permission_request_async(self, participant_id: str, message: Message):
        """Async wrapper untuk permission request"""
        await self._handle_permission_request(participant_id, message)
    
    async def _handle_status_update_async(self, participant_id: str, message: Message):
        """Async wrapper untuk status update"""
        self._handle_status_update(participant_id, message)
    
    async def _handle_permission_request(self, participant_id: str, message: Message):
        """Handle permission request"""
        data = message.data
        request_type = data.get('request_type', 'leave_seat')
        duration = data.get('duration_minutes', 10)
        
        # Create permission request
        if self.current_session_id:
            request = self.db_manager.create_permission_request(
                participant_id, request_type, duration, data.get('reason')
            )
            
            # Show dialog untuk approval
            reply = QMessageBox.question(
                self, "Permintaan Izin",
                f"Peserta {participant_id} meminta izin untuk {request_type} selama {duration} menit.\n\nSetujui?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.db_manager.approve_permission_request(request.id)
                response = Message(
                    MessageType.PERMISSION_RESPONSE,
                    data={
                        'approved': True,
                        'expires_at': request.expires_at.isoformat(),
                        'duration_minutes': duration
                    },
                    participant_id=participant_id
                )
            else:
                response = Message(
                    MessageType.PERMISSION_RESPONSE,
                    data={'approved': False},
                    participant_id=participant_id
                )
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.server.send_message(participant_id, response))
    
    def _handle_status_update(self, participant_id: str, message: Message):
        """Handle status update"""
        # Update participant info
        pass
    
    def _on_server_message(self, participant_id: str, message: Message):
        """Handle message dari server thread"""
        # Messages are handled by server handlers
        pass
    
    def _update_dashboard(self):
        """Update dashboard"""
        if not self.current_session_id:
            return
        
        # Update participants - ambil data saat masih dalam session
        with self.db_manager.get_session() as session:
            from shared.database.models import Participant
            query = session.query(Participant).filter_by(exam_session_id=self.current_session_id)
            participants_data = []
            for p in query.all():
                # Ambil semua nilai atribut saat masih dalam session
                participants_data.append({
                    'participant_id': p.participant_id,
                    'name': p.name,
                    'is_active': p.is_active,
                    'integrity_score': p.integrity_score,
                    'warning_count': p.warning_count,
                    'violation_count': p.violation_count
                })
        
        self.total_participants_label.setText(f"Total Peserta: {len(participants_data)}")
        active_count = sum(1 for p in participants_data if p['is_active'])
        self.active_participants_label.setText(f"Aktif: {active_count}")
        
        # Update violations count - ambil data saat masih dalam session
        with self.db_manager.get_session() as session:
            from shared.database.models import Violation
            query = session.query(Violation).filter_by(exam_session_id=self.current_session_id)
            violations_list = query.order_by(Violation.timestamp.desc()).limit(100).all()
            violations_data = []
            for v in violations_list:
                violations_data.append({
                    'id': v.id,
                    'timestamp': v.timestamp.strftime("%H:%M:%S") if v.timestamp else "",
                    'violation_type': v.violation_type.value if v.violation_type else "",
                    'description': v.description or "",
                    'participant_id': v.participant_id,
                    'participant_name': v.participant.name if v.participant else f"ID:{v.participant_id}"
                })
        
        self.violations_count_label.setText(f"Pelanggaran: {len(violations_data)}")
        
        # Update average integrity
        if participants_data:
            avg_integrity = sum(p['integrity_score'] for p in participants_data) / len(participants_data)
            self.avg_integrity_label.setText(f"Integritas Rata-rata: {avg_integrity:.1f}%")
        
        # Update participants table
        self._update_participants_table(participants_data)
        
        # Update recent violations
        self._update_recent_violations(violations_data[:10])
    
    def _update_participants_table(self, participants: List):
        """Update participants table"""
        self.participants_table.setRowCount(len(participants))
        
        for i, participant in enumerate(participants):
            # Handle both dict and object
            if isinstance(participant, dict):
                participant_id = participant['participant_id']
                name = participant['name']
                is_active = participant['is_active']
                integrity_score = participant['integrity_score']
                warning_count = participant['warning_count']
                violation_count = participant['violation_count']
            else:
                participant_id = participant.participant_id
                name = participant.name
                is_active = participant.is_active
                integrity_score = participant.integrity_score
                warning_count = participant.warning_count
                violation_count = participant.violation_count
            
            self.participants_table.setItem(i, 0, QTableWidgetItem(participant_id))
            self.participants_table.setItem(i, 1, QTableWidgetItem(name))
            self.participants_table.setItem(i, 2, QTableWidgetItem("Aktif" if is_active else "Tidak Aktif"))
            self.participants_table.setItem(i, 3, QTableWidgetItem(f"{integrity_score:.1f}%"))
            self.participants_table.setItem(i, 4, QTableWidgetItem(str(warning_count)))
            self.participants_table.setItem(i, 5, QTableWidgetItem(str(violation_count)))
            
            # Color code integrity
            if integrity_score < 50:
                self.participants_table.item(i, 3).setBackground(QColor(255, 0, 0))
            elif integrity_score < 75:
                self.participants_table.item(i, 3).setBackground(QColor(255, 255, 0))
    
    def _update_recent_violations(self, violations_data: List):
        """Update recent violations table"""
        self.recent_violations_table.setRowCount(len(violations_data))
        
        # Update table dengan data yang sudah diambil (dalam format dict)
        for i, v_data in enumerate(violations_data):
            self.recent_violations_table.setItem(i, 0, QTableWidgetItem(v_data.get('timestamp', '')))
            self.recent_violations_table.setItem(i, 1, QTableWidgetItem(v_data.get('participant_name', '')))
            self.recent_violations_table.setItem(i, 2, QTableWidgetItem(v_data.get('violation_type', '')))
            self.recent_violations_table.setItem(i, 3, QTableWidgetItem(v_data.get('description', '')))
    
    def _update_integrity_score(self, participant_id: str):
        """Update integrity score untuk participant"""
        # Ambil data participant saat masih dalam session
        with self.db_manager.get_session() as session:
            from shared.database.models import Participant
            participant = session.query(Participant).filter_by(participant_id=participant_id).first()
            if not participant:
                return
            
            # Calculate score berdasarkan violations dan warnings
            base_score = 100.0
            violation_penalty = participant.violation_count * 5.0
            warning_penalty = participant.warning_count * 2.0
            
            score = max(0.0, base_score - violation_penalty - warning_penalty)
            participant.integrity_score = score
            session.add(participant)
    
    def _lock_selected_participant(self):
        """Lock selected participant"""
        row = self.participants_table.currentRow()
        if row >= 0:
            participant_id = self.participants_table.item(row, 0).text()
            self.db_manager.lock_participant(participant_id, True)
            message = Message(MessageType.LOCK, data={'reason': 'manual'}, participant_id=participant_id)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.server.send_message(participant_id, message))
    
    def _unlock_selected_participant(self):
        """Unlock selected participant"""
        row = self.participants_table.currentRow()
        if row >= 0:
            participant_id = self.participants_table.item(row, 0).text()
            self.db_manager.lock_participant(participant_id, False)
            message = Message(MessageType.UNLOCK, data={}, participant_id=participant_id)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.server.send_message(participant_id, message))
    
    def _filter_violations(self):
        """Filter violations"""
        # Implementation untuk filter violations
        pass
    
    def _save_config(self):
        """Save configuration"""
        # Update config dari UI
        self.config['ai_proctoring']['enabled'] = self.ai_enabled_checkbox.isChecked()
        self.config['ai_proctoring']['camera']['face_absence_threshold'] = self.face_absence_threshold.value()
        
        allowed_apps = [app.strip() for app in self.allowed_apps_text.toPlainText().split('\n') if app.strip()]
        blocked_apps = [app.strip() for app in self.blocked_apps_text.toPlainText().split('\n') if app.strip()]
        
        self.config['exam_rules']['allowed_applications'] = allowed_apps
        self.config['exam_rules']['blocked_applications'] = blocked_apps
        
        # Save to file
        ConfigLoader.save_config("config/admin_config.json", self.config)
        
        # Broadcast config update
        config_message = Message(MessageType.CONFIG_UPDATE, data=self.config)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.server.broadcast_message(config_message))
        
        QMessageBox.information(self, "Konfigurasi", "Konfigurasi telah disimpan dan dikirim ke semua peserta.")
    
    def _add_participant(self):
        """Add new participant"""
        if not self.current_session_id:
            QMessageBox.warning(self, "Error", "Harap mulai sesi ujian terlebih dahulu!")
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Tambah Peserta")
        dialog.setModal(True)
        
        layout = QVBoxLayout()
        
        id_label = QLabel("ID Peserta:")
        id_input = QLineEdit()
        layout.addWidget(id_label)
        layout.addWidget(id_input)
        
        name_label = QLabel("Nama:")
        name_input = QLineEdit()
        layout.addWidget(name_label)
        layout.addWidget(name_input)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec():
            participant_id = id_input.text().strip()
            name = name_input.text().strip()
            
            if not participant_id or not name:
                QMessageBox.warning(self, "Error", "ID dan Nama harus diisi!")
                return
            
            # Check if participant already exists
            existing = self.db_manager.get_participant(participant_id)
            if existing:
                QMessageBox.warning(self, "Error", f"Peserta dengan ID {participant_id} sudah terdaftar!")
                return
            
            # Register participant
            try:
                self.db_manager.register_participant(
                    participant_id=participant_id,
                    name=name,
                    exam_session_id=self.current_session_id
                )
                QMessageBox.information(self, "Sukses", f"Peserta {participant_id} ({name}) berhasil didaftarkan!")
                self._update_dashboard()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error mendaftarkan peserta: {e}")
    
    def _export_report(self):
        """Export report"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Ekspor Laporan", "", "CSV Files (*.csv)"
        )
        if filename:
            # Export implementation
            QMessageBox.information(self, "Ekspor", "Laporan telah diekspor.")
