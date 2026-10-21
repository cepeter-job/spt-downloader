# Bukti UI B — Phase 2 dialog pemilihan dan penggantian

Tanggal: **20 Oktober 2026 (UTC)**. Rencana **B-TK-P2-P1** dijalankan inline setelah instruksi pemilik `Run B-TK-P2-P1 inline`; jalur bukti tambahan dijalankan setelah `Approve diagnostic PR`. [Spesifikasi yang disetujui](../specs/2026-10-20-magicpath-b-phase2-dialogs-design.md) dan [rencana](../plans/2026-10-20-magicpath-b-phase2-dialogs.md) tetap merupakan snapshot persetujuan, bukan dokumen yang ditulis ulang agar sesuai hasil.

## 1. Hasil dan batas penerimaan

Implementasi dialog dan perbaikan temuan native telah diverifikasi pada kandidat akhir. Matriks mencatat **17 PASS dan 1 PARTIAL**: P2-14 belum mencakup ukuran normal penuh serta tinggi compact penuh pada 200% di layar yang cukup besar. Scaling Windows 200% sendiri berhasil diubah dan diverifikasi, dengan dialog yang ter-clamp secara benar ke work area; itu tidak menggantikan sel bukti ukuran normal penuh. Penerimaan visual manusia tetap terbuka.

