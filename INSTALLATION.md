# Panduan Instalasi Pengawas Pintar

## Persyaratan Sistem

- Python 3.10 atau lebih baru
- Windows 10/11 (Linux support optional)
- Webcam untuk AI detection
- Mikrofon untuk audio analysis
- Jaringan LAN untuk komunikasi
- Akses Administrator (untuk beberapa fitur)

## Instalasi

### 1. Clone atau Download Repository

```bash
git clone <repository-url>
cd "Pengawas Pintar"
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Install pywin32 (Windows only)

```bash
pip install pywin32
python Scripts/pywin32_postinstall.py -install
```

### 4. Setup Konfigurasi

#### Admin Configuration

1. Copy template config:
```bash
copy config\admin_config_template.json config\admin_config.json
```

2. Edit `config/admin_config.json`:
   - Set `server.host` dan `server.port`
   - Konfigurasi AI proctoring settings
   - Set exam rules (allowed/blocked applications)

#### Participant Configuration

1. Copy template config:
```bash
copy config\participant_config_template.json config\participant_config.json
```

2. Edit `config/participant_config.json`:
   - Set `admin_server.host` ke IP address komputer admin
   - Set `admin_server.port` (harus sama dengan admin config)
   - Set `participant.id` dan `participant.name` (atau biarkan kosong untuk input saat runtime)

## Menjalankan Aplikasi

### Admin Application

```bash
python admin_app/main.py
```

Atau menggunakan entry point:
```bash
pengawas-admin
```

### Participant Application

```bash
python participant_app/main.py
```

Atau menggunakan entry point:
```bash
pengawas-participant
```

## Install sebagai Windows Service (Participant)

Untuk install participant app sebagai Windows service:

```bash
python participant_app/install_service.py install
```

Untuk start service:
```bash
python participant_app/install_service.py start
```

Untuk stop service:
```bash
python participant_app/install_service.py stop
```

Untuk uninstall:
```bash
python participant_app/install_service.py remove
```

**Catatan**: Service installation memerlukan akses Administrator.

## Troubleshooting

### Camera tidak terdeteksi
- Pastikan webcam terhubung dan tidak digunakan aplikasi lain
- Check permission untuk akses camera di Windows Settings

### Audio tidak terdeteksi
- Pastikan mikrofon terhubung dan tidak di-mute
- Check permission untuk akses microphone di Windows Settings

### Koneksi ke server gagal
- Pastikan firewall mengizinkan koneksi pada port yang digunakan
- Check IP address dan port di config
- Pastikan admin application sudah running

### Permission denied errors
- Pastikan aplikasi dijalankan dengan akses Administrator
- Beberapa fitur memerlukan elevated privileges

## Konfigurasi Firewall

Untuk Windows Firewall, tambahkan rule untuk mengizinkan koneksi:

1. Buka Windows Defender Firewall
2. Advanced Settings
3. Inbound Rules > New Rule
4. Port > TCP > Specific local ports: 8765 (atau port yang digunakan)
5. Allow the connection
6. Apply untuk semua profiles

## Network Setup

Pastikan semua komputer dalam jaringan LAN yang sama:
- Admin computer: IP address harus dapat diakses dari participant computers
- Participant computers: Harus dapat connect ke admin computer IP
- Test koneksi dengan ping atau telnet

## First Run

1. Start admin application terlebih dahulu
2. Buat sesi ujian baru
3. Start participant applications di komputer siswa
4. Participant akan otomatis terhubung dan terdaftar
