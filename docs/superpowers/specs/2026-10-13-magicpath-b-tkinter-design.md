# Spesifikasi implementasi MagicPath B → Tkinter/ttk

**Penyesuaian konsolidasi, 13 Oktober 2026:** permintaan PR #14 menghapus footer nama pribadi dan ID `app.credit`; subtitle umum serta lima teks terkunci lainnya tetap. Katalog aktif berisi 43 ID. SPT kini hanya berisi worksheet form; Ringkasan/Daftar SPT/Audit berada di `resume.xlsx`. Resume boleh diganti otomatis setelah verifikasi, sedangkan SPT/PDF tetap meminta persetujuan.

**Proyek:** `cepeter-job/spt-downloader`  
**Revisi:** B-TK-1 · 13 Oktober 2026  
**Baseline kode:** `be67f5153a07ce100048d67191a02ca1d0fca1db` (`main` setelah konsolidasi PR #8)  
**Baseline visual:** MagicPath komponen `460285747178659840`, revisi `460301118992445440`, `warmly-meadow-4315`  
**Status:** spesifikasi untuk review. Arah B dan Tkinter/ttk sudah dipilih; dokumen ini tidak menyatakan implementasi, penerimaan Windows, merge, atau deployment sudah dilakukan.

[Prototipe B](https://designs.magicpath.ai/v1/warmly-meadow-4315) · [Kode yang ditinjau](https://github.com/cepeter-job/spt-downloader/tree/be67f5153a07ce100048d67191a02ca1d0fca1db) · [Panduan UI/UX](../../ui-ux/README.md)

## 1. Keputusan implementasi

Gunakan struktur visual B: satu jendela kerja dengan header, empat penanda tahap, area formulir/proses/hasil, ringkasan pekerjaan, dan footer. Gunakan widget Tkinter/ttk yang sebenarnya, bukan React, webview, atau gambar SVG sebagai antarmuka interaktif. Pengaturan serta persetujuan pemilihan/penggantian tetap dialog terpisah.

**Jangan menyalin perilaku prototipe secara harfiah.** Kode sudah lebih maju: pengguna memilih SPT setelah inventaris dibaca, penggantian file memerlukan persetujuan, Excel disusun per masa, dan PDF keuangan/auditan Badan tertentu sudah didukung. Struktur B diterapkan di atas kontrak ini, bukan dengan menghapusnya. Sumber: [App][app], [worker][worker], [interaction][interaction], [publikasi][output], [instruksi repo][agents].

Acuan keputusan: batas bisnis/keamanan yang tetap diwajibkan, keputusan eksplisit pemilik yang paling baru, spesifikasi ini setelah disetujui, lalu visual MagicPath dan catatan desain lama. Tes yang mengunci permintaan pemilik menjadi bukti maksud baseline, bukan larangan untuk perubahan yang kelak disetujui secara eksplisit. Konflik fakta diselesaikan menggunakan kode dan tes, bukan kalimat mockup. Nilai visual di bawah merupakan target desain, bukan hasil pengukuran aplikasi.

Batas pekerjaan ini adalah dokumentasi. Tahap berikutnya memerlukan review spesifikasi, rencana implementasi terpisah, kemudian perubahan kecil dengan tes. Figma dan Penpot bukan dependensi pengembangan atau gerbang penerimaan.

## 2. Perubahan yang wajib dibawa dari kode terbaru

| Area | Prototipe/dokumen B sebelumnya | Kontrak baseline dan keputusan sekarang |
| --- | --- | --- |
| Pemilihan SPT | Form langsung menuju detail; petunjuk mengatakan semua masa ikut diunduh. | Inventaris terlebih dahulu; pilihan awal kosong; detail hanya untuk ID yang dikonfirmasi. Tambahkan representasi visual dialog yang sudah ada. |
| Pencarian daftar | Belum ada dalam B. | Cari jenis pajak, masa, model/pembetulan, atau ID. Mengubah pencarian mengosongkan pilihan, termasuk yang tersembunyi. |
| Penggantian hasil | Belum ada dalam B. | Tampilkan folder aktual dan semua path yang akan diganti. Tolak/X/Escape berarti tidak menyetujui penggantian, bukan lanjut dengan pilihan lain. |
| Makna COMPLETE | Mudah terbaca sebagai seluruh SPT dalam tahun. | Berlaku untuk subset yang disetujui dan cakupan yang didukung. Jangan mengklaim semua SPT tahunan telah diunduh. |
| Susunan Excel | Satu workbook per jenis; semua file rata dalam satu folder. | Workbook masa berada dalam subfolder; Badan memakai sheet per form/pembetulan. Pertahankan seluruh hierarki dan tautan relatif. |
| PDF | Kalimat B menolak semua PDF. | PDF laporan keuangan/auditan Badan dari tautan baca yang didukung dapat ikut dipublikasikan setelah verifikasi. BPE/lampiran lain tetap tidak dijanjikan. |
| Identitas aplikasi | Judul generik dan checkbox dengan bahasa B. | Pertahankan tiga teks khusus pemilik, subtitle, dan tombol `Sedot SPT terpilih` yang sudah dikontrak tes. |
| Runtime | Catatan lama merujuk Python 3.11. | Profil produksi pada [runtime][runtime] adalah CPython `3.14.8`; redesign tidak mengubah pin, dependensi, atau allowlist worker. |
| Bukti penerimaan | Laporan/README masih dapat menyebut PR #8 draft. | Status historis bukan status branch terbaru. Pin spesifikasi ke commit; jangan menganggap catatan lama sebagai bukti eksekusi baru. |

Tes sumber penting: [pemilihan GUI][selection-tests], [teks yang diminta][text-tests]. Jumlah tes yang disebut laporan lama tidak dipakai sebagai bukti bahwa spesifikasi atau implementasi berikutnya sudah lulus.

## 3. Lingkup dan hal yang tidak ditambahkan

Yang termasuk: struktur visual B; teks natural; validasi inline; tahap dan metrik yang benar; hasil lengkap/belum lengkap; login; dialog pemilihan dan penggantian yang sudah ada; konfirmasi edit Pengaturan belum disimpan; layout jendela kecil; keyboard, aksesibilitas, dan pembatasan pekerjaan GUI.

Yang dipertahankan tanpa perluasan: pencarian/seleksi ID, asal data, format Excel/PDF, verifikasi hasil, private consent channel, pembatalan, login origin allowlist, Credential Manager, dan CLI. Sumber: [AGENTS][agents].

Tidak termasuk: antrean banyak NPWP, pekerjaan paralel, riwayat, resume GUI, retry hanya SPT gagal, pemilihan lokasi baru, dark mode, JSON-first capture, generator PDF, atau migrasi toolkit. Tidak ada tombol kosong untuk fitur tersebut. PDF yang sudah ada dan pemilihan SPT **bukan fitur baru** dalam pekerjaan redesign ini.

## 4. Alur dan inventaris permukaan

```text
Form → Persiapan → Autentikasi [↔ login manual di browser]
     → Inventaris → Pilih SPT → Rincian pilihan + PDF yang didukung
     → File Excel dibuat → Publikasi [↔ persetujuan ganti file]
     → Verifikasi controller/cleanup → COMPLETE | PARTIAL

Daftar teramati kosong → jalur kosong worker, tanpa pilihan otomatis.
Stop → sedang menghentikan → terminal yang disahkan controller.
Pengaturan → simpan / cek login / hapus login adalah cabang terpisah.
```

Empat penanda tetap ringkas: **Masuk ke Coretax · Daftar SPT · Mengambil rincian · Hasil unduhan**. Penanda kedua mencakup inventaris dan pilihan; penanda keempat mencakup Excel, publikasi, dan persetujuan penggantian. Perubahan dari “Hasil Excel” menjadi “Hasil unduhan” mengakomodasi keluaran PDF yang sudah ada. Penanda bukan tombol navigasi. Saat form masih idle, belum ada tahap berjalan.

| ID permukaan | Isi dan varian wajib | Implementasi |
| --- | --- | --- |
| B01 | Form kosong/terisi; error NPWP; error tahun. | Frame utama. |
| B02 | Persiapan, autentikasi, tindakan login manual. | Panel status pada area kerja yang sama. |
| B03 | Membaca inventaris dan jumlah sementara. | Panel status; jangan menyamakan jumlah scan dengan ID unik. |
| B04 | Pilih SPT: belum memilih, memilih, filter tanpa hasil, sedang mengisi daftar, permintaan kedaluwarsa. | `Toplevel` + `Treeview` + dua scrollbar. |
| B05 | Mengambil rincian; jumlah diproses/lengkap/belum pasti. | Panel proses. Tidak ada progres PDF terpisah tanpa data event. |
| B06 | File Excel selesai dibuat; publikasi/cleanup belum selesai. | Panel proses; hasil belum dapat dibuka. |
| B07 | Ganti hasil: folder/path panjang, daftar file, setuju, tolak, permintaan tidak berlaku lagi. | `Toplevel` + daftar path. |
| B08 | COMPLETE, COMPLETE kosong, PARTIAL dengan/tanpa output, CANCELLED, BLOCKED, ERROR. | Panel hasil pada area kerja. |
| B09 | Stop diminta / tutup aplikasi saat aktif. | Panel stopping dan dialog konfirmasi tutup. |
| B10 | Pengaturan normal, dirty, save gagal, hapus login, semua hasil cek login, cek sedang dibatalkan. | `Toplevel`; dialog kecil hanya untuk keputusan. |
| B11 | Folder hilang / gagal membuka folder; aplikasi sudah berjalan / gagal startup. | Pesan native dengan tindakan yang sesuai. |
| B12 | Layout compact dan teks panjang untuk seluruh keluarga di atas. | Reflow/scroll, bukan fungsi bisnis lain. |

Daftar ini menggantikan asumsi bahwa paket 36 mockup lama sudah mencakup seluruh kode terbaru. B04/B07 dan konteks hasil PDF/masa harus mendapat bukti visual saat implementasi; tidak ada klaim MagicPath sudah memuatnya.

## 5. Pemetaan layout dan widget

### 5.1 Jendela kerja

```text
Tk root — titlebar Windows asli
└─ shell: ttk.Frame (grid, satu baris konten elastis)
   ├─ header: Title.TLabel + subtitle + tombol Pengaturan
   ├─ stage_strip: empat kelompok label, tanpa tab stop
   ├─ workspace: area yang dapat digulir bila tinggi tidak cukup
   │  ├─ content_slot: FormView | ProgressView | ResultView
   │  └─ ScopeSummary: NPWP, tahun, jumlah pilihan bila diketahui
   ├─ action_bar: aksi untuk state aktif, tetap terjangkau
   └─ footer: results_label yang diminta
```

Teks header panjang milik pemilik tetap satu `Title.TLabel` yang nyata, membungkus sesuai lebar tersedia. Caption Windows dan isi heading harus sama persis. Jangan menyembunyikan heading di balik caption, menggantinya dengan slogan B, atau memperbesar minimum jendela untuk menutupi masalah layout. `results_label` tampil tepat sekali. Sumber kontrak: [test_desktop_requested_text.py][text-tests].

Form, panel proses, dan panel hasil dibuat satu kali lalu ditukar visibility-nya dengan `grid_remove`/`grid`. Ringkasan mempertahankan NPWP/tahun yang diterima saat `start`, bukan field yang dapat berubah selama job. Hanya nilai dari pekerjaan aktif yang boleh masuk ringkasan.

### 5.2 Ukuran dan reflow

| Parameter | Target B-TK-1 |
| --- | --- |
| Jendela regular | 1120 × 800 DIP sebagai ukuran rancangan, dibatasi work area layar. |
| Dua kolom | Lebar client setidaknya 960 DIP: ringkasan sekitar 244 DIP, gap 24 DIP, area utama mengambil sisa. |
| Compact | Di bawah 960 DIP, ringkasan berpindah ke atas area utama; tidak dihilangkan. |
| Form satu kolom | Jika lebar isi kurang dari 560 DIP atau teks aktual tidak muat. |
| Penanda tahap | Empat kolom; pada compact menjadi 2 × 2, tanpa mengurangi ukuran huruf. |
| Spasi | 4/8/12/16/24/32 DIP; padding shell regular 24–32, compact 16. |
| Kontrol | Sasaran tinggi 40–44 DIP, minimal mengikuti tinggi font + padding native. |
| Tabel pilihan | Target dialog 920 × 600 DIP jika work area cukup; isi/kolom boleh digulir dua arah. |
| Pengaturan/penggantian | Ukuran mengikuti konten dan work area; baris tombol tidak berada di luar viewport. |

Breakpoint adalah adaptasi desktop dari B, bukan salinan CSS. Nilai DIP tidak langsung dianggap piksel Tk. Gunakan satu helper skala terpusat berdasarkan DPI efektif yang terukur; font point dan ukuran piksel jangan diskalakan dua kali. Catat Windows scaling serta Tcl/Tk patchlevel pada bukti runner. Perubahan process DPI awareness dilakukan sebelum pembuatan root dan hanya jika memang diperlukan serta diuji; jangan menggantinya di tengah sesi.

Pertahankan pengujian permintaan geometry 540 × 390 dan 900 × 700, lalu tambahkan 640 × 560 dan 1120 × 800 pada matriks yang disepakati. Ukuran aktual boleh menyesuaikan kebutuhan konten sebagaimana baseline, tetapi harus muat di work area. Pada work area pendek, beri scroll pada isi, bukan memaksa minimum melampaui layar. Jangan meluluskan tes clipping hanya dengan membuat jendela melebihi layar.

Gunakan `grid` untuk hubungan antarkelompok, `pack` hanya dalam container berbeda; jangan mencampur kedua geometry manager pada parent yang sama. `<Configure>` memperbarui wraplength/lebar isi dengan debounce 75 ms dan satu callback tertunda. Pertahankan fokus, isi input, pilihan valid, serta posisi scroll yang masuk akal saat reflow. `Canvas` boleh menjadi viewport untuk frame widget yang digulir, bukan tempat menggambar tombol/field palsu. Tabel memakai scroll native `Treeview`.

### 5.3 Komponen konkret

| Elemen MagicPath | Tkinter/ttk | Kontrak |
| --- | --- | --- |
| Header/card | `Frame`, `Label`, `Separator` | Hirarki, spacing, keterbacaan; bukan shadow/gradient wajib. |
| Isian | `Entry` + `StringVar` + helper/error `Label` | NPWP tetap string; label permanen. |
| Dropdown browser/situs | `Combobox(state='readonly')` | Label browser berbeda dari nilai internal, situs dari allowlist. |
| Primary/secondary | `Button` + style map | State disabled/focus nyata, bukan perubahan warna saja. |
| Stage strip | Label nomor/nama + status teks | Tidak bisa melompati pilihan/verifikasi. |
| Progress | `Progressbar` determinate/indeterminate | Angka dari controller; tidak membuat animasi progres rekaan. |
| Metrik | `Label` terikat state | Data tidak diketahui tidak diisi nol. |
| Daftar SPT/path | `Treeview`, `Scrollbar` | ID sumber tidak dijadikan Tcl item ID. |
| Pengaturan/consent | `Toplevel.transient` + grab + restore focus | `WM_DELETE_WINDOW`, Escape, Stop ditangani sesuai jenis dialog. |
| Rincian | Frame disclosure + label/teks read-only yang dibatasi | Status teknis aman; bukan dump payload atau log pajak. |

Gunakan tema ttk Windows yang tersedia; jangan mengganti dengan toolkit pihak ketiga agar sudut menjadi identik. Beberapa pilihan style native tidak mengikuti semua warna CSS. Keterbacaan, fokus, dan state disabled lebih penting daripada radius/shadow pixel-perfect. Rujukan API: [Tkinter][tkinter] dan [ttk][ttk].

## 6. Batas modul dan API

Pertahankan `App(root, workspace, controller=None)` sebagai titik integrasi dan dependency injection tes. Metode aksi `start`, `stop`, `settings`, `selection_dialog`, `overwrite_dialog`, `on_event`, `open_result`, dan `request_close` tidak hilang hanya karena view dipisah. Pertahankan handle widget yang masih dipakai self-test, atau migrasikan pengujiannya secara eksplisit dalam PR yang sama tanpa mengurangi kontrak.

| Modul | Tanggung jawab yang ditetapkan |
| --- | --- |
| `spt_desktop/app.py` — ada | Koordinator aksi, controller, operasi aktif, lifecycle dialog, penjadwalan Tk, serta integrasi state/view. Jangan memindahkan otorisasi worker ke renderer. |
| `spt_desktop/ui_state.py` — usulan | State presentasi dan pemetaan event murni; tidak mengimpor Tk, filesystem output, Playwright, atau openpyxl. |
| `spt_desktop/ui_copy.py` — usulan | ID teks, template bernama, mapping caption browser; tanpa framework i18n baru. |
| `spt_desktop/ui_theme.py` — usulan | Named fonts, style map, spacing/skala, aturan layout. Nilai tidak disalin ke setiap view. |
| `spt_desktop/ui_views.py` — usulan | Widget area kerja dan pembaruan inkremental; fungsi pembangun dialog dapat tetap dekat lifecycle App sampai ada kebutuhan nyata untuk dipisah. |

Empat modul baru ini adalah batas tanggung jawab, bukan perintah membuat interface generik, event bus, dependency container, atau kelas untuk setiap label. Split tambahan dilakukan hanya bila kode yang benar-benar muncul memerlukannya.

API controller tetap: `start(npwp, year, browser, headless)`, `start_login_check(origin, account, browser, headless)`, `poll()`, `stop()`, `close()`, `read_request(event)`, dan `respond(kind, request_id, payload)`. Teks GUI tidak memerlukan event field baru. Nilai return `respond` harus dihormati: `False` bukan persetujuan sukses. Sumber: [controller][controller].

State presentasi minimal menyimpan `operation`, `job_id`, `view_state`, `stage`, `percent`, snapshot NPWP/tahun, counters opsional, status terminal, output yang disahkan, dan konteks consent yang sedang ditampilkan. Detail selection disimpan hanya selama diperlukan. Status login serta hasil ekspor terakhir dipisahkan agar cek login tidak menimpa ringkasan hasil ekspor.

`controller.active`, validitas job/request, serta terminal controller tetap otoritas. Reducer tidak membuat boolean “selesai” berdasarkan persen. Perubahan job mengosongkan counters, error, consent, dan alasan keputusan lokal yang lama. Simpan hanya konteks yang diperlukan, bukan seluruh payload/tax records dalam state global.

## 7. Pemetaan event → state → tindakan

| Bukti/pemicu | State tampilan | Perilaku wajib |
| --- | --- | --- |
| Belum mulai | `idle` | Form aktif, tidak ada tahap berjalan, Mulai tersedia sesuai validasi. |
| Input tidak sah | `form_invalid` | Tidak memanggil worker; error di field dan fokus ke error pertama. |
| Start diterima, event setup | `preparing` | Indeterminate; NPWP/tahun/Pengaturan dikunci; Stop tersedia. |
| `progress`, stage `authentication` | `authenticating` | “Memeriksa akses ke Coretax”; stage saja tidak membuktikan login sudah berhasil. |
| `login_required` | `login_required` | Instruksi pindah ke browser, tanpa tombol yang mengesahkan login sendiri. |
| `progress`, stage `inventory` | `inventory` | Counter sesuai makna inventaris; jangan dianggap jumlah SPT lengkap. |
| `selection_required` yang aktif | `awaiting_selection` | Dialog dibuka sekali; angka progres ditahan, tidak dibuat naik selama menunggu pengguna. |
| Jawaban selection diterima controller | `selection_submitted` | Tutup dialog; simpan jumlah pilihan yang benar-benar disetujui; tunggu event detail. |
| `progress`, stage `details` | `capturing` | `processed/total/verified` milik subset. PDF berada dalam pekerjaan ini, tanpa counter PDF palsu. |
| `progress`, stage `export` | `exported` | Event datang setelah workbook dibuat/diverifikasi; teks “File Excel sudah dibuat”, bukan klaim sedang membuat tahap yang belum teramati. |
| `progress`, stage `publish` | `publishing` | 99% belum selesai. Hasil tidak dapat dibuka. |
| `overwrite_required` yang aktif | `awaiting_overwrite` | Folder dan daftar file exact; aksi aman default; tidak ada timeout yang berarti setuju. |
| Overwrite setuju diterima | `publishing` | Tetap menunggu controller; klik setuju belum berarti file berhasil diganti. |
| Overwrite ditolak diterima | `cancellation_pending` | Tunggu terminal; jangan menampilkan sukses atau menjalankan ekspor lain. |
| Stop pada state aktif | `stopping` | Stop dikirim sekali, dialog invalid, Mulai/Pengaturan tetap terkunci sampai terminal. |
| Terminal `COMPLETE` dari controller | `complete` | Buka output sah; jelas berlaku untuk pilihan saat ini. |
| COMPLETE + bukti scope kosong | `empty_complete` | “Tidak ada SPT yang ditemukan”; bukan hasil filter pencarian kosong. |
| Terminal `PARTIAL` | `partial` | Peringatan; buka hasil hanya bila output sah tersedia. |
| Terminal `CANCELLED` | `cancelled` | Tidak ada sukses; checkpoint yang tersedia dipertahankan; mulai lagi bukan resume. |
| Terminal `BLOCKED` / `ERROR` | `blocked` / `error` | Judul aman dan tindakan relevan; jangan menebak sebab yang tidak diberikan secara terstruktur. |
| Operasi `login_check` | `login_*` | Jalur tersendiri; semua persen nol/tanpa output ekspor; jangan masuk state hasil unduhan. |

Prioritas: job/operasi tidak cocok → abaikan; stopping/closing atau terminal → tidak boleh membuka consent baru; consent aktif → state menunggu; sisanya → progress normal. Callback lama tidak boleh menghentikan job baru. Pending callback ditokenisasi dengan job/request dan generasi view; hasil baca/render tertunda diperiksa ulang sebelum diterapkan.

Batas transport sekarang: baris event maksimal 16.384 karakter; `request_id` hex 32 karakter hanya untuk consent; payload besar dibaca dari pesan privat, maksimal 16 MiB; queue controller 128 event. Jangan menaruh daftar SPT/path privat ke stdout/stdin untuk memudahkan view. Sumber: [controller][controller], [interaction][interaction].

`Progress` memberi bobot autentikasi 5, inventaris 5–20, detail 20–90, export 95, publish 99, dan 100 hanya COMPLETE. Jangan hitung ulang persen di GUI. Pada inventaris, `processed/total` adalah progres unit inventaris, bukan denominator SPT terpilih; `scanned` tidak otomatis jumlah ID unik. Pada detail, tampilkan “SPT diproses”, “Lengkap”, dan “Belum pasti lengkap” dengan selisih `processed - verified` hanya jika semua counter sah. Nilai tidak ada tetap tidak diketahui; jangan mempertahankan denominator inventaris sebagai denominator detail. Sumber: [events][events].

Terminal tidak membawa semua counters atau manifest output. Pertahankan counters sah terakhir dari job yang sama; jangan membaca Excel atau `run.json` di main thread untuk mengarang ringkasan tambahan. Jika belum ada data jumlah, sembunyikan metrik tersebut. Tampilan kosong memerlukan terminal COMPLETE dan bukti detail `0/0` dari jalur kosong yang sah; kesalahan jaringan/daftar terfilter kosong tidak memenuhi syarat.

## 8. Dialog pemilihan SPT: kontrak rinci

Dialog mempertahankan kolom **Jenis pajak · Masa pajak · Normal / pembetulan · ID SPT** dari metadata teramati. Nilai cell tetap literal. Tidak menggabungkan pembetulan berbeda, menormalkan ID, atau mengganti label sumber dengan dugaan.

Pilihan awal kosong, tombol **Sedot SPT terpilih** nonaktif. Pilihan ganda memakai Ctrl/Shift dan navigasi keyboard `Treeview`. Search menggunakan casefold/trim pada query pencarian saja; aturan ini tidak diterapkan pada NPWP. Setiap perubahan filter menghapus semua pilihan, bukan menyimpan hidden selection. Setelah filter berubah, tampilkan petunjuk “Pencarian berubah. Pilih lagi SPT yang akan diunduh.” ketika sebelumnya ada pilihan. Pengosongan pilihan sudah dikontrak tes baseline; petunjuk setelah filter berubah merupakan tambahan copy. Sumber: [tes pilihan][selection-tests].

Ringkasan dialog: “{selected} SPT dipilih · {visible} dari {inventory} SPT ditampilkan.” Semua angka berasal dari payload valid dan row model. Bedakan “Tidak ada SPT yang cocok dengan pencarian” dari “Daftar ini tidak memuat SPT yang bisa dipilih.” Tidak ada default pilih semua dan tidak ada submit kosong.

Jalankan `read_request(event)` melalui controller, bukan membaca path yang dibentuk view. `record_id` dipetakan ke IID lokal, misalnya `record-17`; karakter Tcl pada ID sumber tidak dieksekusi. Pada confirm, kirim hanya `{'selected_ids': [...]}` ke `respond('selection', request_id, payload)`, urutan mengikuti inventaris. Snapshot pilihan harus benar-benar masih terlihat dan terpilih pada generasi filter terakhir.

X, Escape, dan **Hentikan unduhan** membatalkan job tanpa menyetujui pilihan. Fokus awal pada pencarian. Stop/terminal menghancurkan dialog, melepas grab, dan membuang callbacks/traces. Satu request tidak dapat membuka dialog kedua atau dijawab dua kali; request asing tidak mengganti dialog aktif. Callback dari dialog lama hanya ditutup, tidak memengaruhi pekerjaan berikutnya.

Worker memberi tenggat consent 600 detik. View tidak meresetnya saat filter/resize dan tidak mengubah timeout menjadi pilihan default. Teks bantuan boleh menyebut batas sampai 10 menit, tetapi tidak menampilkan countdown exact dari perkiraan waktu event diterima. Timeout saat ini dapat tiba sebagai ERROR generik; tanpa reason code terstruktur, jangan mengklaim penyebab timeout secara pasti.

Untuk daftar besar, sisipkan/filter row bertahap melalui `after` dengan generasi render. Saat render belum selesai, submit nonaktif; setiap batch memeriksa job/request/cancel. Jangan memotong jumlah record agar terlihat cepat. Mulai dengan batch maksimum 100 row atau 8 ms kerja callback, lalu ukur di runner. Batas payload privat tetap berlaku. Pembacaan JSON besar di callback baseline adalah risiko statis yang perlu diukur, bukan bukti hang teramati. Bila melebihi anggaran, gunakan satu jalur I/O terjadwal di controller dengan hasil bertag job/request; tidak ada Tk di thread pembaca, tidak ada akses path tanpa validasi, dan semua pemeriksaan sebelum kirim consent tetap dilakukan ulang. Optimisasi ini tidak mengubah format IPC.

## 9. Dialog penggantian hasil: tidak ada persetujuan tersirat

Gunakan payload `files` dan `folder` yang telah dibaca controller. Tampilkan folder aktual dan setiap path yang akan diganti, termasuk PDF bila tercantum. Daftar berscroll dua arah; path tidak direduksi menjadi basename yang dapat menutupi perbedaan subfolder. Tidak memindai Downloads dari view atau memilih folder “terbaru” sendiri.

Copy inti:

> **Ganti hasil sebelumnya?**  
> File di bawah akan diganti seluruhnya dengan hasil pilihan kali ini. SPT lain yang sebelumnya berada dalam file yang sama tidak ikut dipertahankan. File lain yang tidak tercantum tetap ada.

**Jangan ganti** menerima fokus awal dan mengirim `{'overwrite': False}`; Escape/X sama dengan pilihan tersebut. **Ganti file tersebut** mengirim `{'overwrite': True}`. Alt+S tetap Stop langsung, bukan persetujuan. Hanya controller/worker yang menulis jawaban dan memulai publikasi. Worker saat ini selalu mengirim folder untuk permintaan penggantian, tetapi validator dialog baseline masih menerima payload tanpa folder. B-TK-1 menetapkan penguatan presentasi: payload tanpa konteks folder tidak boleh membuka aksi persetujuan destruktif. Ini perubahan yang harus diuji, bukan klaim perilaku baseline. Fixture lama tanpa folder perlu diperbarui atau dipakai khusus untuk menguji jalur penolakan; jangan melemahkan persetujuan demi fixture.

Persetujuan mengganti file secara utuh, **bukan merge baris**. File masa lain yang tidak terganti tetap ada; `resume.xlsx` baru mengindeks pilihan proses saat ini, bukan mengindeks ulang semua file lama dalam folder. Keduanya harus dijelaskan tanpa menjanjikan seluruh folder homogen/baru. Pemeriksaan identitas folder, hash file, path, rollback, dan penggantian setelah consent tetap tanggung jawab [output.py][output] dan tidak diubah oleh view.

Jawaban gagal/stale tidak dicoba otomatis. Ketika keputusan tidak bisa dikirim, App mengikuti pembatalan aman yang ada. Jangan mengatakan “file sudah diganti” sebelum terminal berhasil. Jangan menawarkan alternatif folder baru yang tidak didukung GUI.

## 10. Hasil Excel/PDF dan batas klaim

COMPLETE memerlukan event terminal sah, exit code cocok, output valid, serta cleanup milik aplikasi selesai. `os.startfile` hanya memakai path yang diloloskan controller. Handle error membuka folder dibedakan: folder tidak lagi ada versus folder ada tetapi Windows gagal membukanya. Tidak menebak path pengganti.

| Keadaan | Judul dan tindakan |
| --- | --- |
| COMPLETE | **File Excel sudah siap**. Isi: “Hasil untuk SPT yang dipilih sudah disimpan dan diperiksa.” Tombol **Buka folder hasil** dan **Unduh SPT lain**. |
| PARTIAL dengan output | **Hasil unduhan belum lengkap**. Isi: “Ada data yang belum bisa dipastikan lengkap. Lihat lembar Audit di resume.xlsx untuk rinciannya.” Tombol **Buka hasil sementara**. Tidak ada centang sukses. |
| PARTIAL tanpa output | Judul sama; jelaskan belum ada folder hasil yang bisa dibuka. Tombol buka tidak tersedia. |
| COMPLETE kosong | **Tidak ada SPT yang ditemukan**. Sebut NPWP/tahun; buka ringkasan hanya jika output sah tersedia. |
| CANCELLED | **Unduhan dihentikan**. “Data sementara yang sudah dibuat tetap disimpan di komputer. Mulai lagi akan menjalankan unduhan baru.” |
| Penolakan ganti yang berakhir CANCELLED | Boleh menambah “Penggantian file tidak disetujui” dari keputusan lokal yang terikat job; jangan memakai alasan ini untuk job lain atau menutupi ERROR. |
| BLOCKED/ERROR | Pesan aman; tidak menyatakan hasil lengkap. Tombol kembali/pengaturan bila operasi sudah tidak aktif. |

Info hasil yang benar:

> Simpan seluruh folder hasil beserta subfoldernya. Jangan mengganti nama file agar tautannya tetap berfungsi. PDF laporan keuangan/auditan Badan ikut disimpan jika tersedia melalui tautan yang didukung dan lolos pemeriksaan. BPE dan lampiran lain belum termasuk.

Kalimat ini menjelaskan kemampuan bersyarat, bukan menyatakan PDF tertentu berhasil diunduh. Jangan menampilkan jumlah PDF, nama WP, daftar file aktual, atau persentase PDF bila data tersebut tidak tersedia pada kontrak presentasi. Metadata lampiran bukan bukti byte PDF sudah tersimpan. Daftar path overwrite hanya membuktikan rencana penggantian, bukan hasil publikasi.

Susunan yang dipertahankan: `resume.xlsx`; `SPT_Badan.xlsx`; `SPT Masa 21/SPT_21_<masa>.xlsx`; `SPT Masa Unifikasi/SPT_Unifikasi_<masa>.xlsx`; `SPT Masa PPN/SPT_PPN_<masa>.xlsx`; serta workbook jenis lain yang teramati. Nama masa berasal dari sumber; view tidak membentuk nama sendiri. Path PDF mengikuti deklarasi backend, tidak ditebak. Kontrak detail: [AGENTS][agents], [README baseline][readme], [publikasi][output].

## 11. Teks final dan pengecualian milik pemilik

Bahasa utama memakai kalimat pendek, natural, dan spesifik. Istilah `worker`, `cleanup`, `job_id`, `request_id`, `COMPLETE`, dan `PARTIAL` tidak menjadi petunjuk utama. Kode status dapat tampil di **Lihat rincian**. Jangan memasukkan instruksi developer atau watermark prototipe ke aplikasi produksi.

Teks berikut **dikunci**, termasuk kapitalisasi dan tanda baca:

| ID presentasi | Teks |
| --- | --- |
| `app.title` | Coretax SPT downloader : kalau bisa ribet, kenapa dibikin gampang |
| `settings.background.label` | jalankan proses sedot di background |
| `results.location_hint` | Hasil Sedot berada di folder Downloads Windows |
| `app.subtitle` | Coretax → Excel · for personal use only |
| `selection.confirm` | Sedot SPT terpilih |

Tiga teks pertama dikunci oleh [tes requested text][text-tests], subtitle ikut self-test, dan selection confirm dipakai [tes consent GUI][selection-tests]. Jangan “memanusiakan” lagi teks ini dengan menghapus humor yang sengaja diminta. Humor tidak diperluas ke error, peringatan kehilangan data, atau persetujuan penggantian.

Katalog berikut merupakan delta terhadap katalog B-copy-2; ID lama dipakai ulang ketika maknanya sama, tidak membuat ID berdasarkan isi kalimat.

| ID | Teks/template B-TK-1 |
| --- | --- |
| `form.title` | Masukkan NPWP dan tahun pajak |
| `form.help` | Setelah daftar muncul, pilih SPT yang ingin diunduh. |
| `form.npwp.label` | NPWP (16 digit) |
| `form.npwp.help` | Ketik 16 angka, tanpa spasi, titik, atau tanda hubung. |
| `form.npwp.error` | Isi NPWP dengan 16 angka (0–9), tanpa pemisah. |
| `form.year.help` | Gunakan tahun pajak, bukan tahun pelaporan. |
| `form.year.error` | Gunakan 4 angka, dari 1900 sampai 2100. |
| `action.start` | Mulai unduh |
| `action.stop` | Hentikan unduhan |
| `action.open_result` | Buka folder hasil |
| `action.open_partial` | Buka hasil sementara |
| `action.new` | Unduh SPT lain |
| `action.details` | Lihat rincian |
| `selection.title` | Pilih SPT yang akan diunduh |
| `selection.summary` | {selected} SPT dipilih · {visible} dari {inventory} SPT ditampilkan. |
| `selection.no_match` | Tidak ada SPT yang cocok dengan pencarian. |
| `selection.filter_reset` | Pencarian berubah. Pilih lagi SPT yang akan diunduh. |
| `download.details.body` | {processed} dari {total} SPT sudah diproses. Kelengkapan {verified} SPT sudah diperiksa. |
| `download.exported.title` | File Excel sudah dibuat |
| `download.publish.title` | Menyimpan hasil unduhan |
| `download.complete.title` | File Excel sudah siap |
| `download.complete.body` | Hasil untuk SPT yang dipilih sudah disimpan dan diperiksa. |
| `download.partial.title` | Hasil unduhan belum lengkap |
| `download.stopping.title` | Menghentikan unduhan… |
| `download.cancelled.title` | Unduhan dihentikan |
| `download.error.title` | Unduhan belum berhasil |
| `overwrite.title` | Ganti hasil sebelumnya? |
| `overwrite.decline` | Jangan ganti |
| `overwrite.confirm` | Ganti file tersebut |
| `settings.origin.label` | Situs login |
| `settings.account.label` | Nama pengguna |
| `settings.password.help` | Kosongkan jika tidak diganti |
| `settings.background.help` | Jika memungkinkan. Browser tetap muncul saat perlu login. |
| `settings.check` | Cek login |
| `settings.cancel_check` | Batalkan cek |
| `settings.delete` | Hapus login |
| `settings.dirty.title` | Perubahan belum disimpan |
| `login.unverified.title` | Password belum bisa dipastikan |

Template memeriksa parameter bernama dan jenis nilainya; key tidak ditemukan adalah cacat presentasi yang diuji, bukan alasan menampilkan exception ke pengguna. Counter terkait SPT tidak dirangkai dengan string persen. Teks raw source dalam tabel bukan objek penerjemahan.

Label lama seperti `Mulai`, `Cek Kredensial`, atau `Buka Hasil` yang bukan tiga teks khusus dapat diganti sesuai katalog. Tes/self-test yang menilai label tersebut harus diperbarui bersama view untuk menegaskan fungsi dan teks baru; jangan menghapus tes hanya agar perubahan kata lulus. Jika hint teknis “Setup Python/uv otomatis saat Mulai.” dipindahkan ke rincian, ubah kontrak penempatan secara eksplisit sambil tetap mempertahankan informasi setup dan bukti tiga teks khusus.

## 12. Pengaturan dan login

Urutan tab dalam dialog: situs login → nama pengguna → password baru → browser → checkbox background → Simpan → Cek login → Batalkan cek bila aktif → Hapus login → Tutup. Domain berasal dari `ALLOWED_ORIGINS`, bukan input URL bebas. Caption Microsoft Edge/Google Chrome dipetakan ke `msedge`/`chrome`; nilai tersimpan tidak berubah.

`dirty` berasal dari perbandingan nilai dengan preferensi tersimpan ditambah password baru yang tidak kosong. Mengetik lalu mengembalikan nilai semula tidak meninggalkan dirty palsu. Ubah browser tidak boleh dianggap sudah disimpan hanya karena combobox ditutup.

Simpan berhasil tidak membuktikan password benar. Password kosong mempertahankan entri sesuai kontrak penyimpanan; perubahan akun yang memerlukan password baru mendapat pesan dekat field. Jangan menjanjikan transaksi atomik antara Credential Manager dan file preferensi. Jika salah satu write gagal, dialog tetap terbuka, status tidak mengatakan semua tersimpan, dan status login tetap belum dicek. Penghapusan hanya untuk origin terpilih, bukan akun portal, login situs lain, atau file hasil.

Cek login tersedia hanya ketika tidak ada operasi lain, tidak dirty, dan akun nonkosong yang valid tersimpan. Selama cek: kontrol edit/Simpan/Hapus dikunci; Batalkan cek aktif; tidak ada ekspor. X/Escape meminta pembatalan dan menunggu controller selesai sebelum menutup dialog. Hasil ekspor sebelumnya tidak hilang atau berubah menjadi hasil pengecekan.

| Status login | Judul dan makna |
| --- | --- |
| Belum diuji | Login belum dicek. |
| Aktif | Mengecek login… Mencoba sekali dengan akun yang disimpan. |
| `LOGIN_OK` | Login berhasil. Akun/password tersimpan benar-benar dipakai dan akses diverifikasi. |
| `LOGIN_UNVERIFIED` | Password belum bisa dipastikan. Ini tidak berarti password salah. |
| `LOGIN_MANUAL` | Perlu login di browser. Lakukan saat mulai unduh. |
| `LOGIN_BLOCKED` | Login belum bisa dicek. Periksa situs login dan akun. |
| `LOGIN_ERROR` / `ERROR` | Cek login belum berhasil. Periksa koneksi intranet dan browser. |
| Permintaan batal | Membatalkan cek login…; bukan terminal CANCELLED buatan view. |
| `CANCELLED` | Cek login dibatalkan. Tidak ada SPT yang diunduh. |

SSO, timeout, atau sebab lain tidak ditebak melalui pencocokan substring pesan. Bila tidak ada reason code aman, gunakan judul generik di tabel. Pesan aman worker boleh muncul sebagai rincian, tetapi tidak dijadikan protokol baru. Sumber: [auth][auth], [controller][controller].

Tutup Pengaturan idle dengan perubahan membuka dialog **Perubahan belum disimpan**: Simpan, Abaikan, Kembali. Escape/X pada konfirmasi berarti Kembali. Simpan hanya menutup setelah seluruh penyimpanan yang diperlukan berhasil. Ini peningkatan UX yang belum ada di baseline, bukan klaim kode sudah mengimplementasikannya.

## 13. Keyboard, fokus, dan aksesibilitas

Urutan fokus mengikuti urutan baca sesudah reflow, bukan urutan pembuatan widget yang kebetulan. Form memulai fokus pada NPWP. Submit invalid mempertahankan teks dan memfokuskan error pertama. Perubahan progres tidak mencuri fokus. Sesudah hasil selesai, fokus ke tindakan hasil yang tersedia hanya pada transisi eksplisit, bukan setiap event; jangan mengambil fokus OS dari browser login yang sedang digunakan.

Alt+M tetap start; Alt+S tetap Stop; Alt+P Pengaturan; Alt+C cek login. Karena S/C bukan huruf pada beberapa label Indonesia, tampilkan shortcut dalam bantuan/rincian dan jangan menggarisbawahi karakter yang salah. Enter pada isian form mengikuti guard start yang sama; Enter/Space pada button mengaktifkan button yang mendapat fokus. Jangan memasang Return global yang dapat menyetujui overwrite saat fokus berada pada tabel atau field lain.

Semantik Escape/X dibedakan: pemilihan SPT → cancel job; overwrite → jawaban false; Pengaturan saat cek → cancel cek lalu tunggu; dirty confirmation → kembali; dialog hapus/tutup aplikasi → pilihan aman. Dialog restore fokus ke pemicu yang masih hidup; bila pemicu nonaktif gunakan Stop saat job aktif atau NPWP saat idle. Callback/traces/after milik dialog dibersihkan sebelum destroy dan sebelum job berikutnya.

Target: kontras teks biasa 4,5:1, teks besar dan komponen relevan 3:1; state tidak hanya warna. Gunakan warna sistem pada High Contrast. Sasaran ukuran kontrol 40–44 DIP adalah keputusan produk, bukan klaim angka wajib universal Windows. Rujukan [WCAG 2.2][wcag] dipakai sebagai acuan visual; aksesibilitas native harus diuji terpisah.

Label yang terlihat dan tag HTML pada MagicPath tidak membuktikan name/role/value/focus terbaca pada Tkinter. Uji Narrator/NVDA dan inspeksi UI Automation pada Windows, terutama hubungan label-input, selection/table, state disabled, dialog, serta pesan status. Jika kontrol kritis tidak terbaca, catat sebagai blocker aksesibilitas; jangan mengklaim compliance atau mengganti toolkit diam-diam. Prinsip fokus dan keyboard: [Microsoft][keyboard].

## 14. Performa, lifecycle, dan kerahasiaan

GUI tidak mengimpor Playwright, openpyxl, `coretax_exporter`, atau `spt_desktop.output`. Semua parsing workbook/PDF, hash file hasil, login, dan download tetap worker. Setup tidak berjalan ketika sekadar membuka aplikasi. Source/frozen GUI tetap tipis; modul UI baru tidak dimasukkan ke `WORKER_FILES`. Sumber: [runtime][runtime], [AGENTS][agents].

Pertahankan loop polling `after(100, ...)` sebagai baseline awal, update hanya properti yang berubah, dan hanya satu timer indeterminate progress aktif. Pergantian job/dialog membatalkan callback tertunda yang relevan. Jangan memakai `sleep`, nested `update()` untuk menunggu worker, atau loop blocking di callback. Model event Tk membutuhkan handler singkat; rujukan [Python][tkinter].

**Anggaran usulan, belum diukur:** p95 feedback aksi/pembatalan ≤100 ms pada harness sintetis; p95 callback render ≤16 ms dengan batching daftar; startup p95 tidak lebih dari 10% baseline pada mesin/runner sebanding; working set GUI idle tidak naik lebih dari 10 MiB; setelah 100 siklus sintetis, tidak ada pertumbuhan jumlah widget, trace, callback, atau thread yang tertinggal. Ukur warm/cold start serta GUI terpisah dari worker/browser. Noise antar-runner tidak dijadikan klaim regresi/lulus; tetapkan toleransi dari pengukuran berulang.

Tenggat cleanup worker 15 detik bukan ETA total penutupan GUI: pembaca/EOF tetap dituntaskan oleh controller. Data sementara belum tentu sempat dibuat pada kegagalan awal; pesan harus mengatakan “yang sudah dibuat”, bukan menjamin checkpoint selalu ada.

NPWP, nama WP, ID SPT, path output, dan isi PDF/Excel tetap data privat. Boleh terlihat pada jendela lokal yang diperlukan, tidak masuk telemetry, log publik, PR, MagicPath, snapshot CI publik, atau payload bantuan otomatis. Rincian presentasi hanya status/tahap/counter aman; simpan maksimal 100 entri status ringkas jika riwayat rincian memang diperlukan, bukan seluruh event. Tidak menambah cloud analytics.

## 15. Matriks penerimaan implementasi

Semua baris adalah kriteria masa depan, bukan hasil tes pada penulisan spesifikasi. Fixture sintetis; tes perilaku memakai API publik dan efek yang terlihat. Nama keluarga tes existing dirujuk dari [laporan baseline][report] dan file yang ditinjau, bukan klaim bahwa setiap skenario baru sudah ada.

| ID | Kasus | Bukti yang harus ada |
| --- | --- | --- |
| AC01 | Shell B dan tiga teks khusus | Caption, satu Title.TLabel nyata, results_label tepat sekali, checkbox terikat preferensi; source/frozen melaporkan teks aktual. |
| AC02 | Input NPWP/tahun | Nol awal terjaga; Unicode digit/spasi/pemisah/tahun dua digit ditolak; tidak ada koreksi otomatis atau worker start. |
| AC03 | Start ganda | Klik/Enter/Alt+M tidak membuat job kedua; field terkunci selama pekerjaan aktif. |
| AC04 | Setup/auth | Indeterminate tanpa ETA; login manual tidak memiliki tombol “sudah login” yang mengesahkan sesi sendiri. |
| AC05 | Counter dan 99% | Unit inventory tidak menjadi total SPT; detail memakai subset; field tidak ada bukan nol; 99% tidak membuka output. |
| AC06 | Pilihan awal | Daftar terisi tetapi tidak terpilih; submit nonaktif; payload tidak pernah otomatis “semua”. |
| AC07 | Pencarian | Filter menghapus pilihan; ID tersembunyi tidak terkirim; no-match berbeda dari inventaris kosong. |
| AC08 | ID literal | ID berkarakter Tcl diperlakukan sebagai data; row menggunakan IID lokal; urutan ID mengikuti inventaris. |
| AC09 | Consent sekali | Duplikat request/click menghasilkan paling banyak satu jawaban; invalid payload tidak mendapat persetujuan. |
| AC10 | Consent stale | Stop, terminal, close, job baru, filter/render tertunda, atau `respond=False` tidak membuka kembali/menyetujui dialog. |
| AC11 | Tenggat consent | Habis waktu tidak berarti pilih semua atau overwrite true; GUI tidak mereset tenggat. |
| AC12 | Overwrite exact | Folder dan seluruh path terlihat; PDF ikut tampil jika ada; tanpa folder tidak ada approve; aksi aman mendapat fokus. |
| AC13 | Menolak ganti | Button/X/Escape mengirim false; file lama tidak dipublikasikan ulang; status menunggu terminal, bukan sukses. |
| AC14 | Replace semantik | File yang diganti tidak diklaim merge; file lain tetap; indeks baru hanya pilihan saat ini. |
| AC15 | Hasil final | COMPLETE/PARTIAL hanya dari controller; output tidak sah tidak bisa dibuka; pilihan subset dinyatakan. |
| AC16 | Scope kosong | Hanya jalur teramati kosong + COMPLETE yang menghasilkan empty-success; error/filter kosong bukan empty-success. |
| AC17 | PDF | Tidak ada janji seluruh PDF terambil atau counter rekaan; metadata saja tidak disebut download; kontrak PDF tetap lulus. |
| AC18 | Stop/close | Stopping berbeda dari CANCELLED; cleanup/EOF selesai; callback lama tidak menghentikan job baru. |
| AC19 | Pengaturan dirty | Simpan/Abaikan/Kembali, Escape, perubahan dikembalikan ke nilai awal, dan kegagalan simpan punya state benar. |
| AC20 | Login check | Operasi terpisah, semua status login terpetakan, SSO/timeout bukan password salah, tanpa ekspor atau perubahan hasil ekspor sebelumnya. |
| AC21 | Penyimpanan | Failure injection Credential Manager/preferences/delete tidak menghasilkan sukses palsu; password tidak muncul pada output tes/log. |
| AC22 | Folder hasil | Bedakan folder hilang dan gagal membuka; tidak menebak lokasi atau mengubah status job. |
| AC23 | Reflow | Regular/compact, label panjang, path panjang, DPI 100/125/150/200%, text scaling, dan multi-monitor; tidak menambah minimum melewati work area. |
| AC24 | Keyboard | Semua aksi punya jalur keyboard; fokus aman; Tab order setelah reflow sesuai visual; grab/restore bersih. |
| AC25 | Teknologi bantu | Name/role/value/state tabel, field, modal, dan hasil diperiksa di Windows; kekurangan tidak ditutupi screenshot. |
| AC26 | Lifecycle/performa | 100 siklus sintetis tanpa kebocoran resource UI; pengukuran latency/working set mengikuti anggaran dan mesin yang dicatat. |
| AC27 | Kontrak output | Regresi period layout, split output, numeric/raw values, PDF capture/publication, collision, overwrite, dan rollback tidak melemah. |
| AC28 | Distribusi | Build source/frozen, resource allowlist, exact run/commit/artifact-ID readback; tidak menyamakan docs-green dengan penerimaan produk. |

Pertahankan keluarga tes `test_desktop_selection_gui.py`, `test_desktop_selection_transport.py`, `test_desktop_consent_lifecycle.py`, `test_desktop_selected_capture.py`, `test_desktop_overwrite.py`, `test_desktop_overwrite_safety.py`, `test_desktop_requested_text.py`, `test_desktop_login_check.py`, serta `test_period_layout.py` dan `test_financial_*.py`. Tambahkan tes murni untuk state/copy dan tes widget untuk perbedaan B; jangan hanya menguji string HTML prototipe.

**Kebijakan eksekusi wajib:** sesuai [AGENTS][agents], pytest, product import, Tk/browser fixture, source/frozen self-test, build, dan EXE hanya di GitHub runner. Lokal hanya pemeriksaan dokumen/source/AST dan hash/metadata, bukan bukti runtime. Jangan mengubah workflow, ruleset, coverage, atau artifact verification demi mendapatkan GREEN. Ikuti [panduan pengembangan](../../pengembangan.md) dan [CI/rilis](../../ci-dan-rilis.md) pada branch pelaksanaan; pin exact head setiap klaim.

Penerimaan Coretax/Excel/UI manual masih ditunda sampai konsolidasi perubahan siap. Dokumen ini tidak memulai portal live atau meminta data pajak asli. Rencanakan penerimaan berizin setelah implementasi gabungan, bukan menganggap fixture runner sebagai pengganti.

## 16. Urutan implementasi setelah review

| Irisan | Lingkup perubahan | Gerbang |
| --- | --- | --- |
| 1 — State, copy, dan shell | Modul presentasi minimum, token/native styles, header terkunci, form + summary + tahap. | AC01–05; API controller dan protokol tidak berubah. |
| 2 — Pemilihan dan penggantian | Terapkan visual B pada dialog existing; search/selection tetap eksplisit; expiry/stale/folder binding tetap aman. | AC06–14 dan AC18; regresi consent/overwrite. |
| 3 — Proses, hasil, login | Copy terbaru subset/PDF; hasil sah; Pengaturan dirty/error; pemisahan cek login. | AC15–22; tidak ada data/counter palsu. |
| 4 — Reflow dan aksesibilitas | Jendela kecil, DPI, keyboard, native accessibility, batching/performa berbukti. | AC23–26; tidak menyembunyikan informasi kritis. |
| 5 — Regresi/distribusi | Seluruh kontrak output, source/frozen, exact artifact, lalu penerimaan manual yang disetujui. | AC27–28; keputusan rilis terpisah. |

Ini urutan irisan perubahan, bukan implementation plan berisi langkah eksekusi yang sudah disetujui. Jangan mengerjakan migrasi Python lagi atau membuat backend baru hanya karena nama file prototipe React. Pilih ukuran PR yang dapat direview; catat acceptance ID yang disentuh dan bukti yang masih kosong.

## 17. Pemeliharaan spesifikasi dan drift

Saat menambah fitur, gunakan [template fitur](../../ui-ux/checklist-fitur.md): kebutuhan pengguna, perubahan alur/status, data yang tersedia, efek tombol, batas privasi, tes, dan acceptance. Cantumkan code commit dan revision MagicPath yang dibandingkan. Dokumentasi harus membedakan: sudah ada di kode; perubahan tampilan yang ditetapkan; peningkatan UX belum diterapkan; serta perilaku prototipe yang bukan kontrak produksi.

Keputusan drift B-TK-1 yang harus konsisten di dokumen pendamping: tidak lagi “semua masa otomatis”; tidak lagi mengecualikan seluruh PDF secara mutlak; hasil tidak selalu satu workbook per jenis; preserve humor/teks khusus; API consent dan semantik Escape/X mengikuti baseline; COMPLETE hanya subset. Perbarui `docs/ui-ux/README.md`, katalog bahasa, dan pola status bersama spesifikasi agar dua pedoman aktif tidak bertentangan.

Ketika `main` bergerak, bandingkan minimal App/controller/interaction/worker/output/runtime, tes consent/teks, dan perubahan output/PDF sebelum implementasi. Tidak perlu merancang ulang B jika hanya CI yang berubah; tetapi perubahan event/selection/output harus direkonsiliasi sebelum membuat kode.

## 18. Bukti dan batas dokumen ini

Sumber dan tes baseline serta source TSX/CSS MagicPath B dibaca. Pratinjau tersimpan MagicPath diperiksa untuk struktur visual; belum ada pengujian interaksi semua state di browser, pengukuran aplikasi, atau uji Windows pada pekerjaan spesifikasi ini. Tidak ada perubahan MagicPath atau kode produk. Spesifikasi menyediakan keputusan dan kriteria uji, bukan klaim implementasi sudah bekerja.

Baseline UI mempunyai blob `6fdae0910c3883ae9f7fa6b7e0f647020a0d520f`; controller `1d4c15b61e2071688ae82b29e6a85c1ada2a1dea`; interaction `a431e63ca8674bc620f9f53585bf1ecb6c2d2aba`; worker `bf184f0692e0be3efc2db52f823fa0acf0c39baf`; events `05f1816c21a2592f46f23170114149d049525751`; runtime `fdba1701a57dea6769813f3927a26078df409147`. Ini identitas sumber, bukan hasil build.

**Keputusan berikutnya:** review B-TK-1, terutama penyesuaian prototipe terhadap pemilihan SPT, consent penggantian, PDF, dan teks yang dikunci. Setelah disetujui, turunkan irisan pertama menjadi rencana implementasi dan tes runner.

[app]: https://github.com/cepeter-job/spt-downloader/blob/be67f5153a07ce100048d67191a02ca1d0fca1db/spt_desktop/app.py
[controller]: https://github.com/cepeter-job/spt-downloader/blob/be67f5153a07ce100048d67191a02ca1d0fca1db/spt_desktop/controller.py
[interaction]: https://github.com/cepeter-job/spt-downloader/blob/be67f5153a07ce100048d67191a02ca1d0fca1db/spt_desktop/interaction.py
[worker]: https://github.com/cepeter-job/spt-downloader/blob/be67f5153a07ce100048d67191a02ca1d0fca1db/spt_desktop/worker.py
[events]: https://github.com/cepeter-job/spt-downloader/blob/be67f5153a07ce100048d67191a02ca1d0fca1db/spt_desktop/events.py
[output]: https://github.com/cepeter-job/spt-downloader/blob/be67f5153a07ce100048d67191a02ca1d0fca1db/spt_desktop/output.py
[runtime]: https://github.com/cepeter-job/spt-downloader/blob/be67f5153a07ce100048d67191a02ca1d0fca1db/spt_desktop/runtime.py
[auth]: https://github.com/cepeter-job/spt-downloader/blob/be67f5153a07ce100048d67191a02ca1d0fca1db/spt_desktop/auth.py
[agents]: https://github.com/cepeter-job/spt-downloader/blob/be67f5153a07ce100048d67191a02ca1d0fca1db/AGENTS.md
[readme]: https://github.com/cepeter-job/spt-downloader/blob/be67f5153a07ce100048d67191a02ca1d0fca1db/README.md
[selection-tests]: https://github.com/cepeter-job/spt-downloader/blob/be67f5153a07ce100048d67191a02ca1d0fca1db/tests/test_desktop_selection_gui.py
[text-tests]: https://github.com/cepeter-job/spt-downloader/blob/be67f5153a07ce100048d67191a02ca1d0fca1db/tests/test_desktop_requested_text.py
[report]: https://github.com/cepeter-job/spt-downloader/blob/be67f5153a07ce100048d67191a02ca1d0fca1db/docs/superpowers/reports/2026-10-13-feature-acceptance.md
[tkinter]: https://docs.python.org/3.14/library/tkinter.html#threading-model
[ttk]: https://docs.python.org/3.14/library/tkinter.ttk.html
[wcag]: https://www.w3.org/TR/WCAG22/
[keyboard]: https://learn.microsoft.com/en-us/windows/apps/design/accessibility/keyboard-accessibility
