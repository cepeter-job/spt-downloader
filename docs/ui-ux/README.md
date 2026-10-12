# Panduan pengembangan UI/UX SPT Downloader

**Keputusan pemilik, 12 Oktober 2026:** gunakan desain **B**, pertahankan **Tkinter/ttk**, dan utamakan proses serta hasil yang mudah dipahami sebelum menambah fitur. Bahasa antarmuka harus terasa seperti petunjuk dari rekan kerja, bukan log mesin atau dokumen teknis.

Dokumen ini adalah pedoman desain untuk perubahan berikutnya. Persetujuan arah B tidak berarti seluruh redesign sudah diterapkan. Baseline kode yang ditinjau: `e99464a2b23c812acfaa4f39499cb5658dbc50c2`. Paket desain revisi **B-copy-2** memperbarui teks dan dokumentasi; kode aplikasi, protokol worker, CLI, dan format Excel tidak diubah.

## Mulai dari sini

| Kebutuhan | Baca |
| --- | --- |
| Menulis judul, tombol, petunjuk, atau pesan gagal | [Bahasa antarmuka](bahasa-antarmuka.md) |
| Menambahkan layar atau mengubah proses dan hasil | [Pola layar dan status](pola-dan-status.md) |
| Menyiapkan fitur baru, review PR, dan pengujian | [Checklist dan template fitur](checklist-fitur.md) |

Pedoman ini melengkapi `AGENTS.md`, `docs/arsitektur.md`, dan panduan pengembangan repo. Jika mockup bertentangan dengan pemeriksaan keamanan atau kelengkapan data, perbaiki mockup, bukan melemahkan pemeriksaannya.

## 1. Bentuk aplikasi yang dipilih

B adalah satu layar kerja, bukan wizard yang menambah halaman. Pengguna mengisi NPWP dan tahun pajak, lalu memilih **Mulai unduh**. Bagian proses menggantikan formulir ketika unduhan berjalan. Tahap yang sedang dikerjakan dan ringkasan NPWP/tahun tetap mudah ditemukan. Hasil muncul di tempat yang sama, dengan tindakan berikutnya yang jelas.

Pengaturan tetap merupakan dialog terpisah pada implementasi Tkinter. Login, CAPTCHA, dan verifikasi tambahan tetap dilakukan di browser milik aplikasi. Jangan meniru form login portal di dalam aplikasi.

Pada jendela lebar, ringkasan berada di samping. Saat ruang menyempit, pindahkan ringkasan ke atas. Jangan menyembunyikan NPWP/tahun aktif, memperkecil teks agar semua muat, atau menambah navigasi hanya untuk meniru dashboard web. Gunakan gulir vertikal bila perlu.

**Belum termasuk:** antrean multi-NPWP, unduhan paralel, riwayat, pemulihan otomatis dari data sementara, pemilihan lokasi baru, dark mode, dan migrasi toolkit. Fitur tersebut memerlukan kebutuhan dan keputusan terpisah. Tidak perlu memasang tombol kosong sebagai persiapan.

## 2. Urutan prioritas

Pertama, pengguna harus tahu apa yang sedang berlangsung, kapan perlu bertindak, apakah hasilnya lengkap, dan apa yang bisa dilakukan setelah gagal. Kedua, rapikan formulir, Pengaturan, fokus keyboard, dan jendela kecil. Ketiga, ukur performa dan aksesibilitas pada Windows. Fitur baru dibahas setelah masalah penting pada alur tersebut ditutup.

Tampilan yang menarik tidak cukup untuk menyebut pekerjaan selesai. Ukuran keberhasilan desain: pengguna dapat menjalankan tugas dan menjelaskan hasilnya dengan benar, tanpa membaca dokumentasi developer.

## 3. Batas teknis yang harus tetap

GUI tetap tipis. Browser, pembuatan Excel, dan pembacaan data besar berada di worker, bukan callback Tk. Semua perubahan widget melalui thread GUI. Controller yang memutuskan apakah hasil sudah layak dinyatakan selesai; view hanya menyajikan hasil keputusan tersebut.

Jangan menukar status internal dengan terjemahan. `COMPLETE`, `PARTIAL`, `CANCELLED`, dan status login tetap menjadi kontrak kode. Teks seperti **Selesai** dan **Belum lengkap** hanya lapisan presentasi. Mengganti teks tidak boleh mengubah exit code, validasi `job_id`, cakupan, output path, atau aturan pembatalan.

NPWP tetap string 16 digit ASCII, termasuk nol awal. Tidak boleh di-trim, dibuang pemisahnya, atau diubah menjadi angka secara diam-diam. Tahun tetap empat digit dalam rentang 1900–2100. Semua masa dan pembetulan yang ditemukan dalam cakupan didukung tetap disertakan. Label awam tidak mengubah arti istilah pajak atau nilai sumber.

Password hanya disimpan melalui Windows Credential Manager untuk situs login yang diizinkan. Hapus login tidak berarti menghapus akun Coretax. Cek login tidak mengunduh SPT. Sesi SSO atau pemeriksaan yang habis waktu tidak membuktikan password benar atau salah.

Syarat sukses tetap: terminal yang sah, exit code cocok, folder dan workbook valid, serta proses milik aplikasi selesai dibersihkan. Angka 99% bukan sukses. Pembatalan tidak berubah menjadi sukses hanya karena event lama datang belakangan.

