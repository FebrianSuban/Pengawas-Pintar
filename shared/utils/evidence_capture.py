"""
Utility untuk capture evidence (screenshot, video)
"""
import os
import cv2
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict
import threading
from collections import deque


class EvidenceCapture:
    """Capture evidence untuk violations"""
    
    def __init__(self, evidence_dir: str = "evidence"):
        """
        Initialize evidence capture
        
        Args:
            evidence_dir: Directory untuk menyimpan evidence
        """
        self.evidence_dir = evidence_dir
        Path(evidence_dir).mkdir(parents=True, exist_ok=True)
        
        # Video recording
        self.video_writers: Dict[str, cv2.VideoWriter] = {}
        self.video_frames: Dict[str, deque] = {}
        self.video_duration = 10.0  # seconds
        self.video_fps = 10
    
    def capture_screenshot(self, filename: str = None) -> Optional[str]:
        """
        Capture screenshot
        
        Args:
            filename: Nama file (optional)
        
        Returns:
            Path ke screenshot file
        """
        try:
            import pyautogui
            screenshot = pyautogui.screenshot()
            
            if filename is None:
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"
            
            filepath = os.path.join(self.evidence_dir, filename)
            screenshot.save(filepath)
            return filepath
        except Exception as e:
            print(f"Error capturing screenshot: {e}")
            return None
    
    def start_video_recording(self, violation_id: str, duration: float = 10.0):
        """
        Start recording video untuk violation
        
        Args:
            violation_id: ID violation
            duration: Durasi recording (seconds)
        """
        self.video_duration = duration
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"video_{violation_id}_{timestamp}.mp4"
        filepath = os.path.join(self.evidence_dir, filename)
        
        # Get screen size
        import pyautogui
        screen_size = pyautogui.size()
        width, height = screen_size
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(filepath, fourcc, self.video_fps, (width, height))
        
        self.video_writers[violation_id] = writer
        self.video_frames[violation_id] = deque(maxlen=int(self.video_fps * duration))
    
    def add_video_frame(self, violation_id: str, frame: np.ndarray):
        """Add frame ke video recording"""
        if violation_id in self.video_writers:
            self.video_writers[violation_id].write(frame)
            self.video_frames[violation_id].append(datetime.utcnow())
    
    def stop_video_recording(self, violation_id: str) -> Optional[str]:
        """
        Stop recording dan return filepath
        
        Args:
            violation_id: ID violation
        
        Returns:
            Path ke video file
        """
        if violation_id not in self.video_writers:
            return None
        
        writer = self.video_writers[violation_id]
        writer.release()
        
        # Get filepath from writer (if available)
        # For now, we'll construct it
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"video_{violation_id}_{timestamp}.mp4"
        filepath = os.path.join(self.evidence_dir, filename)
        
        del self.video_writers[violation_id]
        if violation_id in self.video_frames:
            del self.video_frames[violation_id]
        
        return filepath if os.path.exists(filepath) else None
    
    def capture_violation_evidence(self, violation_id: str, 
                                   violation_type: str) -> Dict[str, str]:
        """
        Capture evidence untuk violation
        
        Args:
            violation_id: ID violation
            violation_type: Type violation
        
        Returns:
            Dict dengan path ke evidence files
        """
        evidence = {}
        
        # Capture screenshot
        screenshot_path = self.capture_screenshot(
            f"screenshot_{violation_id}_{violation_type}.png"
        )
        if screenshot_path:
            evidence['screenshot'] = screenshot_path
        
        # Start video recording
        self.start_video_recording(violation_id, duration=10.0)
        
        return evidence
