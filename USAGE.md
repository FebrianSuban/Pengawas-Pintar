# Panduan Penggunaan Pengawas Pintar

## Untuk Admin/Pengawas

### 1. Memulai Sesi Ujian

1. Jalankan Admin Application
2. Klik "Mulai Sesi Ujian"
3. Masukkan nama sesi ujian
4. Sesi akan dimulai dan server akan aktif

### 2. Monitoring Peserta

**Dashboard Tab:**
- Lihat statistik total peserta, aktif, violations
- Lihat integrity score rata-rata
- Monitor violations terkini

**Participants Tab:**
- Lihat daftar semua peserta
- Monitor status, integrity score, warnings, violations
- Lock/unlock peserta individual

### 3. Konfigurasi AI Proctoring

**Configuration Tab:**
- Enable/disable AI detection
- Set threshold untuk face absence
- Configure allowed/blocked applications
- Set escalation rules

### 4. Mode AI Proctor

- Klik "Mode AI Proctor: OFF" untuk enable
- AI akan otomatis:
  - Handle violations
  - Send warnings
  - Escalate berdasarkan rules
  - Lock peserta jika diperlukan

### 5. Emergency Lock

- Klik "🔒 LOCK SEMUA" untuk lock semua komputer peserta
- Berguna untuk situasi darurat

### 6. Permission Management

- Ketika peserta request permission, dialog akan muncul
- Approve atau reject request
- Permission akan auto-expire setelah durasi yang ditentukan

### 7. Analytics dan Reporting

**Analytics Tab:**
- Lihat integrity scores semua peserta
- Export laporan ke CSV

## Untuk Peserta

### 1. Menjalankan Aplikasi

1. Jalankan Participant Application
2. Jika belum terdaftar, masukkan ID dan nama
3. Aplikasi akan otomatis connect ke admin server

### 2. Selama Ujian

- Aplikasi berjalan di background
- AI monitoring aktif (camera + audio)
- Process monitoring aktif
- Aplikasi tidak dapat ditutup tanpa authorization

### 3. Request Permission

- Klik "Minta Izin Keluar" jika perlu leave seat
- Tunggu approval dari admin
- Jika approved, AI detection untuk face absence akan pause
- Permission akan auto-expire setelah durasi

### 4. Menerima Warning

- Jika terdeteksi violation, warning akan muncul
- Ikuti instruksi dari warning
- Repeated violations akan trigger escalation

### 5. Jika Komputer Terkunci

- Komputer akan terkunci jika:
  - Admin manual lock
  - Emergency lock
  - Auto-escalation (terlalu banyak violations)
- Hubungi admin untuk unlock

## Best Practices

### Untuk Admin:

1. **Sebelum Ujian:**
   - Test koneksi dengan semua komputer peserta
   - Configure AI settings sesuai kebutuhan
   - Set allowed/blocked applications
   - Test emergency lock

2. **Selama Ujian:**
   - Monitor dashboard secara berkala
   - Review violations yang terjadi
   - Respond to permission requests
   - Gunakan AI Proctor mode jika perlu

3. **Setelah Ujian:**
   - Review analytics dan integrity scores
   - Export laporan
   - Archive evidence jika diperlukan

### Untuk Peserta:

1. **Sebelum Ujian:**
   - Pastikan webcam dan mikrofon berfungsi
   - Test koneksi ke admin server
   - Tutup aplikasi yang tidak diizinkan

2. **Selama Ujian:**
   - Tetap di depan komputer
   - Jangan tutup aplikasi participant
   - Request permission jika perlu leave seat
   - Ikuti aturan ujian

3. **Jika Ada Masalah:**
   - Hubungi admin jika ada technical issues
   - Jangan mencoba menutup atau disable aplikasi
   - Report false positives ke admin

## Troubleshooting

### Participant tidak terhubung
- Check IP address dan port di config
- Pastikan admin app sudah running
- Check firewall settings

### Camera tidak terdeteksi
- Check permission untuk camera
- Pastikan tidak digunakan aplikasi lain
- Restart aplikasi

### False positive violations
- Adjust threshold di configuration
- Review evidence untuk konfirmasi
- Update config jika diperlukan

### Performance issues
- Reduce detection frequency
- Disable audio detection jika tidak diperlukan
- Close unnecessary applications