Sumber kontrak: [arsitektur pada baseline](https://github.com/cepeter-job/spt-downloader/blob/e99464a2b23c812acfaa4f39499cb5658dbc50c2/docs/arsitektur.md) dan [AGENTS.md](https://github.com/cepeter-job/spt-downloader/blob/e99464a2b23c812acfaa4f39499cb5658dbc50c2/AGENTS.md).

## 4. Cara memetakan desain ke Tkinter/ttk

Gunakan widget standar yang sesuai: `ttk.Entry` untuk isian, `ttk.Combobox` readonly untuk pilihan terbatas, `ttk.Checkbutton`, `ttk.Button`, `ttk.Progressbar`, dan `Toplevel` untuk dialog. Pertahankan titlebar Windows asli. Jangan menggambar seluruh antarmuka di Canvas demi mengejar screenshot.

Kelompokkan pola berulang, bukan membuat abstraksi untuk setiap label. Usulan pemisahan saat implementasi: pemetaan event ke state tampilan, katalog teks, view unduhan, view hasil, dan dialog Pengaturan. Ini rancangan tanggung jawab, bukan klaim bahwa modul tersebut sudah ada. Jangan mengubah allowlist worker hanya untuk menambah teks di GUI.

Katalog teks sebaiknya memakai ID stabil seperti `download.complete.title`, bukan teks itu sendiri sebagai key. Placeholder bernama, misalnya `{processed}`, `{total}`, dan `{verified}`, harus diperiksa sebelum format. Hindari merangkai potongan kalimat karena urutan kata dapat berubah. Nilai tidak diketahui tampil sebagai **Belum diketahui**, bukan nol. Jika event tidak menyediakan penyebab rinci, gunakan pesan generik yang aman, bukan menebak dari raw exception.

Tetap gunakan `after()` dan aliran event yang sudah ada. Jangan menambahkan loop menunggu, tidur, operasi disk besar, atau proses browser pada callback. Polling baseline 100 ms dan queue 128 event adalah karakteristik kode yang ditinjau, bukan alasan untuk merender ulang seluruh layar pada setiap event. [Controller baseline](https://github.com/cepeter-job/spt-downloader/blob/e99464a2b23c812acfaa4f39499cb5658dbc50c2/spt_desktop/controller.py). Panduan event loop: [Tkinter](https://docs.python.org/3.11/library/tkinter.html#threading-model).

## 5. Fondasi visual

| Elemen | Acuan desain B |
| --- | --- |
| Tipografi Windows | Segoe UI atau Tk named fonts. Jangan membundel font dari aset desain. |
| Ukuran rancangan | Judul 24/32, subjudul 18/26, isi 14/22, catatan 12/18. Pemetaan ke point/DIP perlu diuji. |
| Spasi | 4, 8, 12, 16, 24, 32. |
| Kontrol | Tinggi rancangan 44 DIP, bukan kewajiban umum Windows. |
| Sudut | Kontrol 4, panel 8. Tampilan tema native lebih penting daripada kesamaan piksel mutlak. |
| Warna | Aksi `#0F6CBD`, teks `#182230`, teks sekunder `#526173`, peringatan `#854D0E`, gagal `#B42318`. |
| Fokus | Terlihat jelas, tidak hanya perubahan warna yang samar. High Contrast mengikuti warna sistem. |

Token adalah acuan yang dikelola bersama, bukan hex baru yang disalin bebas ke setiap layar. Inter pada pratinjau merupakan pengganti untuk renderer desain; tidak menjamin ukuran teks sama dengan Segoe UI. Jika label tidak muat, perbaiki kalimat atau layout, jangan memotong arti atau mengecilkan huruf.

Target visual menggunakan teks biasa minimal 4,5:1, teks besar 3:1, dan komponen/fokus yang relevan 3:1 sebagai acuan. Uji pembesaran teks sampai 200%. Ini acuan desain, bukan sertifikat kepatuhan aplikasi native. Rujukan: [WCAG 2.2](https://www.w3.org/TR/WCAG22/). Pengujian Windows tetap perlu keyboard, Narrator/NVDA, High Contrast, DPI antar-monitor, dan urutan fokus.

## 6. Sumber desain dan pengelolaan revisi

[MagicPath B](https://designs.magicpath.ai/v1/warmly-meadow-4315) untuk mencoba teks dan contoh keadaan. A/C adalah arsip perbandingan, bukan arah implementasi. [Figma](https://www.figma.com/design/8EU4fBz484JJLlLr08Im4d) masih berisi fondasi sebelumnya; sinkronisasi tambahan terakhir tertahan kuota MCP. Jangan menganggap teks Figma yang belum tersinkron sebagai versi terbaru.

Paket lokal B-copy-2 berisi 36 mockup, galeri, daftar perubahan teks, token, dan panduan ini. SVG adalah bahan review/import visual, bukan pengganti component instances, auto-layout, atau variable bindings. Build prototype yang berhasil juga bukan bukti aplikasi Tkinter sudah diuji.

Setiap perubahan mencatat: alasan, copy ID atau layar terdampak, kondisi pemicu, sumber data, tindakan tombol, pemeriksaan yang dijalankan, serta hasil yang belum dibuktikan. Perbarui dokumentasi dan aset dalam PR yang sama dengan implementasi nantinya. Jika persyaratan bertentangan, minta keputusan pemilik dan catat alasannya. Jangan membiarkan beberapa versi berbeda tanpa penanda mana yang aktif.

## 7. Syarat sebelum implementasi

Arah B sudah dipilih. Sebelum mengubah kode, tinjau teks revisi, aturan status dan checklist, lalu siapkan rencana implementasi kecil per tahap. Bukti Windows baseline, aksesibilitas, serta performa masih harus dikumpulkan. Perubahan desain ini tidak mengizinkan merge atau deployment otomatis.
