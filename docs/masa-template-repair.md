# Kontrak perbaikan capture dan template Masa

Perbaikan ini menjembatani hasil DOM ke template yang sudah disetujui, tanpa mengubah nilai/identitas sumber dan tanpa memakai data pajak nyata dalam pengujian.

## Perilaku

1. Alias form teramati (A-1/A1, DAFTAR-I/Daftar I, dan pasangan terdaftar lainnya) memilih template yang sama. Nama sheet tetap mengikuti sumber.
2. Header tanggal beranotasi, header PPh bertingkat, dan tooltip dicocokkan tanpa mengubah header mentah. Kelompok tabel diambil dari heading/caption yang terlihat. Tabel ordinal Induk hanya diterima bila seluruh signature baris menentukan satu blok.
3. PPN field-based mengisi slot scalar yang pasti. Label berulang dan kolom berganda membutuhkan bukti grup/kolom. Tidak ada penempatan berdasarkan urutan nilai. Footer dipisahkan dari body; kolom tambahan tetap terlihat sebagai bukti mentah.
4. `resume.xlsx` membedakan status capture dari pemetaan template terbaru (Ringkasan B23 dan Audit). PARTIAL mapping berarti masih ada bukti yang perlu diperiksa; angka ambigu tidak boleh ditebak. Checkpoint lama tanpa konteks grup/span tidak menjamin seluruh isinya dapat dipetakan; capture ulang dapat diperlukan.
5. Penggantian sebagian workbook mempertahankan file lain serta memasukkannya kembali ke indeks global dari proof fisik terverifikasi. Persetujuan overwrite, fingerprint, rollback, scope NPWP/tahun/basis, dan custody PDF tetap berlaku.

## Verifikasi

Regresi sintetis: `tests/test_masa_mapping_regressions.py`, `tests/test_masa_dom_context.py`, dan `tests/test_resume_capture_scope.py`. Jalankan melalui workflow Windows yang ada, bersama suite lengkap, source GUI/worker self-test, frozen self-test, dan pemeriksaan artifact exact commit. Tidak mengubah workflow untuk memperoleh GREEN. Eksekusi lokal produk/pytest/build tetap dilarang oleh AGENTS.md; AST dan pemeriksaan hash bukan bukti eksekusi.

Berkas XLSX referensi adalah resource tersanitasi yang sudah tersimpan pada repository. Jangan menggantinya dengan workbook pajak nyata atau memasukkan checkpoint privat ke CI.
