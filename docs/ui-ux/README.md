# Panduan pengembangan UI/UX SPT Downloader

**Keputusan pemilik, 12 Oktober 2026:** gunakan desain **B**, pertahankan **Tkinter/ttk**, dan utamakan proses serta hasil yang mudah dipahami sebelum menambah fitur. Bahasa antarmuka harus terasa seperti petunjuk dari rekan kerja, bukan log mesin atau dokumen teknis.

**Pembaruan 13 Oktober 2026:** [spesifikasi implementasi B-TK-1](../superpowers/specs/2026-10-13-magicpath-b-tkinter-design.md) merekonsiliasi arah B dengan kode `be67f5153a07ce100048d67191a02ca1d0fca1db`. Pemilihan SPT, persetujuan penggantian, workbook per masa, PDF keuangan/auditan Badan yang didukung, dan teks khusus pemilik sudah ada pada baseline. Irisan 1 sudah diimplementasikan pada branch PR #12: katalog teks, state murni, shell ttk regular/compact, dan integrasi App/self-test. T1–T5 irisan 1 sudah diverifikasi: 719 tes Windows lulus pada commit produk `7aa2f095`, screenshot native sintetis ukuran regular/compact/minimum telah ditinjau, dan artifact frozen dibaca ulang beserta hash. PR #12 belum merged; penerimaan manusia dan tahap berikutnya tetap terpisah. Lihat [bukti tahap 1](../superpowers/reports/2026-10-13-ui-b-phase1-evidence.md). Peningkatan dialog/hasil/Pengaturan dan pengujian menyeluruh tahap berikutnya belum dianggap selesai. Paket B-copy-2 dan baseline `e99464a2…` adalah riwayat desain, bukan kontrak terbaru untuk area yang berubah.

## Mulai dari sini

| Kebutuhan | Baca |
| --- | --- |
| Menerapkan MagicPath B pada kode terbaru | [Spesifikasi B-TK-1: widget, state, dialog, dan 28 kriteria penerimaan](../superpowers/specs/2026-10-13-magicpath-b-tkinter-design.md) |
| Menulis judul, tombol, petunjuk, atau pesan gagal | [Bahasa antarmuka](bahasa-antarmuka.md) |
| Menambahkan layar atau mengubah proses dan hasil | [Pola layar dan status](pola-dan-status.md) |
| Menyiapkan fitur baru, review PR, dan pengujian | [Checklist dan template fitur](checklist-fitur.md) |

Pedoman ini melengkapi [AGENTS.md](../../AGENTS.md), [arsitektur](../arsitektur.md), dan panduan pengembangan repo. Jika mockup bertentangan dengan pemeriksaan keamanan atau kelengkapan data, perbaiki mockup, bukan melemahkan pemeriksaannya. Kode dan tes membuktikan perilaku baseline; perubahan yang sengaja diminta pemilik harus dicatat, bukan dihapus oleh desain lama.

## 1. Bentuk aplikasi yang dipilih

B adalah satu layar kerja, bukan wizard yang menambah halaman. Pengguna mengisi NPWP dan tahun pajak, lalu memilih **Mulai unduh**. Bagian proses menggantikan formulir ketika unduhan berjalan. Sesudah inventaris ditemukan, dialog meminta pilihan SPT secara eksplisit sebelum rincian diambil. Dialog penggantian muncul jika diperlukan sebelum publikasi. Tahap, ringkasan NPWP/tahun, dan hasil tetap mudah ditemukan pada jendela utama.

Pengaturan tetap dialog terpisah pada implementasi Tkinter. Pemilihan dan penggantian memakai dialog native yang sudah ada. Login, CAPTCHA, dan verifikasi tambahan tetap dilakukan di browser milik aplikasi. Jangan meniru form login portal di dalam aplikasi.

Pada jendela lebar, ringkasan berada di samping. Saat ruang menyempit, pindahkan ringkasan ke atas. Jangan menyembunyikan NPWP/tahun aktif, memperkecil teks agar semua muat, atau menambah navigasi hanya untuk meniru dashboard web. Gunakan gulir vertikal bila perlu.

**Belum termasuk:** antrean multi-NPWP, unduhan paralel, riwayat, resume GUI, pemilihan lokasi baru, dark mode, JSON-first capture, dan migrasi toolkit. Fitur tersebut memerlukan kebutuhan dan keputusan terpisah. Pemilihan SPT dan PDF yang sudah didukung bukan fitur baru dalam redesign ini.

