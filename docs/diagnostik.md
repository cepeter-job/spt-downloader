# Log diagnostik untuk bugfixing

[Kembali ke dokumentasi](README.md) · [Gejala dan tindakan awal](pemecahan-masalah.md)

Log ini menjelaskan urutan pekerjaan dan lokasi error aplikasi. Log **bukan** salinan capture, audit pajak, bukti kelengkapan SPT, atau telemetry. Data tetap lokal; aplikasi tidak mengirim log ke layanan eksternal.

## Mengambil log yang relevan

1. Jalankan build yang sedang diperiksa, ulangi masalah satu kali, lalu catat waktu/tahap dan tindakan terakhir tanpa mencantumkan NPWP atau akun pada laporan publik.
2. Buka **Pengaturan → Buka folder log**. Lokasi default Windows adalah `%LOCALAPPDATA%\SPTDownloader\logs`. Jangan mengirim folder `jobs`, `profile`, checkpoint JSON atau hasil pajak bersama log.
3. Cocokkan `job_ref` antara file GUI dan worker. `session_id` membedakan proses; `sequence` dan waktu UTC membantu mengurutkan kejadian. `job_ref` adalah digest ID job, bukan NPWP atau ID SPT.
4. Sertakan commit/artifact build, versi Windows/browser, langkah reproduksi, hasil yang diharapkan, dan hasil yang terjadi. Tinjau berkas sebelum membagikannya; jumlah/timing aktivitas tetap informasi operasional privat.

Nama file: `diag-<gui|worker|cli>-<session UUID>-<segmen>.jsonl`. Satu baris adalah satu objek JSON. File `.active` dan `.diagnostics.lock` dipakai untuk koordinasi lokal, bukan isi laporan bug.

## INFO, DEBUG, dan OFF

Worker baru membuka sink setelah menerima izin mulai; Stop/EOF sebelum izin tidak membuat folder workspace/log. GUI tetap mencatat rekonsiliasi proses.

Default **INFO** mencatat lifecycle, fase berdurasi, persetujuan, terminal yang disahkan controller, serta error. **DEBUG** menambahkan progres/count dan penolakan protokol. Tidak ada level yang membuka akses ke data pajak atau rahasia.

PowerShell, sebelum membuka executable dari terminal yang sama:

```powershell
$env:SPT_LOG_LEVEL = 'DEBUG'
.\SPTDownloader.exe
```

Untuk CLI, variabel yang sama berlaku ketika menjalankan `coretax.py`. Hapus variabel setelah reproduksi:

```powershell
Remove-Item Env:SPT_LOG_LEVEL
```

`SPT_LOG_LEVEL=OFF` menonaktifkan diagnostik baru, **bukan** verifikasi, audit workbook, checkpoint atau pemeriksaan keamanan. Nilai tidak dikenal kembali ke INFO. Untuk lokasi diagnostik alternatif, set `SPT_LOG_ROOT` ke direktori absolut khusus; file masuk ke subfolder `logs` di dalamnya. Jangan memilih folder yang berisi hasil pajak/profil. Root relatif atau symlink/junction/reparse ditolak. Default CLI Linux memakai `~/.local/state/spt-downloader/logs`.

## Isi yang dicatat

Schema 1 memuat waktu UTC, level, role, ID session, referensi job, urutan, durasi, fase, status tetap, counter terbatas, dan exit/OS error code jika sah. Versi Python serta status frozen membantu membedakan lingkungan. Lokasi error berupa token file/fungsi aplikasi dan nomor baris, maksimal delapan frame.

Build baru juga mencatat `build_commit`, `build_run_id`, dan `build_run_attempt` dari metadata publik yang ditanam saat packaging dan disalin ke worker. Metadata dibatasi ukuran dan skemanya; file tidak sah atau source tanpa metadata menghasilkan `build_commit=unknown`, tanpa menebak dari environment. Cocokkan koordinat ini dengan artifact yang dipakai. Field tambahan bukan jaminan keaslian file log; provenance tetap diverifikasi pada distribusi.

Pesan exception, chain, locals, baris kode, path lengkap, URL, NPWP, tahun/nama wajib pajak, akun, password, cookies, token, header/body HTTP, nilai form/tabel, payload consent dan nama/hash PDF **tidak disalin**. Field dan nilai yang tidak termasuk allowlist dibuang tanpa memanggil `str()` pada objek tak dikenal. Tidak ada perekaman browser/network atau penyalinan raw stdout/stderr.

`phase.completed` berarti fungsi keluar normal, **bukan** bukti hasil pajak COMPLETE. Gunakan `worker.finished` yang berasal dari rekonsiliasi controller, beserta Audit hasil untuk lingkup data. Error yang sudah ditangani sebagai PARTIAL tetap mempunyai event diagnostik tanpa mengubah status bisnis.

## Diagnostik pemeriksaan pembaruan

`update.check` merekam status pemeriksaan **manifest publik** Cloudflare Worker
pada log **GUI**, baik ketika dijadwalkan otomatis maupun saat pengguna
memilih **Cek pembaruan**. Field `update_check_trigger` hanya `automatic`
atau `manual`. Field `update_check_result` dibatasi pada kategori berikut:

- `started`: identitas build lokal tersedia dan pekerjaan pemeriksaan
  asinkron dijadwalkan; belum berarti jaringan berhasil.
- `up_to_date`: respons valid tidak mengumumkan build yang lebih baru
  daripada yang terpasang.
- `update_available`: manifest valid mengumumkan run ID yang lebih baru;
  bukan jaminan tanda tangan, review, atau kelayakan instalasi.
- `unavailable`: jaringan, HTTP, skema/manifest, atau pemanggilan gagal;
  tidak ada teks exception atau alamat yang dicatat.
- `invalid_build`: metadata build terpasang tidak bisa diverifikasi,
  sehingga aplikasi **tidak** menghubungi Worker.
- `deferred_active`: pemeriksaan ditunda ketika tugas SPT masih aktif;
  satu event saja untuk rangkaian retry otomatis per pekerjaan.
- `already_pending`: permintaan baru diabaikan karena pemeriksaan
  sebelumnya belum selesai.
- `notice_deferred`: respons memuat manifest baru, tetapi dialog
  pemberitahuan menunggu selesainya pekerjaan/interaksi/Pengaturan;
  event tidak diulang pada setiap polling dialog.

Untuk hasil yang berasal dari jaringan, `duration_ms` mengukur durasi
panggilan pemeriksaan di thread latar, **tidak** termasuk penjadwalan Tk,
penundaan dialog, atau navigasi browser. Tidak ada durasi pada event yang
hanya memeriksa status UI. Bahkan jika `update_available` tercatat,
aplikasi **tidak otomatis mengunduh atau memasang** executable. Log tidak
memuat URL Worker/OneDrive, respons/manifest mentah, commit atau run ID
pembaruan yang diumumkan, token, data pajak, atau error message. Metadata
build terpasang yang sudah diizinkan oleh schema log tetap tersedia pada
envelope umum. `SPT_LOG_LEVEL=OFF` menonaktifkan event ini, dan ketiadaan
event pada log lama tidak membuktikan bahwa update check tidak dijalankan.

## Diagnostik sumber MPN

`mpn.source_rejected` menyimpan penolakan sumber pertama dengan tahap tetap
`mpn_source_stage`. Untuk tahap `ownership`, build baru juga mencatat
`mpn_ownership_reason` dari pemeriksaan pertama yang gagal:

- `navigation`: komit, identitas Document, atau attempt milik capture belum
  terbukti atau berubah.
- `frame`: frame request berbeda dari frame utama saat pemeriksaan.
- `method`: metode request bukan GET.
- `page_route`: halaman saat ini berbeda dari rute ledger yang diikat.
- `request_url`: URL request berbeda dari URL yang ditahan saat admission.
- `resource_kind`: jenis resource berbeda dari jenis saat admission.

Kategori awal mengikuti urutan pemeriksaan yang sudah ada sebelum pembacaan
response/body. Pemeriksaan ulang setelah RPC, termasuk pembacaan body, dapat
menolak perubahan kepemilikan yang terjadi selama pembacaan; byte tersebut
tidak diterima sebagai bukti sumber. Nilai yang dibandingkan tidak dicatat.
Penolakan pada tahap lain tidak menerima kategori ownership. Penolakan fatal
berikutnya tetap menghentikan capture meskipun event pertama sudah tercatat.
Log lama yang hanya menyebut `ownership` belum membuktikan predicate tertentu;
diagnostik ini sendiri belum membuktikan masalah live telah selesai. Penyiapan
sesi Accounting mendahului capture dan tidak menyumbangkan bukti sumber;
status akhir tetap memerlukan inventaris MPN, detail, drain, dan publikasi.

### Tahap penolakan Corporate JSON / MPN (#143)

Pada build setelah perbaikan observabilitas #143, `corporate.observe_unavailable`
menandai kegagalan eligibilitas observer Corporate sebelum fallback penuh DOM
dengan `corporate_observer_stage` terbatas: `build`, `tabs`, `tab`,
`panel`, `form`, `l3`, `l11a`, `l1d`, `l8`, `l7`,
`l11c`, `grid`, `induk`. `form_ordinal` hanya indeks tab
nonnegatif yang teramati, bukan nama form/isi. Tidak ada event bila native
Corporate verified. Khusus `corporate_observer_stage=l3`, sub-observer
mencatat `corporate_l3_reason` dari kategori tetap yang memisahkan pin/build,
hash sumber MAIN (`main_digest`), hash sumber VENDOR (`vendor_digest`),
jumlah tabel L3 (`table_count`), lifetime komponen awal/akhir,
sumber skrip, struktur form/grid, rantai owner,
judul/metadata tabel, paginator, bentuk request, footer, offset dan katalog
referensi. Misalnya `table_structure`, `reference_request`, dan
`grid_or_footer_missing`. Nilai kategori tidak mengambil string, ID,
hash/URL atau isi dari browser. Field yang tidak ada bukan bukti tahap sukses.
Refusal tetap mengembalikan `None` dan memilih fallback seluruh record ke DOM;
verifikasi sumber, identitas, dan pembatasan tetap wajib.

### Waktu tahap observer Corporate

