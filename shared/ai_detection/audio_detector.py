"""
Audio-based detection untuk mendeteksi suara dan multiple speakers
"""
import numpy as np
import sounddevice as sd
import librosa
from typing import Dict, Optional, List
from datetime import datetime
from collections import deque
import threading
import queue


class AudioDetector:
    """Detector untuk analisis audio input"""
    
    def __init__(self, config: Dict = None):
        """
        Initialize audio detector
        
        Args:
            config: Konfigurasi detection
        """
        self.config = config or {}
        
        # Thresholds
        self.voice_activity_threshold = self.config.get('voice_activity_threshold', 0.3)
        self.multiple_speaker_threshold = self.config.get('multiple_speaker_threshold', 0.4)
        
        # Audio parameters
        self.sample_rate = 16000  # Hz
        self.chunk_size = 1024
        self.buffer_duration = 2.0  # seconds
        
        # State
        self.is_running = False
        self.audio_queue = queue.Queue()
        self.audio_buffer = deque(maxlen=int(self.sample_rate * self.buffer_duration))
        self.lock = threading.Lock()
        
        # Detection results
        self.voice_activity = False
        self.voice_activity_level = 0.0
        self.multiple_speakers = False
        self.audio_level = 0.0
    
    def start(self):
        """Start audio detection"""
        if self.is_running:
            return
        
        try:
            self.is_running = True
            self.audio_thread = threading.Thread(target=self._audio_capture_loop, daemon=True)
            self.analysis_thread = threading.Thread(target=self._analysis_loop, daemon=True)
            
            self.audio_thread.start()
            self.analysis_thread.start()
        except Exception as e:
            print(f"Error starting audio detection: {e}")
            self.is_running = False
    
    def stop(self):
        """Stop audio detection"""
        self.is_running = False
        if hasattr(self, 'audio_thread'):
            self.audio_thread.join(timeout=2)
        if hasattr(self, 'analysis_thread'):
            self.analysis_thread.join(timeout=2)
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Callback untuk audio input"""
        if status:
            print(f"Audio status: {status}")
        
        if self.is_running:
            audio_data = indata[:, 0]  # Mono channel
            self.audio_queue.put(audio_data.copy())
    
    def _audio_capture_loop(self):
        """Loop untuk capture audio"""
        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                blocksize=self.chunk_size,
                callback=self._audio_callback,
                dtype=np.float32
            ):
                while self.is_running:
                    sd.sleep(100)
        except Exception as e:
            print(f"Error in audio capture: {e}")
            self.is_running = False
    
    def _analysis_loop(self):
        """Loop untuk analisis audio"""
        while self.is_running:
            try:
                # Get audio data from queue
                if not self.audio_queue.empty():
                    audio_data = self.audio_queue.get_nowait()
                    self.audio_buffer.extend(audio_data)
                
                # Analyze if we have enough data
                if len(self.audio_buffer) >= self.sample_rate * 0.5:  # At least 0.5 seconds
                    audio_array = np.array(list(self.audio_buffer))
                    self._analyze_audio(audio_array)
                
                threading.Event().wait(0.1)  # Sleep 100ms
            except Exception as e:
                print(f"Error in audio analysis: {e}")
                threading.Event().wait(0.5)
    
    def _analyze_audio(self, audio_data: np.ndarray):
        """Analyze audio untuk detect voice activity dan multiple speakers"""
        with self.lock:
            # Calculate audio level (RMS)
            self.audio_level = np.sqrt(np.mean(audio_data**2))
            
            # Voice Activity Detection (VAD)
            # Simple energy-based VAD
            energy = np.mean(audio_data**2)
            self.voice_activity = energy > self.voice_activity_threshold
            self.voice_activity_level = min(1.0, energy / self.voice_activity_threshold)
            
            # Multiple speaker detection menggunakan spectral analysis
            # Method: Analyze frequency content dan pitch variations
            if len(audio_data) > 0:
                try:
                    # Calculate spectral features
                    stft = librosa.stft(audio_data, n_fft=2048, hop_length=512)
                    magnitude = np.abs(stft)
                    
                    # Calculate spectral centroid (brightness)
                    spectral_centroids = librosa.feature.spectral_centroid(
                        y=audio_data, sr=self.sample_rate
                    )[0]
                    
                    # Calculate zero crossing rate
                    zcr = librosa.feature.zero_crossing_rate(audio_data)[0]
                    
                    # Calculate pitch (fundamental frequency)
                    pitches, magnitudes = librosa.piptrack(
                        y=audio_data, sr=self.sample_rate, threshold=0.1
                    )
                    
                    # Simple heuristic: multiple speakers jika ada variasi pitch yang besar
                    # atau multiple spectral peaks
                    if len(spectral_centroids) > 0:
                        centroid_variance = np.var(spectral_centroids)
                        zcr_variance = np.var(zcr)
                        
                        # Multiple speakers jika ada variasi tinggi dalam spectral features
                        # dan voice activity tinggi
                        if (self.voice_activity and 
                            (centroid_variance > self.multiple_speaker_threshold or
                             zcr_variance > self.multiple_speaker_threshold * 0.5)):
                            self.multiple_speakers = True
                        else:
                            self.multiple_speakers = False
                    else:
                        self.multiple_speakers = False
                except Exception as e:
                    # Fallback: simple energy-based detection
                    if self.voice_activity and self.audio_level > self.multiple_speaker_threshold * 1.5:
                        self.multiple_speakers = True
                    else:
                        self.multiple_speakers = False
    
    def get_detection_results(self) -> Dict:
        """
        Get current detection results
        
        Returns:
            Dict dengan hasil detection
        """
        with self.lock:
            return {
                'voice_activity': self.voice_activity,
                'voice_activity_level': self.voice_activity_level,
                'multiple_speakers': self.multiple_speakers,
                'audio_level': self.audio_level
            }
    
    def capture_audio(self, duration: float = 2.0) -> Optional[np.ndarray]:
        """Capture audio untuk evidence"""
        if not self.is_running:
            return None
        
        try:
            audio_data = sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype=np.float32
            )
            sd.wait()
            return audio_data.flatten()
        except Exception as e:
            print(f"Error capturing audio: {e}")
            return None
