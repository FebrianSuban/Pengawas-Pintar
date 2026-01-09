"""
Manager untuk mengkoordinasikan semua AI detection
"""
from typing import Dict, Optional, Callable
from .camera_detector import CameraDetector
from .audio_detector import AudioDetector
from datetime import datetime
import json


class DetectionManager:
    """Manager untuk AI detection"""
    
    def __init__(self, config: Dict = None):
        """
        Initialize detection manager
        
        Args:
            config: Konfigurasi detection
        """
        self.config = config or {}
        self.ai_config = self.config.get('ai_proctoring', {})
        
        # Initialize detectors
        self.camera_detector = None
        self.audio_detector = None
        
        if self.ai_config.get('camera', {}).get('enabled', True):
            self.camera_detector = CameraDetector(
                camera_index=0,
                config=self.ai_config.get('camera', {})
            )
        
        if self.ai_config.get('audio', {}).get('enabled', True):
            self.audio_detector = AudioDetector(
                config=self.ai_config.get('audio', {})
            )
        
        # Callbacks
        self.violation_callback: Optional[Callable] = None
        
        # Permission state
        self.permission_active = False
        self.permission_expires_at = None
    
    def start(self):
        """Start all detectors"""
        if self.camera_detector:
            self.camera_detector.start()
        if self.audio_detector:
            self.audio_detector.start()
    
    def stop(self):
        """Stop all detectors"""
        if self.camera_detector:
            self.camera_detector.stop()
        if self.audio_detector:
            self.audio_detector.stop()
    
    def set_violation_callback(self, callback: Callable):
        """Set callback untuk violation detection"""
        self.violation_callback = callback
    
    def set_permission_active(self, active: bool, expires_at: datetime = None):
        """Set permission state (untuk pause detection saat leave seat)"""
        self.permission_active = active
        self.permission_expires_at = expires_at
    
    def check_permission_expired(self) -> bool:
        """Check if permission has expired"""
        if not self.permission_active:
            return False
        
        if self.permission_expires_at and datetime.utcnow() > self.permission_expires_at:
            self.permission_active = False
            return True
        
        return False
    
    def get_all_detections(self) -> Dict:
        """
        Get semua detection results
        
        Returns:
            Dict dengan semua hasil detection
        """
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'camera': {},
            'audio': {},
            'violations': []
        }
        
        # Check permission
        if self.check_permission_expired():
            self.permission_active = False
        
        # Skip detection jika permission active (untuk face absence)
        skip_face_absence = self.permission_active
        
        # Camera detections
        if self.camera_detector:
            camera_results = self.camera_detector.get_detection_results()
            results['camera'] = camera_results
            
            # Check violations (skip face absence jika ada permission)
            if not skip_face_absence and camera_results.get('face_absent'):
                violation = {
                    'type': 'face_absence',
                    'severity': 'medium',
                    'description': f"Face tidak terdeteksi selama {camera_results.get('face_absence_duration', 0):.1f} detik"
                }
                results['violations'].append(violation)
                if self.violation_callback:
                    self.violation_callback(violation)
            
            if camera_results.get('multiple_faces'):
                violation = {
                    'type': 'multiple_faces',
                    'severity': 'high',
                    'description': f"Terdeteksi {camera_results.get('face_count', 0)} wajah dalam frame"
                }
                results['violations'].append(violation)
                if self.violation_callback:
                    self.violation_callback(violation)
            
            if camera_results.get('suspicious_movement'):
                violation = {
                    'type': 'suspicious_movement',
                    'severity': 'medium',
                    'description': "Terdeteksi gerakan kepala yang mencurigakan"
                }
                results['violations'].append(violation)
                if self.violation_callback:
                    self.violation_callback(violation)
        
        # Audio detections
        if self.audio_detector:
            audio_results = self.audio_detector.get_detection_results()
            results['audio'] = audio_results
            
            # Check violations
            if audio_results.get('voice_activity'):
                violation = {
                    'type': 'voice_activity',
                    'severity': 'medium',
                    'description': f"Terdeteksi aktivitas suara (level: {audio_results.get('voice_activity_level', 0):.2f})"
                }
                results['violations'].append(violation)
                if self.violation_callback:
                    self.violation_callback(violation)
            
            if audio_results.get('multiple_speakers'):
                violation = {
                    'type': 'multiple_speakers',
                    'severity': 'high',
                    'description': "Terdeteksi kemungkinan multiple speakers"
                }
                results['violations'].append(violation)
                if self.violation_callback:
                    self.violation_callback(violation)
        
        return results
    
    def capture_evidence(self, evidence_dir: str) -> Dict:
        """
        Capture evidence (screenshot, video, audio)
        
        Args:
            evidence_dir: Directory untuk menyimpan evidence
            
        Returns:
            Dict dengan path ke evidence files
        """
        import os
        from pathlib import Path
        
        evidence = {}
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        Path(evidence_dir).mkdir(parents=True, exist_ok=True)
        
        # Capture screenshot
        if self.camera_detector:
            frame = self.camera_detector.capture_frame()
            if frame is not None:
                import cv2
                screenshot_path = os.path.join(evidence_dir, f"screenshot_{timestamp}.jpg")
                cv2.imwrite(screenshot_path, frame)
                evidence['screenshot'] = screenshot_path
        
        # Capture audio
        if self.audio_detector:
            audio_data = self.audio_detector.capture_audio(duration=2.0)
            if audio_data is not None:
                import soundfile as sf
                audio_path = os.path.join(evidence_dir, f"audio_{timestamp}.wav")
                sf.write(audio_path, audio_data, self.audio_detector.sample_rate)
                evidence['audio'] = audio_path
        
        return evidence
