# Panduan pengembangan UI/UX SPT Downloader

**Keputusan pemilik, 12 Oktober 2026:** gunakan desain **B**, pertahankan **Tkinter/ttk**, dan utamakan proses serta hasil yang mudah dipahami sebelum menambah fitur. Bahasa antarmuka harus terasa seperti petunjuk dari rekan kerja, bukan log mesin atau dokumen teknis.

**Baseline aktif, 21 Oktober 2026:** perilaku produk dipin pada `main@ecbd9878aa732a379ba94ef848764f9815445003`, setelah PR #53 dan #58 merged. Mulai dari [baseline UI/UX 21 Oktober](baseline-2026-10-21.md). Shell B, dialog pemilihan/penggantian, konteks folder wajib, ID lengkap yang disorot, Alt+J, serta perbaikan waktu filter sudah diimplementasikan. Default desktop JSON-hybrid, saved DOM, login Satu, logging, pemisahan workbook masa/model dan PDF yang didukung tetap dipertahankan.

[Bukti Phase 2](../superpowers/reports/2026-10-20-ui-b-phase2-evidence.md) dan [bukti performa PR #58](../superpowers/reports/2026-10-21-phase2-performance-evidence.md) tetap dipin ke commit yang benar-benar diuji. Filter membaik, tetapi target opening 100 ms belum tercapai; P2-14 untuk ukuran normal/compact penuh pada 200% masih PARTIAL. Jangan menyamakan merge dengan sertifikasi aksesibilitas, penerimaan semua akun Coretax, atau deployment.

[Snapshot 20 Oktober sebelum Phase 2](baseline-2026-10-20.md), [spesifikasi B-TK-1](../superpowers/specs/2026-10-13-magicpath-b-tkinter-design.md), rencana tahap 1, dan [bukti T5](../superpowers/reports/2026-10-13-ui-b-phase1-evidence.md) adalah arsip keputusan/hasil. PR #12 sudah merged pada 13 Oktober. Angka 719 tes dan screenshot lama tidak mengesahkan perubahan berikutnya. Jangan memulihkan footer nama pribadi atau membangun ulang tahap yang sudah selesai.

## Mulai dari sini

| Kebutuhan | Baca |
| --- | --- |
| Menentukan fitur yang sudah ada dan pekerjaan berikutnya | [Baseline aktif 21 Oktober 2026](baseline-2026-10-21.md) |
| Meninjau hasil dialog dan performa | [Phase 2](../superpowers/reports/2026-10-20-ui-b-phase2-evidence.md) dan [PR #58: angka serta batas ukur](../superpowers/reports/2026-10-21-phase2-performance-evidence.md) |
| Menelusuri alasan desain tahap 1 | [Spesifikasi B-TK-1 historis](../superpowers/specs/2026-10-13-magicpath-b-tkinter-design.md); rekonsiliasi dahulu dengan baseline aktif |
| Menulis judul, tombol, petunjuk, atau pesan gagal | [Bahasa antarmuka](bahasa-antarmuka.md) |
| Menambahkan layar atau mengubah proses dan hasil | [Pola layar dan status](pola-dan-status.md) |
| Menyiapkan fitur baru, review PR, dan pengujian | [Checklist dan template fitur](checklist-fitur.md) |

Pedoman ini melengkapi [AGENTS.md](../../AGENTS.md), [arsitektur](../arsitektur.md), dan panduan pengembangan repo. Jika mockup bertentangan dengan pemeriksaan keamanan atau kelengkapan data, perbaiki mockup, bukan melemahkan pemeriksaannya. Kode dan tes membuktikan perilaku baseline; perubahan yang sengaja diminta pemilik harus dicatat, bukan dihapus oleh desain lama.

## 1. Bentuk aplikasi yang dipilih

B adalah satu layar kerja, bukan wizard yang menambah halaman. Pengguna mengisi NPWP dan tahun pajak, lalu memilih **Mulai unduh**. Bagian proses menggantikan formulir ketika unduhan berjalan. Sesudah inventaris ditemukan, dialog meminta pilihan SPT secara eksplisit sebelum rincian diambil. Dialog penggantian muncul jika diperlukan sebelum publikasi. Tahap, ringkasan NPWP/tahun, dan hasil tetap mudah ditemukan pada jendela utama.

Pengaturan tetap dialog terpisah pada implementasi Tkinter. Pemilihan dan penggantian memakai dialog native yang sudah ada. Login, CAPTCHA, dan verifikasi tambahan tetap dilakukan di browser milik aplikasi. Jangan meniru form login portal di dalam aplikasi.

Pada jendela lebar, ringkasan berada di samping. Saat ruang menyempit, pindahkan ringkasan ke atas. Jangan menyembunyikan NPWP/tahun aktif, memperkecil teks agar semua muat, atau menambah navigasi hanya untuk meniru dashboard web. Gunakan gulir vertikal bila perlu.

**Belum termasuk:** antrean multi-NPWP, unduhan paralel, riwayat, resume GUI, pemilihan lokasi baru, dark mode, dan migrasi toolkit. Fitur tersebut memerlukan kebutuhan dan keputusan terpisah. Pemilihan SPT dan PDF yang sudah didukung bukan fitur baru dalam redesign ini. **Sudah tersedia:** pilihan sumber detail `DOM` / `JSON-hybrid (pilot)`. Profil desktop baru atau preferensi sumber yang hilang/tidak sah memakai `json-first`; nilai sah yang tersimpan, termasuk DOM, dipertahankan. Default CLI/library tanpa opsi tetap DOM. Mode ini bukan janji semua format selalu memakai JSON atau lebih cepat.

## 2. Urutan prioritas

Pertama, pengguna harus tahu apa yang sedang berlangsung, kapan perlu bertindak, apakah hasilnya lengkap, dan apa yang bisa dilakukan setelah gagal. Kedua, rapikan formulir, dialog pemilihan/penggantian, Pengaturan, fokus keyboard, dan jendela kecil. Ketiga, ukur performa dan aksesibilitas pada Windows. Fitur baru dibahas setelah masalah penting pada alur tersebut ditutup.

Tampilan yang menarik tidak cukup untuk menyebut pekerjaan selesai. Ukuran keberhasilan desain: pengguna dapat menjalankan tugas dan menjelaskan hasilnya dengan benar, tanpa membaca dokumentasi developer.

## 3. Batas teknis yang harus tetap

GUI tetap tipis. Browser, pembuatan Excel, PDF, dan pembacaan data besar berada di worker, bukan callback Tk. Semua perubahan widget melalui thread GUI. Controller yang memutuskan apakah hasil sudah layak dinyatakan selesai; view hanya menyajikan hasil keputusan tersebut.

Jangan menukar status internal dengan terjemahan. `COMPLETE`, `PARTIAL`, `CANCELLED`, dan status login tetap kontrak kode. Teks seperti **Selesai** dan **Belum lengkap** hanya lapisan presentasi. Mengganti teks tidak boleh mengubah exit code, validasi `job_id`, `request_id`, cakupan, output path, atau aturan pembatalan.

NPWP tetap string 16 digit ASCII, termasuk nol awal. Tidak boleh di-trim, dibuang pemisahnya, atau diubah menjadi angka secara diam-diam. Tahun tetap empat digit dalam rentang 1900–2100. Inventaris mencakup SPT teramati; rincian hanya untuk ID yang dikonfirmasi. Pilihan awal kosong; perubahan pencarian mengosongkan pilihan. Klik header Jenis pajak hanya mengubah urutan tampilan dan mempertahankan pilihan/fokus; ID konfirmasi tetap menurut urutan inventaris asli. Nilai dan pembetulan dalam subset tetap literal dan terpisah sesuai sumber.

Penggantian membutuhkan keputusan untuk folder dan file yang ditampilkan. **Jangan ganti**, Escape, atau X pada dialog penggantian menolak penggantian; menutup dialog pemilihan membatalkan job. Jangan menyamakan kedua jalur atau menganggap timeout sebagai persetujuan. COMPLETE berlaku untuk pilihan saat ini dan cakupan yang didukung, bukan seluruh tahun.

Password hanya disimpan melalui Windows Credential Manager pada `LOGIN_ORIGIN` Satu yang tetap. Pengguna tidak memilih origin; jangan mengembalikan combobox URL dari rancangan lama. Hapus login tidak berarti menghapus akun Coretax. Cek login tidak mengunduh SPT. Sesi SSO atau pemeriksaan yang habis waktu tidak membuktikan password benar atau salah.

Syarat sukses tetap: terminal yang sah, exit code cocok, folder dan workbook valid, serta proses milik aplikasi selesai dibersihkan. Angka 99% bukan sukses. Pembatalan tidak berubah menjadi sukses karena event lama datang belakangan. PDF yang dinyatakan tersimpan harus memiliki byte/deklarasi/verifikasi yang sah, bukan metadata saja.

Setiap jenis pajak memakai workbook per masa/tahun sumber dan **Model SPT literal**. Normal, Pembetulan 1, Pembetulan 2, dan model berikutnya tidak berbagi workbook; lembar di dalamnya hanya form/tab model tersebut. Jenis Masa tetap memakai subfoldernya; Badan memakai `SPT_Badan_<period>_<model>.xlsx`. Pertahankan nilai sumber, seluruh hierarki, dan tautan relatif. Jangan menggabungkan model melalui label sorting yang dinormalisasi, atau menulis ulang/menghapus export gabungan lama secara diam-diam.

`resume.xlsx` tetap memuat Ringkasan/Daftar SPT/Audit. Pada publikasi ke folder yang sudah ada, backend memverifikasi workbook lama dan membuat indeks folder gabungan untuk hasil sah yang dipertahankan serta hasil baru. Ini berbeda dari cakupan COMPLETE job saat ini yang tetap subset terpilih; indeks bukan bukti semua file lama diunduh ulang. Penolakan overwrite mempertahankan hasil lama termasuk resume. PDF keuangan/auditan Badan tertentu dapat ikut disimpan melalui tautan baca yang didukung; jangan mengatakan semua PDF dikecualikan atau semua lampiran tersedia.

Sumber kontrak: [arsitektur pada baseline](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/docs/arsitektur.md), [App](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/spt_desktop/app.py), dan [AGENTS.md](../../AGENTS.md).

## 4. Cara memetakan desain ke Tkinter/ttk

Gunakan `ttk.Entry`, `ttk.Combobox` readonly, `ttk.Checkbutton`, `ttk.Button`, `ttk.Progressbar`, `ttk.Treeview` dengan scrollbar, dan `Toplevel`. Pertahankan titlebar Windows asli. Jangan menggambar seluruh antarmuka di Canvas demi mengejar screenshot. Canvas boleh menjadi viewport bagi frame berisi widget native.

Kelompokkan pola berulang, bukan membuat abstraksi untuk setiap label. B-TK-1 memisahkan tanggung jawab state presentasi, katalog teks, style/layout, dan view. Pada irisan 1, `spt_desktop/ui_state.py`, `ui_copy.py`, `ui_theme.py`, dan `ui_views.py` sudah ditambahkan. Modul tersebut belum berarti semua pola/status tahap berikutnya selesai. Pertahankan `App(root, workspace, controller=None)` serta API consent controller. Jangan mengubah allowlist worker hanya untuk menambah teks GUI.

Katalog teks memakai ID stabil seperti `download.complete.title`, bukan teks itu sendiri sebagai key. Placeholder bernama, misalnya `{processed}`, `{total}`, dan `{verified}`, diperiksa sebelum format. Hindari merangkai potongan kalimat. Nilai tidak diketahui bukan nol. Jika event tidak menyediakan penyebab rinci, gunakan pesan generik yang aman, bukan menebak dari exception.

Tetap gunakan `after()` dan aliran event yang sudah ada. Jangan menambahkan loop menunggu, tidur, parsing workbook, atau proses browser pada callback. Polling baseline 100 ms dan queue 128 event bukan alasan merender ulang seluruh layar setiap event. Consent memakai pesan privat; daftar record tidak dipindahkan ke stdout. Referensi: [controller baseline](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/spt_desktop/controller.py), [Tkinter 3.14](https://docs.python.org/3.14/library/tkinter.html#threading-model).

## 5. Fondasi visual

| Elemen | Acuan desain B |
| --- | --- |
| Tipografi Windows | Segoe UI atau Tk named fonts. Jangan membundel font dari aset desain. |
| Ukuran rancangan | Judul 24/32, subjudul 18/26, isi 14/22, catatan 12/18; pemetaan point/DIP diuji. |
| Spasi | 4, 8, 12, 16, 24, 32 DIP. |
| Kontrol | Sasaran 40–44 DIP, mengikuti tinggi font dan padding native. |
| Sudut | Kontrol 4, panel 8; tema native lebih penting daripada kesamaan piksel mutlak. |
| Warna | Aksi `#0F6CBD`, teks `#182230`, sekunder `#526173`, peringatan `#854D0E`, gagal `#B42318`. |
| Fokus | Terlihat jelas; High Contrast mengikuti warna sistem. |

Token adalah acuan bersama, bukan hex baru yang disalin bebas. Inter pada pratinjau tidak menjamin metrik sama dengan Segoe UI. Jika label tidak muat, perbaiki layout, bukan mengecilkan huruf atau memotong arti. Teks khusus pemilik tetap utuh dan boleh membungkus.

Target visual: teks biasa minimal 4,5:1, teks besar serta komponen/fokus relevan 3:1, pembesaran teks sampai 200%. Ini acuan desain, bukan sertifikat kepatuhan native. Rujukan: [WCAG 2.2](https://www.w3.org/TR/WCAG22/). Pengujian Windows mencakup keyboard, Narrator/NVDA, High Contrast, DPI antar-monitor, dan urutan fokus. Target geometry serta anggaran kinerja tetap dibedakan dari hasil ukur. PR #58 menyediakan bukti sintetis filter, opening, cancellation dan screenshot; full-size 200%, pembaca layar serta High Contrast belum dinyatakan diterima.

## 6. Sumber desain dan pengelolaan revisi

[MagicPath B](https://designs.magicpath.ai/v1/warmly-meadow-4315), komponen `460285747178659840` revisi `460301118992445440`, menjadi acuan struktur visual. A/C adalah arsip perbandingan. Prototipe B tersebut belum memuat pemilihan/penggantian terbaru dan masih memiliki kalimat lama tentang semua masa/PDF; gunakan koreksi B-TK-1, bukan menurunkan perilaku produk agar cocok dengannya.

Figma/Penpot opsional, tidak menjadi syarat melanjutkan pekerjaan. Paket B-copy-2 dan 36 mockup adalah referensi historis yang perlu diselaraskan untuk layar terbaru. SVG bukan pengganti component instances atau binding; keberhasilan build prototipe bukan bukti aplikasi Tkinter sudah diuji.

Lima teks pemilik lama yang masih berlaku serta `app.bugreport` dipertahankan sesuai [katalog](bahasa-antarmuka.md). Footer nama pribadi `app.credit` sudah dihapus, bukan diminta kembali. Aturan gaya umum tidak boleh menghapus humor atau kata yang secara eksplisit diminta dan sudah dikontrak tes.

Setiap perubahan mencatat alasan, copy ID/layar terdampak, kondisi pemicu, sumber data, tindakan tombol, pemeriksaan yang dijalankan, dan bukti yang belum tersedia. Perbarui docs/aset bersama implementasi. Saat codebase berubah, pin commit dan periksa kembali App/controller/interaction/worker/output/runtime serta tes consent/teks.

## 7. Syarat sebelum implementasi

Arah B dan fondasi tahap 1 sudah diselesaikan melalui PR #12; dialog Phase 2 dan perbaikan filter sudah merged melalui PR #53/#58. Untuk tahap berikutnya, tulis delta terhadap [baseline aktif](baseline-2026-10-21.md), bedakan fitur existing dari usulan, lalu minta review desain dan susun rencana kecil. Jangan meminta implementasi ulang tahap 1 atau menyatakan seluruh tahap selanjutnya selesai karena fitur sejenis sudah ada. Perubahan dokumen bukan izin merge atau deployment otomatis.

Sesuai [AGENTS.md](../../AGENTS.md), pytest, product import, Tk/browser fixture, source/frozen self-test, build, dan EXE dijalankan hanya pada GitHub runner. Lokal hanya pemeriksaan dokumen/source/AST dan hash/metadata. Jangan mengubah CI/ruleset untuk mendapatkan GREEN. Bukti baseline Windows, aksesibilitas, performa, dan penerimaan manual tetap dibedakan dari pemeriksaan dokumentasi.

Permintaan PR #14 menghapus footer nama pribadi, bukan subtitle umum atau petunjuk Downloads. Katalog aktif pada commit yang dipin memuat 54 ID termasuk `app.bugreport`; jumlah ID adalah metadata baseline, bukan jumlah kontrol yang dirender. Jangan mengembalikan `app.credit` dari rancangan historis.
