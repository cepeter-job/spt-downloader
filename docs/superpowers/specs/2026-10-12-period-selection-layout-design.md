# Desain pemilihan SPT dan workbook per masa

Disetujui pengguna melalui chat pada 12 Oktober 2026 setelah menarik `feat/windows-desktop` ke `013dd19`. Desain ini membatasi revisi pada alur capture, ekspor, dan desktop yang sudah ada.

**Batas publikasi PR #6:** hanya susunan workbook per masa dan form Badan pada Tugas 1 dalam [rencana implementasi](../plans/2026-10-12-period-selection-layout.md). Pemilihan SPT per proses, konfirmasi overwrite, unduhan PDF, serta perubahan autentikasi dan teks di bawah masih merupakan rancangan pekerjaan berikutnya. Dokumen ini tidak menyatakan fitur tersebut sudah tersedia.

## Kontrak output

- Pertahankan `resume.xlsx` sebagai indeks/audit proses terpilih dengan tautan relatif.
- `SPT Masa 21`, `SPT Masa Unifikasi`, dan `SPT Masa PPN` memiliki folder terpisah, masing-masing tepat satu workbook per masa sumber literal. Normal dan seluruh pembetulan yang dipilih untuk masa yang sama berada dalam workbook tersebut, dengan sheet deskriptif yang berbeda.
- SPT Badan tetap di `SPT_Badan.xlsx`, dengan satu sheet per form/bagian teramati, seperti Induk dan L1-D. Bedakan Normal/Pembetulan dan gunakan ordinal yang aman dari benturan nama. Jangan membuat form yang tidak teramati. Path bagian lengkap menjadi identitas agar bagian dari dua induk berbeda tidak tergabung.
- Gunakan field/tabel datar yang dapat difilter, header dibekukan, lebar kolom, dan bukti sumber. Pertahankan ID/nilai mentah, baris duplikat, caption, serta asal pembetulan secara persis. Tambahkan angka analisis hanya setelah presisinya tervalidasi; teks sumber tidak berubah.
- Rencana PDF: unduh hanya tautan PDF laporan keuangan/auditan yang sudah ada dan telah diperiksa sebagai aksi baca pada Induk Badan. Jangan membuat dokumen remote atau menebak URL API. Gunakan konteks browser yang berizin, origin HTTPS yang tepat, unduhan GET tanpa redirect yang belum diperiksa, batas ukuran, dan validasi PDF. Kontrol yang belum didukung atau kegagalan tetap dilaporkan PARTIAL.

## Interaksi proses yang direncanakan

- Mulai dengan inventaris saja. Tampilkan SPT yang teramati dan izinkan pemilihan per record menurut jenis, masa, serta Normal/Pembetulan. Capture detail hanya untuk ID yang dikonfirmasi. Subset yang sengaja dipilih dapat berstatus COMPLETE untuk subset yang dinyatakan itu, bukan otomatis seluruh tahun.
- Jawaban pemilihan dan overwrite terikat pada job serta memperhatikan pembatalan. Jangan otomatis mengambil seluruh record saat menunggu. Callback GUI tetap pada thread utama Tk dan pembersihan proses milik aplikasi tetap berlaku.
- Publikasi ke Downloads memakai scope tervalidasi dan path relatif. Hasil lama yang berbenturan memerlukan persetujuan overwrite eksplisit; penolakan mempertahankan byte lama. Jangan menimpa file yang tidak dipilih, workbook tak dikenal, scope NPWP/tahun/basis berbeda, atau tujuan yang dialihkan symlink/junction. Gunakan staging dan validasi sebelum penggantian; pertahankan data pemulihan jika gagal.

## Autentikasi dan teks persis yang direncanakan

- Reproduksi celah pengenalan dengan fixture sintetis dan DOM yang telah diperiksa/disanitasi. Pertahankan pembatas origin, form, submit, binding kontrol, CAPTCHA/MFA, serta larangan mencatat rahasia.
- Judul: `Coretax SPT downloader : kalau bisa ribet, kenapa dibikin gampang`
- Pengaturan background: `jalankan proses sedot di background`
- Deskripsi output: `Hasil Sedot berada di folder Downloads Windows`
- Pertahankan subtitle penggunaan pribadi dan kredit yang sudah ada.

## Verifikasi dan batas bukti

Catatan baseline awal pada kode yang ditarik: 289 tes lulus dalam 67,24 detik. Semua data baru harus jelas sintetis. Verifikasi jumlah file per masa, nama form/pembetulan, nilai mentah/filter, dan tautan relatif yang tepat. Untuk tugas berikutnya, tambahkan pemeriksaan capture sesuai pilihan, persetujuan/penolakan overwrite dan rollback, byte/origin/redirect/pembatalan PDF, penolakan/binding autentikasi, serta teks GUI persis. Jalankan self-test source/frozen dan buka ulang XLSX yang dihasilkan untuk audit.

Probe DOM login aktual mengalami timeout. Tidak ada capture wajib pajak nyata atau pengiriman kredensial dalam pekerjaan desain ini. Pengenalan portal dan kontrol unduhan keuangan memerlukan bukti nyata sebelum dinyatakan lulus penerimaan live. Persyaratan awal rencana meminta konfirmasi pengguna secara terpisah sebelum commit/push; batas publikasi yang disepakati dicatat pada rencana dan PR terkait.
