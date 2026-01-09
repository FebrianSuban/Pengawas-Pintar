"""
Database manager untuk operasi database
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager
from .models import Base, ExamSession, Participant, Violation, Evidence, PermissionRequest
from datetime import datetime, timedelta
from typing import Optional, List


class DatabaseManager:
    """Manager untuk operasi database"""
    
    def __init__(self, db_path: str = "data/proctoring.db"):
        """
        Initialize database manager
        
        Args:
            db_path: Path ke file database SQLite
        """
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = db_path
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        # Prevent SQLAlchemy from expiring ORM objects on commit so returned
        # instances remain usable after the session context closes.
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)
        
        # Create tables
        Base.metadata.create_all(self.engine)
    
    @contextmanager
    def get_session(self):
        """Context manager untuk session database"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    # Exam Session Operations
    def create_exam_session(self, name: str, config: str = None) -> ExamSession:
        """Buat sesi ujian baru"""
        with self.get_session() as session:
            exam_session = ExamSession(
                name=name,
                config=config,
                status='active'
            )
            session.add(exam_session)
            session.flush()
            session.refresh(exam_session)
            return exam_session
    
    def get_exam_session(self, session_id: int) -> Optional[ExamSession]:
        """Ambil sesi ujian berdasarkan ID"""
        with self.get_session() as session:
            return session.query(ExamSession).filter_by(id=session_id).first()
    
    def get_active_exam_session(self) -> Optional[ExamSession]:
        """Ambil sesi ujian yang aktif"""
        with self.get_session() as session:
            return session.query(ExamSession).filter_by(status='active').first()
    
    # Participant Operations
    def register_participant(self, participant_id: str, name: str, 
                            exam_session_id: int, computer_ip: str = None,
                            computer_name: str = None) -> Participant:
        """Daftarkan peserta baru"""
        with self.get_session() as session:
            participant = Participant(
                participant_id=participant_id,
                name=name,
                exam_session_id=exam_session_id,
                computer_ip=computer_ip,
                computer_name=computer_name,
                is_active=True
            )
            session.add(participant)
            session.flush()
            session.refresh(participant)
            return participant
    
    def update_participant_heartbeat(self, participant_id: str):
        """Update heartbeat peserta"""
        with self.get_session() as session:
            participant = session.query(Participant).filter_by(
                participant_id=participant_id
            ).first()
            if participant:
                participant.last_heartbeat = datetime.utcnow()
                participant.is_active = True
    
    def get_participant(self, participant_id: str) -> Optional[Participant]:
        """Ambil peserta berdasarkan ID"""
        with self.get_session() as session:
            return session.query(Participant).filter_by(
                participant_id=participant_id
            ).first()
    
    def get_all_participants(self, exam_session_id: int = None) -> List[Participant]:
        """Ambil semua peserta"""
        with self.get_session() as session:
            query = session.query(Participant)
            if exam_session_id:
                query = query.filter_by(exam_session_id=exam_session_id)
            return query.all()
    
    def update_integrity_score(self, participant_id: str, score: float):
        """Update integrity score peserta"""
        with self.get_session() as session:
            participant = session.query(Participant).filter_by(
                participant_id=participant_id
            ).first()
            if participant:
                participant.integrity_score = max(0.0, min(100.0, score))
    
    def increment_warning_count(self, participant_id: str):
        """Tambah warning count"""
        with self.get_session() as session:
            participant = session.query(Participant).filter_by(
                participant_id=participant_id
            ).first()
            if participant:
                participant.warning_count += 1
    
    def lock_participant(self, participant_id: str, locked: bool = True):
        """Lock atau unlock peserta"""
        with self.get_session() as session:
            participant = session.query(Participant).filter_by(
                participant_id=participant_id
            ).first()
            if participant:
                participant.is_locked = locked
    
    # Violation Operations
    def create_violation(self, participant_id: str, exam_session_id: int,
                        violation_type, severity, description: str = None) -> Violation:
        """Buat record pelanggaran baru"""
        with self.get_session() as session:
            # Get participant
            participant = session.query(Participant).filter_by(
                participant_id=participant_id
            ).first()
            
            if not participant:
                raise ValueError(f"Participant {participant_id} not found")
            
            violation = Violation(
                participant_id=participant.id,
                exam_session_id=exam_session_id,
                violation_type=violation_type,
                severity=severity,
                description=description
            )
            session.add(violation)
            
            # Update participant stats
            participant.violation_count += 1
            
            session.flush()
            session.refresh(violation)
            return violation
    
    def get_violations(self, participant_id: str = None, 
                      exam_session_id: int = None,
                      limit: int = 100) -> List[Violation]:
        """Ambil violations"""
        with self.get_session() as session:
            query = session.query(Violation)
            
            if participant_id:
                participant = session.query(Participant).filter_by(
                    participant_id=participant_id
                ).first()
                if participant:
                    query = query.filter_by(participant_id=participant.id)
            
            if exam_session_id:
                query = query.filter_by(exam_session_id=exam_session_id)
            
            return query.order_by(Violation.timestamp.desc()).limit(limit).all()
    
    # Evidence Operations
    def create_evidence(self, violation_id: int, evidence_type: str,
                       file_path: str, file_size: int = None,
                       metadata: str = None) -> Evidence:
        """Buat record evidence baru"""
        with self.get_session() as session:
            evidence = Evidence(
                violation_id=violation_id,
                evidence_type=evidence_type,
                file_path=file_path,
                file_size=file_size,
                evidence_metadata=metadata
            )
            session.add(evidence)
            session.flush()
            session.refresh(evidence)
            return evidence
    
    # Permission Request Operations
    def create_permission_request(self, participant_id: str, request_type: str = 'leave_seat',
                                 duration_minutes: int = 10, reason: str = None) -> PermissionRequest:
        """Buat permintaan izin"""
        with self.get_session() as session:
            participant = session.query(Participant).filter_by(
                participant_id=participant_id
            ).first()
            
            if not participant:
                raise ValueError(f"Participant {participant_id} not found")
            
            request = PermissionRequest(
                participant_id=participant.id,
                request_type=request_type,
                duration_minutes=duration_minutes,
                reason=reason,
                status='pending'
            )
            session.add(request)
            session.flush()
            session.refresh(request)
            return request
    
    def approve_permission_request(self, request_id: int) -> bool:
        """Approve permintaan izin"""
        with self.get_session() as session:
            request = session.query(PermissionRequest).filter_by(id=request_id).first()
            if request and request.status.value == 'pending':
                request.status = 'approved'
                request.approved_at = datetime.utcnow()
                request.expires_at = datetime.utcnow() + timedelta(minutes=request.duration_minutes)
                return True
            return False
    
    def get_active_permission(self, participant_id: str) -> Optional[PermissionRequest]:
        """Ambil permission yang masih aktif untuk peserta"""
        with self.get_session() as session:
            participant = session.query(Participant).filter_by(
                participant_id=participant_id
            ).first()
            
            if not participant:
                return None
            
            return session.query(PermissionRequest).filter_by(
                participant_id=participant.id,
                status='approved'
            ).filter(
                PermissionRequest.expires_at > datetime.utcnow()
            ).first()
    
    def cleanup_old_evidence(self, retention_days: int = 30):
        """Hapus evidence yang sudah lama"""
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        with self.get_session() as session:
            old_evidence = session.query(Evidence).filter(
                Evidence.created_at < cutoff_date
            ).all()
            
            for evidence in old_evidence:
                # Delete file if exists
                if os.path.exists(evidence.file_path):
                    try:
                        os.remove(evidence.file_path)
                    except:
                        pass
                
                session.delete(evidence)
