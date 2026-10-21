# Prioritas 4 — penyelesaian reuse browser dan readiness fixture

Tanggal pengukuran: 21 Oktober 2026. Perubahan dibahas dalam
[PR #70](https://github.com/cepeter-job/spt-downloader/pull/70), setelah merge
[PR #69](https://github.com/cepeter-job/spt-downloader/pull/69).
[Audit batch pertama](2026-10-21-browser-fixture-performance.md) tetap menjadi
sumber hasilnya sendiri; persentase kedua workload tidak dijumlahkan.

## Keputusan dan kontrak yang dipertahankan

Selesaikan reuse proses Edge untuk 85 kasus browser yang masih membuka proses
per kasus. Semua memakai fixture browser berscope modul yang sudah tersedia;
setiap pemakaian tetap mendapat context baru, ditutup dalam `finally`. Tidak ada
route, halaman, storage, katalog, metrik, atau monkeypatch yang dibagi antarkasus.

| Modul | Seluruh kasus lama | Kasus browser lama |
| --- | ---: | ---: |
| `test_ppn_requested_choice.py` | 12 | 8 |
| `test_ppn_capture_readiness.py` | 5 | 5 |
| `test_capture_recovery.py` | 5 | 5 |
| `test_ppn_dom_context.py` | 3 | 3 |
| `test_ppn_dom_layout.py` | 9 | 3 |
| `test_inventory_year_browser.py` | 5 | 5 |
| `test_json_inventory.py` | 90 | 8 |
| `test_inventory_year_collection.py` | 8 | 7 |
| `test_inventory_readiness.py` | 10 | 5 |
| `test_period_cache_readiness.py` | 10 | 10 |
| `test_period_metadata_conflict.py` | 7 | 7 |
| `test_inventory_list_binding.py` | 21 | 9 |
| `test_period_cache_diagnostics.py` | 23 | 10 |
| Total | **208** | **85** |

Seluruh identitas, parametrisasi, assertion lama, payload, HTML, pilihan fixture,
dan kontrol readiness/cancellation tetap dipertahankan. Dua helper inventory dan
seluruh consumer dimigrasikan bersama agar tidak menyisakan nested sync Playwright
manager pada modul yang memakai keduanya. Setiap consumer mendaftarkan fixture
browser secara eksplisit; tes data/ekspor tetap tidak memintanya.

Helper listing mempertahankan timezone `Asia/Jakarta`, route pada context untuk
popup, dan timeout halaman 5000 ms. Helper inventory mempertahankan default
context, route pada page, dan timeout yang sama. Fungsi data
`test_json_inventory.context()` tidak berubah. Monkeypatch `Locator.evaluate`
tetap berscope fungsi; context ditutup sebelum patch dipulihkan.

Satu jeda auxiliary 100 ms diganti dengan
`page.expect_request_finished(predicate=..., timeout=5000)`, dipasang sebelum
pengiriman dan mencocokkan URL, metode POST, serta payload JSON yang tepat.
Assertion bahwa auxiliary tidak mengubah sequence/binding observer tetap ada.
[Kontrak Playwright](https://playwright.dev/python/docs/api/class-page#page-expect-request-finished)
menempatkan `requestfinished` setelah respons dan penyelesaian body. Pada handler
observer yang diperiksa, payload identity-only ini ditolak sebelum pembacaan body.

Satu regresi baru, `test_inventory_helpers_isolate_catalog_routes_and_metrics`,
memeriksa katalog IndexedDB, timezone, popup yang ter-route, penutupan context,
metrik baru, serta penolakan route helper lama pada context berikutnya di proses
browser yang sama. Regresi generic dari PR69 tetap memeriksa cleanup ketika gagal
serta isolasi cookie/local storage/session storage. Kode produksi, deadline
produksi, dependency, pembagian shard, dan seluruh gate paket tidak diubah.

## Revisi dan lingkungan pengukuran

| Ikatan bukti | Nilai |
| --- | --- |
| Baseline hasil merge PR69 | `e8624a8414a20e3edad8d87c80df8393d77d8f1e` |
| Tree baseline | `96139da638ee7cb9b7a2b40ca056aa0ea1368d9d` |
| Head kandidat yang diukur | `306f8969796f2d363c1a5e546df21e5a92dd0f95` |
| Checkout merge yang dieksekusi | `5612a743eb1db9cddce1e095caa0b19b6314435c` |
| Tree kandidat yang diukur | `559842e29a7e2cfb90939871b7e771f0556de6fe` |
| Run perbandingan, attempt 1 | [39624130220](https://github.com/cepeter-job/spt-downloader/actions/runs/39624130220) |
| Runner dan runtime | Windows 2022, CPython/GIL 3.14.8, Edge 155.0.4283.45 |
| Dependensi | Playwright 1.64.0, pytest 9.1.1, uv 0.13.4; instalasi lock dengan hash |
| SHA-256 lock tes | `71a0daa44473eeb882e73dd8f5902840956c111281c75952f302af7987bdb82f` |
| SHA-256 profiler | `f246fd9766603b86e090860ec1144ffbf09a78465b4d81d977f97fa629c6a5fc` |
| SHA-256 daftar terurut 208 node ID | `30efb4976301fdaba110afb0cb4b2503193c32ed46d9312ce63a1c47cbae8ade` |

Inventaris pembanding berasal dari run PR69
[39607973554](https://github.com/cepeter-job/spt-downloader/actions/runs/39607973554),
attempt 1, checkout `3a02401a636ec1762d9a9810db856b52573f5645`, artifact
`12349077203`. Inventaris itu mencakup 3.595 identitas lengkap dan 568 portable.
Tree checkout PR tersebut identik dengan tree baseline hasil merge, dan 208
identitas dipilih kembali secara tepat dari manifest aslinya. Sumber inventaris
ini tetap dicatat sebagai event `pull_request`; kesamaan tree tidak membuktikan
run push main atau attestation main69.

ZIP inventaris pembanding berukuran 64.221 byte, SHA-256
`11031e13a42d951e29ef4f0f87a752e6c06da3e35e112b632ecab4c296381d96`.
SHA-256 byte manifest asli adalah
`9d22c764013b290b9707615bd1585dd490fab6230426658d049d31ebf3d9314c`.

## Tiga pasangan pada workload yang sama

Setiap job memakai satu environment lock yang sama untuk baseline dan kandidat.
Pasangan 2 membalik urutannya. Dua regresi isolasi dijalankan terpisah sesudah
perbandingan agar 208 kasus lama tetap sebanding; hanya satu regresi yang baru.
Tidak ada retry atau pemilihan hasil. Total **3 × (208 + 208 + 2) = 1.254 eksekusi**,
semuanya lulus tanpa failure, error, atau skip. Seluruh 3.762 fase setup/call/teardown
cocok dengan JUnit dan identitas yang dipilih.

Durasi berikut adalah interval sesi pytest yang direkam profiler, dalam detik.

| Pasangan | Urutan | Baseline | Kandidat | Berkurang | Pengurangan |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 | Baseline → kandidat | 296,269 | 160,445 | 135,824 | 45,845% |
| 2 | Kandidat → baseline | 299,144 | 173,854 | 125,290 | 41,883% |
| 3 | Baseline → kandidat | 330,888 | 188,085 | 142,803 | 43,158% |
| Median hasil berpasangan | | | | **135,824** | **43,158%** |

Median dihitung dari selisih/persentase setiap pasangan, bukan persentase dari
selisih dua median terpisah. Pengurangan terlihat pada kedua urutan. Tiga
pengamatan ini tidak memisahkan pengaruh urutan dari variasi runner dan belum
mengukur flake jangka panjang.

Gabungan semua fase untuk 208 kasus menghasilkan median pengurangan berpasangan
135,435 detik (43,272%). Semua 123 kontrol tanpa browser tetap
masuk. Angka untuk subset 85 kasus browser saja tidak dipakai sebagai headline,
karena pytest dapat membebankan teardown browser modul ke tes kontrol terakhir.

Sesi dua regresi terpisah memerlukan 4,780 / 6,601 / 5,422 detik pada pasangan
1 / 2 / 3; median 5,422 detik. Biaya ini tidak dimasukkan ke perbandingan 208 kasus.
Pengukuran sesi tidak mencakup provisioning runner, instalasi environment, seluruh
waktu interpreter dari start hingga exit, atau keseluruhan pipeline Windows.

## Biaya lifecycle yang berkurang

Setiap pasangan mengamati **85 → 13** start Playwright, launch Edge, penutupan
browser, dan penghentian Playwright pada workload bersama. Seluruh 85 pemakaian
tetap membuat context baru. Baseline membuat 31 context implisit melalui
`Browser.new_page()` dan 54 secara eksplisit; kandidat membuat 85 context eksplisit.
Perubahan kategori penghitung tersebut bukan penambahan kasus atau pengurangan
isolasi.

| Operasi, waktu eksklusif | Median baseline (detik) | Median kandidat (detik) | Median selisih berpasangan (detik) |
| --- | ---: | ---: | ---: |
| Menutup browser | 53,043 | 3,908 | 48,973 |
| Memulai Playwright | 29,544 | 4,483 | 25,062 |
| Meluncurkan Edge | 17,765 | 2,886 | 15,128 |
| Menghentikan Playwright | 1,034 | 0,163 | 0,872 |

Durasi operasi sudah berada di dalam waktu fase/sesi. Jangan menambahkannya lagi
sebagai penghematan terpisah. Waktu eksklusif menghindari penghitungan ganda wrapper
yang bersarang. Perubahan biaya context/page juga memindahkan kategori API,
sehingga tiap kategori tidak mengisolasi satu penyebab penghematan.

Pipeline reguler memakai dua shard. Semua 13 modul memiliki kasus browser pada
kedua shard; struktur fixture berarti **26 launch** untuk 85 kasus tersebut dalam
pipeline itu. Angka 26 merupakan perhitungan dari inventaris/shard, bukan hasil
instrumentasi penuh pipeline. Pengurangan serial 85 → 13 tidak boleh dipakai
sebagai hitungan proses seluruh pipeline dua shard.

Perubahan auxiliary hanya menghapus anggaran tetap **0,1 detik** per pemakaian.
Profiler yang sama tidak memberi `expect_request_finished` kategori tersendiri;
biayanya tetap masuk waktu call/sesi. Jumlah seluruh fixed wait berubah
689 → 628, 694 → 650, dan 689 → 664. Selisih bersih itu juga mengikuti polling
produk dan event, sehingga tidak diatribusikan seluruhnya ke satu jeda yang
dihapus. Fixed wait produksi dan kontrol waktu yang disengaja tetap ada.

## Rantai artifact dan verifikasi

Setiap ZIP diunduh kembali menurut ID dan diperiksa terhadap ukuran serta digest
API GitHub. Masing-masing memuat tepat tujuh berkas: profile JSON dan JUnit untuk
baseline, kandidat, dan regresi; serta `comparison.json`. Pemeriksaan independen
mencocokkan commit/tree/parents/run/attempt, sumber inventaris, runtime, lock,
profiler, versi Edge, urutan sesi, identitas, setiap fase, dan hitungan ulang semua
angka. Profiler tidak merekam argumen API, URL request, storage, nilai pajak,
exception text, maupun isi capture.

| Pasangan | Artifact ID | Ukuran ZIP (byte) | SHA-256 ZIP |
| --- | --- | ---: | --- |
| 1 | `12357175273` | 59519 | `1c9d7947412efbf2be1190cfbf27b4a0ab5dc729e80f0a92dc19593e32bc7410` |
| 2 | `12357055591` | 59462 | `89bcd9c1aac5bad7ec5cf484305044657cfce8eb885bd58b4b25c41b3e6e5d03` |
| 3 | `12356696883` | 59823 | `49052425ff62776097837c097a7670994bb9d5cb76594ce13665c4b25e3c3ef4` |

Semua pytest, browser, self-test, dan build dijalankan pada runner GitHub.
Pemeriksaan lokal hanya membaca sumber/AST/Git dan metadata/hash/JSON/XML artifact.
Workflow dan plugin profiling sementara dihapus sebelum verifikasi revisi akhir.
Hasil suite lengkap, source/frozen self-test, checksum paket, pembacaan kembali
artifact exact-ID, dan status main pascamerge dicatat pada
[PR #70](https://github.com/cepeter-job/spt-downloader/pull/70) dengan revisi/runnya;
benchmark ini sendiri tidak menggantikan gate tersebut.

## Disposisi peluang tersisa

Dua varian browser `test_json_capture.py` berada pada shard berbeda. Reuse per
modul tidak mengurangi launch dalam pipeline dua shard saat ini. Satu kasus pada
`test_pr20_residual_contracts.py` tidak mempunyai pasangan untuk reuse. Ketiganya
dipertahankan. Launch browser nyata lain sudah memakai scope modul atau menguji
kepemilikan proses/profil secara sengaja.

Jeda login/prefill terlambat, readiness/cancellation, dan proses anak sintetis
merupakan kontrol perilaku yang diperlukan. Tidak ada penghapusan timeout
produksi, pengurangan pagination/identitas, pengurangan gate paket, atau
paralelisasi tes GUI/Job Object dalam satu runner. Dengan batch ini dan PR69,
seluruh peluang reuse yang ditinjau dan mengurangi launch pada dua shard sudah
memiliki implementasi, pengukuran, serta kontrak isolasi; angka keseluruhan
pipeline harus diukur terpisah jika kelak diperlukan.
