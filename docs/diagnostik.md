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

Pesan exception, chain, locals, baris kode, path lengkap, URL, NPWP, tahun/nama wajib pajak, akun, password, cookies, token, header/body HTTP, nilai form/tabel, payload consent dan nama/hash PDF **tidak disalin**. Field dan nilai yang tidak termasuk allowlist dibuang tanpa memanggil `str()` pada objek tak dikenal. Tidak ada perekaman browser/network atau penyalinan raw stdout/stderr.

`phase.completed` berarti fungsi keluar normal, **bukan** bukti hasil pajak COMPLETE. Gunakan `worker.finished` yang berasal dari rekonsiliasi controller, beserta Audit hasil untuk lingkup data. Error yang sudah ditangani sebagai PARTIAL tetap mempunyai event diagnostik tanpa mengubah status bisnis.

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

## Snapshot setelah timeout panel

`capture.panel_timeout` dicatat pada WARNING sekali ketika budget tunggu panel habis, bukan pada setiap polling. Event ini tidak mengganti `capture.partial` atau mengubah hasil PARTIAL, selector, klik tab, retry, maupun budget tunggu. Durasi `duration_ms` hanya mencakup penantian panel sampai budget habis, tidak mencakup pembukaan detail, pekerjaan sebelumnya, atau pembacaan snapshot sesudahnya.

Snapshot hanya berisi struktur: `panel_controlled` menyatakan penggunaan `aria-controls`; `panel_matches` menghitung kandidat dalam view yang sedang dipakai; `document_panel_matches` menghitung kecocokan ID yang sama di dokumen dan **tidak diisi** pada jalur fallback tanpa ID; `tab_views` menghitung `.p-tabview` di bawah `.main-content`. ID sebenarnya tidak pernah masuk log. `tab_state` adalah `selected`, `unselected`, atau `unknown`; yang terakhir dipakai bila asosiasi tab atau atribut pemilihannya tidak tunggal/teramati.

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

## Batas penyimpanan dan kegagalan

Ukuran file maksimal 1 MiB, maksimal tiga segmen per session. Retensi tujuh hari dan anggaran 32 file pada folder log; file regular milik logger yang tidak aktif dibersihkan paling tua dahulu. File asing, hardlink, symlink/reparse dan session aktif tidak dihapus. Jika kapasitas tidak dapat direklamasi dengan aman, logger tidak menambah file.

Antrian maksimal 256 record, ukuran record maksimal 4 KiB. Saat sink lambat, producer tidak menunggu I/O; `dropped` adalah hitungan event yang tidak dapat dicatat. Flush/close menunggu maksimal dua detik. Kehilangan event saat proses dipaksa berhenti, antrean penuh, storage rusak atau disk hang tetap mungkin. Retensi bekerja saat file baru dibuat, bukan lewat pekerjaan terjadwal.

Tidak ada jaminan forensik, at-rest encryption, zero filesystem latency, ataupun ketahanan terhadap administrator/proses lain yang menguasai akun. DirectoryGuard memegang direktori Windows; implementasi portable melakukan pemeriksaan identitas tanpa jaminan pin namespace Windows. Logging yang gagal tidak mengubah exit code, keluaran protokol, Stop, keputusan overwrite, atau checkpoint.

CLI dan checkpoint/audit yang sudah ada masih dapat mengandung data sumber. Kebijakan sanitasi di sini hanya untuk file diagnostik baru, bukan klaim bahwa seluruh output aplikasi aman dipublikasikan.

## Catatan implementasi

`spt_desktop/diagnostics.py` memegang schema, sanitasi, antrian, session dan instrumentasi fase. `diagnostic_store.py` memegang file/lock/rotasi/retensi. Tidak ada konfigurasi root logger atau filesystem saat import; setiap proses membuat sink sendiri. Kedua modul masuk allowlist worker/frozen, tanpa dependensi baru.

Dasar desain: [Python Logging Cookbook](https://docs.python.org/3.14/howto/logging-cookbook.html) dan [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html). Bukti aktual gate dan artifact ada pada PR logging; dokumen ini bukan klaim live acceptance.
