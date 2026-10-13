# B-TK-P1 — Bukti implementasi tahap 1

**Tanggal:** 13 Oktober 2026. **PR:** [#12](https://github.com/cepeter-job/spt-downloader/pull/12), branch `feat/ui-b-phase1`.

**Status (13 Oktober 2026):** T1–T5 untuk irisan pertama telah diverifikasi, termasuk screenshot native Windows sintetis, tes fokus keyboard dan readback artifact untuk commit produk `7aa2f095`. PR tetap draft, belum merged atau deployed. Ini bukan penerimaan manual Coretax maupun klaim seluruh redesign B/AC01–AC28 selesai.

[Rencana yang disetujui](../plans/2026-10-13-magicpath-b-tkinter-phase1.md) · [Spesifikasi B-TK-1](../specs/2026-10-13-magicpath-b-tkinter-design.md) · [Panduan UI/UX](../../ui-ux/README.md).

## 1. Perubahan yang sudah berjalan pada runner

| Tugas | Implementasi | Bukti |
| --- | --- | --- |
| T1 | `ui_copy.py`: katalog 44 ID, enam teks pemilik literal, placeholder hitungan bernama dengan validasi ketat. | 16 kasus tes baru; teks aktual juga dibaca dari widget pada self-test. |
| T2 | `ui_state.py`: state murni terikat job, counter inventaris/rincian terpisah, persentase bukan sertifikasi, respons consent hanya dicatat setelah diterima controller. | 48 kasus tes baru. |
| T3 | `ui_theme.py` dan `ui_views.py`: ttk nyata, named fonts, pengukuran work area, ringkasan di atas pada compact, gulir, reflow terbatas, timer milik view dibersihkan. | 14 kasus tes baru; empat ukuran jendela diuji. Bukan bukti screenshot atau matriks DPI menyeluruh. |
| T4 | `App` memakai shell baru; validasi inline; klik/Enter/Alt+M memakai satu guard; Stop idempotent; event asing ditolak; self-test memakai controller sintetis terinjeksi. | 20 kasus integrasi baru dan migrasi fixture existing; seluruh suite Windows lulus. |
| T5 | Full Windows/portable, source/frozen, artifact, review sumber, delapan screenshot native sintetis regular/compact/minimum, serta regresi fokus keyboard. | Selesai untuk cakupan visual tahap 1. Bukti tambahan dan batasnya pada bagian 8. |

Baseline produk `be67f5153a07ce100048d67191a02ca1d0fca1db`; parent dokumentasi `00da93ce90bcf42221f824df849cfda9c979f6c7`. Head produk yang diuji dan direview adalah **`e25f8bd163b1c9c3c84f4aee136698644e410192`**. Commit laporan ini datang sesudah head tersebut dan hanya menyentuh dokumentasi; hasil runtime di bawah tidak diberi label sebagai eksekusi commit laporan.

Controller, private interaction channel, worker, capture, Excel/PDF, Credential Manager, allowlist resource, pin Python, dependensi, build validator, LICENSE, dan workflow tidak diubah. PR ini membawa dua commit dokumentasi dari PR #11 yang belum merged.

## 2. Regresi yang ditutup saat resume

Sesudah kegagalan pemantauan ekspor, `_poll_failed` masih bernilai True ketika pengguna memulai cek login baru. Kegagalan pada job kedua kemudian tidak meminta cleanup lagi.

Regresi `test_new_login_check_gets_its_own_poll_failure_cleanup` dipublikasikan lebih dahulu pada `c4aac4257db0264444d371180166fa3bc1986d22`. [Run RED 38383189959](https://github.com/cepeter-job/spt-downloader/actions/runs/38383189959) menunjukkan **1 gagal, 712 lulus**: dua job memerlukan dua permintaan cleanup, tetapi hanya satu tercatat. Perbaikan `e25f8bd` mereset guard setelah `start_login_check` berhasil, seperti jalur start ekspor. Tidak mengubah controller, consent, atau menghapus assertion.

Full suite setelah perbaikan: **713 lulus**. Cleanup tidak diklaim selesai hanya karena error pemantauan; UI tetap menunggu otoritas controller.

## 3. Jejak RED → GREEN

| Tugas | RED teramati | GREEN teramati |
| --- | --- | --- |
| T1 | `b3570fc`, [38376180100](https://github.com/cepeter-job/spt-downloader/actions/runs/38376180100): 16 gagal, 611 lulus. | `a1b3852`, [38376704144](https://github.com/cepeter-job/spt-downloader/actions/runs/38376704144): 627 lulus. |
| T2 | `e86485f`, [38377473576](https://github.com/cepeter-job/spt-downloader/actions/runs/38377473576): 48 gagal, 627 lulus. | `ad188a7`, [38378361277](https://github.com/cepeter-job/spt-downloader/actions/runs/38378361277): 675 lulus. |
| T3 | `20fb36f`, [38379018801](https://github.com/cepeter-job/spt-downloader/actions/runs/38379018801): modul tema/view belum ada. Kandidat pertama juga mengekspos nilai wraplength ttk kosong. | `c1be368`, [38380628556](https://github.com/cepeter-job/spt-downloader/actions/runs/38380628556): 689 lulus setelah nilai default wraplength ditangani. |
| T4 | `30bdba2`, [38381866708](https://github.com/cepeter-job/spt-downloader/actions/runs/38381866708): 25 gagal, 683 lulus. Kandidat berikutnya mengekspos teardown fixture lama; regresi cleanup dua job kemudian dibuktikan terpisah. | `e25f8bd`, [38385813293](https://github.com/cepeter-job/spt-downloader/actions/runs/38385813293): 713 lulus. |

Perbaikan teardown fixture membuang timer milik view melalui `app._dispose()` sebelum timer milik root tes; tidak menghapus pemeriksaan callback error atau mengurangi kontrak lifecycle. Seluruh pytest, fixture Tk/browser, source/frozen self-test, dan build berjalan pada GitHub runner, bukan vm148 atau container ChatGPT.

## 4. Bukti runner pertama (arsip historis)

> Bagian 4–5 mempertahankan bukti product head `e25f8bd` dari sebelum perbaikan visual T5. **Bukti runner dan artifact paling baru berada pada bagian 8.** Jangan memakai angka 713 sebagai hasil terakhir.

| Pemeriksaan | Hasil yang dibaca |
| --- | --- |
| Run/attempt/head | [38385813293](https://github.com/cepeter-job/spt-downloader/actions/runs/38385813293), attempt 1, `e25f8bd163b1c9c3c84f4aee136698644e410192`, conclusion `success`. |
| Checkout PR merge | `a98c9070316c0b1011170c9e35a3a62515484008`. Ini berbeda dari head branch; manifest mengikat checkout ini. |
| Windows, job `115257267061` | **713 passed in 161.43s**. Tidak ada tes Windows yang dipotong menjadi subset. |
| Portable, job `115257267097` | **367 passed, 346 deselected in 8.03s**. 346 hanya dikecualikan dari jalur Linux tambahan; tetap ada pada full Windows. |
| Package, job `115258481246` | Source GUI self-test, frozen build/self-test, verifikasi inventory, upload, exact-ID readback, dan checksum gate lulus. |

Manifest Windows dan portable diunduh sebagai artifact exact-ID `11805272890` dan `11806246005`. Kedua collector menghasilkan 713 node yang sama; Windows memilih seluruh 713. Subset portable persis mengikuti allowlist dan pengecualian baseline. Ada **98 kasus dalam lima modul tes UI baru**, ditambah **empat kasus geometry baru pada modul existing**: kenaikan suite dari 611 menjadi 713 bukan 102 kasus dalam modul baru saja.

Audit dependency dan routing lulus. Job attestation dan cleanup branch tidak dijalankan pada event PR ini; tidak ada klaim attestation baru dari run ini. Tidak ada perubahan workflow untuk melewati pemeriksaan.

## 5. Artifact dan pemeriksaan byte

Artifact [Windows `11806441407`](https://github.com/cepeter-job/spt-downloader/actions/runs/38385813293/artifacts/11806441407) berukuran **30.970.801 byte** dan bernama `SPTDownloader-Windows-x64-a98c9070316c0b1011170c9e35a3a62515484008-python3.14.8`. Koordinat run/head pada API cocok. SHA-256 arsip sama dengan digest API:

```text
b7427f15837555260a93388057c7868d78c670ca8deae14a7730851181117af7
```

Arsip benar-benar diunduh ulang. Isinya tepat lima file: `SPTDownloader.exe`, `LICENSE.txt`, `README.txt`, `build-selftest.json`, dan `SHA256SUMS.txt`. Keempat entri manifest cocok dengan byte payload; tidak ada file tambahan atau nama duplikat. Digest transport keempat artifact run juga cocok.

| Payload | SHA-256 |
| --- | --- |
| SPTDownloader.exe | `37b6565407f619873eaebbea7eaa06f05a2ed9a0bfbad1b4aa3c7e809ca7bca1` |
| LICENSE.txt | `230184f60bae2feaf244f10a8bac053c8ff33a183bcc365b4d8b876d2b7f4809` |
| README.txt | `e4dff164ae669eea8f52ae57f4b09d74235b4b2f998657ff1f4f19d50bf3dc92` |
| build-selftest.json | `dd44227464a8bcbc8fc8c4a0aceab19157e19b067069f58b870a3c96f6ec6bfb` |

Report frozen yang dibaca menunjukkan CPython **3.14.8**, 64-bit, GIL aktif, profil production, Tcl/Tk **9.0.4**, worker Python 3.14.8, dan daftar resource worker persis sama dengan source. `ok`, `frozen`, `uv_bundled` bernilai True; `credentials_accessed` dan `live_scrape` bernilai False. Judul humor, checkbox background, petunjuk Downloads, kedua label personal-use, serta tombol `Mulai unduh`/`Hentikan unduhan`/`Buka folder hasil` cocok.

Bukti source adalah langkah self-test source yang lulus di runner dan assertion report source dalam full suite. **Report source tersendiri tidak diekspor oleh workflow**, sehingga tidak diklaim telah diunduh. Report yang dibaca kembali dari ZIP adalah report frozen. EXE yang diunduh tidak dijalankan di luar runner. Inspeksi lokal hanya membaca metadata/hash dan AST sumber, tanpa import produk.

## 6. Pemetaan penerimaan irisan 1

| Kriteria | Bukti otomatis pada run akhir | Batas bukti |
| --- | --- | --- |
| AC01 — shell/teks khusus | `test_shell_has_one_real_heading_and_downloads_hint`, `test_self_test_uses_job_bound_progress_and_real_captions`, tes branding/requested-text, report frozen. | Bukan inspeksi visual screenshot native atau pembaca layar. |
| AC02 — NPWP/tahun literal | `test_invalid_fields_do_not_start_and_focus_first_error`, equivalence validator pada tes state, error field/geometry. | Data sintetis; tidak ada akses wajib pajak. |
| AC03 — guard start | `test_click_enter_and_alt_m_share_one_start_guard`, field disabled, snapshot job tidak berubah oleh StringVar belakangan. | Tidak mengubah otoritas controller. |
| AC04 — setup/login | `test_setup_login_required_and_counts_use_correct_presentation`, indeterminate timer tidak digandakan, login browser tidak disahkan melalui tombol GUI. | Tidak menguji portal aktual atau seluruh redesign Pengaturan. |
| AC05 — counter/99% | `test_99_percent_cannot_open_a_result`, counter inventaris/detail terpisah, missing/bool/negatif/tidak konsisten tidak menjadi angka pasti. | Tidak menambah progres PDF yang belum disediakan event. |

Ukuran 540×390, 640×560, 900×700, dan 1120×800 diuji sebagai geometry pada runner. Empat ukuran itu **bukan** empat DPI atau bukti tampilan identik di semua monitor. Tes 100 render memeriksa widget reuse/fokus, bukan benchmark 100 pekerjaan atau klaim batas RAM.

## 7. Review, bagian terbuka, dan serah-terima

Review sumber independen dilakukan oleh agen Codex dengan konteks baru, read-only, untuk rentang `00da93ce..e25f8bd`. Hasilnya tidak menemukan masalah Critical/Important/Minor pada kode; identitas job, counter, Stop/consent stale, fixture, teks, timer, dan pemisahan backend diperiksa. Ini **bukan review manusia** atau bukti runtime; hasil runner/artifact diverifikasi terpisah oleh pelaksana setelah review.

| Bagian | Status |
| --- | --- |
| T1–T4 dan gerbang otomatis T5 | Selesai pada head produk yang dipin di atas. |
| Inspeksi screenshot shell regular/compact Windows | **Selesai untuk 8 keadaan sintetis**, ukuran client 1120×800, 640×560, dan 540×390 (lihat bagian 8). |
| High Contrast, Narrator/NVDA, DPI antar-monitor, benchmark aplikasi | Belum dilakukan; tetap kebutuhan tahap berikutnya, bukan disimpulkan dari tes geometry. |
| Redesign dialog pemilihan/penggantian, dirty settings, seluruh hasil/login; penerimaan Coretax/Excel manual | Di luar irisan pertama atau menunggu penerimaan terpisah; fungsi baseline dan regresinya dipertahankan. |
| Merge, rilis, deployment, dan tahap 2 | Tidak dijalankan atau disetujui otomatis oleh pekerjaan ini. |

PR tetap draft karena keputusan merge/deployment dan penerimaan manual masih terpisah. Bukti visual T5 sintetis sudah diperoleh; catatan baseline dan proposal lama tidak diperlakukan sebagai status produk terkini.

## 8. Penutupan T5: review visual native dan regresi fokus (13 Oktober 2026)

**Produk yang dinyatakan lulus pengujian T5:** `7aa2f0958aa113f4bae9afea75e8da8382dc9a53` pada [GitHub Actions run 38402368800](https://github.com/cepeter-job/spt-downloader/actions/runs/38402368800), checkout PR merge `52a4ac7f0a7f02a4ba7e7209004de28b0699b0a6`. Run tersebut selesai **success**: **719/719 tes Windows lulus** (168,64 detik), 367 tes portable lulus (352 tidak dipilih di jalur Linux tambahan, tetapi tercakup pada Windows), audit dependensi dan packaging lulus. Kedua inventory artefak terbaca dengan 719 node sama, seluruh 719 dipilih pada Windows, dan kedua regresi fokus compact termasuk di dalamnya.

**Artifact produk terbaru:** [11815323374](https://github.com/cepeter-job/spt-downloader/actions/runs/38402368800/artifacts/11815323374), ZIP SHA-256 `efb09ca02652b5fdc20702c2761a393f7eed89a6b45e119af9a6eead71944ee7`. Artifact benar-benar diunduh, memuat tepat `SPTDownloader.exe`, `LICENSE.txt`, `README.txt`, `build-selftest.json`, `SHA256SUMS.txt`; empat checksum payload cocok. Report frozen berisi CPython 3.14.8 (GIL), Tcl/Tk 9.0.4, `credentials_accessed=false`, `live_scrape=false`, serta tiga teks khusus pemilik yang tepat. Screenshot bukan bagian executable dan tidak dimasukkan ke payload distribusi.

### Sumber dan keadaan visual

Review memakai **delapan screenshot dari Windows 2022 asli**, bukan gambar mockup, dengan CPython 3.14.8 dan controller sintetis tanpa browser, login, pajak nyata atau Excel/PDF. Capture Windows memakai `PrintWindow`, display virtual 1440×900. Client window 1120×800 (regular), 640×560 (compact), 540×390 (minimum), termasuk native titlebar. Sumber: [PR diagnostik terpisah #15](https://github.com/cepeter-job/spt-downloader/pull/15), [run 38397827128](https://github.com/cepeter-job/spt-downloader/actions/runs/38397827128), [artifact 11812836577](https://github.com/cepeter-job/spt-downloader/actions/runs/38397827128/artifacts/11812836577), ZIP SHA-256 `a07b796ea198562958221702a3689245246184a040b11a2ffd4e38d4ef1a347c`. Capture menggunakan tree UI `b9fddc0`; commit `7aa2f095` berikutnya hanya memperbaiki perpindahan fokus setelah terminal tanpa mengubah struktur/layout gambar. Delapan file berisi `regular-idle`, `regular-details`, `regular-complete`, `compact-idle`, `compact-invalid`, `compact-details`, `compact-partial`, `tiny-idle`. SHA tiap PNG dan ukuran layar dicocokkan dengan manifest. Arsip ZIP dan contact sheet juga disimpan di Library pengguna untuk menghindari bergantung hanya pada retensi artifact Actions.

Hasil inspeksi: judul, empat tahap, form/input, status, tombol dan petunjuk Downloads terlihat pada layar yang relevan. Ringkasan regular tetap di kanan; compact menjadi tiga kolom di atas tugas. Progress 66% dan aksi PARTIAL tampak tanpa scroll manual. Pada 540×390, ruang tidak cukup untuk seluruh form, tetapi label NPWP dan Entry langsung terlihat, sementara konten lain tersedia melalui scroll. Warna bilah progres mengikuti tema Windows (hijau pada runner), tidak dipaksa menjadi biru seperti CSS MagicPath.

### Defect → RED → GREEN

| Defect yang ditangkap T5 | Bukti RED sebelum perbaikan | Bukti akhirnya |
| --- | --- | --- |
| Ringkasan compact terlalu tinggi, input/progres keluar viewport | [Run 38394513552](https://github.com/cepeter-job/spt-downloader/actions/runs/38394513552): empat tes compact baru gagal, 713 existing lulus. | Ringkasan 3 kolom dan reveal tindakan; screenshot menunjukkan form/progres. |
| Judul ringkasan terpotong; label NPWP terpotong di jendela minimum | [Run 38396755580](https://github.com/cepeter-job/spt-downloader/actions/runs/38396755580): dua tes gagal, 715 lulus. | Padding dan scroll disesuaikan; screenshot setelah `b9fddc0` membuktikan keterbacaan. |
| Fokus keyboard tetap berada pada NPWP yang tersembunyi setelah terminal | [Run 38399422347](https://github.com/cepeter-job/spt-downloader/actions/runs/38399422347): dua tes gagal, 717 lulus. | `App.on_event` memfokuskan tindakan Buka hasil ketika tersedia atau Mulai unduh jika tidak; run 38402368800 menunjukkan 719 lulus. |

**Status T5:** review visual sintetis/native, regresi keyboard yang ditemukan, full suite, source/frozen, dan hash artifact **selesai untuk cakupan irisan 1**. Tidak diartikan sebagai persetujuan pemilik atas UI akhir, uji High Contrast, Narrator/NVDA, 200% text scaling, DPI multi-monitor, benchmark RAM/performa, atau penerimaan Coretax/Excel secara manual. PR #12 tetap tidak di-merge; keputusan merge, deployment dan tahap 2 menunggu instruksi terpisah. Screenshot diagnostik PR #15 tidak ikut ke branch produk; tidak ada perubahan user-owned CI agar tes berlalu.
