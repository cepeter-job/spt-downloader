# Perbaikan correctness dari audit fungsi duplikat

Tujuan: satukan kontrak persentase PPh21/Unifikasi dan identitas build yang
berbeda antara CI dan runtime. Pengguna mengotorisasi pembuatan PR dan merge.
Baseline awal: `8391dde2fa78afdbcc9f2ee07502d4f603fa15ee` (PR #88).

## Kontrak dan implementasi

Parser murni di `coretax_template_cells.py` mengembalikan pasangan
`(fraction, valid)`. PPh21 dan Unifikasi tetap menangani penulisan sel dan
audit mapping masing-masing. Pertahankan blank, sintaks digit ASCII dengan
koma desimal opsional, rentang 0–100, maksimum 15 digit koefisien sumber
sebelum pembagian, serta konversi float yang mempertahankan nilai desimal.
Tolak hasil nonzero subnormal sesuai batas Excel yang sudah diterapkan
`coretax_exporter.validate_excel_value`. Nilai yang tidak aman tetap literal
dan unresolved; checkpoint tidak berubah. Grammar persentase Badan terpisah.

Predicate schema murni di `spt_desktop/build_info.py` dipakai pembaca runtime
dan validator CI. Pertahankan tepat empat field, schema integer 1, commit
40 digit heksadesimal kecil, run ID positif 1–24 digit, dan run attempt
integer 1–1.000.000. Boolean bukan integer yang valid. Runtime tetap
mengembalikan `None`; adapter CI tetap melempar `ValueError`. Pemeriksaan
file, pembacaan terbatas, dan diagnostik unknown tetap berlaku.

## Urutan kerja dan bukti

1. Tinjau PR #88, baseline main, dan interaksi PR #93. Dua modul bersama
   sudah berada dalam `WORKER_FILES`; tidak perlu dependensi atau rute baru.
2. Tambahkan regresi pada empat modul tes yang sudah ada. Push commit tes
   terlebih dahulu dan konfirmasi kegagalan yang dimaksud di GitHub runner.
   Ekspor tersimpan memeriksa nilai/tipe sel, audit unresolved, dan sumber
   yang tidak berubah. Tes identitas memeriksa producer serta kedua reader.
3. Terapkan kedua fungsi bersama, pertahankan adapter, dan catat kontrak
   aktual pada `AGENTS.md`. Tinjau diff secara independen.
4. Jalankan pipeline PR yang sudah ada tanpa perubahan workflow. Tes
   identitas CI juga masuk portable; ekspor dan diagnostik masuk gabungan
   dua shard Windows. Verifikasi source/frozen self-test, inventory tes,
   checksum, metadata, dan bootstrap artifact berdasarkan ID artifact.
5. Periksa main/PR lain lagi sebelum merge. Integrasikan perubahan baru
   bila ada, tunggu bukti untuk tree gabungan final, lalu merge head yang
   diverifikasi. Catat commit/run/artifact pada deskripsi PR.

Semua pytest, import produk, build, dan eksekusi EXE hanya pada GitHub
runner sesuai `AGENTS.md`. Lokal hanya pemeriksaan AST/source dan
hash/metadata artifact. Bukti RED/GREEN disimpan pada riwayat commit dan
deskripsi PR, sehingga tidak memerlukan commit dokumentasi setelah setiap
run. Audit cleanup Windows dan refactor duplikat lain tetap pekerjaan lain.
