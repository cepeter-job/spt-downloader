# Rencana implementasi pemilihan SPT dan workbook per masa

> **Untuk agen pengembang:** gunakan `superpowers:subagent-driven-development` atau `superpowers:executing-plans` untuk menjalankan tugas berurutan. Checklist mencatat status, bukan menggantikan bukti pengujian.

**Tujuan lengkap rancangan:** menerapkan sepuluh revisi downloader yang diminta, mencakup ekspor sesuai scope, pemilihan/overwrite dengan persetujuan eksplisit, PDF yang aman, serta perilaku Windows yang dapat diverifikasi.

**Arsitektur:** perluas exporter, capture browser, dan worker desktop yang sudah ada. Helper layout murni dipakai bersama oleh ekspor dan verifier. Permintaan interaktif terikat pada job; pertahankan pemeriksaan origin/provenance dan pembatalan. Pustaka browser/Excel tidak diimpor ke proses GUI.

**Toolchain:** baseline tersinkron `main e99464a`: CPython produksi 3.11.17/GIL, uv 0.12.22, Tkinter stdlib, Playwright 1.63.0, openpyxl 3.1.5, pytest 9.1.1, dan lock dengan hash. Python 3.14.8 tetap profil kandidat. Tidak ada dependensi produksi baru.

**Spesifikasi:** [desain pemilihan SPT dan workbook](../specs/2026-10-12-period-selection-layout-design.md).

**Batas publikasi terbaru:** PR #6 mencakup Tugas 1 dan lanjutan Tugas 2: pemilihan SPT serta konfirmasi penggantian hasil desktop. Batas lama yang hanya mencakup Tugas 1 sudah digantikan. Implementasi Tugas 2 dan tesnya sudah tersedia; verifikasi menyeluruh pada commit implementasi masih menunggu CI. Tugas 3 (PDF), Tugas 4 (pengenalan autentikasi dan teks global), serta penerimaan fitur lengkap pada Tugas 5 tetap tertunda.

## Batas umum

- Pertahankan NPWP/ID, nilai sumber, dan baris duplikat secara persis; gunakan tes sintetis saja.
- Folder: `SPT Masa 21`, `SPT Masa Unifikasi`, `SPT Masa PPN`; satu workbook per masa sumber, dengan sheet Normal/Pembetulan terpisah.
- Form Badan memiliki sheet masing-masing. Rencana PDF hanya mengizinkan laporan keuangan yang sudah tersedia dan diperiksa sebagai aksi baca.
- Teks persis yang direncanakan pada Tugas 4, belum diterapkan: `jalankan proses sedot di background`; `Hasil Sedot berada di folder Downloads Windows`; `Coretax SPT downloader : kalau bisa ribet, kenapa dibikin gampang`.
- Jangan melonggarkan autentikasi, menebak aksi remote, meng-commit data privat, melakukan overwrite otomatis, atau menjalankan browser pada thread UI.
- Persyaratan awal rencana meminta persetujuan terpisah sebelum commit/push. Ikuti scope publikasi yang benar-benar diizinkan pengguna pada sesi terkait.

## Fokus review

- Dua masa atau jenis pajak yang tersanitasi menjadi path Windows sama harus ditolak sebelum penulisan.
- Caption form/pembetulan yang panjang tetap menghasilkan nama Excel unik dan tautan resume yang tepat. Path bagian lengkap membedakan form dengan nama akhir sama.
- Angka analisis harus dibandingkan dengan sumber sebelum pembulatan dapat menghilangkan bukti digit yang berbeda.
- Jawaban pemilihan tidak sah, duplikat, usang, atau lintas job tidak boleh mengambil record yang tidak dipilih.
- Tujuan yang terkunci, diganti, atau dialihkan symlink selama persetujuan/publikasi harus mempertahankan hasil lama dan data pemulihan.
- HTML, redirect origin asing, sesi kedaluwarsa, dan unduhan PDF yang dibatalkan tidak boleh ditampilkan sebagai PDF sah atau COMPLETE.

### Tugas 1: Layout workbook dan form untuk analisis

**Berkas:** `coretax_exporter.py`, `coretax.py`, `tests/test_split_output.py`, `tests/test_exporter.py`, serta `tests/test_period_layout.py`.

**Antarmuka:** `workbook_groups(run) -> dict[str, list[dict]]` menentukan path XLSX relatif. `record_sheet_titles(ordinal, record) -> list[str]` menentukan sheet per form; `detail_sheet_title(ordinal, record)` mengembalikan target pertama. Pertahankan `export_split_workbooks(run, folder) -> dict[str, Path]`. Verifier memakai helper yang sama dan tetap membaca ulang file yang dihasilkan.

- [x] Buat dan jalankan tes RED untuk file Januari/Februari/PPN, pembetulan dalam masa sama, sheet Induk/L1-D, benturan Windows, teks/duplikat, tabel, serta tautan.
- [x] Terapkan helper dan perbarui exporter, verifikasi, serta scope staging bersarang. Data field/tabel tidak digabung dalam sel; kolom numerik opsional memerlukan format dan presisi yang didukung.
- [x] Jalankan tes exporter/output; kontrak scope dan rollback tetap dipertahankan. Temuan review lanjutan harus ditutup dengan regresi sebelum merge.

### Tugas 2: Capture sesuai pilihan dan dialog overwrite

**Berkas:** modul `spt_desktop/interaction.py`, `app.py`, `controller.py`, `worker.py`, `output.py`, `runtime.py`; serta tes pemilihan, GUI, lifecycle, output, dan worker.