## 2. Urutan prioritas

Pertama, pengguna harus tahu apa yang sedang berlangsung, kapan perlu bertindak, apakah hasilnya lengkap, dan apa yang bisa dilakukan setelah gagal. Kedua, rapikan formulir, dialog pemilihan/penggantian, Pengaturan, fokus keyboard, dan jendela kecil. Ketiga, ukur performa dan aksesibilitas pada Windows. Fitur baru dibahas setelah masalah penting pada alur tersebut ditutup.

Tampilan yang menarik tidak cukup untuk menyebut pekerjaan selesai. Ukuran keberhasilan desain: pengguna dapat menjalankan tugas dan menjelaskan hasilnya dengan benar, tanpa membaca dokumentasi developer.

## 3. Batas teknis yang harus tetap

GUI tetap tipis. Browser, pembuatan Excel, PDF, dan pembacaan data besar berada di worker, bukan callback Tk. Semua perubahan widget melalui thread GUI. Controller yang memutuskan apakah hasil sudah layak dinyatakan selesai; view hanya menyajikan hasil keputusan tersebut.

Jangan menukar status internal dengan terjemahan. `COMPLETE`, `PARTIAL`, `CANCELLED`, dan status login tetap kontrak kode. Teks seperti **Selesai** dan **Belum lengkap** hanya lapisan presentasi. Mengganti teks tidak boleh mengubah exit code, validasi `job_id`, `request_id`, cakupan, output path, atau aturan pembatalan.

NPWP tetap string 16 digit ASCII, termasuk nol awal. Tidak boleh di-trim, dibuang pemisahnya, atau diubah menjadi angka secara diam-diam. Tahun tetap empat digit dalam rentang 1900–2100. Inventaris mencakup SPT teramati; rincian hanya untuk ID yang dikonfirmasi. Pilihan awal kosong; perubahan filter mengosongkan pilihan. Nilai dan pembetulan dalam subset tetap literal dan terpisah sesuai sumber.

Penggantian membutuhkan keputusan untuk folder dan file yang ditampilkan. **Jangan ganti**, Escape, atau X pada dialog penggantian menolak penggantian; menutup dialog pemilihan membatalkan job. Jangan menyamakan kedua jalur atau menganggap timeout sebagai persetujuan. COMPLETE berlaku untuk pilihan saat ini dan cakupan yang didukung, bukan seluruh tahun.

Password hanya disimpan melalui Windows Credential Manager untuk situs login yang diizinkan. Hapus login tidak berarti menghapus akun Coretax. Cek login tidak mengunduh SPT. Sesi SSO atau pemeriksaan yang habis waktu tidak membuktikan password benar atau salah.

Syarat sukses tetap: terminal yang sah, exit code cocok, folder dan workbook valid, serta proses milik aplikasi selesai dibersihkan. Angka 99% bukan sukses. Pembatalan tidak berubah menjadi sukses karena event lama datang belakangan. PDF yang dinyatakan tersimpan harus memiliki byte/deklarasi/verifikasi yang sah, bukan metadata saja.

Excel masa memakai subfolder jenis pajak; Badan memakai sheet per form/pembetulan. Pertahankan seluruh hierarki dan tautan relatif. PDF keuangan/auditan Badan tertentu dapat ikut disimpan melalui tautan baca yang didukung; jangan mengatakan semua PDF dikecualikan atau semua lampiran tersedia.

