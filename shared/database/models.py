"""
Database models untuk sistem proctoring
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


class ViolationType(enum.Enum):
    """Jenis pelanggaran yang dapat dideteksi"""
    APPLICATION_BLOCKED = "application_blocked"
    PROCESS_TERMINATION_ATTEMPT = "process_termination_attempt"
    FACE_ABSENCE = "face_absence"
    MULTIPLE_FACES = "multiple_faces"
    SUSPICIOUS_MOVEMENT = "suspicious_movement"
    VOICE_ACTIVITY = "voice_activity"
    MULTIPLE_SPEAKERS = "multiple_speakers"
    SCREEN_SWITCH = "screen_switch"
    SHORTCUT_BLOCKED = "shortcut_blocked"
    UNAUTHORIZED_WEBSITE = "unauthorized_website"


class ViolationSeverity(enum.Enum):
    """Tingkat keparahan pelanggaran"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PermissionStatus(enum.Enum):
    """Status permintaan izin"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ExamSession(Base):
    """Sesi ujian"""
    __tablename__ = 'exam_sessions'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    status = Column(String(20), default='active')  # active, paused, completed
    config = Column(Text)  # JSON config untuk sesi ini
    
    participants = relationship("Participant", back_populates="exam_session")
    violations = relationship("Violation", back_populates="exam_session")
    
    def __repr__(self):
        return f"<ExamSession(id={self.id}, name='{self.name}', status='{self.status}')>"


class Participant(Base):
    """Peserta ujian"""
    __tablename__ = 'participants'
    
    id = Column(Integer, primary_key=True)
    participant_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    exam_session_id = Column(Integer, ForeignKey('exam_sessions.id'), nullable=False)
    computer_ip = Column(String(50))
    computer_name = Column(String(200))
    joined_at = Column(DateTime, default=datetime.utcnow)
    last_heartbeat = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    integrity_score = Column(Float, default=100.0)
    warning_count = Column(Integer, default=0)
    violation_count = Column(Integer, default=0)
    is_locked = Column(Boolean, default=False)
    
    exam_session = relationship("ExamSession", back_populates="participants")
    violations = relationship("Violation", back_populates="participant")
    permission_requests = relationship("PermissionRequest", back_populates="participant")
    
    def __repr__(self):
        return f"<Participant(id={self.id}, participant_id='{self.participant_id}', name='{self.name}')>"


class Violation(Base):
    """Pelanggaran yang terdeteksi"""
    __tablename__ = 'violations'
    
    id = Column(Integer, primary_key=True)
    participant_id = Column(Integer, ForeignKey('participants.id'), nullable=False)
    exam_session_id = Column(Integer, ForeignKey('exam_sessions.id'), nullable=False)
    violation_type = Column(Enum(ViolationType), nullable=False)
    severity = Column(Enum(ViolationSeverity), default=ViolationSeverity.MEDIUM)
    description = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(100), nullable=True)
    
    participant = relationship("Participant", back_populates="violations")
    exam_session = relationship("ExamSession", back_populates="violations")
    evidence = relationship("Evidence", back_populates="violation")
    
    def __repr__(self):
        return f"<Violation(id={self.id}, type='{self.violation_type.value}', participant_id={self.participant_id})>"


class Evidence(Base):
    """Bukti pelanggaran (screenshot, video)"""
    __tablename__ = 'evidence'
    
    id = Column(Integer, primary_key=True)
    violation_id = Column(Integer, ForeignKey('violations.id'), nullable=False)
    evidence_type = Column(String(20))  # screenshot, video, audio
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)  # bytes
    created_at = Column(DateTime, default=datetime.utcnow)
    evidence_metadata = Column(Text)  # JSON metadata (renamed from 'metadata' to avoid SQLAlchemy reserved word)
    
    violation = relationship("Violation", back_populates="evidence")
    
    def __repr__(self):
        return f"<Evidence(id={self.id}, type='{self.evidence_type}', violation_id={self.violation_id})>"


class PermissionRequest(Base):
    """Permintaan izin untuk leave seat"""
    __tablename__ = 'permission_requests'
    
    id = Column(Integer, primary_key=True)
    participant_id = Column(Integer, ForeignKey('participants.id'), nullable=False)
    request_type = Column(String(50), default='leave_seat')  # leave_seat, toilet, etc
    status = Column(Enum(PermissionStatus), default=PermissionStatus.PENDING)
    requested_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, default=10)
    reason = Column(Text, nullable=True)
    
    participant = relationship("Participant", back_populates="permission_requests")
    
    def __repr__(self):
        return f"<PermissionRequest(id={self.id}, participant_id={self.participant_id}, status='{self.status.value}')>"
