# Pengawas Pintar - Smart Exam Proctoring System

Sistem proctoring ujian desktop yang cerdas untuk laboratorium komputer universitas. Aplikasi ini berjalan secara offline di jaringan lokal (LAN) tanpa ketergantungan cloud.

## Fitur Utama

### Admin/Proctor Application
- Dashboard monitoring real-time untuk semua peserta
- Konfigurasi aturan ujian dan AI monitoring
- Mode manual dan otomatis (AI Proctor)
- Emergency button untuk lock semua komputer
- Analytics dan integrity scoring
- Logging dan evidence capture (screenshot, video)

### Participant Application
- Berjalan sebagai background service
- Auto-start saat boot
- Resistant terhadap termination
- Monitoring aplikasi dan blocking aplikasi tidak diizinkan
- AI detection (camera + audio)
- Request permission untuk leave seat
- Exam interface minimal

## Persyaratan Sistem

- Python 3.10 atau lebih baru
- Windows 10/11 (Linux support optional)
- Webcam untuk AI detection
- Mikrofon untuk audio analysis
- Jaringan LAN untuk komunikasi

## Instalasi

1. Clone atau download repository ini
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Untuk Windows, install pywin32:
```bash
pip install pywin32
python Scripts/pywin32_postinstall.py -install
```

## Konfigurasi

1. Edit `config/admin_config.json` untuk konfigurasi admin
2. Edit `config/participant_config.json` untuk konfigurasi participant
3. Pastikan firewall mengizinkan komunikasi LAN

## Menjalankan Aplikasi

### Admin Application
```bash
python admin_app/main.py
```

### Participant Application
```bash
python participant_app/main.py
```

Untuk install sebagai service (Windows):
```bash
python participant_app/install_service.py
```

## Struktur Proyek

```
Pengawas Pintar/
├── admin_app/              # Aplikasi Admin/Proctor
├── participant_app/        # Aplikasi Participant
├── shared/                 # Kode yang digunakan bersama
│   ├── ai_detection/      # Modul AI detection
│   ├── database/          # Database models dan schema
│   ├── networking/        # Networking layer
│   └── utils/             # Utilities
├── config/                 # File konfigurasi
└── logs/                  # Log files dan evidence
```

## Lisensi

Proprietary - Untuk penggunaan internal universitas
