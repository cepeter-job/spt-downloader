# Desain pemilihan SPT dan workbook per masa

Disetujui pengguna melalui chat pada 12 Oktober 2026 setelah menarik `feat/windows-desktop` ke `013dd19`. Desain ini membatasi revisi pada alur capture, ekspor, dan desktop yang sudah ada.

**Batas publikasi terbaru:** PR #6 mencakup Tugas 1–2. PDF, autentikasi/teks, dan follow-up base/konteks PDF terverifikasi pada head produk `89a3830d65bae04660f90d75992f06c78003088f` di draft PR #8; PR belum digabung. Tugas 5 dibuka kembali sesudah dokumentasi awal dan pengguna menyetujui regresi/perbaikan PDF. Lima kegagalan direproduksi, perbaikan direview, lalu seluruh 608 tes Windows lulus. Bukti eksekusi tetap terikat pada head produk tersebut; penerimaan portal live belum terbukti. Lihat [rencana](../plans/2026-10-12-period-selection-layout.md) dan [matriks sepuluh persyaratan](../reports/2026-10-13-feature-acceptance.md).

## Kontrak output

- Pertahankan `resume.xlsx` sebagai indeks/audit proses terpilih dengan tautan relatif. Setelah penggantian desktop, indeks baru merangkum pilihan saat ini; workbook lama di luar pilihan yang tetap tersimpan tidak otomatis masuk indeks baru.
- `SPT Masa 21`, `SPT Masa Unifikasi`, dan `SPT Masa PPN` memiliki folder terpisah, masing-masing tepat satu workbook per masa sumber literal. Normal dan seluruh pembetulan yang dipilih untuk masa yang sama berada dalam workbook tersebut, dengan sheet deskriptif yang berbeda.
- SPT Badan tetap di `SPT_Badan.xlsx`, dengan satu sheet per form/bagian teramati, seperti Induk dan L1-D. Bedakan Normal/Pembetulan dan gunakan ordinal yang aman dari benturan nama. Jangan membuat form yang tidak teramati. Path bagian lengkap menjadi identitas agar bagian dari dua induk berbeda tidak tergabung.
- Gunakan field/tabel datar yang dapat difilter, header dibekukan, lebar kolom, dan bukti sumber. Pertahankan ID/nilai mentah, baris duplikat, caption, serta asal pembetulan secara persis. Tambahkan angka analisis hanya setelah presisinya tervalidasi; teks sumber tidak berubah.
- PDF Tugas 3: unduh hanya tautan PDF laporan keuangan/auditan yang sudah ada dan telah diperiksa sebagai aksi baca pada Induk Badan. Jangan membuat dokumen remote atau menebak URL API. Gunakan konteks browser yang berizin, origin HTTPS tepat, GET tanpa redirect, batas ukuran/tenggat/signature/footer/hash. Metadata saja bukan byte PDF. Hanya deklarasi COMPLETE terikat pada SPT terpilih ikut publikasi; kontrol yang belum didukung atau kegagalan tetap PARTIAL.
- Resolusi target PDF mengikuti href native browser, termasuk base dokumen; guard href mentah tetap berlaku. Scope record dan URL dokumen observasi diperiksa sebelum GET, termasuk pada giliran JS yang memulai fetch. Pergantian detail setelah scan atau sebelum fetch tidak mengesahkan request yang tertinggal.

## Interaksi desktop pada implementasi Tugas 2

