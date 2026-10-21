# Panduan pengembangan UI/UX SPT Downloader

**Keputusan pemilik, 12 Oktober 2026:** gunakan desain **B**, pertahankan **Tkinter/ttk**, dan utamakan proses serta hasil yang mudah dipahami sebelum menambah fitur. Bahasa antarmuka harus terasa seperti petunjuk dari rekan kerja, bukan log mesin atau dokumen teknis.

Untuk fitur yang sudah ada, batas yang masih terbuka dan bukti per commit, gunakan
[baseline UI/UX 21 Oktober](baseline-2026-10-21.md). Halaman ini memegang arah desain
dan pemetaan Tkinter; pola interaksi, copy, dan checklist dipelihara di halaman
masing-masing. Snapshot dan laporan lama tetap menjadi sejarah, bukan persetujuan
untuk membangun ulang fitur atau memulihkan footer yang telah dihapus.

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

GUI tetap tipis dan hanya memperbarui widget pada thread utama. Browser, Excel
serta PDF berada di worker; controller mengesahkan status dan lokasi hasil.
Tata letak atau kata yang lebih ramah tidak boleh melemahkan validasi scope,
consent, tenggat, Stop, atau kepemilikan proses.

Rujukan rinci dipelihara pada satu pemilik topik:

- [Pola layar/status](pola-dan-status.md): input literal, search vs sort, fokus,
  keputusan dialog, COMPLETE/PARTIAL, dan Pengaturan dengan origin Satu tetap.
- [Kontrak backend](../arsitektur.md): identitas/provenance, exit code, sumber
  angka, workbook masa/model, PDF terverifikasi, resume dan rollback.
- [AGENTS.md](../../AGENTS.md): batas akses, privasi dan lingkungan eksekusi.

Selalu perbaiki mockup yang melanggar kontrak tersebut, bukan mengubah guard
agar cocok dengan mockup. Angka 99%, event sukses lama, metadata PDF atau
penutupan dialog tidak boleh ditafsirkan sebagai keberhasilan/consent baru.

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

Teks yang dikunci pemilik, `app.bugreport` dan larangan memulihkan `app.credit` mengikuti [panduan bahasa](bahasa-antarmuka.md#teks-khusus-yang-tidak-diganti). Aturan gaya umum tidak menghapus kata yang telah diminta dan dikontrak tes.

Setiap perubahan mencatat alasan, copy ID/layar terdampak, kondisi pemicu, sumber data, tindakan tombol, pemeriksaan yang dijalankan, dan bukti yang belum tersedia. Perbarui docs/aset bersama implementasi. Saat codebase berubah, pin commit dan periksa kembali App/controller/interaction/worker/output/runtime serta tes consent/teks.

## 7. Syarat sebelum implementasi

Mulai dari delta terhadap [baseline aktif](baseline-2026-10-21.md), lalu gunakan
[checklist fitur dan PR](checklist-fitur.md). Bedakan perubahan perilaku, copy,
layout dan bukti yang dibutuhkan; jangan meminta implementasi ulang tahap yang
sudah selesai. Perubahan dokumentasi tidak mengotorisasi merge atau deployment.

Batas eksekusi mengikuti [AGENTS.md](../../AGENTS.md#verification), prosedur setup
dan tes mengikuti [pengembangan](../pengembangan.md). Pemeriksaan dokumen/source
bukan bukti baru atas screenshot, aksesibilitas, performa atau akun nyata.
