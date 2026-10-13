# Rencana implementasi pemilihan SPT dan workbook per masa

> **Untuk agen pengembang:** gunakan `superpowers:subagent-driven-development` atau `superpowers:executing-plans` untuk menjalankan tugas berurutan. Checklist mencatat status, bukan menggantikan bukti pengujian.

**Tujuan lengkap rancangan:** menerapkan sepuluh revisi downloader yang diminta, mencakup ekspor sesuai scope, pemilihan/overwrite dengan persetujuan eksplisit, PDF yang aman, serta perilaku Windows yang dapat diverifikasi.

**Arsitektur:** perluas exporter, capture browser, dan worker desktop yang sudah ada. Helper layout murni dipakai bersama oleh ekspor dan verifier. Permintaan interaktif terikat pada job; pertahankan pemeriksaan origin/provenance dan pembatalan. Pustaka browser/Excel tidak diimpor ke proses GUI.

**Toolchain:** baseline desain awal `main e99464a` memakai produksi 3.11.17/GIL dan kandidat 3.14.8; bukti historis dua profil di bawah tetap dipertahankan. Pada head terverifikasi `3cc500e49764b4daa4ad11fcfbcdf8891ee62377`, produksi GUI/worker sudah CPython 3.14.8 x64/GIL. Pin aktual mengikuti `PYTHON_PROFILES` dan lock berhash; tidak ada dependensi produksi baru untuk Tugas 3–4.

**Spesifikasi:** [desain pemilihan SPT dan workbook](../specs/2026-10-12-period-selection-layout-design.md).

**Batas publikasi terbaru:** PR #6 mencakup Tugas 1–2. Tugas 3–4 dan follow-up PDF terverifikasi pada head produk `89a3830d65bae04660f90d75992f06c78003088f` di draft PR #8; PR belum digabung. Setelah publikasi lima dokumen awal, Tugas 5 dibuka kembali untuk temuan base/konteks dokumen PDF yang belum tercakup. Pengguna mengizinkan regresi/perbaikan PDF di PR #8; RED 5 kegagalan diperbaiki menjadi GREEN 608 tes. Laporan penerimaan dikoreksi terhadap bukti baru. Tidak ada izin merge atau publikasi pilot; penerimaan portal live belum terbukti. Lihat [matriks penerimaan dan artifact](../reports/2026-10-13-feature-acceptance.md).

## Batas umum

- Pertahankan NPWP/ID, nilai sumber, dan baris duplikat secara persis; gunakan tes sintetis saja.
- Folder: `SPT Masa 21`, `SPT Masa Unifikasi`, `SPT Masa PPN`; satu workbook per masa sumber, dengan sheet Normal/Pembetulan terpisah.
- Form Badan memiliki sheet masing-masing. Implementasi PDF hanya mengizinkan laporan keuangan/auditan yang sudah tersedia dan diperiksa sebagai aksi baca; byte, hash, scope dan deklarasi publikasinya diverifikasi.
- Tiga teks Tugas 4 sudah diterapkan dan di-attest source/frozen: `jalankan proses sedot di background`; `Hasil Sedot berada di folder Downloads Windows`; `Coretax SPT downloader : kalau bisa ribet, kenapa dibikin gampang`. Teks Downloads menggantikan hint lama; header nyata diperiksa terpisah dari caption OS.
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

**Berkas:** modul `spt_desktop/interaction.py`, `app.py`, `controller.py`, `worker.py`, `output.py`, `output_windows.py`, `runtime.py`; serta tes pemilihan, GUI, lifecycle, output, dan worker.

**Antarmuka:** event `selection_required` dan `overwrite_required` membawa `job_id`/`request_id`; data daftar dan jawaban berada dalam JSON privat milik job. GUI memakai `read_request(event)` dan `respond(kind, request_id, payload)`. `publish_workbooks(..., overwrite=False, expected_outputs=...)` mengikat persetujuan pada folder/file yang sudah diperiksa; default tetap menolak penggantian.

- [x] Buat/jalankan tes RED untuk detail sesuai pilihan, pilihan kosong, ID salah/duplikat, jawaban lintas job, Stop saat menunggu, penolakan/persetujuan overwrite, serta file di luar pilihan yang tetap utuh.
- [x] Terapkan request/reply terbatas dan dialog Tk pada thread utama; ambil rincian hanya untuk ID yang dikonfirmasi dan catat scope. Tampilkan folder/file penggantian, periksa ulang tujuan dan workbook lama, serta pertahankan salinan pemulihan saat publikasi gagal.
- [x] Tuntaskan suite lifecycle, worker, selection, dan output, termasuk regresi verifikasi workbook pada Python `-O`, serta self-test source/frozen pada commit implementasi; catat run dan artifact yang tepat.