- Mulai dengan inventaris saja. Dialog menampilkan SPT teramati menurut jenis, masa, serta Normal/Pembetulan, dengan pencarian dan tanpa pilihan bawaan. **Sedot SPT terpilih** hanya aktif setelah pengguna memilih. Rincian hanya diambil untuk ID yang dikonfirmasi; subset dapat berstatus COMPLETE untuk subset yang dinyatakan itu.
- Jawaban pemilihan/penggantian terikat pada job dan hanya dapat dipakai sekali. Pilihan kosong, jawaban usang, dan ID tidak sah tidak menjadi pilihan semua record. Stop atau menutup dialog pemilihan membatalkan pekerjaan. Dialog tidak menunggu secara blocking; polling dan callback widget tetap pada thread utama Tk.
- Jika ada hasil sebelumnya, dialog menunjukkan folder ekspor terbaru yang dikenali dan daftar file yang akan diganti. **Jangan ganti**, Escape, atau menutup dialog menolak penggantian. **Ganti file tersebut** menyetujui folder/file yang ditampilkan, dengan pemeriksaan ulang sebelum publikasi.
- Penggantian berlaku per file Excel: workbook masa/jenis terpilih diganti seluruhnya, termasuk bila file lama memuat SPT lain dalam masa/jenis yang sama. Workbook masa lain tetap utuh. Scope NPWP/tahun/basis, identitas folder/file, benturan path, dan symlink/junction tetap diperiksa. Staging, rollback, dan data pemulihan tidak memberikan jaminan transaksi atomik saat proses mati atau listrik padam.

Dialog dan protokol persetujuan ini khusus desktop. CLI tetap menentukan cakupan lewat argumen/checkpoint dan tidak memakai keputusan dari dialog desktop.

## Autentikasi dan teks persis yang diterapkan pada Tugas 4

- Celah kesiapan form awal direproduksi melalui fixture sintetis. Penantian terbatas hanya saat form belum siap; form siap tetap melewati pengenal strict yang sama. Pertahankan origin/account/control/action binding, jalur manual untuk challenge/unknown, serta larangan mencatat rahasia. Jangan mengklaim loop post-login yang tidak diubah sudah diperbaiki.
- Header nyata dan caption OS: `Coretax SPT downloader : kalau bisa ribet, kenapa dibikin gampang`
- Pengaturan background: `jalankan proses sedot di background`
- Deskripsi output: `Hasil Sedot berada di folder Downloads Windows`, menggantikan hint hierarki lama tanpa menghapus informasi setup. Self-test membaca widget nyata, bukan hanya string caption; build menolak attestation hilang/keliru.
- Pertahankan subtitle penggunaan pribadi dan kredit yang sudah ada.

## Verifikasi dan batas bukti

Bukti historis RED/GREEN pemilihan/overwrite dicatat pada [Tugas 2](../plans/2026-10-12-period-selection-layout.md#tugas-2-capture-sesuai-pilihan-dan-dialog-overwrite); dua profil Python pada bukti lama bukan profil aktif terbaru. Pada run `38360875900`, produksi GUI/worker CPython 3.14.8/GIL lulus 608 tes Windows dan 367 tes portable/241 deselected; source/frozen, persiapan worker/pemakaian ulang, serta artifact `11794902211` diverifikasi berdasarkan hash dan tree yang sama dengan head. Seluruh sepuluh kontrak dipetakan pada laporan penerimaan; angka test group beririsan. Fixture baru tetap sintetis; tidak ada eksekusi produk lokal untuk pekerjaan ini.

Kontrak otomatis byte/origin/redirect/pembatalan/custody PDF, kesiapan/binding autentikasi, teks global, dan header nyata Tugas 3–4 sudah dijalankan. Ini tidak membuktikan semua layout portal, keaslian isi laporan PDF, ACL server, seluruh perilaku keyboard/fokus, aksesibilitas Windows, atau performa inventaris besar. Penerimaan live berizin tetap terpisah dari penerimaan otomatis.

Probe DOM login pada desain awal mengalami timeout; pada tahap desain tersebut tidak ada capture wajib pajak nyata atau pengiriman kredensial. Sesudahnya, pengguna menyediakan capture JSON privat yang diperiksa lokal secara baca-saja di luar repo; data tersebut tidak diunggah atau dijadikan fixture. Tidak ada akses portal live untuk verifikasi Tugas 3–5 ini. Pengenalan portal dan kontrol keuangan memerlukan bukti nyata sebelum dinyatakan lulus penerimaan live. Commit/push mengikuti scope yang disetujui, tanpa merge/auto-merge. Pilot JSON-first Badan sebagai alternatif DOM baru dimulai setelah Tugas 5 ditutup, bukan menggantikan kontrak ini.