Kandidat produk yang diverifikasi: **`6440e03df821db2882446d729c62257666286d0a`**, [PR #53][product-pr]. Baseline pembanding: **`977b06846554ca1f2e5af512a69fb201f2cbe8d1`**. Seluruh pytest, import produk, native/Tk/browser fixture, self-test source/frozen, build dan eksekusi EXE hanya terjadi pada runner GitHub. vm148/container dipakai untuk source/AST, review, Git serta pemeriksaan hash/metadata/gambar artifact; tidak ada akses portal atau akun nyata.

**Bukti pengukuran performa dan pencapaian sasaran 100 ms adalah dua hal berbeda.** P2-16 PASS untuk pengukuran baseline/kandidat dan keputusan tindak lanjut. Sasaran opening ≤100 ms **BELUM TERCAPAI**: keempat kelompok opening kandidat melebihi 100 ms pada 10/10 sampel. Angka ini adalah sasaran evaluasi pada shared runner, bukan assertion CI keras; tidak ada klaim telah optimal.

PR produk tetap menunggu penerimaan manusia. Laporan ini tidak mengizinkan merge, deployment, perubahan Pengaturan, batching, multijob, atau tahap UI berikutnya. Harness berada hanya pada [PR diagnostik #54][diagnostic-pr], dengan dua berkas terisolasi dan tidak dibawa ke produk/EXE.

## 2. Revisi dan bukti runner

| Peran | Head / checkout | Run dan hasil |
| --- | --- | --- |
| Baseline produk | `977b06846554ca1f2e5af512a69fb201f2cbe8d1` | Checkout baseline tersendiri pada job pengukuran yang sama dengan kandidat |
| T1 GREEN | `ef08bc969f61d0ead48d27e5a450fb1ec1af9b5f`; merge `776199c384b16d34049b4d1d4c902b827500dc51` | [39416690008](https://github.com/cepeter-job/spt-downloader/actions/runs/39416690008): 3.249 tes Windows lulus |
| T2 GREEN sebelum temuan native | `d8dc09babe0ba96d6288862a57cf9095cd8857d7`; merge `ece2a265752b728773b915967f9747072667a8d6` | [39424910414](https://github.com/cepeter-job/spt-downloader/actions/runs/39424910414): 3.290 tes Windows lulus; bukan bukti untuk perubahan produk setelahnya |
| Regresi keyboard RED awal | Produk test-only `a37111b05060f10eb9af694dcd1fd1692f538b84`; harness `677870a9d7c47a44e9ccc055cce36650d6fc225a` | [39435192273](https://github.com/cepeter-job/spt-downloader/actions/runs/39435192273): 4 kegagalan assertion yang diharapkan, 6,22 detik |
| Regresi keyboard RED lengkap | Produk test-only `7475d89c85db4730270fefcd41f18291b9ba75b9`; harness `d22563d3595349173d24efd2c7fa070b9d8abb53` | [39435990788][keyboard-red]: 5 kegagalan assertion yang diharapkan, 6,83 detik; tanpa collection/setup error |
| Kandidat akhir | Head `6440e03df821db2882446d729c62257666286d0a`; merge `94f7870a8db469e3aa10bb61669e7dd0845b9afa` | [39436714539][product-ci], attempt 1: sukses; 3.295/3.295 tes Windows lulus dalam 1.085,13 detik; 456/456 portable; source/frozen dan exact-ID readback runner lulus |
| Diagnostik akhir | Head `67396564dd12b8a3d9eb8cd08920316cf83ae2d3`; checkout `8dab408f53ef3fe91c0a228ce87ff119bda66400`; kandidat dipin terpisah | [39436831760][native-ci], attempt 1: sukses; 5/5 regresi keyboard lulus dalam 8,80 detik, 90 screenshot fisik dan pengukuran berpasangan tersimpan |

T1 RED terdahulu: `a7d9989` / run [39411414833](https://github.com/cepeter-job/spt-downloader/actions/runs/39411414833). T2 RED: `eb8675a541dabf70efd84b488619abd502043f89` / run [39419860130](https://github.com/cepeter-job/spt-downloader/actions/runs/39419860130), 40 gagal dan 3.250 lulus sebelum implementasi overwrite. Hasil tersebut dicatat sebelum solusi. Run full yang dibatalkan setelah digantikan head baru tidak dianggap GREEN atau bukti kegagalan produk; RED keyboard berasal dari job diagnostik terfokus dengan interpreter dan lock yang sama. Full Windows GREEN akhir tetap wajib.

Commit dokumentasi yang menerbitkan laporan ini datang setelah kandidat di atas. Kesamaan pohon produk diperiksa terpisah; jangan menempelkan SHA/head dokumen pada EXE atau hasil runtime kandidat yang berbeda.

## 3. Temuan review dan perbaikan

Review seluruh rentang produk dengan konteks baru pada `d8dc09b` menemukan dua masalah keyboard. Run native awal mereproduksi keduanya: Tab menuju tabel selection lalu Down tidak mengisi item focus, dan tombol horizontal pada tabel overwrite tidak memindahkan viewport. Pemeriksaan tambahan menemukan bahwa daftar overwrite juga memerlukan item focus awal agar native Down dapat menjangkau file berikutnya. Regresi ditulis dan kegagalannya diamati pada Windows sebelum perbaikan.

Perbaikan `ab75c76` menambahkan 34 baris App: Down pertama yang eksplisit memulai selection pada baris visible pertama; Ctrl-navigation existing tetap native; tabel overwrite memakai item focus `file-0` tanpa memilih file atau memindahkan keyboard focus dari **Jangan ganti**; Ctrl+Left/Right/Home/End menggulir viewport path. Binding memakai registry milik modal dan current-interaction guard yang sama. Tidak ada timer, thread, trace, format reply, atau jalur persetujuan baru.

Screenshot awal juga memperlihatkan heading **Normal / pembetulan** terpotong pada ukuran kecil dan heading overwrite terpusat di luar viewport kolom path yang lebar. `6440e03` menetapkan minimum lebar heading selection dari ukuran font `SPTLabel` yang sebenarnya dan meratakan heading overwrite ke kiri. Font, copy dan nilai data tidak diubah. Ini perbaikan presentasi kecil berdasarkan gambar sebelum/sesudah, bukan alasan menambah tes yang menyalin implementasi.

Review source independen pada delta T3 akhir tidak menemukan blocker: pilihan tetap kosong sebelum Down eksplisit, item focus overwrite berbeda dari keyboard focus, seluruh binding baru memakai current guard/cleanup, dan heading hanya berubah secara presentasi. Batas bukti yang masih terbuka: ukuran normal penuh serta tinggi compact penuh pada 200% memerlukan display lain yang cukup besar; opening end-to-end belum memenuhi sasaran 100 ms; penerimaan manusia belum dilakukan. Ini tidak disamarkan sebagai PASS penuh atau dipakai untuk mengubah snapshot persetujuan. Tidak ada perubahan batching atau fitur berikutnya.

## 4. Matriks penerimaan P2-01–P2-18

Nama tes di bawah berada di `tests/test_desktop_dialog_layout.py` kecuali disebut lain. PASS mengacu pada bukti kandidat akhir, bukan semata keberadaan fungsi tes. [Inventory dan hasil full Windows][product-ci] menjadi sumber pemilihan/hasil node.

| ID | Hasil | Bukti kandidat akhir dan batasnya |
| --- | --- | --- |
| P2-01 | PASS | `test_selection_context_uses_matching_job_snapshot`, `test_selection_missing_snapshot_is_not_guessed_from_form`: raw NPWP/tahun dari snapshot cocok, bukan form yang berubah. |
| P2-02 | PASS | `test_selection_empty_and_no_match_keep_exact_counts`; `test_selection_starts_empty_and_search_sends_only_the_clicked_return` (`test_desktop_selection_gui.py`); initial/no-match PNG di tiga skala. |
| P2-03 | PASS | `test_filter_reset_survives_empty_tree_events`; `test_chronology_survives_filter_clear_without_restoring_consent` (`test_desktop_selection_sorting.py`); fresh keyboard setelah filter serta enam body-bottom reset/no-match per skala. |
| P2-04 | PASS | `test_alt_j_and_header_preserve_filtered_selection_and_reply_order`; `test_chronology_preserves_filtered_selection_focus_and_inventory_order_reply` (`test_desktop_selection_sorting.py`); `test_default_display_does_not_reorder_confirmed_inventory_ids` (`test_desktop_selection_default.py`). |
| P2-05 | PASS | `test_focused_id_tracks_navigation_without_selecting`; `test_selection_uses_local_row_ids_and_preserves_the_observed_identifier` (`test_desktop_selection_gui.py`); raw ID panjang/Unicode dan suffix readonly di PNG. |
| P2-06 | PASS | `test_only_focused_submit_activation_sends_selection_once`; dua kasus baru `test_fresh_selection_keyboard_navigation_can_authorize_only_at_button`; search/tree tidak mengirim reply. |
| P2-07 | PASS | `test_blank_or_nonstring_folder_never_opens_confirmation`, `test_missing_folder_is_not_defaulted`, `test_stale_malformed_folder_cannot_stop_new_job`. |
| P2-08 | PASS | `test_long_readonly_values_remain_literal_and_reachable`; `test_overwrite_displays_the_exact_prior_export_folder` (`test_desktop_selection_gui.py`); `test_overwrite_count_template_is_strict` (`test_desktop_ui_copy.py`); folder/path suffix fisik dapat dicapai. |
| P2-09 | PASS | `test_overwrite_keyboard_decisions_preserve_protocol`; `test_closing_selection_cancels_without_implicitly_selecting_every_record` (`test_desktop_selection_gui.py`); native X/Alt+S/terminal mempunyai reply/Stop yang benar dan safe focus. |
| P2-10 | PASS | `test_overwrite_response_false_and_exception_do_not_fabricate_results`; `test_rejected_consent_dismisses_without_cancelling_terminal_cleanup` dan `test_terminal_destroys_pending_consent_before_another_job_can_start` (`test_desktop_selection_gui.py`). |
| P2-11 | PASS | `test_dialog_callback_cannot_authorize_a_different_job`, `test_duplicate_selection_requests_keep_one_dialog_and_cannot_reopen_after_reply`, `test_foreign_request_does_not_replace_the_pending_dialog` (`test_desktop_selection_gui.py`); deadline test pada `test_desktop_selection.py`. |
| P2-12 | PASS | `test_selection_reflow_preserves_data_and_owned_resources`, `test_dialog_close_cancels_only_owned_callbacks`; 25 siklus/sentinel root dan 18 close probe dengan token timer yang benar-benar pending. |
| P2-13 | PASS | `test_selection_layout_keeps_actions_visible_and_body_reachable`, `test_overwrite_layout_keeps_actions_visible_and_paths_reachable`; `test_dialog_sizes_leave_parent_unchanged` dan `test_dialog_small_work_area_does_not_force_an_unreachable_minimum` (`test_desktop_ui_theme.py`); ukuran normal/compact/minimum tercapai pada layar cukup di 100%/150%, serta clamping layar kecil pada 200%. |
| P2-14 | **PARTIAL** | Windows scaling aktual 100/150/200%, hash/bounds 90 physical PNG dan minimum/clamping lulus. **Ukuran normal penuh serta tinggi compact penuh pada 200% di display cukup besar NOT VERIFIED**: batas runner 1600×1200. Unit DIP/theme tidak dipakai menggantikan bukti OS. |
| P2-15 | PASS | Lima kasus keyboard baru RED→GREEN; `test_old_reflow_cannot_steal_terminal_focus`; fresh navigation, Ctrl+Home/End, file terakhir dan 18 pemeriksaan fokus setelah timer settle. |
| P2-16 | PASS pengukuran | Sepuluh sampel sesudah satu warm-up, baseline/kandidat pada job yang sama dan payload SHA yang cocok, 1/100/1.000 record serta 101 file. Sasaran opening 100 ms **belum tercapai**; delta performa diusulkan terpisah. |
| P2-17 | PASS | 3.295/3.295 full Windows dan 456/456 portable; source/frozen job sukses; enam digest ZIP pipeline, five-file allowlist dan empat SHA256SUMS cocok. `test_decline_overwrite_preserves_all_old_bytes` serta output/consent safety existing lulus pada inventory penuh. |
| P2-18 | PASS | Oracle literal `test_locked_owner_copy_is_literal`/`test_catalog_matches_approved_copy` (ui_copy), footer/bugreport existing; JSON preferences `test_new_missing_or_invalid_desktop_preference_defaults_to_json_hybrid`, `test_saved_mode_survives_load_save_and_reload`, `test_library_worker_and_checkpoint_implicit_dom_contracts_remain_compatible`; origin `test_default_preferences_choose_satu_without_user_origin_choice`; grouping `test_grouping_never_combines_normal_or_distinct_amendment_numbers` dan `test_literal_amendment_text_and_leading_zeroes_are_not_coalesced`. CLI default DOM diverifikasi dari source tidak berubah, bukan disimpulkan dari tes worker. |

Regresi batas produk yang tetap dipertahankan mencakup `test_decline_overwrite_preserves_all_old_bytes`, `test_ready_reply_arriving_after_the_deadline_cannot_authorize_overwrite`, `test_workbook_changed_while_consent_is_open_is_not_replaced`, dan `test_captured_consent_never_switches_to_a_newer_export_folder`. Lima teks pemilik, bugreport dan 54 ID katalog dikontrak oracle literal. Preferensi JSON-hybrid desktop, saved DOM, default CLI DOM, origin Satu, serta pemisahan workbook per masa/model tetap diperiksa melalui suite existing dan diff scope.

## 5. Screenshot Windows, ukuran dan scaling aktual

Run akhir menghasilkan **90 PNG fisik**, masing-masing 30 pada **100%, 150%, dan 200% Windows scaling**. Ketiga skala dibuktikan oleh `GetScaleFactorForMonitor`, `HRESULT=0`, serta metadata produk dan capture helper. Semua hash PNG cocok dengan manifest; semua dialog foreground dan berada sepenuhnya dalam monitor serta work area. Pemeriksaan native dan review gambar mencakup initial/multi-select, search reset/no-match, body bottom, ID/path suffix, safe focus, normal/compact/minimum.

Display yang diterima runner adalah **1600×1200 pixel fisik**, 32 bpp, 64 Hz. Mode 2560×1440 dan 1920×1200 ditolak oleh `CDS_TEST=-2`; mode 1600×1200 ter-enumerasi, lolos test, apply dan readback. Pada 200%, work area fisik 1600×1120 menghasilkan area logical 800×560. Oleh sebab itu normal selection 920×600 dan overwrite 800×520 tidak dapat diuji penuh: default produk menyesuaikannya menjadi ukuran di bawah. **P2-14 tetap PARTIAL / ukuran normal/compact penuh 200% NOT VERIFIED**. Hasil ini membuktikan clamping dan keterjangkauan pada layar kecil, bukan kecukupan layar untuk semua ukuran yang diminta.

Ukuran berikut adalah **actual logical client**, bukan dimensi PNG. Perbedaan satu pixel berasal dari konversi metrik native; setiap PNG tetap 1600×1200 pixel fisik.

| Windows scale | Selection normal (request 920×600) | Overwrite normal (request 800×520) | Compact, kedua dialog (640×560) | Minimum, kedua dialog (540×390) |
| --- | --- | --- | --- | --- |
| 100% | 921×600 | 801×520 | 641×560 | 540×390 |
| 150% | 921×601 | 801×521 | 641×561 | 541×390 |
| 200% | 784×521, ter-clamp | 784×519, ter-clamp | 639×521, ter-clamp | 539×389 |

Setiap frame menyimpan state, requested DIP, actual client, work area, native DPI, awareness, Tk scaling, effective scale, nama PNG dan SHA-256. Screenshot akhir memakai helper proses terpisah yang memverifikasi per-monitor awareness lalu mengambil pixel desktop fisik melalui BitBlt. Proses App tetap memakai awareness existing; helper tidak mengimpor Tk/produk. **Gambar tidak diperbesar sesudah diambil dan nilai scaling produk tidak dimonkeypatch.**

App yang DPI-unaware tetap melaporkan `GetDpiForWindow=96` menurut [kontrak API Microsoft](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getdpiforwindow); Tk effective scale sekitar 1 pada proses yang diuji tidak membatalkan perubahan skala monitor. Klaim scaling diikat juga ke [native monitor scale dan HRESULT](https://learn.microsoft.com/en-us/windows/win32/api/shellscalingapi/nf-shellscalingapi-getscalefactorformonitor), awareness, physical mode, serta physical window/work-area bounds. [EnumDisplaySettingsW](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-enumdisplaysettingsw) melaporkan resolusi fisik tanpa DPI virtualization. Requested client yang ter-clamp ditulis sebagai ukuran aktual; tidak diklaim sebagai 920×600 penuh jika area layar tidak cukup.

Display preflight hanya menerima mode setelah `CDS_TEST`, apply dan readback; source DPI dibaca ulang sesudah perubahan resolusi. Paket DisplayConfig source-DPI yang digunakan adalah antarmuka **undocumented** untuk diagnostik sementara, bukan dependency produk. Permintaan di luar range tidak dipaksa atau di-clamp menjadi skala lain. Pemulihan resolusi dan source DPI asli pada `finally` keduanya mengembalikan kode 0. Tidak ada perubahan display yang dibawa ke produk.

Run pertama [39433410876](https://github.com/cepeter-job/spt-downloader/actions/runs/39433410876) memuat 24 frame 100%. Run kedua [39434208365](https://github.com/cepeter-job/spt-downloader/actions/runs/39434208365) membuktikan monitor 100%/150%, tetapi PNG PrintWindow-nya adalah rendering virtualized dan beberapa geometry dipaksa melampaui work area. Keduanya dipertahankan sebagai jejak diagnosis, **bukan bukti akhir keterlihatan fisik pada DPI tinggi**. Screenshot akhir menggantikannya untuk kesimpulan native.

## 6. Keyboard, penjelasan di bawah viewport dan teardown

Pada ketiga skala, fresh selection dimulai dengan fokus search dan pilihan kosong; Tab menuju tabel kemudian Down mengisi `record-0`, menampilkan raw ID yang sesuai dan tidak mengirim reply. Regresi juga menguji navigasi setelah filter menghapus pilihan dan persetujuan hanya melalui tombol eksplisit. Overwrite mempertahankan keyboard focus aman pada **Jangan ganti**; item focus awal `file-0` membuat Down mencapai `file-1` dan pengulangan Down mencapai `file-100`. Ctrl+End mencapai akhir viewport (`xview` akhir 1,0), Ctrl+Home kembali ke 0; tidak ada selection atau persetujuan implisit.

**18/18 probe close dengan timer sungguh pending** lulus: dua jenis dialog × X/Alt+S/terminal × tiga skala. Usia timer sebelum close terukur paling tinggi sekitar 7,85–12,54 ms, masih sebelum deadline reflow 75 ms. Token timer hilang, modal/grab terlepas, reply/Stop sesuai kontrak, dan identitas fokus tetap sama setelah 200 ms. X/Alt+S kembali ke root; terminal kembali ke tombol shell existing yang enabled (`.!mainview.!frame4.!button`) tanpa callback modal mengambilnya lagi. Hanya selection X/Alt+S dan overwrite Alt+S memanggil Stop; overwrite X menolak (`False`), terminal tidak mengirim reply/Stop baru.

Penjelasan reset/no-match berada sesudah tabel dan field ID sesuai urutan body yang disetujui. Gambar awal menunjukkan sebagian teks berada di bawah fold; keberadaan string dalam widget saja tidak dianggap bukti keterbacaan. Capture `*-body-bottom` secara khusus memperlihatkan summary/notice sesudah body digulir dan merekam bounds terhadap viewport. Action bar tetap terpisah dari body scroll.

Probe close awal mempunyai `pending_timer_before=false`, sehingga tidak membuktikan pembatalan reflow yang benar-benar pending. Probe akhir memproses Configure tanpa mengeksekusi timer, mengamati token `layout_after`, menutup modal, memeriksa token hilang, lalu menunggu 200 ms dan membandingkan identitas fokus. Tes 25 siklus dan sentinel root memberi bukti lifetime tambahan; tidak ada klaim benchmark RAM jangka panjang.

## 7. Pengukuran berpasangan dan keputusan performa

Baseline dan kandidat berada pada job Windows yang sama, dengan checkout serta proses Tk terpisah dan payload sintetis identik. Satu warm-up dikecualikan; ada 10 sampel untuk setiap kombinasi aksi/inventaris. Waktu end-to-end memakai `perf_counter_ns` dari handler sampai pekerjaan layout terkait stabil, tidak memasukkan screenshot atau fixed sleep fixture. Durasi handler disimpan terpisah. Percobaan pembatalan terpisah menjadwalkan Stop pada 1 ms agar tidak memotong sampel layout normal.

| Dialog / inventaris | Aksi | Baseline median / p95 | Kandidat median / p95 | Kandidat cancel maksimum |
| --- | --- | --- | --- | --- |
| selection / 1 | open | 68.75 / 71.36 | 130.64 / 137.59 | 31.70 |
| selection / 1 | filter | 2.04 / 3.60 | 78.28 / 78.62 | 12.35 |
| selection / 1 | sort | 1.80 / 1.94 | 2.44 / 3.62 | 14.10 |
| selection / 100 | open | 73.33 / 82.00 | 140.60 / 144.08 | 58.31 |
| selection / 100 | filter | 5.99 / 8.61 | 78.75 / 79.12 | 14.44 |
| selection / 100 | sort | 4.40 / 8.43 | 4.31 / 5.96 | 16.19 |
| selection / 1000 | open | 83.26 / 97.33 | 154.19 / 158.34 | 53.01 |
| selection / 1000 | filter | 16.66 / 26.95 | 83.01 / 84.56 | 18.16 |
| selection / 1000 | sort | 11.94 / 23.88 | 9.56 / 10.72 | 19.39 |
| overwrite / 101 | open | 75.97 / 77.53 | 158.40 / 179.71 | 63.65 |

Satuan tabel adalah milidetik. Dengan 10 sampel, p95 nearest-rank sama dengan maksimum; seluruh raw samples, median/p95/max, handler samples, cancellation-service samples, payload bytes/SHA-256, versi Python/Tcl/Tk dan ukuran/scale tersimpan dalam `evidence.json`. Semua timing berpasangan dilakukan pada scaling monitor aktual 100%, display 1600×1200, CPython 3.14.8 dan Tcl/Tk 9.0.4. App tetap awareness 0, native DPI 96 dan effective scale sekitar 1,000788. Setiap pasangan dialog/ukuran/operasi memiliki payload SHA-256 yang identik. Benchmark memakai ukuran default masing-masing revisi: baseline selection 739×429 dan overwrite 599×402, kandidat 921×600 dan 801×520 logical client. Ini perbandingan pengalaman default produk, bukan eksperimen yang mengisolasi satu variabel algoritme.

Median opening selection bertambah dari baseline 68,75/73,33/83,26 ms menjadi 130,64/140,60/154,19 ms untuk 1/100/1.000 record; overwrite 101 file menjadi 158,40 ms dari 75,97 ms. End-to-end mencakup deferred reflow 75 ms yang benar-benar selesai, berbeda dari handler median sekitar 26,49–46,23 ms. Kandidat filter berada sekitar 78,28–83,01 ms dan sort 2,44–9,56 ms; seluruh sampel kedua operasi di bawah 100 ms. Semua cancellation-service samples juga di bawah 100 ms, maksimum keseluruhan 63,65 ms. Sampel ini tidak membuktikan performa seluruh mesin pengguna atau portal nyata.

**Keputusan:** ajukan delta performa terpisah: profilkan initial layout dan deferred reflow, lalu bandingkan opsi pengurangan kerja layout atau batching row dengan payload dan metode timing yang sama. Ukur kembali opening, filter/sort dan respons Stop sebelum memilih solusi. Batching belum diimplementasikan, dan data ini sendiri tidak membuktikan batching akan menghilangkan jeda. Perubahan tersebut menunggu persetujuan/scope tersendiri.

## 8. Pipeline dan exact artifact readback

Run kandidat akhir sukses. Windows job `118676117996` melaporkan **3.295 lulus, 0 gagal, 0 error, 0 skip**; stdout 1.085,13 detik (pengukuran pytest internal 1.084,9918683 detik). Portable melaporkan **456 lulus, 0 gagal/error/skip** dalam 16,42890287 detik. Kedua collector memuat 3.295 node yang identik, semua dipilih di Windows; lima kasus regresi keyboard baru berada dalam inventory final. Run/attempt, merge SHA dan CPython 3.14.8 pada inventory serta measurements cocok dengan artifact.

Routing/actionlint, lock freshness, dependency audit tanpa vulnerability yang dilaporkan, fresh managed worker setup/reuse, source GUI self-test, frozen build/self-test, validasi payload dan exact-ID readback runner semuanya sukses. Job package `118685868201` serta gate agregat juga sukses; release-provenance dan branch-cleanup memang skipped pada PR ini, bukan tes gagal yang diabaikan. Keenam ZIP pipeline diunduh kembali dan digest transport dibandingkan dengan API GitHub; hasil pembacaan byte disimpan dalam arsip.

| Bukti | Artifact ID | Byte ZIP | SHA-256 ZIP |
| --- | --- | ---: | --- |
| dependency-audit | [12273345813](https://github.com/cepeter-job/spt-downloader/actions/runs/39436714539/artifacts/12273345813) | 762 | `870122a8bc9f9ee5a3d8bf3ff4adb755615d1150a19697831efea53b5d026804` |
| test-inventory-windows-python3.14.8 | [12273039095](https://github.com/cepeter-job/spt-downloader/actions/runs/39436714539/artifacts/12273039095) | 102866 | `f34c904d1c68f296d5088df9ed0edbaba1fe55cf90a749cb6a531dbb1fc354e1` |
| Paket Windows x64 | [12273034336](https://github.com/cepeter-job/spt-downloader/actions/runs/39436714539/artifacts/12273034336) | 28518329 | `42c227d596ba5b7bce76f5683fd650ac4d8727af7efdfb4b32152ef4eae6ac02` |
| test-inventory-portable-python3.14.8 | [12272916293](https://github.com/cepeter-job/spt-downloader/actions/runs/39436714539/artifacts/12272916293) | 59023 | `50836f5ba35bf22b70423823bfc751c3db795516bdf5b1ebc83a9c0c50be85bd` |
| test-results-windows-python3.14.8 | [12272584370](https://github.com/cepeter-job/spt-downloader/actions/runs/39436714539/artifacts/12272584370) | 59031 | `93ddf9f59ffacb3759ed97fb9f992fffc6fd2b586eeb6ea0bad173dcef180dd0` |
| test-results-portable-python3.14.8 | [12272226533](https://github.com/cepeter-job/spt-downloader/actions/runs/39436714539/artifacts/12272226533) | 9380 | `61024b44d877fa900b1fed94e365e5dede676a95d21a17af2061e33eb53212e5` |
| SPT_Phase2_Diagnostic_Run1.zip (historis) | [12268244580](https://github.com/cepeter-job/spt-downloader/actions/runs/39433410876/artifacts/12268244580) | 404087 | `bb56f7ae81ce0b4101946b9350759755b62443e020af823928842708d647db6d` |
| SPT_Phase2_Diagnostic_Run2.zip (historis) | [12270105396](https://github.com/cepeter-job/spt-downloader/actions/runs/39434208365/artifacts/12270105396) | 1137466 | `b81b1ca55c3b54e3fdda280185f226dccd54700fad7554effd13d9cd7fec224d` |
| SPT_Phase2_Keyboard_Red.zip (historis) | [12269542922](https://github.com/cepeter-job/spt-downloader/actions/runs/39435192273/artifacts/12269542922) | 1438 | `f5e7a314bccad34f9c7dda03f1907efc46ce3da372dc9ee97a031a79a3ac7fc8` |
| SPT_Phase2_Keyboard_Red_Complete.zip (historis) | [12272830296](https://github.com/cepeter-job/spt-downloader/actions/runs/39435990788/artifacts/12272830296) | 1810 | `f7c63ae97965f3ea46577b34d6ef6146a70e91a1211e781b63ad93661c8d0b9b` |
| Native final, 90 PNG | [12273111778](https://github.com/cepeter-job/spt-downloader/actions/runs/39436831760/artifacts/12273111778) | 36363680 | `d0e53c36cefade824aa742f86654228f7c1c39a8cdd0b2f0e9e82ba02c192aea` |

Paket final berisi tepat lima berkas tanpa duplikasi; empat entry pada `SHA256SUMS.txt` cocok dengan hash yang dihitung ulang.

| Berkas | Byte | SHA-256 |
| --- | ---: | --- |
| `LICENSE.txt` | 35823 | `230184f60bae2feaf244f10a8bac053c8ff33a183bcc365b4d8b876d2b7f4809` |
| `SPTDownloader.exe` | 28475483 | `0f09e1537a68fca921ea2b87da6edcff7264ad2cecc038ba5c7e37a5c67b48af` |
| `README.txt` | 2060 | `0fc3c646d1f2bee56924912fe8527921af71afb4dc01808cc4216558b6ea5459` |
| `build-selftest.json` | 4010 | `50b263e9bbfa960f74bd79a2c4f3ff73b18a7bc86de9d66fc4ce7f5884469d7a` |
| `SHA256SUMS.txt` | 329 | `dc685b5be25b055729a922497fae7dde3e69e5b6aa0edd89eb2529a0f88339b8` |

Frozen report mencatat `ok=true`, `frozen=true`, `uv_bundled=true`, CPython 3.14.8/x64/GIL, Tcl/Tk 9.0.4 dan build profile production. Daftar 37 worker resources cocok tepat dengan allowlist source kandidat. Caption pemilik/bugreport, kontrak credential-check/automatic-login, sorting sintetis dan default desktop `json-first` cocok; `credentials_accessed=false` dan `live_scrape=false`.

Report frozen tidak memiliki field eksplisit `synthetic=true` atau identitas commit/run di dalam JSON. Provenance diikat melalui metadata artifact/run/head, merge SHA pada nama artifact dan digest ZIP yang telah diverifikasi; jangan mengarang field yang tidak diekspor. Semua 32 pemeriksaan readback paket lulus.

Report source GUI tidak diekspor sebagai artifact terpisah oleh pipeline existing; buktinya berasal dari langkah source self-test pada runner serta assertion/inventory suite. Jangan menyebut ada file source-report yang diunduh bila yang diekspor hanya report frozen. Verifikasi lokal hanya membaca byte ZIP/JSON/hash; EXE tidak dijalankan di vm148/container.

## 9. Scope, arsip dan tindak lanjut

Diff baseline `977b068` → kandidat `6440e03` berisi 11 path: dua snapshot spec/plan, tiga modul App/copy/theme dan enam berkas tes/support. Delta T3 dari `d8dc09b` hanya `spt_desktop/app.py` (37 tambahan, 2 hapusan) dan `tests/test_desktop_dialog_layout.py` (100 tambahan). Dokumen bukti dan tautan README diterbitkan sesudah hasil runtime ini; pohon produk diuji tetap kandidat `6440e03`.

Arsip mencakup lima ZIP diagnostik (dua investigasi awal, dua RED keyboard, satu final), enam artifact pipeline kandidat, laporan ini, manifest provenance/hash, ringkasan exact readback, snapshot spec/plan yang tidak berubah, serta log source/frozen runner. Artifact lama dipertahankan sebagai sejarah, bukan digunakan untuk menggantikan hasil kandidat akhir. SHA-256 ZIP akhir dan ukuran dicatat pada manifest luar yang diserahkan bersama arsip; manifest internal mencatat hash setiap anggota tanpa membuat hash-diri yang melingkar.

Harness hanya berisi `.github/workflows/p2-dialog-evidence.yml` dan `scripts/_p2_dialog_evidence.py` di branch diagnostik. Workflow memakai exact checkouts, action SHA yang dipin, CPython 3.14.8/GIL, dependency hash-lock, permissions `contents: read`, tanpa secrets/portal, dan artifact JSON/PNG sintetis. Workflow produksi, runtime allowlist, dependencies, LICENSE, controller/worker/private IPC, capture dan output bisnis tidak diubah.

Paket bukti untuk diserahkan bernama `SPT_Phase2_Verification_2026-10-20.zip`, dengan manifest hash dan salinan bukti yang diperlukan sebelum retensi artifact diagnostik habis. Ketentuan penutupan adalah menutup PR #54 tanpa merge sesudah arsip tersimpan; status penutupan aktual tersedia pada [halaman PR diagnostik][diagnostic-pr]. Branch pemulihan tidak dihapus. Spec approved, plan dan arsip Phase 1 dipertahankan.

**Tindakan pemilik berikutnya, kurang dari 2 menit:** buka [PR #53][product-pr] dan dua screenshot minimum 200% pada arsip, lalu beri keputusan visual untuk label/aksi serta catatan reset/path panjang. Keputusan visual tersebut tidak menutup gap display P2-14 atau sasaran opening 100 ms; keduanya tetap tertulis. Tidak ada merge/deployment otomatis.

[product-pr]: https://github.com/cepeter-job/spt-downloader/pull/53
[diagnostic-pr]: https://github.com/cepeter-job/spt-downloader/pull/54
[product-ci]: https://github.com/cepeter-job/spt-downloader/actions/runs/39436714539
[native-ci]: https://github.com/cepeter-job/spt-downloader/actions/runs/39436831760
[keyboard-red]: https://github.com/cepeter-job/spt-downloader/actions/runs/39435990788
