# Pemecahan masalah

[Kembali ke dokumentasi](README.md)

Mulai dari tahap dan status yang terlihat. Pertahankan checkpoint serta hasil lama. Error atau PARTIAL memberi informasi bahwa cakupan belum dapat disertifikasi; jangan mengubah status/JSON secara manual untuk melanjutkan.

## Setup dan runtime

| Gejala | Pemeriksaan dan tindakan |
| --- | --- |
| `uv` tidak ditemukan atau versinya ditolak | Jalankan `uv --version`, cocokkan dengan [kebijakan Python](python-314.md), lalu pasang/update dari distribusi resmi yang diverifikasi. Jangan memakai executable acak dari PATH. |
| Python terpasang tetapi aplikasi tetap menyiapkan runtime | Worker memakai interpreter managed di workspace aplikasi. Periksa patch version, x64, CPython, GIL, dan lokasi base; Python sistem tidak menggantikan runtime ini. |
| Hanya Python 3.11.9 dari installer Windows yang tersedia | Gunakan managed Python versi produksi melalui `uv`; jangan menurunkan pin agar installer lama diterima. |
| Unduhan runtime/paket gagal | Periksa koneksi, proxy, sertifikat tepercaya, ruang disk, dan izin LocalAppData. Coba ulang setelah penyebab terselesaikan. Jangan menonaktifkan TLS atau meneruskan stderr mentah yang dapat memuat kredensial proxy. |
| Hash lock tidak cocok | Pastikan checkout/lock/toolchain benar. Hentikan instalasi dan periksa asal paket; jangan menghapus hash atau menambahkan pengecualian untuk meloloskan setup. |
| Tk tidak tersedia saat build | Jalankan `python -m tkinter` pada interpreter yang benar di Windows. Perbaiki distribusi runtime/Tk; jangan melewati self-test packaging. |
| Setup berhenti tetapi tidak ada tanda siap | Ini perilaku yang diharapkan setelah pembatalan/kegagalan. Coba persiapan lagi; jangan membuat file penanda readiness secara manual. |

Jangan menghapus seluruh `%LOCALAPPDATA%\SPTDownloader` sebagai langkah pertama: direktori itu juga berisi profil dan checkpoint privat. Identifikasi subdirektori runtime/cache yang bermasalah dan simpan data pemulihan sebelum tindakan pemeliharaan yang memang diperlukan.

## Browser dan autentikasi

| Gejala | Pemeriksaan dan tindakan |
| --- | --- |
| Edge/Chrome tidak ditemukan | Pasang browser yang dipilih melalui saluran organisasi/resmi, lalu ulangi. Tes fixture memakai Edge terpasang; memasang Chromium generik tidak otomatis memenuhi `channel='msedge'`. |
| Profil sedang dipakai | Tutup jendela automation khusus aplikasi atau tunggu job sebelumnya selesai. Jangan mematikan browser pribadi atau menyalin cookie profil pribadi. |
| Login manual berhenti di homepage | Aplikasi perlu kontrol pencarian `ObjectPermitNumber`, bukan homepage saja. Periksa akses intranet dan apakah rute pencarian benar-benar dapat dimuat. |
| Cek Kredensial menunjukkan password belum diuji | Sesi SSO sudah login. Hasil ini tidak menyatakan password tersimpan benar atau salah. |
| Cek Kredensial timeout/belum terverifikasi | Periksa jaringan, challenge, dan layout login. Jangan berulang kali mencoba password untuk menganggap timeout sebagai password salah. |
| CAPTCHA/MFA atau form baru | Selesaikan challenge pada browser terlihat. Perubahan form perlu inspeksi dan fixture baru sebelum login otomatis diperluas. |
| `--reuse-browser` ditolak | Gunakan hanya origin loopback HTTP/HTTPS tanpa path, query, fragment, atau kredensial. Jangan mengekspos port debugging ke jaringan. |
| Login berhasil pada browser tetapi headless ditolak | Browser dapat tetap terlihat ketika pemindahan sesi tidak diterima. Jangan memaksa pemindahan cookie ke origin atau profil lain. |

## Capture, scope, dan output