`corporate.observe_timing` mencatat waktu per segmen tahap observer
(`corporate_observer_stage` + `duration_ms` + `form_ordinal`), tanpa nilai,
URL, digest, atau status halaman. Catatan diterbitkan idempoten pada jalur
sukses maupun penolakan (segmen berjalan ditutup terlebih dahulu), sehingga
pelacakan performa (#208) tetap memberi data pada live run yang gagal.
Catatan ini tidak mengubah hasil adopsi JSON.

### Gate bukti L7 raw-negative Corporate

`corporate.l7_negative_gate` mencatat `corporate_l7_negative_gate` — kategori
tetap `protocol`, `pins`, `enabled`, `structure_start`, `environment`,
`builds`, `table`, `route`, `enabled_end`, `structure_end`, atau `lifetime` —
setiap kali bukti opsional `raw_negative_projection` L7 tidak tersedia. Event
ini hanya dinamai pada penolakan; bukti yang lengkap tidak mencatat apa pun.
Tidak ada URL, digest, route, identitas, atau nilai yang direkam, dan
ketersediaan bukti opsional tetap tidak mengubah jalur non-negatif v1.

`corporate.l7_capture_gate` menamai lapisan custody di bawah gate
`structure_start`: kategori tetap `component`, `component_end`, `history`,
`flagged`, `handle_form`/`handle_grid`/`handle_table`/`handle_tab`/`handle_panel`,
`state_malformed`, `incomplete`, serta `js_*` untuk alasan skrip riwayat anak L7
(`budget`, `chain`, `enabled`, `roles`, `shape`, `document`, `removed`, `depth`,
`visibility`, `identity`, `boundary`, `unknown`). Alasan `js_*` berasal dari
skrip halaman dan hanya dipetakan ke enum; teks bebas, node, atribut, dan nilai
tidak pernah dicatat. Event ini tidak mengubah hasil adopsi JSON.

`corporate.l7_history_arm` mencatat prasyarat pemasangan skrip riwayat L7 pada
saat View diperiksa: `clear` (tidak ada root/host corporate di dokumen),
`occupied` (sudah ada root/host corporate), `document` (dokumen yang dipertahankan
bukan dokumen aktif), atau `unsupported`. Event ini tidak memuat elemen, atribut,
URL, atau nilai, dan tidak mengubah admission.

`native.paginator_timing` (Stage 0b untuk #161/#208) merekam *agregat per satu
pemanggilan* paginator native yang sudah ada, bukan satu event per halaman.
Field `native_paginator_step` dibatasi ke `reset_probe`,
`reset_click`, `reset_marker_wait`, `reset_overlay_wait`,
`advance_probe`, `advance_click`, `advance_marker_wait`,
`advance_overlay_wait`, `other`, dan `total`. Probe membaca hanya
status serta teks marker paginator dari *p-table* yang sama, tidak membaca
isi tabel bisnis. Probe dan klik masing-masing satu evaluasi browser dengan
verifikasi ulang kepemilikan; tombol dan marker ambigu/berubah tetap ditolak.
Keduanya mengurangi panggilan locator terpisah per halaman tanpa mengubah
aksi Next/Previous, sumber/request, pilihan rows-per-page, atau page limit.
`duration_ms` adalah waktu aktual di boundary Playwright; `count` jumlah
operasi untuk tahap itu. `total` memuat satu panggilan, sedangkan `other`
adalah residual nonnegatif termasuk pemeriksaan host dan pembuangan
handle, **bukan otomatis waktu jaringan**. Pada jalur baru, `*_probe`
mengisolasi waktu inspeksi marker + kontrol native yang sebelumnya ikut
`other`; `*_click` mencakup validasi ulang dan pemanggilan click.
`*_overlay_wait` tetap mempertahankan waktu stabilisasi 180 ms per
transisi; `*_marker_wait` menggunakan pemeriksaan tiap 100 ms. Tidak
boleh menyimpulkan latensi backend secara langsung dari keduanya. Tahap yang tidak dijalankan tidak menghasilkan
event (kecuali `other`/`total`). Semua tahap tetap direkam saat refusal,
Stop maupun exception sepanjang owner awal berhasil diperoleh, tanpa mengubah
aksi atau deadline. Event ini dipakai bersama urutan
`corporate.observe_timing(l3)`; karena paginator dipakai juga oleh observer
lain, jangan mengatribusikan semua event `native.paginator_timing` ke L3
tanpa konteks rangkaian waktu yang cocok. Tidak ada nilai baris, label,
request, response, query parameter, URL, identity, atau file path yang dicatat.

Tahap ini belum memisahkan kronologi request/response maupun membuktikan
pilihan ukuran halaman native. Live acceptance membutuhkan run yang cocok
dengan build dan scope yang diuji serta validasi source/parity/PDF terpisah.

### Rincian penantian First yang sudah ada (#161)

Mulai build yang memuat perubahan ini, event `table.first_page_timing`
muncul otomatis untuk tabel besar (`max_page_size >= 250`)
selama diagnostik worker aktif, **tanpa flag / browser call baru**.
Masing-masing empat tahap asli hanya direkam maksimal sekali pada
jalurnya: `pilot_label_lookup` (selector label ukuran halaman yang
sudah dicari), `pilot_label_text` (pembacaan label yang sudah terjadi),
`first_overlay_wait` (wait global hidden yang sudah ada, timeout
45.000 ms), dan `first_settle_wait` (jeda Playwright 180 ms yang
sudah ada, hanya jika wait pertama sukses). Setiap event memiliki
`table_first_page_outcome=returned|raised`,
`duration_ms`, `table_rpc_thread_cpu_ms` dan ordinal form/tabel.
Waktu `first_overlay_wait` adalah waktu host Python,
**bukan** lamanya overlay target sebenarnya atau waktu jaringan.

Jumlah `table_first_page_finished_requests` menunjukkan hanya berapa
request-object yang teramati *selesai* selama wait First yang asli.
`table_first_page_last_finish_ms` adalah selisih waktu lokal sejak
awal wait hingga event finish terakhir, hanya jika ada yang selesai.
Callback request-object berasal dari observer yang **sudah ada**,
tidak mencatat URL, header, response, isi tabel, kode sumber atau ID.
Lifecycle itu bersifat **unbound**: request yang selesai tidak
membuktikan overlay/tab target siap, dan tidak mengisolasi backend,
Chromium, Node, jaringan, atau penyebab timeout. Jika callback tidak
lengkap/drop, bukti tetap tidak lengkap, bukan 0 network activity.

Pemisahan ini tidak mengganti locator global yang memang sudah dipakai
oleh `wait_idle(page)`. Overlay lain di tab yang sama mungkin
memengaruhi wait, tetapi identitas overlay **tetap tidak diketahui**
tanpa pembacaan DOM tambahan (tidak diizinkan dalam PR diagnostik ini).
Pada timeout, tahap settle **tidak boleh** muncul. Pada Stop atau error,
exception asli tetap diteruskan; tidak ada retry, polling lain,
perubahan deadline 180 detik, klik tambahan atau promosi PARTIAL menjadi
COMPLETE. Scope event hanya pada penantian setelah klik First; bukan
semua `wait_idle` di aplikasi. `table.reset_timing:first_idle` tetap
merupakan durasi inklusif; jangan jumlahkan dengan kedua tahap anak
yang baru. Uji penerimaan live perlu membuktikan identitas build,
event lengkap dan jumlah Playwright call tidak berubah, bukan
mengasumsikan root cause dari satu run.

### Pembagian waktu reset tabel DOM besar (#161)

`table.reset_timing` hanya diterbitkan untuk tabel dengan batas
`max_page_size >= 250` (jalur besar L3-B), tanpa pembacaan DOM tambahan.
`table_reset_step` berupa kategori tetap:

- `size_action`: satu pemanggilan pemilihan ukuran halaman yang **sudah ada**,
  termasuk menunggu idle jika ukuran berubah; `count=1` berarti pemanggilan,
  bukan jumlah perubahan atau request.
- `pilot_guard`: verifikasi ulang ukuran halaman yang **sudah ada**
  setelah `size_action` (termasuk locator/label asli). `count=1`
  berarti verifikasi dipanggil, bukan keberhasilan atau perubahan ukuran.
- `first_lookup`: hanya pencarian tombol First yang sudah ada.
  `count=1` berarti kontrol ditemukan, bukan diklik.
- `first_click`: hanya validasi dan klik First yang sudah ada.
  `count=1` berarti klik telah berhasil diajukan, bukan respons selesai.
- `first_idle`: penantian loading overlay global dan 180 ms settle
  **asli**, sesudah klik First. `count=1` berarti wait dijalankan
  meskipun timeout; tidak mengklaim overlay milik tabel ini.
- `first_navigation`: interval inklusif pencarian, klik jika tersedia,
  dan `wait_idle` aslinya; `count=0/1` berarti jumlah klik First yang
  berhasil diajukan. **Jangan menjumlahkan** tahap ini dengan tahap anak.
- `previous_stop_check`, `previous_lookup`, `previous_state`,
  `previous_click`, `previous_idle`, `previous_verify`, dan
  `previous_limit_lookup`: durasi agregat setiap jenis operasi
  **yang sudah ada** di loop Previous. `count` berarti jumlah
  pemanggilan/percobaan tahap, **bukan** jumlah respons atau klik sukses.
  Semua tahap hanya diterbitkan sekali per tabel besar, termasuk saat
  exception/Stop; tahap yang belum dicapai tidak diterbitkan.
  `previous_limit_lookup` adalah pemeriksaan akhir setelah loop,
  bukan permintaan tambahan. Jumlah klik Previous sukses tetap
  di `previous_rewind.count`.
- `previous_rewind`: seluruh loop Previous, verifikasi state,
  `wait_idle` serta pemeriksaan limit yang sudah ada. `count` adalah
  jumlah klik Previous yang berhasil diajukan, **bukan** bukti respons
  server atau total halaman; event tetap dicatat pada Stop/exception.
- `total_pre_read`: total waktu persiapan sebelum memulai pembacaan
  sel halaman pertama (`TABLE_JS`). Tidak termasuk biaya snapshot
  pertama, yang sudah tercatat sebagai `table.page_timing:initial`.

Semua catatan hanya membawa `form_ordinal`, `table_ordinal`,
`duration_ms` dan `count` yang sudah lolos sanitizer. Tidak ada label
paginator, isi/identitas baris, URL, request atau nama dokumen.
Durasi berasal dari boundary host/Playwright dan tidak dengan
sendirinya membuktikan waktu jaringan. Event tiap tahap tidak boleh
dijumlahkan begitu saja dengan `total_pre_read`, karena total mencakup
semua tahap. Penyebaran event hanya pada large-table candidate mencegah
log spam untuk tabel kecil.

### Probe RPC browser/renderer opsional untuk L3-B (#161)

Pengukuran ini **tidak berjalan secara default**. Pada run diagnostik
yang secara eksplisit diizinkan, aktifkan environment proses
`SPT_DIAG_DOM_RPC_PROBE=1` bersama log diagnostik pada **proses GUI
sebelum worker dijalankan**. Hanya nilai tepat `1` diteruskan oleh
allowlist worker; flag ini tidak diteruskan ke bootstrap/uv, dan tidak
tersedia pada job yang sudah berjalan. **Setiap run worker** dilabeli
`table_rpc_probe_enabled=true/false` pada `session.started`,
`operation.started`, `operation.finished`, dan `session.closed`,
berdasarkan flag worker saat session dimulai. `true` berarti mode
investigasi diizinkan, **bukan** bukti probe benar-benar dijalankan:
budget guard dapat melewati keduanya sehingga tidak ada event
`table.browser_rpc_probe`. Pisahkan seluruh run berlabel `true`
dari run baseline, termasuk pada analisis COMPLETE/PARTIAL,
waktu eksekusi, dan perbandingan baris. **Jika field
`table_rpc_probe_enabled` hilang pada event batas run, statusnya
UNKNOWN, bukan `false`.** Logger dapat kehilangan event saat antrean
penuh, record lebih dari 4096 byte, atau logging gagal. Run dengan
penanda hilang/tidak lengkap **tidak boleh** diperlakukan sebagai
baseline tanpa probe atau dimasukkan ke perbandingan performa maupun
kelengkapan. Tidak adanya event `table.browser_rpc_probe` juga
bukan bukti probe dimatikan. Penanda ini hanya metadata
log worker dan tidak ditambahkan pada `run.json`/workbook.

Pada tabel dengan
`max_page_size >= 250`, fungsi baca-saja akan mencoba maksimal dua
RPC tambahan terhadap **owner paginator awal**: satu tepat sebelum
`previous_lookup` pertama dan satu sebelum `previous_limit_lookup`
akhir. Probe pertama **dilewati** jika sisa budget asli kurang dari
**120 detik**; probe sebelum limit dilewati jika kurang dari **150 detik**.
Kedua ambang melampaui observasi panggilan Previous terlama **108,80 detik**
dengan cadangan lebih besar di tahap akhir. Observasi ini hanya satu
sampel dan bukan batas maksimum latensi browser; guard 150 detik
**sering melewati probe tahap akhir pada run lambat**, sehingga hasil
diagnostik bisa kosong. Catat skip ini dalam laporan run.
Tahap yang dilewati tidak membuat event.
Jika loop Previous memiliki banyak klik, tidak dilakukan probe per klik.

Event `table.browser_rpc_probe` hanya membawa:
`table_rpc_stage` (kategori tetap `before_previous_lookup` atau
`before_previous_limit_lookup`), `table_rpc_state`
(`present`/`absent`/`detached`/`unavailable`/`error`),
`form_ordinal`, `table_ordinal`, `duration_ms` (waktu host
dalam Python), `table_rpc_renderer_ms` (durasi selector
`performance.now()` **di dalam eksekusi JS**) dan
`table_rpc_residual_ms=max(0, duration_ms-renderer_ms)`. Dua field
terakhir tidak diterbitkan jika respons tidak valid/terjadi error.
Semua field melalui allowlist diagnostik. Tidak ada teks HTML, hasil
selector, label, baris, nilai SPT, URL, header, body atau identitas.

**Interpretasi:** residual bukan pengukuran antrean browser murni;
ia juga memuat driver Playwright, serialisasi, IPC/transport, scheduling
dan pembulatan jam. Probe sendiri merupakan operasi terpisah dari
`query_selector` asli; hasilnya **bukan durasi eksekusi JS dari
`query_selector` asli**. Korelasikan dengan `table.reset_timing`
untuk mencari indikasi macet di luar eksekusi selector, bukan
menyatakan akar sebab. Mode opt-in menambah hingga dua panggilan yang
dapat menghabiskan waktu capture dan mengubah jumlah halaman atau
status PARTIAL. Batas awal 120/150 detik **bukan timeout RPC**:
`evaluate` sinkron yang sudah dijalankan tidak dapat diputus saat
browser/transport macet. Run dengan probe tidak boleh digunakan sebagai
tolok ukur peningkatan performa atau bukti COMPLETE. Keputusan klik
tetap mengikuti jalur asli, tetapi konsumsi budget bisa mengubah hasil
akhir tabel. Capture, Stop, source proof, batas 180 detik dan verifikasi
publikasi tidak diberi kewenangan baru oleh probe. Error probe
disanitasi sebagai WARNING; hanya exception probe yang ditahan.

### Waktu RPC Playwright asli tanpa browser call tambahan (#161)

Pengukuran pasif ini **berbeda** dari `SPT_DIAG_DOM_RPC_PROBE=1`,
yang mengirim probe browser tambahan. Dengan sesi diagnostik normal
dan `max_page_size >= 250`, event `table.existing_rpc_timing`
mengukur panggilan Playwright **yang sudah dibutuhkan scraping**:
`previous_lookup`, `previous_limit_lookup`, `initial_snapshot`,
`cursor_init`, `cursor_advance`, `cursor_poll` dan
`cursor_snapshot`. Event memakai ordinal form/tabel, fixed enum
`table_existing_rpc_stage` dan `table_existing_rpc_outcome`
(`returned`/`raised`), `duration_ms` (wall-clock Python),
`table_rpc_thread_cpu_ms` (CPU thread Python saat memanggil),
dan hanya jika sudah disediakan oleh panggilan asli:
`table_rpc_renderer_ms` serta selisih
`table_rpc_residual_ms`. Tidak ada teks kontrol, isi tabel,
URL, selector, request/response, raw exception maupun identitas
pengguna. Maksimal **48 event per tabel**; saat ambang tercapai,
tidak lagi dicatat, dan drop logger juga mungkin terjadi.
Hilangnya event tidak membuktikan bahwa RPC tidak berjalan.

Tidak ada `evaluate`/locator/handler/CDP/network tambahan, tidak
ada modifikasi JavaScript halaman atau isi capture. CPU thread
Python **tidak** menghitung proses Node Playwright atau Chromium.
Wall-clock tinggi dengan CPU thread rendah merupakan bukti thread
menunggu, **bukan pengukuran spesifik** IPC, antrean Chromium,
Node event loop, serialisasi atau network. Durasi renderer yang
dikembalikan hanya mengukur lingkup JavaScript yang sudah
diinstrumentasi sebelumnya. Perbedaan wall-versus-renderer
mencampur semua latensi di luar lingkup itu. Batas 180 detik,
prioritas Stop, sumber baris, dan COMPLETE/PARTIAL tidak berubah.
Flag run `table_rpc_probe_enabled` tetap merepresentasikan
**probe invasif ekstra** saja, bukan event pasif. Hindari klaim
perbaikan throughput/kelengkapan dari perbedaan run tunggal,
terutama jika digest katalog berubah. Gunakan sebagai dasar
penentuan stage bottleneck untuk investigasi terpisah.

### Sample CPU proses anak milik worker — opt-in, khusus Windows (#161)

Pada build baru, **set `SPT_DIAG_HOST_CPU=1` sebelum menjalankan EXE
dari PowerShell bersih**, dan biarkan
`SPT_DIAG_DOM_RPC_PROBE` *tidak disetel*. Mode ini berbeda dari
probe JavaScript tambahan: tidak ada RPC/DOM/browser command baru.
Flag `table_host_cpu_enabled` pada `session.started`,
`operation.started`, `operation.finished`, dan `session.closed`
membuktikan status opt-in; marker tidak tersedia = **UNKNOWN**.

Untuk tabel besar (`max_page_size >= 250`), tepat sebelum/sesudah
panggilan Playwright yang **sudah ada**, worker mengamati counter
CPU melalui Toolhelp/GetProcessTimes hanya untuk proses anak di
bawah PID worker saat itu. Sampel maksimum: lookup Previous pertama,
tiga `cursor_advance` pertama, dan tiga `cursor_snapshot`
pertama — maksimum **7 pasangan (14 snapshot Win32) per tabel**.
Tidak ada PID, nama executable, path, command line, request atau
konten pajak pada log. Jika seluruh pasangan proses cocok (PID +
creation time + kedalaman), event `table.existing_rpc_timing`
menambahkan `table_host_cpu_state=paired`,
`table_rpc_direct_child_cpu_ms`, dan
`table_rpc_nested_child_cpu_ms` (waktu **CPU kumulatif**,
bukan durasi wall). Apabila gagal mengakses proses, terdapat
kelahiran/keluarnya subprocess, pergantian PID, atau dukungan OS
tidak ada, metrik CPU tidak dipaksakan; event sampling Windows
menggunakan `table_host_cpu_state=unavailable`.
Di luar jatah tujuh sampel, field CPU host sengaja tidak tersedia.

Kedalaman proses 1 sering berisi driver Node Playwright, sedangkan
yang lebih dalam bisa berisi proses Chromium; **itu bukan bukti
identitas proses**. CPU proses anak rendah tidak membuktikan
penyebab antrean IPC, event-loop driver, scheduling Chromium,
blokir jaringan atau rendering. Snapshot Win32 itu sendiri
mengonsumsi sedikit waktu di dalam budget asli 180 detik, meskipun
di luar interval wall-clock RPC. Karena itu, run opt-in **tidak
boleh dibandingkan sebagai benchmark** kelengkapan/kecepatan
dengan run normal. Status COMPLETE/PARTIAL, urutan data, Stop,
sumber, deadline, dan penerbitan berkas tetap sama. Hasil
investigasi harus dibahas sebagai korelasi CPU, bukan kepastian
akar masalah; perubahan mekanisme scraper membutuhkan desain,
tes regresi, dan review tersendiri.

**Tindak lanjut 11 November 2026 (build `df60d3d7`):** operator-run
berakhir PARTIAL pada form 4/tabel 3, `first_idle_timeout` setelah
60,14 detik sejak awal persiapan. `size_action` 1,49 detik dan interval
`first_navigation` 45,18 detik; jeda sekitar 13,5 detik sebelum
`first_navigation` belum dipisahkan. Dua request-object yang teramati
sudah selesai pada timeout; bukti itu tidak memastikan backend idle
atau overlay sasaran. Tahap baru hanya memisahkan batas waktu pemanggilan
yang **sudah terjadi**, tanpa RPC/browser lookup, perubahan klik,
deadlines, dan tanpa mengubah PARTIAL atau native JSON. Live run baru
perlu membuktikan penyebab visual idle sebelum ada perubahan perilaku.

**Tindak lanjut 12 November 2026:** build PR #242 `a781e778`
(tree-identik dengan head `5cadfc9`) menghasilkan `previous_rewind`
53,83 detik dengan **nol klik Previous** pada L3-B form 4/tabel 3.
Tahap baru memisahkan waktu dalam pemeriksaan Stop, locator, state,
klik, idle dan verifikasi yang semula tidak bisa dibedakan. Tabel
kemudian PARTIAL pada 1.500/4.654 baris karena budget 180 detik.
Log sebelumnya sudah memuat `table.page_timing`: DOM read halaman
kedua/ketiga 28,74/33,84 detik dan waktu advance/click hingga
29,52 detik. Instrumentasi baru **bukan** perbaikan latensi atau
bukti penyebab backend. Tidak ada tambahan operasi browser dan
pemilihan sumber/Stop/timeout/PARTIAL tidak berubah.

**Alasan penambahan:** pada 11 November 2026 build `8726aae5`, log
mencatat `first_idle_complete` di 15:01:19 WIB tetapi
`table.page_timing:initial` baru di 15:03:20 WIB (jeda ~121 detik).
Tidak ada event di antara keduanya; loop Previous memang dijalankan
di area tersebut tetapi jumlah klik dan waktunya **belum terbukti**.
Pengukuran baru dibuat untuk membedakan biaya reset dari pembacaan DOM,
tanpa menaikkan batas waktu 180 detik, tanpa mengubah request/klik,
dan tanpa menerima baris yang tidak terverifikasi. Untuk pembuktian
diperlukan operator-run build yang cocok dan hasil terminal tetap jujur.

Pada penolakan `table.elapsed_budget` setelah aksi halaman, event yang sama
sekarang dapat menyertakan durasi host untuk `duration_ms` seluruh aksi,
`table_click_ms`, `table_poll_ms`, `table_idle_ms`, dan
`table_dom_ms` **hanya bila tahap itu sudah dicapai**. Kategori
`before_next_click` dapat mencatat durasi persiapan advance cursor
yang dihentikan sebelum klik. Field tambahan memakai sanitizer numerik
yang sudah ada, tanpa response, marker, URL, atau perubahan keputusan
PARTIAL. Ketiadaan field bukan berarti durasi nol.

`table.initial_loading` (PR #235) merekam tahapan persiapan DOM pertama:
`size_complete`, `size_idle_timeout`, `first_idle_complete`, dan
`first_idle_timeout`, ordinal form/tabel, durasi serta hitungan lifecycle
request-object yang dipantau sementara. Tidak ada URL, NPWP, identitas
record, header, body, isi pajak, nama dokumen, atau nilai DOM yang dibaca.
Request tidak dipetakan secara spekulatif ke pemilik tabel;
`table_request_scope` hanya `other_unbound` atau `unavailable` jika
overflow/registrasi tidak lengkap.

Untuk menjamin jalur Stop dan timeout asli, **tidak ada lagi probe CDP,
panggilan struktural tambahan, WeakRef, setTimeout, maupun penulisan
property window dari diagnostik**. Semua kategori struktural
`table_loading_scope`, `table_loading_first_match`, dan
`table_owner_state` sengaja dilaporkan `unavailable`, termasuk ketika
overlay tabel sendiri, tabel lain atau BlockUI tampak pada fixture.
Tidak dilaporkan `none` atau `target_datatable` tanpa bukti. Pengamatan
request dihentikan dan referensinya dilepas saat persiapan selesai atau
pada kegagalan/Stop melalui cleanup yang sudah dimiliki capture.
Saat logging `OFF`, observer tidak dipasang. Perilaku klik, durasi tunggu,
pemilihan source, PARTIAL, dan pemrosesan panel berikutnya tidak berubah.

Pada tahap `l11a`, `corporate_l11a_reason` memisahkan pin/provider, lifetime,
jumlah tabel, ancestry/grup, paginator, perubahan metadata, bentuk/offset request,
inventori grid dan katalog yang belum teramati. Contoh kategori tetap adalah
`grid_ownership`, `stable_table_metadata`, `grid_request_missing` dan
`reference_request_missing`. `visibility_changed` pada L3/L11-A menolak proof
bila binding tab/panel aktif berubah sesudah observasi. Error yang tidak terduga
di tahap L11-A hanya memakai `observation_error` serta ringkasan tipe/frame yang
sudah disanitasi; tidak menyimpan pesan, caption bisnis, request atau URL.

Untuk penolakan L3 `table_count`, `corporate_l3_table_shape` mengklasifikasikan
hasil pembacaan struktur dari form yang sama hanya sebagai `zero`, `one`,
atau `more_than_two`; angka asli, isi tabel, caption, dan selector detail
tidak dicatat. Syarat **tepat dua tabel** tetap berlaku. Kategori ini
menentukan pemeriksaan kepemilikan DOM berikutnya, bukan izin menerima
bentuk tabel baru atau menonaktifkan fallback. Bila tabel lebih dari dua,
`corporate_l3_extra_layout` hanya mengklasifikasikan pasangan grid sumber
terinspeksi dan tabel tambahan sebagai `reviewed_pair_hidden_extra`,
`reviewed_pair_visible_extra`, atau `reviewed_pair_unproved`. Seluruhnya
tetap menolak JSON native. Tidak ada isi DOM, selector yang bersifat dinamis,
atau jumlah mentah yang dicatat. Untuk kasus `reviewed_pair_visible_extra`,
`corporate_l3_extra_owner` hanya mencatat `nested_in_reviewed_table`,
`reviewed_grid_extra`, `other_form_owner`, `mixed_owners`,
`reviewed_pair_unproved`, atau `no_visible_extra` setelah pemeriksaan
struktur DOM dalam form yang sama. Tidak ada tabel tambahan yang
diterima sebagai data sumber native berdasarkan kategori tersebut.

Pada langkah `open → search` MPN, trial click tetap satu kali uji aksi dan
klik nyata hanya sekali. Klik Search memiliki batas paling lama 5 detik,
selalu dibatasi sisa deadline persiapan 45 detik sejak DOMContentLoaded;
kontrol dropdown dan aksi lain tetap menggunakan batas 1 detik. Timeout
klik nyata tidak dicoba ulang karena permintaan mungkin sudah terdistribusi,
sehingga jalur PARTIAL dan bukti sumber asli tetap berlaku.

Sebelum setiap upaya membersihkan filter periode setelah respons MPN
yang belum terbukti tidak-terfilter, `mpn.unfiltered_refused` mencatat
`mpn_filter_reason` dari pilihan `request_shape`, `date_filter_present`,
`additional_filter`, `cancelled_filter_missing`, atau
`cancelled_filter_modified` serta `mpn_clear_state` dari `ambiguous`,
`absent`, `present`, atau `hidden`. Kategori ini hanya diturunkan dari
bentuk *request sumber asli* dan status kontrol clear yang telah
diinspeksi. Tidak ada nama filter, tanggal, nilai, kode, identitas,
pajak, URL ataupun DOM content yang direkam; nilai enum ini bukan
izin menerima sumber terfilter. Jalur Search dua percobaan, pemilihan
kontrol dan `MpnUnsupported` tetap sama. Status `present` hanya berarti
tombol clear teramati, **bukan** bukti bahwa klik berhasil menghapus
filter pada request berikutnya. Lookup sekarang mencari clear hanya di dalam
satu `ui-grid` asli yang menjadi ancestor dari tepat satu `p-table`
hasil inventory; ini juga mencakup clear yang ditempatkan sebagai
saudara (sibling) tabel di header grid. Lookup tidak memindai
halaman secara umum. Filter sumber harus dibuktikan hilang pada
respons Search berikutnya sebelum inventory digunakan.

`mpn.capture_failed` mencatat kegagalan terminal MPN dengan enum
`mpn_capture_stage`: `session` (pembuatan UI termasuk inisialisasi),
`open` (kesiapan UI), `parent_inventory`, `parent_detail`, atau
`final_drain`. Bila terjadi saat `open`, `mpn_ui_stage` dapat menunjukkan
`navigation`, `owner`, `environment`, `source`, `dropdowns`,
`search`, `period_clear`, atau `ready` (kategori tahap saja,
bukan nilai kontrol). `error` hanya kelas exception dan frame terpilih melalui
sanitizer. `mpn.source_rejected` tetap menjadi sumber pertama untuk
penolakan kepemilikan sumber; event baru bukan penggantinya.

`mpn.paginator_refused` dicatat tepat sebelum penolakan fatal pada
pemeriksaan paginator MPN (`_pages`). `mpn_paginator_kind` hanya
`list` atau `detail`. `mpn_paginator_reason` memisahkan tiga bentuk
yang beragam dalam satu pemeriksaan: `first_mismatch` (offset
`First` snapshot berbeda dari offset yang diharapkan), `filter_changed`
(hanya inventory list yang tidak lagi terbukti tidak terfilter), dan
`binding_changed` (binding request selain `First` berubah).
Prioritasnya berurutan: offset diperiksa pertama, lalu filter pada
list, lalu binding umum; filter yang berubah juga mengubah binding,
sehingga alasan filter didahulukan agar tidak tersamarkan.
`pages` adalah nomor halaman yang ditolak. Identitas query
membandingkan request tanpa `First` lewat `normalized_mpn_query`:
kunci opsional `CaseSensitive`/`AsString` yang absen diisi dengan
default yang direview (`true`/`false`), sehingga serialisasi
Search yang menghilangkan kunci dan serialisasi paginator yang
menulis default secara eksplisit dianggap query yang sama.
Nilai eksplisit non-default tetap berbeda, dan semua bidang lain
tetap dibandingkan persis. Normalisasi hanya untuk perbandingan;
request mentah dan bukti yang disimpan tidak ditulis ulang. Khusus
`binding_changed`, `mpn_paginator_field` mencatat bidang binding
**pertama** yang berbeda dalam urutan tetap: `taxpayer`,
`record_id`, `rows`, `sort_field`, `sort_order`, `language`,
`filters`, atau `other` untuk kunci tak dikenal; dan
`mpn_paginator_filter_shape` mencatat perubahan keberadaan kunci
opsional `CaseSensitive`/`AsString` pada satu rule filter:
`none`, `<kunci>_added`, `<kunci>_removed`, `both_added`,
`both_removed`, atau `mixed`. Kedua kategori hanya berasal dari
perbandingan bentuk request yang sudah ada, tidak mengandung nilai
pembanding, dan tidak mengizinkan aksi. Dua field ini tidak
direkam untuk `first_mismatch`/`filter_changed`. Tidak ada offset, nilai
request, filter, tanggal, kode, identitas, pajak, URL, atau isi
baris yang direkam; kategori ini hanya menunjukkan bentuk penolakan,
bukan penyebab live-nya dan bukan izin menerima snapshot baru.
`MpnSafetyError` tetap fatal, checkpoint PARTIAL tetap berlaku, dan
`mpn.capture_failed` tetap mencatat tahap terminalnya.

`mpn.catalog_preparation` adalah kategori terpisah selama
navigasi normal *sebelum* source-binding `AccountingUI` dimulai.
`request_seen` berarti sebuah GET yang tepat cocok dengan rute
referensi, method, frame utama dan tipe resource telah *teramati* selama
navigasi; `not_observed` berarti tidak ada GET yang memenuhi syarat.
Event ini **tidak** mengunduh, mengikat, menyimpan atau menerima byte katalog,
dan bukan izin untuk mengambil katalog dari cache/bekas halaman. Listener
sementara selalu dilepas saat navigasi selesai maupun gagal. Gabungkan
kategori ini dengan `mpn.catalog_readiness` pada tahap detail untuk
membedakan kemungkinan katalog dimuat sebelum listener sumber aktif.
Keduanya tetap tidak membuktikan kecocokan identitas pembayaran.

Status tambahan `mpn.catalog_readiness` memisahkan `accepted` (byte referensi
asli berhasil diikat), `observed_unbound` (GET sumber yang memenuhi syarat
teramati tetapi belum ada katalog yang diterima), dan `not_observed`
(tidak ada GET referensi yang memenuhi syarat selama sesi). Ini **bukan**
perintah untuk melakukan fetch baru, memakai cache/browser state, atau
mengganti nama/label. Jika hanya jenis pencatatan DOM berbeda dan inventaris
kode `ACCOUNTING_TYPE` asli tidak tersedia, penolakan dilakukan sebagai
`MpnUnsupported`, bukan mengklaim kontradiksi `MpnSafetyError` yang
belum dibuktikan; tombol detail tetap **tidak** diklik. Mismatch kolom
independen lain tetap fatal.

`mpn.parent_binding_mismatch` dicatat tepat sebelum penolakan fatal saat
identitas baris induk yang terlihat di DOM berbeda dari sumber asli.
`mpn_parent_field` hanya kategori kolom **pertama** yang berbeda:
`accounting_type`, `accounting_detail`, `currency`, `revenue_code`,
`payment_code`, `tax_period`, atau `transaction_number`.
`mpn_parent_secondary_field` adalah kategori kolom berbeda
kedua atau `none` bila hanya satu kolom; `mpn_parent_mismatch_count`
adalah jumlah posisi yang berbeda dengan batas keras 1 sampai 7.
Ketiga kategori berasal dari **perbandingan identitas sumber dan DOM yang
sudah ada**, tidak mengandung nilai pembanding, dan tidak mengizinkan aksi.
Jika katalog tidak ada *namun* kolom lain juga berbeda, `MpnSafetyError`
tetap fatal. Kategori pertama-kedua tidak menjelaskan sendiri mengapa
teks atau data berbeda.

Tidak ada nilai DOM, data sumber, identitas transaksi, nomor pajak, atau
jumlah rupiah di log. Bila `mpn_parent_field=accounting_type`,
`mpn_accounting_type_projection` membedakan `catalog_label` (label dari
referensi asli yang lolos syarat), `raw_code_fallback` (kode ada di inventaris
namun tidak memiliki label yang boleh digunakan), `catalog_missing`
(inventaris tidak tersedia), `code_not_in_catalog` (kode tidak ada dalam
inventaris), dan `source_code_missing`. Kelima nilai adalah enum yang ditetapkan
dalam kode, tidak pernah teks dari Coretax. Semua kategori tetap **bukan**
pembuktian bahwa label atau DOM harus diganti. Kategori mismatch itu sendiri
belum membuktikan apakah perbedaannya berasal dari label/mapping, pergantian data,
atau identitas yang salah; `MpnSafetyError` tetap fatal dan tombol detail
tidak diklik.

State pagination memeriksa seluruh urutan teks node baris dengan
`textContent`, bukan `innerText`. Ini menghindari
permintaan layout browser pada tiap polling, tetapi **tidak** mengubah
`TABLE_JS` sebagai sumber nilai tabel, klik paginator, deadline,
atau aturan PARTIAL; efektivitas di Coretax masih perlu pengujian nyata.

Capture DOM dengan paginator sekarang memiliki **batas elapsed 180 detik per
satu tabel** (bukan per keseluruhan return). Sebelum setiap klik halaman berikutnya,
Stop diprioritaskan lalu batas elapsed diperiksa. Saat habis, tabel menjadi
`PARTIAL` dengan alasan tetap `Table capture elapsed budget exceeded`, data
yang sudah diamati tidak disertifikasi lengkap, dan tidak ada klik pagination
berikutnya. Satu operasi browser yang sedang berlangsung masih tunduk pada
timeout lama hingga selesai; angka ini bukan hard interrupt 180 detik ataupun
izin retry klik yang tidak pasti. Pada saat batas terlampaui,
event `table.elapsed_budget` mengirim enum
`table_elapsed_stage=before_next_click` atau `state_poll` serta
jumlah halaman yang sudah dicatat. Kategori ini tidak menambah
klik, tidak memulihkan data yang hilang, dan belum membuktikan penyebab
waktu lambat. Pembacaan teks sel tabel menggunakan traversal text node
tanpa clone/mutasi DOM dan mempertahankan kontrak pembersihan teks yang
sama; regresi sintetis membandingkan hasil sebelum dan sesudah.
Pada halaman setelah klik paginator, pembacaan DOM kini
memakai batas Playwright maksimal 10 detik dan sisa budget tabel. Apabila
pembacaan itu timeout, event `table.dom_read_failed` dengan kategori tetap
`table_dom_stage=post_pagination` direkam; hanya halaman yang telah lolos
pembacaan sebelumnya dipertahankan sebagai PARTIAL, tanpa retry klik yang
sudah terkirim atau mengarang isi halaman terbaru. Batas ini bukan jaminan
interupsi wall-clock bila proses browser macet. Perlu acceptance live untuk dampaknya.

Tidak ada perubahan pada isi checkpoint, `COMPLETE`/`PARTIAL`, Stop, retry,
atau kebijakan sumber/identitas. Log lama tidak memiliki field baru;
perbandingan memerlukan build yang benar-benar menjalankan versi ini.

## Diagnostik Cek Kredensial

Pada build dengan perbaikan redirect, INFO mencatat `auth.state` dan `auth.result` untuk pengecekan yang sudah membuka browser. Log versi sebelumnya hanya mempunyai fase/status terminal; `LOGIN_BLOCKED` atau `LOGIN_MANUAL` saja tidak membuktikan penyebabnya. Perubahan ini tidak menambahkan informasi ke log lama.

`auth.state` membedakan `waiting_redirect`, `waiting_form`, dan `login_form_ready`. Kombinasi state/origin hanya dicatat sekali per pengecekan, bukan setiap polling. Shell Coretax yang belum menampilkan form tidak langsung dibandingkan dengan origin kredensial: aplikasi menunggu form yang dikenali atau sesi yang teramati, dengan polling kesiapan paling lama lima detik setelah navigasi awal. Form tak aman dan CAPTCHA/MFA tidak dilonggarkan atau dicoba ulang.

`auth.result` menambahkan `reason`, `expected_origin`, `observed_origin`, dan `submitted`. Kedua origin **hanya kategori** `coretax`, `satu`, atau `other`, bukan URL. `submitted=true` berarti satu percobaan klik submit telah dimulai; bukan bukti server menerima password atau login berhasil. Tuple hasil, status IPC, dan channel event worker tidak berubah.

| Reason | Makna |
|---|---|
| `verified` | Satu pengiriman kredensial diikuti marker sesi yang dikenali |
| `origin_mismatch`, `origin_blocked` | Form final berbeda dari origin tersimpan, atau origin tidak diizinkan; bukan alasan memindahkan kredensial otomatis |
| `credential_missing`, `account_mismatch` | Entri origin belum tersimpan, atau identifier berbeda dari Pengaturan |
| `challenge`, `unsafe_form`, `form_changed` | Perlu login manual; form/challenge tidak boleh dilewati |
| `readiness_timeout`, `verification_timeout` | Halaman belum siap sebelum pengiriman, atau sesi belum terverifikasi sesudah pengiriman; **bukan** diagnosis password salah |
| `existing_session`, `existing_home` | Sesi/beranda tersedia sebelum pengiriman; password tersimpan belum diuji |
| `check_error`, `cancelled` | Pengecekan gagal atau dibatalkan; tanpa pesan exception privat |

Aplikasi desktop memakai `LOGIN_ORIGIN` Satu yang tetap: tidak ada pilihan origin pada Pengaturan. Kredensial baru dibaca setelah form Satu dan identifier akun terikat dengan benar. Preferensi origin Coretax lama tidak menjadi alasan memindahkan atau membaca credential lintas-origin; isi akun/password pada Pengaturan lalu Simpan bila entri Satu belum tersedia. Catatan log lama hanya menggambarkan build pembuatnya. Tidak ada fallback lintas-origin, POST langsung, atau pemalsuan Referer.

### Request diblokir saat pengecekan login

`auth.request_blocked` mencatat kategori tujuan (`target_origin`: `satu`, `coretax`, `other`), metode (`GET`, `HEAD`, `POST`, `OTHER`), jenis resource (`document`, `xhr`, `fetch`, `other`), dan alasan tetap (`origin_not_allowed` atau `cross_origin_write`). Kombinasi kategori dicatat sekali per pengecekan; `auth.result.blocked_requests` menghitung seluruh request yang diblokir. Tidak ada URL/path/query, header, cookie, token, atau body request yang dibaca untuk diagnostik ini.

Aturan jaringan tidak dilonggarkan: origin asing dan request non-GET/HEAD ke origin selain origin kredensial tetap ditolak. Counter bukan bukti bahwa request yang diblokir menyebabkan reload loop, dan timeout bukan diagnosis password salah. Gunakan urutan state dan kategori blocking untuk menentukan observasi lanjutan; jangan mengirim HAR mentah atau kredensial.

## Diagnostik pencarian wajib pajak

`search.result` merangkum pengamatan pasif sejak sebelum Enter pada pencarian
sampai baris diverifikasi, timeout, error, atau Stop. Pengamatan hanya mencakup
XHR/fetch baru dari frame utama, ke origin Coretax yang disetujui, ketika dokumen
pencarian terverifikasi masih aktif. Identitas request mengikat respons dan
kegagalan ke jendela tersebut; respons request yang dimulai lebih awal, iframe,
origin lain, gambar dan navigasi dokumen tidak masuk hitungan.

- `search_result`: `matched`, `timeout`, `error`, atau `cancelled`. `matched`
  memerlukan satu baris dengan NPWP literal yang cocok; kecocokan sebagian dan
  duplikat tetap ditolak sebelum Pilih.
- `search_observation`: `complete` bila listener dapat mengamati scope tersebut;
  `limited` bila batas 128 identitas request tercapai dan trafik tambahan
  teramati; `unavailable` bila pengamatan gagal. Pada `limited`, hitungan adalah
  batas bawah. Pada `unavailable`, hitungan yang tidak dapat dijamin dihilangkan.
- `search_requests`, `search_responses`, `search_failed`: jumlah request,
  respons ber-header, dan kegagalan transport yang terikat. Request dapat masih
  menunggu respons saat ringkasan dibuat; respons ber-header juga dapat diikuti
  kegagalan transport. Ketiga hitungan bukan persamaan jumlah yang selalu sama.
- `search_http_1xx` sampai `search_http_5xx`, serta `search_http_401`,
  `search_http_403` dan `search_http_429`: kategori status yang teramati.
- `search_table`: `missing`, `hidden`, `empty`, `rows_present`, atau `unavailable`
  dari struktur tabel pada `.main-content`. Keberadaan baris saja belum
  memverifikasi kecocokan wajib pajak.
- `duration_ms`: durasi jendela pengamatan sebelum snapshot struktur.

Trafik pada jendela ini dapat mencakup aktivitas latar belakang. Status 403/429
memberi petunjuk untuk memeriksa pesan portal; pengamatan ini belum mengikat
respons ke endpoint pencarian tertentu atau membuktikan deteksi bot. Baris yang
sudah cocok tetap dapat diverifikasi meski ada respons latar belakang 403.

Pesan timeout menyebut petunjuk teramati secara terbatas. Worker meneruskan hanya
pesan `TaxpayerSearchTimeout` yang dibangun dari kategori dan template tetap ke
desktop; pesan exception browser umum tetap diganti pesan generik. Jika beberapa
status teramati, petunjuk mengutamakan 429, lalu 403 dan 401; seluruh hitungan
tetap disimpan dalam event. Header/identitas browser
tetap berasal dari browser yang digunakan. Listener dilepas pada semua jalur,
dan Stop melewati snapshot DOM. Budget penantian baris tetap 45 detik dengan
pemeriksaan Stop di antaranya; tidak ada klik atau request ulang tambahan.
Snapshot memakai pembacaan struktur singkat seperti probe panel, sehingga batas
locator bukan jaminan latensi JavaScript/browser yang macet.

Log hanya menyimpan enum, hitungan dan durasi. URL/path/query, NPWP, header,
cookie, token, request/response body, nilai form, teks tabel, pesan exception
dan pesan portal tidak disalin. Hasil pengujian sintetis bukan penerimaan live.

## Snapshot setelah timeout panel

Penantian panel membaca ulang `aria-controls` selama budget yang sama. Bila DOM
mengganti binding, kolektor mengikuti kandidat terbaru yang tunggal, terlihat,
dan dimiliki view yang sama. Panel tersembunyi, ambigu atau milik view lain tetap
tidak ditangkap. Perubahan ini tidak menambah budget atau klik ulang tab.
Setelah binding pernah teramati, atribut yang hilang sementara harus kembali
valid; kolektor tidak beralih ke panel lain yang kebetulan terlihat. Fallback
tanpa ID hanya berlaku untuk tab yang belum pernah memiliki binding dan harus
menemukan tepat satu panel yang benar-benar terlihat, termasuk visibilitas
ancestor. Caption, view pemilik dan binding diperiksa bersama sebelum capture.

`capture.panel_timeout` dicatat pada WARNING sekali ketika budget tunggu panel habis, bukan pada setiap polling. Event ini tidak mengganti `capture.partial` atau mengubah hasil PARTIAL, selector, klik tab, retry, maupun budget tunggu. Durasi `duration_ms` hanya mencakup penantian panel sampai budget habis, tidak mencakup pembukaan detail, pekerjaan sebelumnya, atau pembacaan snapshot sesudahnya.

Snapshot hanya berisi struktur: `panel_controlled` menyatakan bahwa binding `aria-controls` pernah teramati; saat binding hilang sementara, probe memakai ID terakhir yang teramati. `panel_matches` menghitung kandidat dalam view yang sedang dipakai; `document_panel_matches` menghitung kecocokan ID yang sama di dokumen dan **tidak diisi** pada jalur fallback tanpa ID; `tab_views` menghitung `.p-tabview` di bawah `.main-content`. ID sebenarnya tidak pernah masuk log. `tab_state` adalah `selected`, `unselected`, atau `unknown`; yang terakhir dipakai bila asosiasi tab atau atribut pemilihannya tidak tunggal/teramati.

`panel_state` memakai kategori tetap:

| State | Observasi sesudah timeout |
|---|---|
| `missing` | Tidak ada kandidat pada view maupun kecocokan ID dokumen yang teramati |
| `outside_view` | ID memiliki kecocokan di dokumen, tetapi tidak di view yang sedang dipakai |
| `hidden` | Kandidat tunggal tidak mempunyai kotak berukuran positif atau CSS visibility-nya hidden/collapse |
| `visible` | Kandidat tunggal mempunyai kotak berukuran positif dan CSS visibility yang teramati bukan hidden/collapse |
| `ambiguous` | Ada lebih dari satu kandidat dalam view; diagnostik tidak memilih salah satunya |
| `unavailable` | Snapshot gagal/tidak tersedia; counter yang tidak diketahui dihilangkan, bukan ditulis nol |

State merupakan observasi struktur dan geometri saat snapshot, **bukan** salinan keputusan visibilitas internal Playwright atau bukti penyebab timeout. DOM dapat berubah antara kegagalan dan snapshot; `visible` setelah timeout bukan alasan mengulang atau mengesahkan capture. Tidak ada pembacaan nilai form, caption, HTML, URL, atau isi tabel untuk event ini. Logger tetap memfilter enum, tipe dan rentang counter; exception dari probe tidak mengganti timeout asli.

Jika evaluasi probe gagal, `probe_failure=evaluation_error` dan ringkasan `error`
mencatat tipe exception serta frame source yang diizinkan. Pesan exception, DOM,
ID panel, dan nilai form tetap tidak dicatat. `unavailable` pada log lama tidak
menentukan apakah kegagalan berasal dari pencarian view atau evaluasi browser;
field baru hanya tersedia pada run yang memakai build ini.

Probe melakukan satu evaluasi sinkron read-only setelah kegagalan. Batas 100 ms pada `Locator.evaluate` membatasi pencarian view, **bukan** seluruh eksekusi JavaScript atau respons browser yang macet. Ini bukan jaminan latensi keras; mekanisme Stop dan cleanup proses milik aplikasi tetap berlaku. Snapshot juga tidak menambah informasi pada log historis. Penggunaan build diagnostik dan reproduksi live memerlukan persetujuan terpisah; tes sintetis tidak membuktikan timeout live telah diperbaiki.

## Benchmark DOM versus JSON (lokal, tanpa payload)

`detail.source` mencatat `source_requested` (`dom`/`json-first`), `source_used` (`dom`/`json`), dan `source_reason` dari kategori tetap: `dom_requested`, `native_verified`, `capture_incomplete`, `adapter_ineligible`, `coverage_incomplete`, `forms_unavailable`, `unsupported_tax`, atau `checkpoint_reuse`. Ini tidak mencatat string alasan adapter mentah. `tax_kind` hanya `ppn`, `pph21`, `unifikasi`, `corporate`, atau `other`; `ordinal` adalah posisi anonim dalam pilihan job, bukan ID SPT.

Ketika observer PPh21 menolak native coverage (`forms_unavailable`), `pph21.observer_gate` mencatat gate konkret yang mengembalikan `None` dari kategori tetap: `unsupported_tax`, `build_digest`, `tab_set`, `environment`, `tab_disabled`, `tab_caption`, `panel`, `form_root`, `fields`, `grid_structure`, `table_shape`, `total`, `reference`, `reference_bindings`, atau `evaluation_error`. Ini hanya kategori gate — tanpa nilai, offset, identitas, atau payload — dan tidak menggantikan `source_reason`.

Ketika observer Masa menolak native coverage (`forms_unavailable`), `masa.observer_gate` mencatat gate konkret yang mengembalikan `None` dari kategori tetap: `unsupported_tax`, `build_digest`, `tab_set`, `tab_disabled`, `panel`, `form_root`, `fields`, `grid_structure`, `table_shape`, `total`, `reference`, `catalog`, atau `evaluation_error`. Ini hanya kategori gate — tanpa nilai, offset, identitas, atau payload.

Ketika digest build live tidak ada di allowlist terreview `resources/build-pins.json`, `build.unfamiliar_build` mencatat `build_source` (`main`, `article`, `ppn_chunk`, `unifikasi_chunk`) tanpa URL/digest/nilai. Pins adalah data terreview berversi; file hilang/rusak membuat allowlist kosong (fail-closed ke DOM). Update pin = perubahan satu JSON dalam PR terreview dengan bukti pengukuran live, bukan edit konstanta tersebar.

Fase `return_detail` adalah waktu inklusif per record (termasuk restore list, buka View, observer/projection, DOM/PDF dan checkpoint). `list_restore`, `open_detail`, `json_observe`, dan `json_project` memisahkan pekerjaan tersebut; fase `detail` yang lama tetap khusus capture DOM. Fase anak berada di dalam waktu induk: jangan menjumlahkannya lagi. Context ordinal direset sebelum berpindah record/keluar karena error atau Stop.

Completion `return_detail` menyertakan mode hasil, `status` COMPLETE/PARTIAL dan `cached`; `source_used=none` berarti belum ada hasil sumber yang dapat ditetapkan. Source decision dapat tercatat sebelum pekerjaan berikutnya gagal; itu bukan bukti ekspor berhasil. Error/Stop menghasilkan phase.failed/phase.cancelled, bukan completion. `forms`/`grids` menghitung section/table container hasil proyeksi, bukan endpoint unik. `body_rows`/`pages` hanya dicatat bila seluruh tabel menyediakan count eksplisit; field hilang bukan nol. Scalar/tree/grid antara mode dapat memiliki representasi berbeda: samakan scope dan makna counter sebelum membandingkan.

Untuk benchmark, gunakan SPT/model/opsi PDF dan versi build yang sama, pisahkan login/seleksi dan cache reuse, verifikasi status serta mode aktual, kemudian ukur berulang dengan urutan mode bergantian. Jangan membandingkan satu job timeout/PARTIAL dengan job COMPLETE sebagai kecepatan normal. Logging ini tidak menghapus navigasi ulang atau melonggarkan binding identitas dan tidak memberikan klaim peningkatan kecepatan sebelum pengukuran.

Default Pengaturan desktop baru adalah JSON-hybrid; pilihan DOM yang sudah disimpan tetap berlaku. CLI/collector tetap DOM tanpa opsi eksplisit. Log lama tidak memperoleh field benchmark ini secara retroaktif.

### Pengukuran per tabel DOM

Fase `table` mencatat durasi pembacaan satu tabel, termasuk pemilihan ukuran
halaman, reset ke halaman pertama, dan seluruh pagination. `form_ordinal` dan
`table_ordinal` menunjukkan posisi form serta tabel dalam traversal; `ordinal`
tetap menunjuk SPT terpilih. Tidak ada nama form, nama file, URL, atau isi sel
dalam event ini. Cocokkan posisi dengan checkpoint secara privat bila perlu.

Completion tabel menyertakan `pages`, `body_rows`, dan `status` COMPLETE/PARTIAL.
Error dan Stop tetap menghasilkan `phase.failed`/`phase.cancelled`. Waktu tabel
termasuk di dalam `detail` dan `return_detail`, sehingga jangan dijumlahkan
kembali. Banyak halaman yang seluruh jumlah barisnya cocok bukan bukti loop
macet. Bandingkan run dengan cakupan dan build yang sama sebelum menyatakan
percepatan; log lama hanya memiliki durasi detail keseluruhan.

Pada Cek Kredensial, `auth.state` dapat menandai `code_exchange_allowed`,
`code_exchange_failed`, `home_detected`, dan `search_opened` untuk menelusuri
alur Satu → callback Coretax → beranda → pencarian. `auth.request_blocked`
membedakan `request_kind=code_exchange` dari `other`; nilai itu kategori tetap,
bukan URL. Code, state, verifier PKCE, token, header, dan body tetap tidak dicatat.
Pertukaran kode yang diizinkan belum membuktikan login berhasil: hasil akhir
tetap berasal dari `auth.result` dan marker pencarian yang terlihat.

## Pengamatan tambahan login, panel, dan PDF

Pada `auth.state` dengan alasan `code_exchange_failed`, `exchange_failure`
membedakan `fetch_exception`, `http_rejected`, `redirect_rejected`,
`response_url_changed`, `callback_changed`, dan `fulfill_exception`.
Semua nilai berasal dari enum tetap; pesan exception, kode HTTP/body respons,
URL callback, code, state dan verifier tidak disalin. Setelah kegagalan definitif,
pemeriksaan berhenti tanpa menunggu siklus reload berikutnya. Penyebab transport
live tetap harus dibuktikan dari kategori yang teramati pada build tersebut.

Untuk `exchange_failure=fetch_exception`, `transport_failure` menambahkan
subkategori tetap berikut. Nilai ini mempersempit pengamatan, bukan membuktikan
penyebab jaringan, validitas password, atau keberhasilan login.

| `transport_failure` | Pengamatan yang dikenali |
|---|---|
| `timeout` | Tipe timeout Playwright atau penanda timeout yang dikenali |
| `tls` | Penanda kegagalan TLS/sertifikat yang dikenali |
| `dns` | Penanda `getaddrinfo` untuk kegagalan resolusi nama |
| `proxy` | Penanda kegagalan koneksi/autentikasi/handshake proxy yang eksplisit |
| `connection` | Penanda koneksi ditolak, terputus, atau tidak terjangkau |
| `context_closed` | Penanda page/context/browser ditutup atau request context dibuang |
| `unknown` | Exception atau format yang tidak dikenali dengan aman |

Pengenalan memakai tipe error Playwright dan paling banyak 512 karakter dari
baris pertama pesan bertipe string, dengan pola yang terikat pada awal pesan.
Isi pesan tetap hanya diproses di memori dan tidak disalin ke diagnostik. URL,
call log, chain, header dan body tidak dipakai sebagai sumber penanda; exception
atau nilai yang tidak dikenal tidak diubah menjadi string. Format baru atau
ambigu tetap `unknown`. Kegagalan HTTP/redirect/callback/fulfill mempertahankan
`exchange_failure` yang sudah ada tanpa subkategori transport tambahan.
Aturan origin, satu percobaan, tanpa retry/redirect transport, batas waktu,
verifikasi sesi dan prioritas Stop tetap berlaku.

Fase `panel_ready`, `accordion_expand`, dan `panel_extract` memisahkan penantian
panel, pembukaan accordion, serta pengambilan field/teks. Posisi form memakai
`form_ordinal`; nama form atau isi field tidak dicatat. Durasi fase anak termasuk
di dalam `detail`, bukan tambahan waktu yang boleh dijumlahkan kembali.

`pdf.discovery` mencatat jumlah tabel lampiran/kontrol, kategori kontrol
(`anchor`, `button`, `input`, `other`, `none`), keberadaan href/handler sebagai boolean,
dan hasil binding (`bound`, `unbound`, `ambiguous`, `no_control`). Tidak ada
nama file, href, HTML, label bebas, atau isi lampiran dalam event. Hasil ini
tidak memberi izin klik tambahan: kontrol yang belum didukung tetap PARTIAL.
Capture lama tanpa struktur kontrol tidak dapat dipakai untuk menebak endpoint.

## Batas penyimpanan dan kegagalan

Ukuran file maksimal 1 MiB, maksimal tiga segmen per session. Retensi tujuh hari dan anggaran 32 file pada folder log; file regular milik logger yang tidak aktif dibersihkan paling tua dahulu. File asing, hardlink, symlink/reparse dan session aktif tidak dihapus. Jika kapasitas tidak dapat direklamasi dengan aman, logger tidak menambah file.

Antrian maksimal 256 record, ukuran record maksimal 4 KiB. Saat sink lambat, producer tidak menunggu I/O; `dropped` adalah hitungan event yang tidak dapat dicatat. Flush/close menunggu maksimal dua detik. Kehilangan event saat proses dipaksa berhenti, antrean penuh, storage rusak atau disk hang tetap mungkin. Retensi bekerja saat file baru dibuat, bukan lewat pekerjaan terjadwal.

Tidak ada jaminan forensik, at-rest encryption, zero filesystem latency, ataupun ketahanan terhadap administrator/proses lain yang menguasai akun. DirectoryGuard memegang direktori Windows; implementasi portable melakukan pemeriksaan identitas tanpa jaminan pin namespace Windows. Logging yang gagal tidak mengubah exit code, keluaran protokol, Stop, keputusan overwrite, atau checkpoint.

CLI dan checkpoint/audit yang sudah ada masih dapat mengandung data sumber. Kebijakan sanitasi di sini hanya untuk file diagnostik baru, bukan klaim bahwa seluruh output aplikasi aman dipublikasikan.

## Catatan implementasi

`spt_desktop/diagnostics.py` memegang schema, sanitasi, antrian, session dan instrumentasi fase. `diagnostic_store.py` memegang file/lock/rotasi/retensi. Tidak ada konfigurasi root logger atau filesystem saat import; setiap proses membuat sink sendiri. Kedua modul masuk allowlist worker/frozen, tanpa dependensi baru.

Dasar desain: [Python Logging Cookbook](https://docs.python.org/3.14/howto/logging-cookbook.html) dan [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html). Bukti aktual gate dan artifact ada pada PR logging; dokumen ini bukan klaim live acceptance.


### Perbedaan kegagalan capture dan persetujuan penggantian file

Alur *overwrite* hanya bisa mempublikasikan file terpilih setelah respons
eksplisit dari operator. `consent.requested` di controller berarti permintaan
diterima antrean, **bukan** bukti dialog tampil. `consent.dialog_presented`
dicatat **sekali** saat jendela dialog *overwrite* telah memperoleh peristiwa
`Map` dan benar-benar `winfo_viewable`; event hanya berisi jenis keputusan
`overwrite` dan **jumlah** berkas. Event ini belum membuktikan operator
melihat atau menyetujui dialog. Dialog dibawa di atas jendela aplikasi tanpa
mengaktifkan tombol persetujuan.

`consent.replied` tetap menjadi bukti persetujuan/penolakan yang dikirim
ke worker. Jika tidak ada jawaban valid hingga batas 600 detik, worker
mencatat `consent.timeout` dengan jenis `overwrite` atau `selection`,
mengakhiri operasi dengan status **BLOCKED** (exit 3) dan pesan yang
menyebut keputusan belum diterima. Ini **bukan** kegagalan scraping
DOM, tidak mempromosikan PARTIAL menjadi COMPLETE, tidak otomatis menyetujui
overwrite, dan tidak menimpa file lama. Hasil lokal dan checkpoint yang
sudah diverifikasi tetap dipertahankan tanpa publikasi baru.


### Tindak lanjut Issue #143: ukuran L3-B, rute katalog, dan L3 ekstra

Pengujian DOM 30 Oktober 2026 pukul 14.46?14.51 WIB pada build PR #153
masih gagal membaca halaman setelah pagination untuk **form 4/tabel 3**.
Tabel L3-B sebelumnya memilih ukuran 500 baris. Untuk mengurangi risiko
halaman besar yang tidak responsif, capture DOM sekarang memakai **paling
banyak 100 baris per halaman** pada pemilih ukuran halaman asli yang
terinspeksi. Tidak ada sintesis endpoint, offset, atau data sumber.
Proses ini mungkin memerlukan lebih banyak klik/halaman, tetapi jumlah
baris, urutan, Stop, paginasi ulang yang dilarang, sumber total, dan
batas 180 detik setiap tabel tetap harus diverifikasi. Apabila opsi
100 atau lebih kecil tidak tersedia, tidak ada opsi rekaan; tabel
tidak otomatis dianggap lengkap. Keberhasilan hanya dapat ditentukan
dengan *live acceptance* pada build yang sesuai.

Ketika baik `mpn.catalog_preparation` maupun `mpn.catalog_readiness`
bernilai `not_observed`, field `mpn_catalog_route_shape` mencatat
`alternate_reference_get` jika GET XHR/fetch di frame utama teramati
ke **prefix rute referensi id-ID yang sama, tetapi URL-nya bukan URL
katalog tepat yang telah ditinjau**, atau `not_observed` jika tidak.
Ini hanya identifikasi **kemungkinan perubahan rute**; tidak ada
URL, query, body, label, kode, identitas, atau byte respons yang
dibaca/direkam. Endpoint alternatif tidak boleh menjadi sumber
data atau mengizinkan klik detail; seluruh pin/validasi yang ada
tetap berlaku.

`mpn_parent_tertiary_field` menyimpan kategori kolom berbeda ketiga
dari tujuh kolom terverifikasi, atau `none` jika tidak ada. Semua
kategori berasal dari allowlist, tidak mencatat nilai sumber/DOM.
Bila mismatch lebih dari satu kolom, `MpnSafetyError` tetap fatal.

Mode JSON-hybrid untuk L3 dengan tabel ketiga yang terlihat tetap
menolak sumber native dan memilih fallback DOM, sekalipun dua grid
asli dapat ditemukan. Tes sintetis mereplikasi bentuk ini tanpa
mengakses portal atau data wajib pajak. **Tes sintetis bukan bukti
live acceptance**.

### Issue #143: per-page DOM timing dan bentuk rute katalog MPN

table.page_timing mencatat pengukuran hanya sesudah halaman tabel selesai
terbaca dan tetap terverifikasi: pages, page_rows, page_size_cap,
duration_ms, table_poll_ms, table_idle_ms, dan table_dom_ms.
table_page_stage=initial|advanced membedakan halaman pertama dan hasil
paginasi. Semua nilai waktu adalah angka terbatas, tidak menyertakan teks sel,
URL, identitas, label, request, atau response. Batas 180 detik dan keputusan
PARTIAL tidak diubah. Event table.elapsed_budget masih mencatat stage
ketika halaman berikutnya tidak dapat diterima sebagai selesai.

Pada build PR #155, batas L3-B masih **100** baris per halaman. Pengujian sintetis
membandingkan opsi UI asli 100 dan 250 yang tersedia, tanpa mengganti
kebijakan live; perbandingan hanya bisa memilih ukuran berikutnya setelah
data time-per-page live memperlihatkan penyebab lambat yang terukur.

mpn_catalog_variant_kind=not_observed|query_variant|path_variant
membedakan rute original GET referensi yang tidak tepat dari URL katalog
yang sudah disetujui, hanya pada frame utama dan origin yang sama. Ini
bukti bentuk rute saja, bukan izin membaca, mengikat, atau memanfaatkan
respons rute tersebut. Mismatch parent tetap fatal; tidak ada klik Detail
ketika sumber belum terbukti dan Issue #143 tetap terbuka hingga live
acceptance build-matched.


### Issue #143: uji batas L3-B 250 baris (31 Oktober 2026)

Build ac195741 mengukur tabel L3-B 41 halaman berisi 4.100 baris
dengan batas 100 per halaman dari sumber total 4.654 baris.
Tabel PARTIAL setelah 182,87 detik dan membutuhkan enam halaman.
Waktu klik dan verifikasi belum terpisah dari durasi lainnya.
Diagnostik baru mencatat table_click_ms dan table_verify_ms hanya
untuk halaman terverifikasi, tanpa informasi identitas atau nilai.

Untuk L3-B dengan form, komponen dan grup asli yang terbukti,
kandidat memakai opsi ukuran halaman UI paling banyak 250; 500
dilarang. Opsi harus tersedia dan pilihan aktif <=250 terverifikasi.
Tanpa opsi aman, capture ditolak, bukan memaksakan klik/API baru.
Tabel lain tetap <=100. Batas 180 detik, Stop, larangan klik ulang
setelah state tidak pasti, rekonsiliasi total/baris dan PARTIAL
tetap berlaku. Perlu izin terpisah untuk tes live build berikutnya.


### Issue #143: DOM pascapaginasi gagal pada batas 250 (31 Oktober 2026)

Live test frozen Python 3.14.8 build `22239d7` (Actions `41176978943`)
memilih opsi UI L3-B 250 baris. Halaman awal terverifikasi 250 baris
(dibaca sekitar 168 ms), namun pembacaan DOM setelah klik pertama
mengalami `TimeoutError` pada `coretax_browser.py:404` dengan
`table_dom_stage=post_pagination`. Tabel membutuhkan 19 halaman untuk
total sumber 4.654 baris; tabel ini PARTIAL setelah sekitar 62,32 detik.
Status keseluruhan job PARTIAL; MPN mempunyai kendala independen di #156.

Kegagalan itu belum membuktikan penyebab: klik paginator, penggantian
state, waktu idle, verifikasi state, dan pembacaan DOM harus dibedakan.
Pada kegagalan DOM pascapaginasi, `table.dom_read_failed` menyertakan
`page_size_cap`, jumlah halaman *sebelumnya* yang telah terverifikasi,
`duration_ms`, `table_click_ms`, `table_poll_ms`, `table_idle_ms`,
`table_verify_ms`, dan `table_dom_ms`. Semua berupa angka terbatas
dan tidak mencatat row/DOM, URL, identitas, nilai sel, request/response,
atau pesan exception bebas. Jika halaman belum terverifikasi, tidak
boleh menaikkan penghitung halaman, mengulang klik yang tidak pasti,
atau menyatakan COMPLETE. Batas 180 detik, Stop, total sumber, guard
MPN, dan pemilihan ukuran UI lainnya tetap sama. Hasil tes sintetis
bukan bukti keberhasilan live acceptance.


### Issue #143: state DOM lambat setelah pagination (31 Oktober 2026)

Pada live build `3799767` (run `41184453836`), tabel L3-B 250 baris
awal terbaca ~139 ms. Percobaan halaman berikutnya mencatat klik 448 ms,
polling state 85 ms, idle 855 ms, verifikasi state 9041 ms, kemudian
`Locator.evaluate(TABLE_JS)` gagal setelah ~10037 ms.
Parameter `timeout` pada `Locator.evaluate` membatasi resolusi locator,
**bukan** waktu eksekusi JS setelah elemennya ditemukan. Karena itu,
`table_dom_ms` tidak sendirinya membuktikan `TABLE_JS` lambat:
elemen `table` yang belum siap, render browser, atau evaluasi sendiri
masih perlu dibedakan sebelum mengubah aturan pagination.

Timeout Playwright selama pembacaan `STATE_JS` **setelah** satu klik
paginator (pada tahap `poll` atau `verify`) sekarang menghasilkan
PARTIAL dengan peringatan tetap `Table state read timed out after pagination`,
bukan melepaskan exception tanpa status tabel. Event
`table.state_read_failed` mencatat tahap enum `poll|verify`, jumlah
halaman **terverifikasi sebelumnya**, cap ukuran halaman, durasi bounded
dan ukuran waktu fase yang sudah diketahui. Tidak ada teks sel, URL,
identitas, request/response, atau pesan exception bebas.
Halaman yang state-nya gagal tidak dipromosikan menjadi COMPLETE dan
paginator tidak diklik ulang. Stop, deadline 180 detik, kontrak
pembacaan seluruh row text, dan MPN fail-closed tetap sama.
Dua skenario time-out diuji memakai fixture lokal sintetis, bukan bukti
bahwa kegagalan live telah sembuh. Jika `TABLE_JS` gagal, satu probe
read-only sesudah timeout (`wait_for(state=attached, timeout=1000)`)
merekam hanya `table_locator_state=attached|not_attached|unavailable`
sebagai diagnosis ada/tidaknya locator pada saat probe. Ini bukan
bukti bahwa locator awal gagal, tabelnya benar, atau datanya lengkap.
`table_dom_ms` dan `duration_ms` dihitung sebelum probe agar tambahan
waktu probe tidak mengubah metrik sebelumnya. Issue #143 tetap terbuka.


### Issue #143: verifikasi tabel dalam snapshot DOM terikat (31 Oktober 2026)

Pada live build `430715d`, tabel L3-B berhasil membaca 10/19 halaman
(2.500/4.654 baris). Pergantian halaman memerlukan ~16–17 detik:
pembacaan state verifikasi umumnya ~7,3–8,3 detik disusul DOM
~7,8–8,2 detik. Setelah kegagalan halaman berikutnya,
`table_locator_state=not_attached`, tetapi ini **tidak** membuktikan
kapan/kenapa elemen terlepas. Capture 180 detik tetap PARTIAL dan
gagalnya identitas MPN tetap terpisah (#156).

Percobaan terikat ini menggantikan verifikasi state dan pembacaan tabel
berurutan dengan satu `TABLE_VERIFIED_JS` yang menggunakan pemilik
paginator awal (`p-table`/container tersimpan) dan membacanya secara
atomik dengan seluruh state raw-row asli. Snapshot ditolak sebelum
menambahkan baris ketika tabel berpindah ke pemilik lain, metadata
header/grup berubah, atau state halaman berulang. Rebinding tabel di
dalam pemilik yang sama boleh diuji hanya dengan pembuktian struktur
tersebut. Tidak ada klik paginator ulang, request baru, atau penerimaan
baris tanpa pemilik dan metadata yang terverifikasi.

`table.identity_refused` mencatat hanya kategori
`table_identity_reason=owner_changed|metadata_changed|repeated_state`,
jumlah halaman terverifikasi sebelumnya, batas ukuran halaman, dan
durasi terbatas. Tidak mencatat nama, header, nilai sel, DOM, URL,
permintaan, atau respons. `table_verify_ms=0` pada halaman baru karena
verifikasi state dilakukan di dalam evaluasi `table_dom_ms` yang sama;
jangan bandingkan dua metrik fase ini lintas build secara langsung.

Pada jalur cursor L3-B250 yang menggabungkan loading dan snapshot, tidak ada
RPC `wait_idle` terpisah untuk halaman lanjutan. `table_idle_ms` hanya mencatat
waktu bagian host yang kini kosong; `table_dom_ms` mencakup RPC snapshot beserta
tunggu overlay dan settling180ms. `table_dom_renderer_ms` tetap mengukur
ekstraksi setelah tunggu tersebut. Pending slice paling lama1000ms memberi
kesempatan pemeriksaan Stop di Python; deadline loading45s dan tabel180s tetap
berjalan dan tidak diulang. Selisih wall/renderer bukan ukuran antrean murni,
dan pengurangan RPC tidak membuktikan peningkatan kecepatan live.

Perubahan ini menguji hipotesis pengurangan pembacaan state ganda dan
membatasi penerimaan data pada pemilik/metadata yang sama. Bukti
synthetic browser RED→GREEN bukan bukti peningkatan kecepatan atau
keberhasilan live Coretax. Batas 180 detik, Stop, opsi L3-B maksimal
250, opsi tabel lain maksimal 100, jumlah sumber, status PARTIAL dan
pengamanan MPN tetap dipertahankan. Issue #143 tetap OPEN sampai ada
live acceptance build-matched yang diotorisasi terpisah.


### Issue #161: rebind tabel hanya di dalam owner paginator asal (31 Oktober 2026)

Live build `79e351a` / Actions `41198640120` mencatat dua
`table.dom_read_failed` pasca-pagination pada batas 250 dan 100
baris, masing-masing ~10 detik, dan probe setelah kegagalan menghasilkan
`table_locator_state=not_attached`. Ini hanya membuktikan keadaan
locator pada waktu probe, bukan kapan tabel terlepas.

Jalur setelah klik kini memanggil `TABLE_VERIFIED_JS` pada **ElementHandle
owner paginator yang sudah diperiksa sebelum klik**, bukan meminta Playwright
mencari ulang `Locator` tabel lama. Satu callback browser menemukan tabel
yang tepat **hanya di bawah owner yang sama** dan memerlukan tepat satu tabel
dengan `closest('p-table')` / `closest('.p-datatable')` yang cocok.
Baru setelah itu `TABLE_JS` dan state seluruh baris dibaca dalam
snapshot sinkron yang sama. Pergantian wrapper tabel di bawah owner yang sama
dapat diterima bila header/grup, state pagination, dan jumlah sumber cocok.

Bila owner terlepas, tidak ada tabel miliknya, atau terdapat lebih dari satu
tabel milik owner, capture menjadi PARTIAL sebelum menggabungkan baris;
`table.identity_refused` mengeluarkan kategori terbatas
`owner_changed|table_missing|table_ambiguous`. Tidak ada pencarian
owner baru di seluruh halaman, klik ulang, request tambahan, atau pelebaran
batas 250/100 dan 180 detik. Stop, footer tunggal, source-total, identitas
header/grup dan MPN tetap terpisah. `ElementHandle.evaluate` tidak
memiliki timeout locator Playwright; callback JS sinkron tetap tunduk
pada pembatasan eksternal dan perlu diverifikasi di live secara terpisah.
Hasil regression test sintetis tidak menyatakan Corporate COMPLETE.


### Issue #156: pembuktian owner filter periode dan ketersediaan katalog (1 November 2026)

Live build `7a1d143` / Actions `41220217018` masih
`MpnSafetyError` pada `parent_detail`. Sumber asli menampilkan filter
tanggal yang belum terhapus (`date_filter_present`), sementara kontrol
clear yang sudah diperiksa tidak ditemukan (`mpn_clear_state=absent`).
Sumber referensi `ACCOUNTING_TYPE`, `ACCOUNTING_TYPE_DETAIL`, dan
`PERIOD` yang tepat belum terbukti terikat, dan tiga kategori identitas
parent tetap berbeda. Jangan menyamakan tidak ditemukannya katalog dengan
izin melanjutkan ke Detail Transaksi.

Saat sumber list masih mengandung filter tak diizinkan, diagnosis baru
`mpn_period_widget_state=absent|present|ambiguous` menghitung
`#filterPeriodCode` di `ui-grid` yang terbukti memiliki tepat satu
`p-table`. Keunikan tombol clear saja tidak cukup: dua widget periode
dengan hanya satu tombol clear sekarang juga ditolak tanpa klik.
Kategori tidak mengeluarkan label, teks DOM, data request, URL, kode
akun, atau identitas wajib pajak.

Jika parent sumber berbeda dengan proyeksi tabel, diagnostik
`mpn_mismatch_reference_state` membedakan
`all_reference_missing|some_reference_missing|references_observed|no_reference_mismatch`
berdasarkan **ada atau tidaknya inventory kode referensi asli** pada
field yang berbeda. Diagnosis ini tidak membuktikan label cocok. Seluruh
mismatch independen tetap melalui `MpnSafetyError`, termasuk kombinasi
`accounting_type`, `accounting_detail`, dan `tax_period`. Katalog
tetap hanya boleh berasal dari exact GET asli dengan pin kepemilikan,
bukan `path_variant` atau request baru.

Regression test sintetis meliputi widget absen, unik, dua icon, widget
ganda dengan satu icon, ketiga kategori ketersediaan referensi, tidak
ada Detail click, fail-closed PARTIAL dan serialisasi diagnostik
allowlisted. Tidak ada live replay otomatis. Issue #156 tetap OPEN
hingga sumber/owner asli terbukti dan ada acceptance build-matched.

### Kesiapan dialog detail MPN (3 November 2026)

`mpn.detail_readiness_failed` mencatat satu penolakan pada pemeriksaan kesiapan
yang sudah ada. `mpn_ui_stage` membedakan `detail_dialog`, `detail_title`, dan
`detail_grid`. State terakhir `mpn_readiness_state` hanya salah satu dari
`unobserved`, `missing`, `hidden`, `visible`, atau `ambiguous`; alasan
`mpn_readiness_reason` hanya `deadline` atau `ambiguous`.
`missing` berarti selector yang sudah diperiksa menghasilkan nol match,
termasuk filter `:visible` yang sudah ada pada selector dialog; ini bukan
pernyataan bahwa tidak ada host dialog tersembunyi di dokumen.

`mpn_readiness_budget_ms` adalah sisa budget ketika panggilan kesiapan tersebut
dimulai, dibatasi 0..5000 ms; `duration_ms` adalah waktu panggilan itu sendiri.
Ketiga panggilan tetap memakai satu deadline bersama lima detik. State `visible`
dengan alasan `deadline` berarti hasil pemeriksaan akhir terlambat dan tetap
tidak mengizinkan capture. `unobserved` berarti belum ada hasil count/visibility,
misalnya saat identitas Document masih pending. Angka ini tidak mengukur waktu
render murni atau durasi seluruh pengambilan detail.

Event memakai hasil count/visibility yang sudah dibaca oleh gate; tidak ada
probe DOM tambahan setelah gagal. Tidak ada selector, caption, URL, pesan
exception, isi tabel, atau identitas wajib pajak. Stop dan kegagalan safety dari
callback tetap didahulukan. Kegagalan RPC lain mempertahankan diagnostik error
yang sudah ada dan tidak direka sebagai hasil readiness.

Mode DOM dan JSON-first tetap memerlukan owner dialog/grid yang sama sebelum
fallback detail. `mpn.capture_failed` tetap menyatakan `parent_detail`/PARTIAL
dan kini dapat menunjukkan stage kesiapan yang lebih tepat. Keberhasilan tes
sintetis tidak membuktikan penyebab struktur live atau keberhasilan MPN live.
Event `catalog_readiness` sebelumnya hanya menggambarkan observasi pasif saat
itu; katalog dapat kemudian diperoleh oleh adapter yang sudah disetujui dengan
origin `adapter-get-v1` di bukti privat. Jangan menyimpulkan kegagalan katalog
hanya dari event pasif tersebut.