**Antarmuka:** event `selection_required` dan `overwrite_required` membawa `job_id`/`request_id`; data daftar dan jawaban berada dalam JSON privat milik job. GUI memakai `read_request(event)` dan `respond(kind, request_id, payload)`. `publish_workbooks(..., overwrite=False, expected_outputs=...)` mengikat persetujuan pada folder/file yang sudah diperiksa; default tetap menolak penggantian.

- [x] Buat/jalankan tes RED untuk detail sesuai pilihan, pilihan kosong, ID salah/duplikat, jawaban lintas job, Stop saat menunggu, penolakan/persetujuan overwrite, serta file di luar pilihan yang tetap utuh.
- [x] Terapkan request/reply terbatas dan dialog Tk pada thread utama; ambil rincian hanya untuk ID yang dikonfirmasi dan catat scope. Tampilkan folder/file penggantian, periksa ulang tujuan dan workbook lama, serta pertahankan salinan pemulihan saat publikasi gagal. Checkbox ini menyatakan kode tersedia, bukan hasil GREEN.
- [ ] Tuntaskan suite lifecycle, worker, selection, output, keamanan dalam mode Python teroptimasi, serta self-test source/frozen pada commit implementasi; catat run dan artifact yang tepat.

**Bukti RED pada runner Windows:**

| Run | Commit yang diuji |
| --- | --- |
| [38229426598](https://github.com/cepeter-job/spt-downloader/actions/runs/38229426598) | `9b49bb1f1d45ba3eda8f381d0aeaabb70cd5b1a7` |
| [38234647737](https://github.com/cepeter-job/spt-downloader/actions/runs/38234647737) | `4079ace06d3efbfc916f30a17df00bc9f36d1df4` |

Desktop tidak memilih semua SPT secara otomatis. Menutup pemilihan atau menekan Stop membatalkan pekerjaan; jawaban usang/duplikat/lintas job tidak mengesahkan pilihan. Dialog penggantian menunjukkan folder ekspor sebelumnya dan file yang berbenturan; persetujuan mengganti file Excel tersebut, sedangkan workbook masa lain tetap utuh. `resume.xlsx` baru mengindeks pilihan saat ini. CLI mempertahankan alur argumen/checkpoint yang terpisah dari dialog desktop.

### Tugas 3: Capture PDF laporan keuangan yang sudah tersedia

**Berkas:** rencana `coretax_attachments.py`, `coretax_browser.py`, rendering tautan exporter, manifest worker, allowlist `WORKER_FILES`, dan `tests/test_financial_attachments.py`.

**Antarmuka:** `download_financial_attachments(page, record, folder, check_cancel=None) -> list[dict]` menyimpan PDF tervalidasi dan metadata label/path relatif/status/byte/hash. Integrasi dilakukan sebelum halaman detail Badan yang diperiksa ditutup. Publisher menyertakan hanya PDF yang dideklarasikan dan tervalidasi bersama XLSX.

- [ ] Buat/jalankan tes browser/HTTP sintetis untuk href teramati, kontrol tak tersedia, origin/redirect/HTML asing, batas ukuran, pembatalan, dan path output.
- [ ] Terapkan unduhan GET dari tautan yang sudah ada; jangan menebak URL atau mengeklik pembuatan/submit dokumen. Pertahankan PARTIAL untuk kontrol belum didukung atau kegagalan.
- [ ] Verifikasi byte/hash PDF dan tautan relatif; perbarui allowlist resource dan tes build.

### Tugas 4: Pengenalan autentikasi dan teks UI

**Berkas:** `spt_desktop/auth.py`, `app.py`, `spt_gui.py`, `build_desktop.py`, serta tes autentikasi/branding/GUI.

**Antarmuka:** pertahankan `_login_fields`, binding kontrol, origin tepat, dan kepemilikan kredensial. Diagnostik alasan yang disanitasi serta penantian kondisi hanya ditambah bila didukung bukti; tidak ada data kredensial dalam diagnostik.

- [ ] Buat/jalankan fixture RED untuk kesiapan form asinkron dan caption/field yang dikenal, sambil tetap menolak challenge, field tambahan, serta aksi tak aman.
- [ ] Terapkan perbaikan pengenalan yang sempit dan teks yang disetujui; perbarui assertion self-test source/frozen.
- [ ] Jalankan suite autentikasi/binding/pembatalan dan GUI. Pengenalan portal live tetap belum terverifikasi sampai benar-benar diperiksa.

### Tugas 5: Penerimaan fitur lengkap, review, dan artifact

**Berkas:** kontrak output `AGENTS.md`, `README.md`, ekspektasi tes, artifact di luar repo, serta laporan penerimaan.

- [ ] Petakan seluruh sepuluh persyaratan ke tes yang dijalankan; perbarui dokumentasi sesuai kontrak yang disetujui.
- [ ] Jalankan seluruh pytest dengan basetemp scratch unik; periksa XLSX sintetis dan seluruh tautan/jumlah file.
- [ ] Dapatkan review kode/keamanan independen dan perbaiki temuan penting dengan tes regresi.
- [ ] Bangun executable Windows di luar repo, jalankan self-test source/frozen, verifikasi checksum artifact dan keamanan resource, lalu laporkan hasil serta batas penerimaan live.
- [ ] Sajikan diff dan commit sesuai scope yang diizinkan pengguna. PR #6 mencakup Tugas 1 dan lanjutan Tugas 2; penerimaan fitur lengkap tetap menunggu verifikasi akhir implementasi serta Tugas 3–4.
