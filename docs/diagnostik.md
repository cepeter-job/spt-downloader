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
mencatat `corporate_l3_reason` dari 19 kategori tetap yang memisahkan pin/build,
hash sumber MAIN (`main_digest`), hash sumber VENDOR (`vendor_digest`),
jumlah tabel L3 (`table_count`), lifetime komponen awal/akhir,
sumber skrip, struktur form/grid, rantai owner,
judul/metadata tabel, paginator, bentuk request, footer, offset dan katalog
referensi. Misalnya `table_structure`, `reference_request`, dan
`grid_or_footer_missing`. Nilai kategori tidak mengambil string, ID,
hash/URL atau isi dari browser. Field yang tidak ada bukan bukti tahap sukses.
Refusal tetap mengembalikan `None` dan memilih fallback seluruh record ke DOM;
verifikasi sumber, identitas, dan pembatasan tetap wajib.

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
