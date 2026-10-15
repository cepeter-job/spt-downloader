# SPT Downloader

Aplikasi lokal untuk mengambil SPT Coretax melalui akses yang diizinkan dan mengekspornya ke Excel. Tersedia antarmuka Windows dan CLI. Pengambilan data hanya memakai navigasi baca, mempertahankan identitas serta nilai sumber, dan mencatat kelengkapan hasil secara eksplisit.

**Untuk kontributor:** mulai dari [dokumentasi development](docs/README.md). Panduan tersebut mencakup setup `uv`, arsitektur, pengujian, CI, persiapan Python 3.14, dan penerimaan manual.

## Memakai aplikasi Windows

**Status fitur:** kode ini mencakup pemilihan SPT, workbook terpisah untuk setiap masa dan Model SPT literal, PDF keuangan/auditan Badan langsung di folder Excel, template form PPh 21/26/PPN/Unifikasi, sorting jenis pajak, dan logging diagnostik lokal. **DOM** tetap sumber detail bawaan; **JSON-hybrid (pilot)** tersedia sebagai pilihan di Pengaturan atau `--detail-source json-first` pada CLI. JSON primer hanya digunakan untuk format teramati yang dapat diverifikasi; format yang belum didukung memakai fallback DOM yang diaudit, bukan mengabaikan kegagalan identitas atau otorisasi. Hasil integrasi dan artefak commit terbaru dicatat pada [PR #18](https://github.com/cepeter-job/spt-downloader/pull/18), yang menggabungkan [PR logging #19](https://github.com/cepeter-job/spt-downloader/pull/19). Penerimaan manual/live tetap terpisah dari tes sintetis dan build.

Unduh artifact produksi `SPTDownloader-Windows-x64-<commit>-python3.14.8` dari run yang berhasil pada [Build Windows app](https://github.com/cepeter-job/spt-downloader/actions/workflows/windows-build.yml). Cocokkan commit dan profil Python, ekstrak seluruh isinya, lalu jalankan **SPTDownloader.exe**. GUI dan worker memakai CPython 3.14.8 x64/GIL yang sama. Lihat [cara memverifikasi artifact](docs/ci-dan-rilis.md#memverifikasi-artifact).

Aplikasi ditujukan untuk Windows 10/11 x64. Membuka GUI tidak memerlukan administrator atau Python pada PATH. Lokasi portable yang dapat dipakai adalah `%LOCALAPPDATA%\Programs\SPTDownloader`. Executable belum memiliki tanda tangan Authenticode dari penerbit; checksum dan provenance build memiliki fungsi berbeda dari tanda tangan penerbit.

1. Buka **Pengaturan**. Pilih origin login intranet yang memang diizinkan, browser `msedge` atau `chrome`, dan preferensi headless. Masukkan akun serta password langsung pada dialog Windows yang menyamarkan password.
2. Masukkan **NPWP tepat 16 digit ASCII** dan **tahun pajak empat digit**. Spasi, pemisah, dan perubahan otomatis atas input tidak diterima. Klik **Mulai**. Hanya satu aplikasi/job yang boleh menggunakan profil khusus ini pada saat yang sama.
3. Persiapan pertama memeriksa runtime yang sesuai atau menyiapkan CPython produksi terisolasi di `%LOCALAPPDATA%\SPTDownloader`, kemudian memasang dependensi dengan `uv` dan pemeriksaan hash. Persiapan membutuhkan akses unduhan paket/runtime; pengambilan SPT membutuhkan koneksi intranet berizin dan Edge/Chrome terpasang. Kegagalan setup dapat dicoba kembali.
4. Selesaikan CAPTCHA, MFA, atau login yang tidak dikenali pada browser aplikasi yang terlihat. Login otomatis hanya berlaku untuk form yang sudah diperiksa dan kredensial yang cocok dengan origin. Bila pemindahan sesi ke headless ditolak, browser tetap terlihat.
5. Setelah daftar SPT muncul, cari menurut jenis pajak, masa, pembetulan, atau ID, lalu pilih SPT yang ingin diunduh. Tidak ada pilihan otomatis. Klik **Sedot SPT terpilih**; aplikasi hanya mengambil rincian untuk ID yang dikonfirmasi. Menutup dialog pemilihan membatalkan pekerjaan.
6. `resume.xlsx` diperbarui otomatis tanpa konfirmasi setelah scope dan file lama lolos pemeriksaan. Jika **file SPT/PDF terpilih** sudah ada, periksa **folder yang ditampilkan dan daftar file yang akan diganti**. **Jangan ganti**, Escape, atau menutup dialog mempertahankan seluruh hasil lama dan membatalkan publikasi, termasuk pembaruan resume. **Ganti file tersebut** menyetujui penggantian pada folder itu. File masa lain yang tidak dipilih tetap tersimpan.
7. Tunggu status terminal. **100% berarti COMPLETE untuk pilihan yang dikonfirmasi, setelah verifikasi workbook, publikasi, dan pembersihan proses milik aplikasi.** Klik **Buka Hasil** untuk membuka folder yang telah dipublikasikan.

**Stop** meminta pembatalan pekerjaan; checkpoint yang tersedia tetap disimpan sebagai data belum lengkap. Aplikasi menutup proses worker/browser yang dimilikinya; worker yang tidak berhenti diterminasi setelah 15 detik. Menutup jendela utama saat pekerjaan berjalan meminta konfirmasi. Permintaan atau jawaban lama tidak melanjutkan pekerjaan yang sudah dihentikan. File SPT/PDF hasil terdahulu tidak diganti tanpa persetujuan; pembaruan resume otomatis tetap melewati pemeriksaan scope dan race.

### Log diagnostik untuk bugfixing

Buka **Pengaturan → Buka folder log** untuk melihat diagnostik lokal berotasi. Log mencatat tahap, durasi, status, dan lokasi error tanpa menyalin data SPT/kredensial atau raw stdout/stderr. Lihat [cara menggunakan log, level DEBUG, retensi, dan batas privasi](docs/diagnostik.md). Logging bukan bukti COMPLETE dan tidak mengunggah data otomatis.

### Cek Kredensial

Simpan origin, akun, dan password pada **Pengaturan**, kemudian klik **Cek Kredensial**. Pemeriksaan ini tidak memerlukan NPWP atau tahun, memakai profil browser sementara yang baru, dan mencoba kredensial tersimpan satu kali. Pemeriksaan tidak memulai pengambilan SPT atau ekspor. Tombol dinonaktifkan selama ada perubahan pengaturan yang belum disimpan; **Simpan** mempertahankan dialog agar pemeriksaan bisa segera dijalankan.

**Login berhasil** memerlukan bukti bahwa kredensial tersimpan telah dikirim melalui form yang sah dan kontrol pencarian wajib pajak Coretax terlihat. Sesi SSO yang sudah login dilaporkan sebagai **password belum diuji**. CAPTCHA/MFA atau form yang tidak dikenal membutuhkan tindakan manual. Timeout berarti **belum terverifikasi**, bukan bukti password salah. Hasil ini berlaku untuk pemeriksaan tersebut, bukan jaminan password tetap valid di kemudian hari.

Gunakan **Batalkan Cek**, Escape, atau tutup Pengaturan untuk menghentikan pemeriksaan milik aplikasi sebelum dialog ditutup. Password disimpan hanya di Windows Credential Manager, terikat pada origin yang diizinkan. Password kosong mempertahankan entri lama; penghapusan entri meminta konfirmasi. File preferensi tidak menyimpan password, token, atau cookie.

### Setelah login manual

Rute `https://coretax.intranet.pajak.go.id/home/id-ID/` hanya menjadi petunjuk navigasi. Aplikasi membuka alamat pencarian wajib pajak yang dikenal satu kali, lalu menunggu kontrol `ObjectPermitNumber` terlihat. Homepage saja tidak membuktikan autentikasi siap. Batas lima menit adalah tenggat maksimum; pekerjaan berlanjut segera setelah kontrol pencarian terverifikasi. Mekanisme yang sama dipakai sesudah pengiriman password pada Cek Kredensial tanpa mencoba password untuk kedua kali.

## Lokasi hasil dan kerahasiaan

Downloads ditentukan melalui Windows Known Folder API, termasuk lokasi yang dipindahkan, OneDrive, jaringan, atau nama non-ASCII.

| Isi | Lokasi |
| --- | --- |
| Set Excel yang dipublikasikan desktop | `<Downloads aktual>\NPWP - NAMA WP\TAHUN PAJAK\WAKTU EKSPOR-JOB ID\` |
| Checkpoint dan data pemulihan desktop | `%LOCALAPPDATA%\SPTDownloader\jobs\<job-id>\` |
| Profil browser khusus desktop | `%LOCALAPPDATA%\SPTDownloader\profile\` |
| Runtime, paket, dan preferensi desktop | `%LOCALAPPDATA%\SPTDownloader\` |

Nama folder memakai nama wajib pajak dari hasil pencarian NPWP yang cocok persis. Hanya komponen nama berkas yang disanitasi; nama sumber tetap literal di Excel. Nama wajib pajak yang hilang atau Downloads yang tidak dapat ditulisi menghasilkan error. Aplikasi tidak membuat nama pengganti atau diam-diam mengganti tujuan.

Saat penggantian disetujui, desktop memakai folder ekspor sebelumnya yang ditampilkan pada dialog. Aplikasi memeriksa ulang folder dan file tersebut sebelum menggantinya; perubahan sejak konfirmasi menghentikan publikasi.

Workbook, checkpoint, dan profil merupakan data rahasia lokal. Workbook tidak terenkripsi. Jangan unggah berkas tersebut, cookie, kredensial, atau tangkapan layar berisi data wajib pajak ke issue, PR, log publik, atau percakapan.

## Cakupan pengambilan

Dasar seleksi bawaan adalah **masa/tahun pajak**, bukan tahun penyampaian. SPT Desember 2025 yang disampaikan Januari 2026 termasuk ekspor tahun pajak 2025. CLI menyediakan `--year-basis submission` bila seleksi memang harus berdasarkan tanggal penyampaian.

Aplikasi membuka `/returnsheets/id-ID/taxpayer-search`, memilih NPWP yang cocok persis, menemukan daftar status yang tersedia bagi wajib pajak tersebut, lalu membaca seluruh halaman. Respons JSON yang diamati berasal dari navigasi UI itu sendiri. `TotalRecords` direkonsiliasi dengan baris yang dibaca; aplikasi tidak mengambil token autentikasi atau menjalankan request penulisan API tersendiri.

Inventaris mencakup jenis SPT, masa, dan pembetulan yang ditemukan dalam scope. Desktop kemudian mengambil rincian hanya untuk pilihan pengguna dan mencatat jumlah serta ID yang dipilih. Pilihan kosong atau ID yang tidak sah tidak otomatis menjadi pilihan semua SPT. `RecordId` yang sama pada beberapa daftar status diekspor sekali dengan asal kemunculannya dicatat. ID pembetulan berbeda tetap menjadi entri terpisah. Format tahun yang tidak dapat dibuktikan menjadi error, bukan alasan untuk membuang SPT secara diam-diam.

Setiap detail dibuka hanya melalui kontrol **View** yang dikenali. URL detail harus cocok dengan wajib pajak dan identitas SPT. Tab yang tersedia, field baca, tabel, dan paginasi yang didukung diambil; tab dinonaktifkan tidak dijelajahi. Tautan PDF laporan keuangan/auditan yang sudah terlihat sebagai href biasa pada Induk Badan terverifikasi dapat diunduh melalui GET pada origin HTTPS yang disetujui. Redirect, kontrol pembentukan dokumen, HTML, byte/ukuran/hash yang tidak valid, serta scope tidak cocok tetap ditolak atau dilaporkan PARTIAL. Hanya PDF yang dideklarasikan COMPLETE dan diverifikasi ikut dipublikasikan dengan tautan relatif pada Audit resume; metadata bukan bukti bahwa byte PDF sudah diunduh. PDF/BPE/lampiran lain, pembuatan PDF jarak jauh, dan dialog rincian per baris tetap di luar cakupan.

**COMPLETE** berarti cakupan halaman yang didukung telah direkonsiliasi; pada desktop, hasil ini berlaku untuk subset SPT yang dikonfirmasi. Status ini tidak menyatakan bahwa seluruh tahun, dokumen, atau objek database Coretax sudah diunduh. Layout yang tidak didukung, halaman gagal, batas pengujian, atau pembatalan tetap membatasi status hasil sesuai tahapnya. Baca **Ringkasan → Status** dan lembar **Audit** pada `resume.xlsx`.

## Susunan workbook

| Berkas | Isi |
| --- | --- |
| `resume.xlsx` | Ringkasan proses saat ini, Daftar SPT, dan Audit; indeks menaut ke workbook serta lembar detail yang tepat. Pada desktop, ringkasan menyatakan pilihan pengguna. |
| `SPT_Badan_<masa-tahun>_<model>.xlsx` | Normal, Pembetulan 1, Pembetulan 2, dan seterusnya memiliki file terpisah; setiap file berisi seluruh form teramati milik model itu. |
| `SPT Masa 21/SPT_21_<masa>_<model>.xlsx` | Satu file per masa literal dan model PPh Pasal 21/26, satu sheet per form/tab teramati. |
| `SPT Masa Unifikasi/SPT_Unifikasi_<masa>_<model>.xlsx` | Satu file per masa literal dan model PPh Unifikasi, satu sheet per form/tab teramati. |
| `SPT Masa PPN/SPT_PPN_<masa>_<model>.xlsx` | Satu file per masa literal dan model PPN, satu sheet per form/tab teramati. |
| `SPT_<jenis>_<masa-tahun>_<model>.xlsx` | Pemisahan masa/model yang sama untuk jenis pajak lainnya yang benar-benar tertangkap. |

**PDF laporan keuangan yang baru diunduh tersimpan langsung di folder hasil yang sama dengan Excel**, tanpa subfolder `attachments`. Nama `LK_<record-key>_<document-key>.pdf` tetap unik per SPT dan dokumen; tautan relatif pada Audit/proof mengarah ke file itu. Capture/proof lama tidak ditulis ulang atau dipindahkan. Untuk beralih dari hasil dengan PDF bersubfolder ke unduhan baru yang datar, desktop memeriksa hasil lama lalu memakai folder hasil baru.

**Normal dan setiap nomor pembetulan memiliki file sendiri.** Masa/model berasal dari sumber, disanitasi hanya untuk keamanan nama file; nilai literal dan nol awal tetap disimpan dalam proof. Contoh: `SPT Masa PPN/SPT_PPN_Januari 2025_Normal.xlsx` dan `SPT Masa PPN/SPT_PPN_Januari 2025_Pembetulan 1.xlsx`. Aturan ini menggantikan penggabungan model pada spesifikasi lama.

Workbook SPT jenis/masa/model **hanya berisi lembar form**; Ringkasan, Daftar SPT, dan Audit hanya berada di `resume.xlsx`. Banner judul/NPWP/tahun/tautan umum serta header/footer cetak tidak ditambahkan pada lembar form. Field sumber, teks konteks, path bagian, dan header kolom tabel tetap disimpan. Tidak ada workbook masa/jenis yang dibuat bila datanya tidak terambil. **Pertahankan seluruh hierarki folder dan jangan mengganti nama workbook** agar tautan relatif tetap berfungsi. Folder hasil dapat dipindahkan bersama. Sheet menggunakan tabel berfilter/freeze panes; field dan nilai sumber tidak digabung dalam sel data. Kolom numerik opsional membantu pengolahan angka format Indonesia tanpa mengganti nilai sumber atau mengubah NPWP/ID menjadi angka.

Identitas dan angka sumber berbentuk teks dipertahankan sebagai teks literal, termasuk nol awal, format angka Indonesia, dan teks yang diawali `=`. Hitungan ringkasan tetap numerik. Sel yang melebihi 32.767 karakter, karakter XML yang tidak didukung, atau angka numerik yang akan kehilangan presisi menghentikan ekspor secara eksplisit. Teks konteks halaman yang panjang dipecah antar-sel tanpa pemotongan. Hanya URL HTTP/HTTPS menjadi tautan aktif.

Seluruh set ditulis ke staging dan diperiksa sebelum publikasi. Workbook SPT baru menyimpan deklarasi scope/identitas/form/PDF dalam properti dokumen XLSX nonvisual `identifier`; workbook lama masih diperiksa melalui header/index/Audit fisiknya, secara independen dari `run.json`. Resume tetap membuktikan scope melalui sheet administratif. Proof pada output baru wajib cocok dengan capture terpilih dan sheet fisiknya; proof yang hilang, berubah, atau tidak sah ditolak. Pemeriksaan hasil lama mendukung format legacy tetapi tetap menolak scope lain. Metadata bukan tanda tangan digital maupun pengganti verifikasi byte/hash PDF. Benturan nama berkas tanpa membedakan kapital dan berkas tak dikenal ditolak. Kegagalan penggantian mencoba rollback serta mempertahankan data pemulihan. Proses mati atau listrik padam di tengah penggantian beberapa berkas tidak memiliki jaminan transaksi atomik. Gunakan folder baru saat mengubah scope atau memulihkan publikasi yang terblokir.

Penggantian desktop bekerja **per file SPT/PDF yang disetujui**. Workbook masa/model yang tercantum pada dialog diganti seluruhnya dengan hasil pilihan saat ini. File model atau masa lain yang tidak dipilih tetap utuh. `resume.xlsx` diperbarui otomatis hanya setelah pemeriksaan scope/fingerprint/race lolos, bukan izin untuk menimpa SPT/PDF lain. Resume baru merangkum pilihan saat ini; file lama yang dipertahankan di luar pilihan tidak otomatis ditambahkan ke indeks baru itu.

Desktop memvalidasi scope hasil gabungan lama, lalu membuat **folder hasil baru** untuk format terpisah agar proof/PDF lama tidak menjadi kedaluwarsa. File lama tidak dihapus atau diganti saat migrasi ini. Untuk membuat ulang capture lama melalui CLI, pilih **folder output baru** melalui `--from-json ... --output ...`. Susunan lama tidak ditimpa atau dihapus secara otomatis ketika set nama berkasnya berbeda. Path output relatif maupun absolut didukung; pindahkan seluruh folder hasil bersama agar tautannya tetap utuh.

## Memakai CLI di Windows

CLI tetap memakai argumen dan checkpoint untuk menentukan cakupan serta folder output. CLI tidak memakai dialog pemilihan atau persetujuan penggantian milik desktop; pengambilan biasa tetap memproses inventaris dalam cakupan argumennya, kecuali dibatasi oleh opsi di bawah.

Pasang `uv` sesuai [kebijakan toolchain](docs/python-314.md), lalu jalankan **setup.cmd** dari checkout ini. Setelah setup berhasil, jalankan **run.cmd** untuk mengisi NPWP dan tahun secara interaktif. Login dilakukan langsung di browser terpisah; selesaikan password, CAPTCHA, atau MFA di sana, lalu tekan Enter pada terminal bila diminta.

`run.cmd` dapat memakai ulang browser automation lokal pada port 9235 yang sudah aktif. Browser baru biasa tidak mengaktifkan port debugging. Jangan mengekspos endpoint debugging ke jaringan atau memakai profil browser pribadi.

Contoh berikut untuk **Command Prompt**. Ganti `NPWP_16_DIGIT_ANDA` dengan NPWP yang memang berwenang Anda akses; placeholder sengaja bukan NPWP valid. Tentukan folder baru di luar checkout untuk data lokal.

```bat
.venv\Scripts\python.exe coretax.py --npwp NPWP_16_DIGIT_ANDA --year 2025 --output "%LOCALAPPDATA%\SPTDownloader-CLI\run-baru" --profile "%LOCALAPPDATA%\SPTDownloader-CLI\profile"
```

Bila browser automation yang sesuai sudah login:

```bat
.venv\Scripts\python.exe coretax.py --npwp NPWP_16_DIGIT_ANDA --year 2025 --output "%LOCALAPPDATA%\SPTDownloader-CLI\run-baru" --reuse-browser http://127.0.0.1:9235
```

Endpoint harus berupa origin HTTP/HTTPS loopback tanpa kredensial, path, query, atau fragment. Tutup browser automation setelah selesai; proses lokal lain mungkin dapat mengakses endpoint selama browser tersebut terbuka.

### Checkpoint dan pemulihan CLI

`--resume` melanjutkan pengambilan data dari `inventory.json` dan checkpoint detail yang cocok. Opsi tersebut berbeda dengan nama workbook `resume.xlsx`. Detail lengkap yang valid dilewati, detail yang belum lengkap dicoba kembali.

```bat
.venv\Scripts\python.exe coretax.py --resume "%LOCALAPPDATA%\SPTDownloader-CLI\run-sebelumnya" --reuse-browser http://127.0.0.1:9235
```

`--from-json` membentuk ulang seluruh set Excel secara offline tanpa membuka browser. Gunakan folder baru agar hasil lama tetap mudah diperiksa:

```bat
.venv\Scripts\python.exe coretax.py --from-json "%LOCALAPPDATA%\SPTDownloader-CLI\run-sebelumnya\run.json" --output "%LOCALAPPDATA%\SPTDownloader-CLI\hasil-pemulihan-baru"
```

`--inventory-only` mengambil daftar saja sehingga statusnya PARTIAL untuk cakupan detail penuh. `--detail-limit N` membatasi jumlah detail untuk pengujian; sisa SPT yang belum diambil membuat run tetap PARTIAL. `--max-pages` memiliki batas bawaan 1000 per daftar/tabel; batas yang menghalangi kelengkapan dilaporkan sebagai PARTIAL. Jangan mengedit checkpoint secara manual.

| Exit code CLI | Arti |
| --- | --- |
| `0` | COMPLETE untuk cakupan yang didukung. |
| `2` | PARTIAL. |
| `1` | Terblokir/gagal. |
| `130` | Diinterupsi. |

Kode protokol worker desktop berbeda untuk beberapa status; rujuk [arsitektur](docs/arsitektur.md#status-dan-stop) saat mengubah controller.

## Development dan verifikasi

Repositori [cepeter-job/spt-downloader](https://github.com/cepeter-job/spt-downloader) menyatukan CLI dan aplikasi desktop. `main` menjadi branch integrasi; perubahan dilakukan lewat branch berumur pendek dan PR yang dapat ditinjau.

- [Setup, pengujian lokal, dan kontribusi](docs/pengembangan.md).
- [Arsitektur serta kontrak keamanan dan data](docs/arsitektur.md).
- [Pembagian CI, cache, dan verifikasi artifact](docs/ci-dan-rilis.md).
- [Kebijakan Python produksi dan persiapan 3.14](docs/python-314.md).
- [Checklist penerimaan manual Coretax dan Excel](docs/penerimaan-manual.md).
- [Pemecahan masalah](docs/pemecahan-masalah.md).
- [Audit 12 Oktober 2026](docs/audit-2026-10-12.md), sebagai catatan historis baseline dan temuan.

Pengujian otomatis memakai data sintetis. Tes browser memakai fixture HTML lokal, tanpa akun atau data wajib pajak. Self-test GUI source/frozen tidak mengakses kredensial nyata dan tidak mengambil SPT. Bukti tersebut tidak menggantikan penerimaan manual berizin pada Coretax aktual.

## Lisensi

Lisensi yang ada dipertahankan: **GNU General Public License versi 3**. Lihat [LICENSE](LICENSE).
