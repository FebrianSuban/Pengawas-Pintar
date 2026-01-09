"""
Camera-based detection untuk mendeteksi perilaku mencurigakan
"""
import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import deque
import threading
import time
import os
from pathlib import Path

# MediaPipe Tasks API (untuk versi 0.10+)
mp = None
try:
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    from mediapipe import Image as MPImage
    from mediapipe import ImageFormat
    MEDIAPIPE_TASKS_AVAILABLE = True
except ImportError:
    # Fallback untuk versi lama
    try:
        import mediapipe as mp
        MEDIAPIPE_TASKS_AVAILABLE = False
    except ImportError:
        raise ImportError("MediaPipe tidak terinstall. Install dengan: pip install mediapipe")


class CameraDetector:
    """Detector untuk analisis camera input"""
    
    def __init__(self, camera_index: int = 0, config: Dict = None):
        """
        Initialize camera detector
        
        Args:
            camera_index: Index kamera (default 0)
            config: Konfigurasi detection
        """
        self.camera_index = camera_index
        self.config = config or {}
        
        # Thresholds
        self.face_absence_threshold = self.config.get('face_absence_threshold', 5.0)  # seconds
        self.multiple_face_threshold = self.config.get('multiple_face_threshold', 0.5)  # confidence
        self.suspicious_movement_threshold = self.config.get('suspicious_movement_threshold', 3.0)  # movements per minute
        
        # MediaPipe initialization
        self.face_detector = None
        self.face_landmarker = None
        self.face_detection = None
        self.face_mesh = None
        self.use_tasks_api = False
        self.mediapipe_available = False
        
        if MEDIAPIPE_TASKS_AVAILABLE:
            # Menggunakan MediaPipe Tasks API (versi 0.10+)
            try:
                # Coba download model atau gunakan model yang sudah ada
                model_path = self._get_mediapipe_model_path()
                
                if model_path:
                    base_options = python.BaseOptions(model_asset_path=model_path)
                else:
                    # Jika model tidak ditemukan, gunakan model buffer dari package
                    # Atau nonaktifkan face detection
                    print("Peringatan: Model MediaPipe tidak ditemukan. Camera detection dinonaktifkan.")
                    self.mediapipe_available = False
                    return
                
                options = vision.FaceDetectorOptions(
                    base_options=base_options,
                    running_mode=vision.RunningMode.IMAGE,
                    min_detection_confidence=0.5
                )
                self.face_detector = vision.FaceDetector.create_from_options(options)
                
                # Face Landmarker untuk tracking lebih akurat
                landmarker_model_path = self._get_mediapipe_landmarker_model_path()
                if landmarker_model_path:
                    landmarker_base_options = python.BaseOptions(model_asset_path=landmarker_model_path)
                else:
                    # Gunakan model face detector untuk landmarker juga (fallback)
                    landmarker_base_options = base_options
                
                landmarker_options = vision.FaceLandmarkerOptions(
                    base_options=landmarker_base_options,
                    running_mode=vision.RunningMode.IMAGE,
                    num_faces=2,
                    min_face_detection_confidence=0.5,
                    min_face_presence_confidence=0.5
                )
                self.face_landmarker = vision.FaceLandmarker.create_from_options(landmarker_options)
                self.use_tasks_api = True
                self.mediapipe_available = True
            except Exception as e:
                print(f"Error initializing MediaPipe Tasks: {e}")
                print("Camera detection akan dinonaktifkan.")
                self.mediapipe_available = False
        else:
            # Fallback ke API lama (jika tersedia)
            try:
                self.mp_face_detection = mp.solutions.face_detection
                self.face_detection = self.mp_face_detection.FaceDetection(
                    model_selection=1,
                    min_detection_confidence=0.5
                )
                self.mp_face_mesh = mp.solutions.face_mesh
                self.face_mesh = self.mp_face_mesh.FaceMesh(
                    max_num_faces=2,
                    refine_landmarks=True,
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5
                )
                self.use_tasks_api = False
                self.mediapipe_available = True
            except Exception as e:
                print(f"Error initializing MediaPipe (legacy): {e}")
                print("Camera detection akan dinonaktifkan.")
                self.mediapipe_available = False
        
        # State tracking
        self.last_face_detected = None
        self.face_absence_start = None
        self.face_count_history = deque(maxlen=60)  # Last 60 frames
        self.movement_history = deque(maxlen=300)  # Last 5 minutes at 1fps
        self.is_running = False
        self.cap = None
        self.lock = threading.Lock()
        
        # Detection results
        self.current_face_count = 0
        self.face_absent = False
        self.multiple_faces = False
        self.suspicious_movement = False
    
    def _get_mediapipe_model_path(self) -> Optional[str]:
        """Mendapatkan path ke model MediaPipe Face Detector atau mengunduhnya"""
        try:
            import urllib.request
            import tempfile
            
            # URL model MediaPipe Face Detector (short range)
            model_url = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite"
            
            # Simpan model di temp directory
            temp_dir = Path(tempfile.gettempdir()) / "mediapipe_models"
            temp_dir.mkdir(exist_ok=True)
            
            model_path = temp_dir / "blaze_face_short_range.tflite"
            
            # Download model jika belum ada
            if not model_path.exists():
                print("Mengunduh model MediaPipe Face Detector...")
                urllib.request.urlretrieve(model_url, str(model_path))
                print(f"Model berhasil diunduh ke: {model_path}")
            
            return str(model_path)
        except Exception as e:
            print(f"Error mendapatkan model MediaPipe: {e}")
            return None
    
    def _get_mediapipe_landmarker_model_path(self) -> Optional[str]:
        """Mendapatkan path ke model MediaPipe Face Landmarker atau mengunduhnya"""
        try:
            import urllib.request
            import tempfile
            
            # URL model MediaPipe Face Landmarker
            model_url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
            
            # Simpan model di temp directory
            temp_dir = Path(tempfile.gettempdir()) / "mediapipe_models"
            temp_dir.mkdir(exist_ok=True)
            
            model_path = temp_dir / "face_landmarker.task"
            
            # Download model jika belum ada
            if not model_path.exists():
                print("Mengunduh model MediaPipe Face Landmarker...")
                urllib.request.urlretrieve(model_url, str(model_path))
                print(f"Model berhasil diunduh ke: {model_path}")
            
            return str(model_path)
        except Exception as e:
            print(f"Error mendapatkan model MediaPipe Face Landmarker: {e}")
            return None
    
    def start(self):
        """Start camera detection"""
        if self.is_running:
            return
        
        if not self.mediapipe_available:
            print("Camera detection tidak tersedia karena MediaPipe tidak terinisialisasi dengan benar.")
            return
        
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                raise ValueError(f"Cannot open camera {self.camera_index}")
            
            self.is_running = True
            self.detection_thread = threading.Thread(target=self._detection_loop, daemon=True)
            self.detection_thread.start()
        except Exception as e:
            print(f"Error starting camera: {e}")
            self.is_running = False
    
    def stop(self):
        """Stop camera detection"""
        self.is_running = False
        if self.cap:
            self.cap.release()
        if hasattr(self, 'detection_thread'):
            self.detection_thread.join(timeout=2)
        if self.use_tasks_api:
            if hasattr(self, 'face_detector'):
                self.face_detector.close()
            if hasattr(self, 'face_landmarker'):
                self.face_landmarker.close()
        else:
            if hasattr(self, 'face_detection'):
                self.face_detection.close()
            if hasattr(self, 'face_mesh'):
                self.face_mesh.close()
    
    def _detection_loop(self):
        """Main detection loop"""
        while self.is_running:
            try:
                ret, frame = self.cap.read()
                if not ret:
                    time.sleep(0.1)
                    continue
                
                if not self.mediapipe_available:
                    time.sleep(0.1)
                    continue
                
                # Convert BGR to RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Face detection
                if self.use_tasks_api:
                    # MediaPipe Tasks API
                    if self.face_detector and self.face_landmarker:
                        mp_image = MPImage(image_format=ImageFormat.SRGB, data=rgb_frame)
                        face_results = self.face_detector.detect(mp_image)
                        mesh_results = self.face_landmarker.detect(mp_image)
                    else:
                        time.sleep(0.1)
                        continue
                else:
                    # API lama
                    if self.face_detection and self.face_mesh:
                        face_results = self.face_detection.process(rgb_frame)
                        mesh_results = self.face_mesh.process(rgb_frame)
                    else:
                        time.sleep(0.1)
                        continue
                
                with self.lock:
                    self._process_detections(face_results, mesh_results, frame)
                
                time.sleep(0.1)  # ~10 FPS
            except Exception as e:
                print(f"Error in detection loop: {e}")
                time.sleep(0.5)
    
    def _process_detections(self, face_results, mesh_results, frame):
        """Process detection results"""
        current_time = datetime.utcnow()
        
        # Count faces - handle both API formats
        face_count = 0
        if self.use_tasks_api:
            # MediaPipe Tasks API
            if face_results.detections:
                face_count = len(face_results.detections)
        else:
            # API lama
            if hasattr(face_results, 'detections') and face_results.detections:
                face_count = len(face_results.detections)
        
        self.current_face_count = face_count
        self.face_count_history.append((current_time, face_count))
        
        # Check face absence
        if face_count == 0:
            if self.face_absence_start is None:
                self.face_absence_start = current_time
            else:
                absence_duration = (current_time - self.face_absence_start).total_seconds()
                self.face_absent = absence_duration >= self.face_absence_threshold
        else:
            self.face_absence_start = None
            self.face_absent = False
        
        # Check multiple faces
        self.multiple_faces = face_count > 1
        
        # Check suspicious movement
        if self.use_tasks_api:
            # MediaPipe Tasks API
            if face_count > 0 and hasattr(mesh_results, 'face_landmarks') and mesh_results.face_landmarks:
                for face_landmarks in mesh_results.face_landmarks:
                    # Get key points (nose, left eye, right eye)
                    # MediaPipe Tasks API menggunakan struktur yang berbeda
                    # face_landmarks adalah list dari NormalizedLandmark objects
                    if len(face_landmarks) > 263:
                        nose = face_landmarks[4]  # Nose tip
                        left_eye = face_landmarks[33]
                        right_eye = face_landmarks[263]
                        
                        # Calculate head position
                        head_center = np.array([nose.x, nose.y])
                        eye_distance = np.linalg.norm([
                            left_eye.x - right_eye.x,
                            left_eye.y - right_eye.y
                        ])
                        
                        self.movement_history.append((current_time, head_center, eye_distance))
                    elif len(face_landmarks) > 0:
                        # Fallback jika landmark tidak lengkap
                        center_landmark = face_landmarks[len(face_landmarks) // 2]
                        head_center = np.array([center_landmark.x, center_landmark.y])
                        self.movement_history.append((current_time, head_center, 0.0))
        else:
            # API lama
            if face_count > 0 and hasattr(mesh_results, 'multi_face_landmarks') and mesh_results.multi_face_landmarks:
                # Calculate head position/angle changes
                for face_landmarks in mesh_results.multi_face_landmarks:
                    # Get key points (nose, left eye, right eye)
                    nose = face_landmarks.landmark[4]  # Nose tip
                    left_eye = face_landmarks.landmark[33]
                    right_eye = face_landmarks.landmark[263]
                    
                    # Calculate head position
                    head_center = np.array([nose.x, nose.y])
                    eye_distance = np.linalg.norm([
                        left_eye.x - right_eye.x,
                        left_eye.y - right_eye.y
                    ])
                    
                    self.movement_history.append((current_time, head_center, eye_distance))
        
        # Analyze movement history
        if len(self.movement_history) > 10:
            recent_movements = list(self.movement_history)[-60:]  # Last minute
            if len(recent_movements) > 1:
                movements = 0
                for i in range(1, len(recent_movements)):
                    prev_pos = recent_movements[i-1][1]
                    curr_pos = recent_movements[i][1]
                    movement = np.linalg.norm(curr_pos - prev_pos)
                    if movement > 0.05:  # Threshold for significant movement
                        movements += 1
                
                movements_per_minute = movements * (60.0 / len(recent_movements))
                self.suspicious_movement = movements_per_minute > self.suspicious_movement_threshold
    
    def get_detection_results(self) -> Dict:
        """
        Get current detection results
        
        Returns:
            Dict dengan hasil detection
        """
        with self.lock:
            return {
                'face_count': self.current_face_count,
                'face_absent': self.face_absent,
                'multiple_faces': self.multiple_faces,
                'suspicious_movement': self.suspicious_movement,
                'face_absence_duration': (
                    (datetime.utcnow() - self.face_absence_start).total_seconds()
                    if self.face_absence_start else 0
                )
            }
    
    def capture_frame(self) -> Optional[np.ndarray]:
        """Capture current frame untuk evidence"""
        if not self.cap or not self.is_running:
            return None
        
        ret, frame = self.cap.read()
        if ret:
            return frame
        return None
    
    def is_face_present(self) -> bool:
        """Check if face is currently present"""
        return self.current_face_count > 0
