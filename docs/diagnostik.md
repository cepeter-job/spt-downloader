# Log diagnostik untuk bugfixing

Log ini menjelaskan urutan pekerjaan dan lokasi error aplikasi. Log **bukan** salinan capture, audit pajak, bukti kelengkapan SPT, atau telemetry. Data tetap lokal; aplikasi tidak mengirim log ke layanan eksternal.

## Mengambil log yang relevan

1. Jalankan build yang sedang diperiksa, ulangi masalah satu kali, lalu catat waktu/tahap dan tindakan terakhir tanpa mencantumkan NPWP atau akun pada laporan publik.
2. Buka **Pengaturan → Buka folder log**. Lokasi default Windows adalah `%LOCALAPPDATA%\SPTDownloader\logs`. Jangan mengirim folder `jobs`, `profile`, checkpoint JSON atau hasil pajak bersama log.
3. Cocokkan `job_ref` antara file GUI dan worker. `session_id` membedakan proses; `sequence` dan waktu UTC membantu mengurutkan kejadian. `job_ref` adalah digest ID job, bukan NPWP atau ID SPT.
4. Sertakan commit/artifact build, versi Windows/browser, langkah reproduksi, hasil yang diharapkan, dan hasil yang terjadi. Tinjau berkas sebelum membagikannya; jumlah/timing aktivitas tetap informasi operasional privat.

Nama file: `diag-<gui|worker|cli>-<session UUID>-<segmen>.jsonl`. Satu baris adalah satu objek JSON. File `.active` dan `.diagnostics.lock` dipakai untuk koordinasi lokal, bukan isi laporan bug.

## INFO, DEBUG, dan OFF

Worker baru membuka sink setelah menerima izin mulai; Stop/EOF sebelum izin tidak membuat folder workspace/log. GUI tetap mencatat rekonsiliasi proses.

Default **INFO** mencatat lifecycle, fase berdurasi, persetujuan, terminal yang disahkan controller, serta error. **DEBUG** menambahkan progres/count dan penolakan protokol. Tidak ada level yang membuka akses ke data pajak atau rahasia.

PowerShell, sebelum membuka executable dari terminal yang sama:

```powershell
$env:SPT_LOG_LEVEL = 'DEBUG'
.\SPTDownloader.exe
```

Untuk CLI, variabel yang sama berlaku ketika menjalankan `coretax.py`. Hapus variabel setelah reproduksi:

```powershell
Remove-Item Env:SPT_LOG_LEVEL
```

`SPT_LOG_LEVEL=OFF` menonaktifkan diagnostik baru, **bukan** verifikasi, audit workbook, checkpoint atau pemeriksaan keamanan. Nilai tidak dikenal kembali ke INFO. Untuk lokasi diagnostik alternatif, set `SPT_LOG_ROOT` ke direktori absolut khusus; file masuk ke subfolder `logs` di dalamnya. Jangan memilih folder yang berisi hasil pajak/profil. Root relatif atau symlink/junction/reparse ditolak. Default CLI Linux memakai `~/.local/state/spt-downloader/logs`.

## Isi yang dicatat

Schema 1 memuat waktu UTC, level, role, ID session, referensi job, urutan, durasi, fase, status tetap, counter terbatas, dan exit/OS error code jika sah. Versi Python serta status frozen membantu membedakan lingkungan. Lokasi error berupa token file/fungsi aplikasi dan nomor baris, maksimal delapan frame.

Pesan exception, chain, locals, baris kode, path lengkap, URL, NPWP, tahun/nama wajib pajak, akun, password, cookies, token, header/body HTTP, nilai form/tabel, payload consent dan nama/hash PDF **tidak disalin**. Field dan nilai yang tidak termasuk allowlist dibuang tanpa memanggil `str()` pada objek tak dikenal. Tidak ada perekaman browser/network atau penyalinan raw stdout/stderr.

`phase.completed` berarti fungsi keluar normal, **bukan** bukti hasil pajak COMPLETE. Gunakan `worker.finished` yang berasal dari rekonsiliasi controller, beserta Audit hasil untuk lingkup data. Error yang sudah ditangani sebagai PARTIAL tetap mempunyai event diagnostik tanpa mengubah status bisnis.

## Batas penyimpanan dan kegagalan

Ukuran file maksimal 1 MiB, maksimal tiga segmen per session. Retensi tujuh hari dan anggaran 32 file pada folder log; file regular milik logger yang tidak aktif dibersihkan paling tua dahulu. File asing, hardlink, symlink/reparse dan session aktif tidak dihapus. Jika kapasitas tidak dapat direklamasi dengan aman, logger tidak menambah file.

Antrian maksimal 256 record, ukuran record maksimal 4 KiB. Saat sink lambat, producer tidak menunggu I/O; `dropped` adalah hitungan event yang tidak dapat dicatat. Flush/close menunggu maksimal dua detik. Kehilangan event saat proses dipaksa berhenti, antrean penuh, storage rusak atau disk hang tetap mungkin. Retensi bekerja saat file baru dibuat, bukan lewat pekerjaan terjadwal.

Tidak ada jaminan forensik, at-rest encryption, zero filesystem latency, ataupun ketahanan terhadap administrator/proses lain yang menguasai akun. DirectoryGuard memegang direktori Windows; implementasi portable melakukan pemeriksaan identitas tanpa jaminan pin namespace Windows. Logging yang gagal tidak mengubah exit code, keluaran protokol, Stop, keputusan overwrite, atau checkpoint.

CLI dan checkpoint/audit yang sudah ada masih dapat mengandung data sumber. Kebijakan sanitasi di sini hanya untuk file diagnostik baru, bukan klaim bahwa seluruh output aplikasi aman dipublikasikan.

## Catatan implementasi

`spt_desktop/diagnostics.py` memegang schema, sanitasi, antrian, session dan instrumentasi fase. `diagnostic_store.py` memegang file/lock/rotasi/retensi. Tidak ada konfigurasi root logger atau filesystem saat import; setiap proses membuat sink sendiri. Kedua modul masuk allowlist worker/frozen, tanpa dependensi baru.

Dasar desain: [Python Logging Cookbook](https://docs.python.org/3.14/howto/logging-cookbook.html) dan [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html). Bukti aktual gate dan artifact ada pada PR logging; dokumen ini bukan klaim live acceptance.