Sumber kontrak: [arsitektur pada baseline](https://github.com/cepeter-job/spt-downloader/blob/be67f5153a07ce100048d67191a02ca1d0fca1db/docs/arsitektur.md), [App](https://github.com/cepeter-job/spt-downloader/blob/be67f5153a07ce100048d67191a02ca1d0fca1db/spt_desktop/app.py), dan [AGENTS.md](../../AGENTS.md).

## 4. Cara memetakan desain ke Tkinter/ttk

Gunakan `ttk.Entry`, `ttk.Combobox` readonly, `ttk.Checkbutton`, `ttk.Button`, `ttk.Progressbar`, `ttk.Treeview` dengan scrollbar, dan `Toplevel`. Pertahankan titlebar Windows asli. Jangan menggambar seluruh antarmuka di Canvas demi mengejar screenshot. Canvas boleh menjadi viewport bagi frame berisi widget native.

Kelompokkan pola berulang, bukan membuat abstraksi untuk setiap label. B-TK-1 memisahkan tanggung jawab state presentasi, katalog teks, style/layout, dan view. Pada irisan 1, `spt_desktop/ui_state.py`, `ui_copy.py`, `ui_theme.py`, dan `ui_views.py` sudah ditambahkan. Modul tersebut belum berarti semua pola/status tahap berikutnya selesai. Pertahankan `App(root, workspace, controller=None)` serta API consent controller. Jangan mengubah allowlist worker hanya untuk menambah teks GUI.

Katalog teks memakai ID stabil seperti `download.complete.title`, bukan teks itu sendiri sebagai key. Placeholder bernama, misalnya `{processed}`, `{total}`, dan `{verified}`, diperiksa sebelum format. Hindari merangkai potongan kalimat. Nilai tidak diketahui bukan nol. Jika event tidak menyediakan penyebab rinci, gunakan pesan generik yang aman, bukan menebak dari exception.

Tetap gunakan `after()` dan aliran event yang sudah ada. Jangan menambahkan loop menunggu, tidur, parsing workbook, atau proses browser pada callback. Polling baseline 100 ms dan queue 128 event bukan alasan merender ulang seluruh layar setiap event. Consent memakai pesan privat; daftar record tidak dipindahkan ke stdout. Referensi: [controller baseline](https://github.com/cepeter-job/spt-downloader/blob/be67f5153a07ce100048d67191a02ca1d0fca1db/spt_desktop/controller.py), [Tkinter 3.14](https://docs.python.org/3.14/library/tkinter.html#threading-model).

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

Target visual: teks biasa minimal 4,5:1, teks besar serta komponen/fokus relevan 3:1, pembesaran teks sampai 200%. Ini acuan desain, bukan sertifikat kepatuhan native. Rujukan: [WCAG 2.2](https://www.w3.org/TR/WCAG22/). Pengujian Windows mencakup keyboard, Narrator/NVDA, High Contrast, DPI antar-monitor, dan urutan fokus. Target geometry serta anggaran kinerja dijelaskan pada B-TK-1, belum dianggap hasil ukur.

## 6. Sumber desain dan pengelolaan revisi

[MagicPath B](https://designs.magicpath.ai/v1/warmly-meadow-4315), komponen `460285747178659840` revisi `460301118992445440`, menjadi acuan struktur visual. A/C adalah arsip perbandingan. Prototipe B tersebut belum memuat pemilihan/penggantian terbaru dan masih memiliki kalimat lama tentang semua masa/PDF; gunakan koreksi B-TK-1, bukan menurunkan perilaku produk agar cocok dengannya.

Figma/Penpot opsional, tidak menjadi syarat melanjutkan pekerjaan. Paket B-copy-2 dan 36 mockup adalah referensi historis yang perlu diselaraskan untuk layar terbaru. SVG bukan pengganti component instances atau binding; keberhasilan build prototipe bukan bukti aplikasi Tkinter sudah diuji.

Tiga teks khusus pemilik, subtitle, dan **Sedot SPT terpilih** dipertahankan sesuai [katalog](bahasa-antarmuka.md). Aturan gaya umum tidak boleh menghapus humor atau kata yang secara eksplisit diminta dan sudah dikontrak tes.

Setiap perubahan mencatat alasan, copy ID/layar terdampak, kondisi pemicu, sumber data, tindakan tombol, pemeriksaan yang dijalankan, dan bukti yang belum tersedia. Perbarui docs/aset bersama implementasi. Saat codebase berubah, pin commit dan periksa kembali App/controller/interaction/worker/output/runtime serta tes consent/teks.

## 7. Syarat sebelum implementasi

Arah B sudah dipilih; spesifikasi B-TK-1 tersedia untuk review. Setelah disetujui, buat rencana implementasi kecil per tahap. Perubahan dokumen bukan izin merge atau deployment otomatis.

Sesuai [AGENTS.md](../../AGENTS.md), pytest, product import, Tk/browser fixture, source/frozen self-test, build, dan EXE dijalankan hanya pada GitHub runner. Lokal hanya pemeriksaan dokumen/source/AST dan hash/metadata. Jangan mengubah CI/ruleset untuk mendapatkan GREEN. Bukti baseline Windows, aksesibilitas, performa, dan penerimaan manual tetap dibedakan dari pemeriksaan dokumentasi.

Permintaan PR #14 menghapus footer nama pribadi, bukan subtitle umum atau petunjuk Downloads. Katalog aktif memuat 43 ID; jangan mengembalikan `app.credit` dari rancangan historis.
