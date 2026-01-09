# Arsitektur Sistem Pengawas Pintar

## Overview

Sistem Pengawas Pintar adalah aplikasi desktop untuk proctoring ujian yang terdiri dari dua aplikasi utama:

1. **Admin Application** - Aplikasi untuk pengawas/proctor
2. **Participant Application** - Aplikasi untuk peserta ujian

## Arsitektur Komponen

### 1. Admin Application (`admin_app/`)

Aplikasi desktop berbasis PySide6 yang berfungsi sebagai:
- **Central Server**: FastAPI server dengan WebSocket support
- **Dashboard**: Monitoring real-time semua peserta
- **Controller**: Kontrol AI monitoring, violations, dan permissions
- **Analytics**: Integrity scoring dan reporting

**Komponen Utama:**
- `main.py`: Entry point
- `app.py`: Main application class dengan UI dashboard

### 2. Participant Application (`participant_app/`)

Aplikasi desktop berbasis PySide6 yang berjalan di komputer peserta:
- **Background Service**: Berjalan sebagai service, resistant terhadap termination
- **AI Detection Client**: Mengirim data detection ke admin
- **Process Monitor**: Monitor dan block aplikasi tidak diizinkan
- **Minimal UI**: Interface minimal untuk exam dan permission request

**Komponen Utama:**
- `main.py`: Entry point
- `app.py`: Main application class
- `install_service.py`: Script untuk install sebagai Windows service

### 3. Shared Modules (`shared/`)

Modul yang digunakan bersama oleh kedua aplikasi:

#### AI Detection (`shared/ai_detection/`)
- `camera_detector.py`: Face detection, multiple faces, suspicious movements
- `audio_detector.py`: Voice activity, multiple speakers detection
- `detection_manager.py`: Manager untuk koordinasi semua detection

#### Database (`shared/database/`)
- `models.py`: SQLAlchemy models (ExamSession, Participant, Violation, Evidence, PermissionRequest)
- `database_manager.py`: Database operations manager

#### Networking (`shared/networking/`)
- `protocol.py`: Message protocol untuk komunikasi
- `server.py`: FastAPI + WebSocket server untuk admin
- `client.py`: WebSocket client untuk participant

#### Utilities (`shared/utils/`)
- `config_loader.py`: Load dan save konfigurasi
- `process_monitor.py`: Monitor dan block processes
- `system_utils.py`: System utilities (Windows/Linux)
- `evidence_capture.py`: Capture screenshot dan video

## Alur Komunikasi

```
Participant App                    Admin App
     |                                |
     |---- Register ----------------->|
     |<--- Register ACK -------------|
     |                                |
     |---- Heartbeat --------------->|
     |                                |
     |---- Violation Report -------->|
     |                                |
     |<--- Warning -------------------|
     |                                |
     |---- Permission Request ------>|
     |<--- Permission Response -------|
     |                                |
     |<--- Lock/Unlock ---------------|
```

## Database Schema

### ExamSession
- Sesi ujian dengan start/end time
- Status (active, paused, completed)

### Participant
- Informasi peserta
- Integrity score
- Warning dan violation counts
- Lock status

### Violation
- Type (application_blocked, face_absence, etc.)
- Severity (low, medium, high, critical)
- Timestamp dan description

### Evidence
- Screenshot, video, audio files
- Linked ke violation

### PermissionRequest
- Request untuk leave seat
- Status (pending, approved, rejected)
- Expiration time

## AI Detection Flow

1. **Camera Detection**:
   - Face detection menggunakan MediaPipe
   - Track face absence duration
   - Detect multiple faces
   - Analyze head movements

2. **Audio Detection**:
   - Voice activity detection (VAD)
   - Multiple speaker detection menggunakan spectral analysis

3. **Violation Detection**:
   - Real-time monitoring
   - Evidence capture (screenshot, video)
   - Report ke admin server

## Process Monitoring

- Continuous monitoring setiap 2 detik
- Whitelist/Blacklist aplikasi
- Auto-kill blocked applications
- Report violations

## Permission System

1. Participant request permission (leave seat)
2. Admin approve/reject
3. AI detection paused selama permission active
4. Auto-resume setelah expiration

## Integrity Scoring

Score dihitung berdasarkan:
- Base score: 100
- Violation penalty: -5 per violation
- Warning penalty: -2 per warning
- Minimum score: 0

## Security Features

- Participant app resistant terhadap termination
- Process monitoring dan blocking
- Screen lock capability
- Emergency lock semua peserta
- Evidence capture untuk audit

## Deployment

### Admin Computer
- Install admin app
- Configure server IP dan port
- Start server
- Create exam session

### Participant Computers
- Install participant app
- Configure admin server address
- Install sebagai service (optional)
- Auto-start saat boot

## Network Requirements

- LAN connection (offline, no cloud)
- WebSocket communication
- Port: 8765 (configurable)
- Firewall rules untuk allow connection