**Bukti RED pada runner Windows:**

| Run | Head PR | Kegagalan yang direproduksi |
| --- | --- | --- |
| [38229426598](https://github.com/cepeter-job/spt-downloader/actions/runs/38229426598) | `9b49bb1f1d45ba3eda8f381d0aeaabb70cd5b1a7` | Dialog pemilihan/penggantian belum tersedia. |
| [38234647737](https://github.com/cepeter-job/spt-downloader/actions/runs/38234647737) | `4079ace06d3efbfc916f30a17df00bc9f36d1df4` | Regresi tambahan pemilihan, lifecycle, dan overwrite sebelum integrasi. |
| [38236203384](https://github.com/cepeter-job/spt-downloader/actions/runs/38236203384) | `28d2b0db9fc3f593f12287a3b424684efa806552` | Empat kegagalan mutasi output saat publikasi. |
| [38238540703](https://github.com/cepeter-job/spt-downloader/actions/runs/38238540703) | `3c8f57da41e7d70e9dc150a32040486130c0be05` | 26 kegagalan publikasi awal Windows akibat mode berbagi direktori. |

**Bukti GREEN Tugas 2:** [38239213602](https://github.com/cepeter-job/spt-downloader/actions/runs/38239213602). CI menguji commit merge `6b188802eb1a859dba654c1601a487110ba3a8e7`, dengan tree `091ebdad6d2626483a8d9bc1a9ab9605610074c6` yang identik dengan head PR `92e4af8e275c6ba4228374f4fadc48b1e22628a6`.

| Profil | Suite Windows | Suite portable |
| --- | --- | --- |
| Produksi — CPython 3.11.17 | 492 lulus (112,23 detik) | 339 lulus; 153 deselected |
| Kandidat — CPython 3.14.8 | 491 lulus, 1 dilewati (107,35 detik) | 339 lulus; 153 deselected |

Satu tes cache tar native yang dipakai bersama dilewati pada kandidat dan dijalankan pada produksi. Persiapan worker baru, pemakaian ulang runtime, self-test source/frozen, packaging, dan pembacaan kembali artifact berdasarkan ID persis lulus pada kedua profil.

| Profil | Artifact ID | Nama artifact |
| --- | --- | --- |
| Produksi — CPython 3.11.17 | [11742506238](https://github.com/cepeter-job/spt-downloader/actions/runs/38239213602/artifacts/11742506238) | `SPTDownloader-Windows-x64-6b188802eb1a859dba654c1601a487110ba3a8e7-python3.11.17` |
| Kandidat — CPython 3.14.8 | [11741819154](https://github.com/cepeter-job/spt-downloader/actions/runs/38239213602/artifacts/11741819154) | `SPTDownloader-Windows-x64-6b188802eb1a859dba654c1601a487110ba3a8e7-python3.14.8` |

Kedua artifact juga diunduh ulang dan diperiksa secara independen: digest ZIP dari GitHub, seluruh checksum payload, tepat lima berkas distribusi, serta pemeriksaan frozen, resource, dan README cocok. [Laporan audit 11742525416](https://github.com/cepeter-job/spt-downloader/actions/runs/38239213602/artifacts/11742525416) dibaca kembali: 45 dependensi, 0 kerentanan, 0 dilewati. Run di atas berlaku untuk commit implementasi yang disebutkan. Status commit penutupan dokumentasi dan head terbaru dicatat pada [pemeriksaan PR #6](https://github.com/cepeter-job/spt-downloader/pull/6/checks).

Desktop tidak memilih semua SPT secara otomatis. Menutup pemilihan atau menekan Stop membatalkan pekerjaan; jawaban usang/duplikat/lintas job tidak mengesahkan pilihan. Dialog penggantian menunjukkan folder ekspor sebelumnya dan file yang berbenturan; persetujuan mengganti file Excel tersebut, sedangkan workbook masa lain tetap utuh. `resume.xlsx` baru mengindeks pilihan saat ini. CLI mempertahankan alur argumen/checkpoint yang terpisah dari dialog desktop.

### Tugas 3: Capture PDF laporan keuangan yang sudah tersedia

**Berkas:** rencana `coretax_attachments.py`, `coretax_browser.py`, rendering tautan exporter, manifest worker, allowlist `WORKER_FILES`, dan `tests/test_financial_attachments.py`.

**Antarmuka:** `download_financial_attachments(page, record, folder, check_cancel=None) -> list[dict]` menyimpan PDF tervalidasi dan metadata label/path relatif/status/byte/hash. Integrasi dilakukan sebelum halaman detail Badan yang diperiksa ditutup. Publisher menyertakan hanya PDF yang dideklarasikan dan tervalidasi bersama XLSX.

- [x] Buat/jalankan tes browser/HTTP sintetis untuk href teramati, kontrol tak tersedia, origin/redirect/HTML asing, batas ukuran, pembatalan, dan path output.
- [x] Terapkan unduhan GET dari tautan yang sudah ada; jangan menebak URL atau mengeklik pembuatan/submit dokumen. Pertahankan PARTIAL untuk kontrol belum didukung atau kegagalan.
- [x] Verifikasi byte/hash PDF dan tautan relatif; perbarui allowlist resource dan tes build. Exact GREEN `a6d76eb7fca24be80c438efd2b1e456bceacf9b5`, run `38338852350`, 563 tes Windows; suite terbaru kembali menjalankan seluruh kontrak PDF. Bukti lengkap ada pada laporan penerimaan.

Follow-up base/konteks PDF: test-only `925d29c184e5690e3dc50db940906443ffc9d244`, run `38359524325`, mereproduksi lima kegagalan sebelum perbaikan. Perbaikan satu modul direview dan dipublikasikan pada `89a3830d65bae04660f90d75992f06c78003088f`; run `38360875900` lulus 608 tes Windows dan 367 portable/241 deselected. Capture memakai href native browser sambil mempertahankan guard mentah, pemeriksaan selected-record sebelum GET, dan binding lokasi pada JS pre-fetch.

### Tugas 4: Pengenalan autentikasi dan teks UI

**Berkas:** `spt_desktop/auth.py`, `app.py`, `spt_gui.py`, `build_desktop.py`, serta tes autentikasi/branding/GUI.

**Antarmuka:** pertahankan `_login_fields`, binding kontrol, origin tepat, dan kepemilikan kredensial. Diagnostik alasan yang disanitasi serta penantian kondisi hanya ditambah bila didukung bukti; tidak ada data kredensial dalam diagnostik.

- [x] Buat/jalankan fixture RED untuk kesiapan form asinkron dan caption/field yang dikenal, sambil tetap menolak challenge, field tambahan, serta aksi tak aman.
- [x] Terapkan perbaikan pengenalan yang sempit dan teks yang disetujui; perbarui assertion self-test source/frozen. Empat kontrak tambahan header nyata/hint/mutasi terbukti RED pada `02a0d5e016900010e11efb7bf14d79f4eacba91d`, run `38352112259`.
- [x] Jalankan suite autentikasi/binding/pembatalan dan GUI. Head `3cc500e49764b4daa4ad11fcfbcdf8891ee62377`, run `38353364106`, lulus 600 tes Windows/367 portable; source/frozen dan artifact `11791354479` terverifikasi. Pengenalan portal live tetap belum terverifikasi sampai benar-benar diperiksa.

### Tugas 5: Penerimaan fitur lengkap, review, dan artifact

**Berkas:** kontrak output `AGENTS.md`, `README.md`, ekspektasi tes, artifact di luar repo, serta laporan penerimaan.

- [x] Petakan seluruh sepuluh persyaratan ke node inventaris suite yang dijalankan; dokumentasi diperbarui sebagai draft lokal sesuai kontrak yang disetujui.
- [x] Jalankan seluruh pytest pada GitHub runner dengan basetemp di luar repo; kontrak menulis/membuka ulang XLSX sintetis serta memeriksa tautan/jumlah file. Tidak ada pytest/product import/Tk/browser/build/EXE lokal untuk verifikasi ini.
- [x] Review awal 12 modul produksi dilakukan, namun melewatkan catatan P2 base/konteks. Temuan tersebut direproduksi dengan delapan regresi, diperbaiki setelah RED, dan perbaikan direview `deleg_f9e2a38f` sebelum GREEN. Dugaan dot-segment yang berbeda tetap NotBug. ACL server/keaslian isi PDF bukan jaminan downloader.
- [x] Bangun executable Windows pada runner, jalankan self-test source/frozen, verifikasi artifact ID `11794902211`, lima berkas/empat checksum manifest/17 resource eksplisit, lalu laporkan batas penerimaan live pada laporan penerimaan. Head/merge tree terbaru sama: `6f4e913372904b9142d40e84bf017df0063c79fa`.
- [x] Review dokumentasi independen PASS (`deleg_8c9b98c1`), diff disajikan, dan pengguna menyetujui commit/push lima dokumen Task 5 saja. Jangan merge/auto-merge. Izin ini tidak mencakup publikasi pilot JSON-first; implementasi pilot sebagai alternatif DOM tetap mengikuti urutan setelah penutupan Tugas 5.
