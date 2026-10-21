# Prioritas 4 — pengukuran dan optimasi fixture browser sintetis

Tanggal pengukuran: 21 Oktober 2026. Perubahan dibahas dalam
[PR #69](https://github.com/cepeter-job/spt-downloader/pull/69).

## Keputusan dan batas perubahan

Batch pertama prioritas 4 memakai satu proses Edge per modul pada
`test_browser.py` dan `test_pagination_actionability.py`. Setiap kasus tetap
mendapat context baru; context ditutup dalam `finally`, termasuk halaman popup
ketika kasus gagal. Dua modul ini berisi 20 kasus. Seluruh identitas,
parametrisasi, dan 46 assertion lama dipertahankan. Timeout yang sengaja diuji
juga dipertahankan.

Helper Masa `observed()` mengganti jeda tetap 200 ms dengan sinyal bahwa request
prefill awal sudah selesai, dengan batas 5 detik. Sinyal `.finally()` mencakup
respons 200 dan 403. Capture dipasang sebelum sinyal ditunggu dan tetap aktif
untuk request grid berikutnya. Sinyal ini membuktikan fetch sudah selesai dan
statusnya tersedia; penyelesaian body dan bukti capture tetap diperiksa oleh
`capture.drain()` serta assertion masing-masing kasus.

Lima kasus baru memeriksa empat kombinasi PPN/Unifikasi dan sukses/403, serta
penutupan context/popup dan isolasi cookie, local storage, session storage, dan
route setelah kegagalan sintetis. Regresi readiness sengaja menunda request
750 ms. Penundaan ini merupakan kontrol regresi yang tetap dipertahankan.

Kode produksi, deadline produksi, dependensi, pembagian shard, dan gate paket
Windows tidak diubah. Workflow serta plugin profiling hanya digunakan untuk
pengukuran di riwayat PR, lalu dihapus dari hasil akhir. Semua eksekusi pytest,
browser, dan build dilakukan pada runner GitHub; pemeriksaan lokal terbatas
pada sumber serta metadata/hash/JSON/XML artifact.

## Revisi, lingkungan, dan workload

| Ikatan bukti | Nilai |
| --- | --- |
| Baseline `main` | `766dd3e79b4077fa1ae86a7c32161dc77248cb6c` |
| Tree baseline | `23dda52c59451c7c2f847090af6bcc0320b18955` |
| Head kandidat yang diukur | `781ffbf3e9a5fa13c52e5dcbfc74403dfa0001a9` |
| Checkout merge kandidat yang dieksekusi | `2baaeb010b8649131728eb0f6bdf40f61ae16137` |
| Tree kandidat yang diukur | `7b682ec02141c08ca040ff890cfda87449d1df30` |
| Run perbandingan, attempt 1 | [39605685020](https://github.com/cepeter-job/spt-downloader/actions/runs/39605685020) |
| Runner dan runtime | Windows 2022, CPython/GIL 3.14.8, Edge 155.0.4283.45 |
| Dependensi | Playwright 1.64.0, pytest 9.1.1, uv 0.13.4; instalasi `locks/test.txt` dengan hash |
| SHA-256 lock tes | `71a0daa44473eeb882e73dd8f5902840956c111281c75952f302af7987bdb82f` |
| SHA-256 profiler yang sama untuk kedua varian | `f246fd9766603b86e090860ec1144ffbf09a78465b4d81d977f97fa629c6a5fc` |
| SHA-256 daftar terurut 107 node ID | `74ee391b88c8670d4c32985c214f2f97fc9c301d218195f1ceb4d93c5e3c9899` |

Workload bersama mencakup delapan modul: `test_browser` (10 kasus),
`test_pagination_actionability` (10), `test_masa_json_observer` (26),
`test_masa_json_field_observation` (21), `test_ppn_json_build_budget` (12),
`test_ppn_json_surface` (16), `test_ppn_json_replacement_control` (9), dan
`test_unifikasi_json_browser` (3). Seluruh 107 identitas cocok dengan inventaris
baseline yang diambil kembali dari
[run 39601237898](https://github.com/cepeter-job/spt-downloader/actions/runs/39601237898),
artifact `12346511034`: 3.590 kasus Windows dan 568 kasus portable.

Tiga job independen menjalankan baseline dan kandidat pada runner yang sama
untuk setiap pasangan. Pasangan 2 membalik urutannya. Lima regresi baru dijalankan
terpisah setelah perbandingan agar workload 107 kasus tetap identik. Tidak ada
retry atau pemilihan ulang hasil. Totalnya 3 × (107 + 107 + 5) = **657 eksekusi**.

Profiler merekam setup, call, teardown, durasi sesi, dan durasi operasi publik
Playwright. Tidak ada argumen API, nilai pajak, URL request, storage, maupun isi
capture yang direkam. Verifier memeriksa inventaris, tiga fase per kasus, JUnit,
commit/tree/run/attempt, versi runtime/browser, hash lock/profiler, dan hitungan
ulang hasil. Artifact diunduh dan diperiksa kembali berdasarkan ID, ukuran,
digest ZIP, serta tujuh berkas yang diizinkan.

## Hasil tiga perbandingan

Durasi berikut adalah seluruh sesi pytest untuk 107 kasus yang sama, dalam detik.

| Pasangan | Urutan | Baseline | Kandidat | Berkurang | Pengurangan |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 | Baseline → kandidat | 194,366 | 138,244 | 56,121 | 28,874% |
| 2 | Kandidat → baseline | 185,578 | 159,487 | 26,091 | 14,059% |
| 3 | Baseline → kandidat | 170,986 | 123,197 | 47,789 | 27,949% |
| Median hasil berpasangan | | | | **47,789** | **27,949%** |

Seluruh 657 eksekusi lulus, tanpa failure, error, atau skip. Median dihitung dari
selisih/persentase masing-masing pasangan; angka itu bukan persentase dari
selisih dua median terpisah. Besarnya pengurangan bervariasi. Pasangan 2 memakai
urutan terbalik; eksperimen ini tidak memisahkan pengaruh urutan dari variasi
runner. Tiga pengamatan mendukung adopsi batch ini, tetapi belum mengukur
tingkat flake jangka panjang.

Sesi lima regresi terpisah memerlukan 9,186 / 17,294 / 7,790 detik untuk pasangan
1 / 2 / 3, dengan median 9,186 detik. Biaya tambahan ini tidak dimasukkan ke
perbandingan workload bersama. Hasil di atas adalah penghematan pada 107 tes
terpilih; pengurangan persentase seluruh pipeline Windows belum diukur oleh
eksperimen ini.

## Apa yang berkurang

Pada setiap pasangan, jumlah start Playwright dan launch browser untuk workload
107 kasus turun dari 26 menjadi 8. Khusus dua modul yang diubah, jumlahnya turun
dari 20 menjadi 2 pada eksekusi serial ini. Pipeline produksi menggunakan dua
shard; bila kedua modul muncul pada kedua shard, browser fixture dibuat sekali
per modul per shard, sehingga pengurangan serial 20 → 2 tidak boleh disamakan
dengan jumlah proses dalam seluruh pipeline.

Durasi gabungan setup + call + teardown untuk 20 kasus tersebut adalah
55,224 → 19,287 / 58,262 → 31,075 / 49,700 → 17,279 detik. Median selisih
berpasangan 32,421 detik dan median pengurangan 65,076%. Mengukur call saja akan
menyesatkan karena sebagian pekerjaan lifecycle berpindah ke fixture setup.

| Operasi pada workload 107 kasus | Median baseline (detik) | Median kandidat (detik) | Median selisih berpasangan (detik) |
| --- | ---: | ---: | ---: |
| Menutup browser | 17,753 | 2,046 | 15,706 |
| Memulai Playwright | 8,799 | 2,746 | 5,891 |
| Meluncurkan Edge | 5,497 | 1,591 | 3,713 |
| Menghentikan Playwright | 0,325 | 0,120 | 0,211 |

Durasi operasi berada di dalam durasi fase/sesi, sehingga tidak boleh dijumlahkan
kembali sebagai penghematan tambahan. API `Browser.new_page()` pada baseline
mencakup pembuatan context sekaligus page. Perubahan menuju `new_context()` dan
`context.new_page()` memindahkan kategori biaya tersebut; metrik kategori itu
tidak menunjukkan murni biaya context.

Helper Masa dipanggil 49 kali dalam workload ini. Penghapusan 49 jeda × 200 ms
menghapus anggaran tunggu tetap 9,8 detik. Pengganti berbasis kondisi memerlukan
total 1,203 / 2,110 / 0,813 detik per pasangan, dengan median 1,203 detik.
Anggaran 9,8 detik bukan penghematan wall time yang terukur secara terpisah:
pekerjaan asynchronous dapat tumpang tindih dan masih ada wait pada driver.
Jumlah semua fixed wait berubah 445 → 374, 425 → 396, dan 444 → 374 panggilan.
Hanya 49 penghapusan yang dapat diatribusikan langsung ke perubahan helper;
perubahan bersihnya juga mengikuti perilaku driver/event selama eksekusi.
Fixed wait produksi dan kontrol timeout tetap ada.

## Bukti regresi sebelum perbaikan

[Run diagnostik 39604626898](https://github.com/cepeter-job/spt-downloader/actions/runs/39604626898),
attempt 1, memakai head `0b08dac8e9d0b9a07b05643420b893beb938dcd6`, checkout
`ce09a858e18f4eece5b0cc8da6b6a148c15b08f2`, dan tree
`cb70f1fc3691428f1fb46fc232dbbd5bb8b5fbf0`. Baseline 107 kasus lulus. Keempat
kasus readiness baru gagal tepat pada pemeriksaan bahwa prefill harus sudah
diamati sebelum fixture menyerahkan kontrol: jumlah metadata masih nol.
Setup dan teardown lulus; kegagalan bukan akibat import atau alat profiling.
Semua empat regresi kemudian lulus pada ketiga pasangan kandidat.

Profil diagnostik baseline mencatat 57,390 detik gabungan fase untuk 20 kasus
browser, termasuk 18,345 detik untuk penutupan browser dan 13,175 detik untuk
start Playwright serta launch Edge. Biaya baseline ini mengarahkan pemilihan
perubahan; hasil adopsi diambil dari tiga pasangan di atas.

## Rantai artifact

| Pengamatan | Artifact ID | Ukuran ZIP (byte) | SHA-256 ZIP |
| --- | ---: | ---: | --- |
| Baseline full inventory | [12346511034](https://github.com/cepeter-job/spt-downloader/actions/runs/39601237898/artifacts/12346511034) | 64128 | `b00f4b25133c314c2ddc2890b90afdda12a4995957e57999982522a91aa04966` |
| Diagnostik | [12348266550](https://github.com/cepeter-job/spt-downloader/actions/runs/39604626898/artifacts/12348266550) | 25513 | `ea5016a3d9a378eabf9758be31fb2b1d38e1377f0e92cffd19cf92d79452515e` |
| Pasangan 1 | [12349145045](https://github.com/cepeter-job/spt-downloader/actions/runs/39605685020/artifacts/12349145045) | 48030 | `53bb9dbcf1332a1ea3ac94e58bea69215e5508596d20153a6d6699a59496e60d` |
| Pasangan 2 | [12347924913](https://github.com/cepeter-job/spt-downloader/actions/runs/39605685020/artifacts/12347924913) | 47929 | `6e0bd5d13436f8e309c225bbd860e323e247ada7938c6b2a643c4ad6f4bf6c6f` |
| Pasangan 3 | [12348094157](https://github.com/cepeter-job/spt-downloader/actions/runs/39605685020/artifacts/12348094157) | 47916 | `d874e5ac5e57cc47722fed279dd334b4744dd541331014206f1da0a19d78bba5` |

Setiap artifact pasangan berisi `comparison.json` dan `profile.json`/`results.xml`
untuk baseline, kandidat, serta lima regresi kandidat. Artifact diagnostik
mempertahankan empat kegagalan yang disengaja. Hasil final setelah penghapusan
alat sementara dan penambahan laporan ini harus diikat ke head/checkout/run
serta artifact paket final di PR #69. Target inventaris final adalah seluruh
3.590 identitas lama ditambah tepat lima kasus baru, dengan 568 identitas portable
yang sama. Bukti pengukuran tidak menggantikan gate suite, audit dependensi,
source/frozen self-test, checksum, dan pembacaan ulang paket final.

## Kandidat batch berikutnya

Mulai dari delapan kasus `test_ppn_requested_choice.py`, yang masih meluncurkan
browser per kasus. Profilkan lifecycle terlebih dahulu dan pertahankan context
baru untuk setiap kasus. Modul capture readiness/recovery serta helper listing
bersama mempunyai scope yang lebih luas dan memerlukan pemeriksaan route,
IndexedDB, timezone, dan teardown sebelum pola yang sama diadopsi.

Satu jeda fixture literal 100 ms masih ada pada `test_inventory_list_binding.py`
setelah auxiliary fetch; readiness event dapat diteliti, dengan peluang anggaran
tunggu hanya 0,1 detik. Jangan menghapus penundaan yang sengaja membuktikan
timeout, late request, penolakan otorisasi, atau cleanup proses. Penghematan untuk
kandidat lanjutan belum diukur dan tidak termasuk hasil PR ini.
