# Desain pemilihan SPT dan workbook per masa

Disetujui pengguna melalui chat pada 12 Oktober 2026 setelah menarik `feat/windows-desktop` ke `013dd19`. Desain ini membatasi revisi pada alur capture, ekspor, dan desktop yang sudah ada.

**Batas publikasi terbaru PR #6:** mencakup susunan workbook pada Tugas 1 dan Tugas 2, yaitu pemilihan SPT serta konfirmasi penggantian hasil desktop. Batas publikasi lama yang hanya mencakup Tugas 1 sudah digantikan. Implementasi dan verifikasi otomatis Tugas 2 selesai pada commit yang dicatat dalam rencana. Unduhan PDF pada Tugas 3 serta perubahan autentikasi dan teks global pada Tugas 4 tetap tertunda. Lihat [rencana dan bukti pengujian](../plans/2026-10-12-period-selection-layout.md).

## Kontrak output

- Pertahankan `resume.xlsx` sebagai indeks/audit proses terpilih dengan tautan relatif. Setelah penggantian desktop, indeks baru merangkum pilihan saat ini; workbook lama di luar pilihan yang tetap tersimpan tidak otomatis masuk indeks baru.
- `SPT Masa 21`, `SPT Masa Unifikasi`, dan `SPT Masa PPN` memiliki folder terpisah, masing-masing tepat satu workbook per masa sumber literal. Normal dan seluruh pembetulan yang dipilih untuk masa yang sama berada dalam workbook tersebut, dengan sheet deskriptif yang berbeda.
- SPT Badan tetap di `SPT_Badan.xlsx`, dengan satu sheet per form/bagian teramati, seperti Induk dan L1-D. Bedakan Normal/Pembetulan dan gunakan ordinal yang aman dari benturan nama. Jangan membuat form yang tidak teramati. Path bagian lengkap menjadi identitas agar bagian dari dua induk berbeda tidak tergabung.
- Gunakan field/tabel datar yang dapat difilter, header dibekukan, lebar kolom, dan bukti sumber. Pertahankan ID/nilai mentah, baris duplikat, caption, serta asal pembetulan secara persis. Tambahkan angka analisis hanya setelah presisinya tervalidasi; teks sumber tidak berubah.
- Rencana PDF: unduh hanya tautan PDF laporan keuangan/auditan yang sudah ada dan telah diperiksa sebagai aksi baca pada Induk Badan. Jangan membuat dokumen remote atau menebak URL API. Gunakan konteks browser yang berizin, origin HTTPS yang tepat, unduhan GET tanpa redirect yang belum diperiksa, batas ukuran, dan validasi PDF. Kontrol yang belum didukung atau kegagalan tetap dilaporkan PARTIAL.

## Interaksi desktop pada implementasi Tugas 2

- Mulai dengan inventaris saja. Dialog menampilkan SPT teramati menurut jenis, masa, serta Normal/Pembetulan, dengan pencarian dan tanpa pilihan bawaan. **Sedot SPT terpilih** hanya aktif setelah pengguna memilih. Rincian hanya diambil untuk ID yang dikonfirmasi; subset dapat berstatus COMPLETE untuk subset yang dinyatakan itu.
- Jawaban pemilihan/penggantian terikat pada job dan hanya dapat dipakai sekali. Pilihan kosong, jawaban usang, dan ID tidak sah tidak menjadi pilihan semua record. Stop atau menutup dialog pemilihan membatalkan pekerjaan. Dialog tidak menunggu secara blocking; polling dan callback widget tetap pada thread utama Tk.
- Jika ada hasil sebelumnya, dialog menunjukkan folder ekspor terbaru yang dikenali dan daftar file yang akan diganti. **Jangan ganti**, Escape, atau menutup dialog menolak penggantian. **Ganti file tersebut** menyetujui folder/file yang ditampilkan, dengan pemeriksaan ulang sebelum publikasi.
- Penggantian berlaku per file Excel: workbook masa/jenis terpilih diganti seluruhnya, termasuk bila file lama memuat SPT lain dalam masa/jenis yang sama. Workbook masa lain tetap utuh. Scope NPWP/tahun/basis, identitas folder/file, benturan path, dan symlink/junction tetap diperiksa. Staging, rollback, dan data pemulihan tidak memberikan jaminan transaksi atomik saat proses mati atau listrik padam.

Dialog dan protokol persetujuan ini khusus desktop. CLI tetap menentukan cakupan lewat argumen/checkpoint dan tidak memakai keputusan dari dialog desktop.

## Autentikasi dan teks persis yang direncanakan

- Reproduksi celah pengenalan dengan fixture sintetis dan DOM yang telah diperiksa/disanitasi. Pertahankan pembatas origin, form, submit, binding kontrol, CAPTCHA/MFA, serta larangan mencatat rahasia.
- Judul: `Coretax SPT downloader : kalau bisa ribet, kenapa dibikin gampang`
- Pengaturan background: `jalankan proses sedot di background`
- Deskripsi output: `Hasil Sedot berada di folder Downloads Windows`
- Pertahankan subtitle penggunaan pribadi dan kredit yang sudah ada.

## Verifikasi dan batas bukti

Bukti RED dan GREEN pemilihan/overwrite beserta commit tepatnya dicatat pada [Tugas 2](../plans/2026-10-12-period-selection-layout.md#tugas-2-capture-sesuai-pilihan-dan-dialog-overwrite). Suite pada commit implementasi tersebut, self-test source/frozen, dan pemeriksaan artifact telah lulus pada kedua profil Python. Penerimaan fitur lengkap tetap menunggu Tugas 3–4 serta pemeriksaan live berizin. Semua fixture baru harus sintetis; periksa pilihan ID, byte file yang dipertahankan, jumlah workbook, nilai sumber, dan tautan relatif.

Tugas 3–4 masih memerlukan pengujian byte/origin/redirect/pembatalan PDF, pengenalan/binding autentikasi, dan teks global yang direncanakan. Pengujian dialog saat ini juga belum membuktikan perilaku keyboard/fokus pada jendela terlihat, aksesibilitas Windows, atau performa inventaris besar.

Probe DOM login aktual mengalami timeout. Tidak ada capture wajib pajak nyata atau pengiriman kredensial dalam pekerjaan desain ini. Pengenalan portal dan kontrol unduhan keuangan memerlukan bukti nyata sebelum dinyatakan lulus penerimaan live. Persyaratan awal rencana meminta konfirmasi pengguna secara terpisah sebelum commit/push; batas publikasi yang disepakati dicatat pada rencana dan PR terkait.