| Gejala | Pemeriksaan dan tindakan |
| --- | --- |
| NPWP tidak ditemukan atau ambigu | Periksa 16 digit persis dan kewenangan akun. Jangan memilih kecocokan sebagian atau menghapus nol awal. |
| Tahun tidak dapat ditentukan | Lihat metadata pada checkpoint privat. Pola sumber baru harus dipahami dan diuji; jangan mengecualikan record diam-diam. |
| Jumlah sumber berubah atau tidak cocok | Mulai inventaris baru di folder baru dan periksa Audit. Resume memakai inventaris yang sama, sehingga bukan pengganti rekonsiliasi daftar yang berubah. |
| Checkpoint berbeda scope/provenance | Pilih checkpoint yang benar atau buat run baru. Jangan mengedit ID/scope checkpoint atau menggabungkan data antar-wajib-pajak. |
| View/layout detail tidak dikenal | Pertahankan PARTIAL/BLOCKED. Periksa struktur yang berizin secara privat, lalu buat fixture sintetis dan selector baca yang jelas. |
| PARTIAL setelah inventory-only/detail-limit/batas halaman | Periksa batas yang sengaja dipakai. COMPLETE membutuhkan seluruh cakupan yang didukung; menaikkan angka progres tidak mengubah kelengkapan data. |
| Nilai tidak dapat diwakili Excel | Pertahankan sumber JSON. Periksa lokasi field yang dilaporkan; jangan memotong teks, membulatkan angka, atau menghapus karakter sumber diam-diam. |
| Workbook terkunci atau rollback terblokir | Tutup workbook yang relevan di Excel, simpan direktori staging/backup, lalu ekspor ulang dari capture ke folder baru. Jangan menghapus recovery yang dilaporkan. |
| Output lama berbeda NPWP/tahun/basis/set file | Gunakan folder baru. Header Excel lama diperiksa walaupun `run.json` lebih baru. |
| Downloads tidak dapat ditulisi atau path ditolak | Periksa Known Folder, izin, koneksi lokasi jaringan, dan junction/symlink. Jangan mengalihkan diam-diam ke direktori lain. |
| Tautan Excel tidak bekerja | Pastikan seluruh set workbook berada bersama dan namanya tidak diubah. Periksa file/lembar target yang tercantum; jangan hanya menyalin `resume.xlsx`. |

## Tes dan CI

Jika langkah instalasi Windows gagal dengan **`Failed to create Python minor version link directory`** dan **`os error 267`** setelah cache berhasil dipulihkan, periksa laporan `ci_python_cache.py` pada langkah bootstrap. Perbaikan hanya berlaku untuk alias minor di cache runner; jangan menghapus direktori aplikasi pengguna, menurunkan pin Python, atau mematikan verifikasi hash. Tes restore cache di job produksi harus lulus sebelum kegagalan ini dinyatakan selesai. Lihat [kebijakan cache CI](ci-dan-rilis.md#cache-dan-cpu).

Tes GUI yang gagal karena display tidak tersedia, Edge hilang, atau API Windows dijalankan pada Linux adalah masalah lingkungan yang perlu dibedakan dari kegagalan perilaku. Gunakan [workload yang sesuai](pengembangan.md#pengujian-lokal); keberhasilan portable belum menutup gate Windows.

Jika tes baru hanya muncul pada workload Windows, itu default konservatif pemilih tes. Klasifikasikan sebagai portable setelah memeriksa seluruh fixture/dependensinya. Jangan menambahkan skip luas supaya matrix hijau.

Cache miss sah dan harus tetap menghasilkan instalasi dari lock. Bila cache dicurigai, bandingkan job dengan kunci yang benar dan instalasi baru; jangan memasukkan `.venv` atau profil browser ke cache. Audit advisory yang gagal terhubung tetap belum terverifikasi dan harus diulang setelah layanan tersedia.

Untuk produksi Python 3.14.8, catat versi GUI dan worker yang benar-benar dipakai, error import/wheel/Tk/PyInstaller, serta workload pertama yang gagal. Perbaiki kompatibilitas secara terarah; jangan memakai `continue-on-error` untuk melewatkan tes.

## Melaporkan bug tanpa data rahasia

Sertakan commit/profil Python, Windows/browser, tahap, hasil yang diharapkan, hasil aktual, exit/status yang aman, dan reproduksi sintetis bila tersedia. Ringkas error tanpa credential, URL berisi rahasia, identifier wajib pajak nyata, atau isi capture. Jangan melampirkan seluruh folder LocalAppData, checkpoint, workbook, tangkapan layar portal, atau browser profile pada issue publik.

Jika inspeksi data nyata diperlukan, lakukan melalui prosedur privat dan izin yang sesuai. Hasil review publik cukup menyatakan invariant yang gagal serta test case sintetis yang memverifikasi perbaikannya.
