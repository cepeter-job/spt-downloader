# Evaluasi dua shard Windows setelah optimasi fixture

## Keputusan

Adopsi **dua shard Windows terisolasi** sebagai default PR, push kode, dan dispatch.
Lima pasangan pipeline lengkap pada satu commit memenuhi target evaluasi:
median penurunan waktu sampai check gabungan **40,54%**, melampaui
target 20%. Seluruh sepuluh run lulus pada attempt pertama, dengan inventory penuh,
JUnit tanpa failure/error/skip, dan package yang diverifikasi ulang.

Pemakaian runner dinyatakan terpisah: median perubahan jumlah waktu runner Windows
per pasangan adalah **+8,16%**.
Angka ini mengukur penggunaan kapasitas runner; perhitungan tagihan berada di luar
evaluasi. Kontrol serial tetap
tersedia melalui dispatch untuk diagnosis dan perbandingan berikutnya.

Prioritas 1 dan 2 sudah masuk `main` melalui PR #63/#65. PR #66 menyelesaikan
prioritas 3; reuse browser dan penggantian sleep fixture pada prioritas 4 tetap
merupakan pekerjaan terpisah.

## Identitas dan metode

- Baseline aplikasi: `a7d742ea887dffe7c37af04a2bd6cfcbfe69af63`.
- Commit pilot beku untuk seluruh pasangan: `a6afdb97eeef26f38e4f8f2c7969b42e1438c27d`.
- Tree pilot: `c597b4463864051a3b9b3058b51066fa6ccc95cf`.
- Workflow: `.github/workflows/windows-build.yml`; event `workflow_dispatch`,
  attempt `1`, CPython/GIL produksi `3.14.8`, runner `windows-2022`.
- Tiga pasangan `restore` dan dua pasangan `cold`, urutan mulai bergantian:
  serial dahulu pada pasangan 1/3/5; dua shard dahulu pada pasangan 2/4.

Definisi metrik:

- Endpoint utama: `completed_at` job **Windows tests and dependency audit**
  dikurangi `created_at` workflow run. Nilai mencakup antrean, routing, setup,
  portable/audit, seluruh shard, managed worker, build, upload, artifact readback,
  dan check gabungan; pekerjaan yang paralel tidak dijumlahkan ke endpoint ini.
- Pengurangan pasangan: `(serial - dua_shard) / serial × 100%`. Target memakai
  median lima persentase pasangan, bukan rasio dua median yang berbeda.
- Waktu runner Windows: jumlah `completed_at - started_at` seluruh job berlabel
  `windows-2022` (integration, audit, package), tanpa antrean. Ini waktu terukur,
  bukan pembulatan menit yang ditagihkan atau perkiraan biaya uang.

Pilot mempertahankan default serial sampai pengumpulan bukti selesai. Delta
adopsi mengubah default dan kontrak routing terkait; fixture aplikasi dan algoritme
partisi tidak berubah. Empat identitas kasus kontrak CI berubah nama agar sesuai
dengan default baru; validasi PR akhir harus mengumpulkan ulang inventory lengkap.
PR #64 (`58d1c2227f87ad10c84db9fd6e473b10bbd1f570`) kemudian dikonsolidasikan
ke PR #66: perbaikan callback SSO, discovery PDF laporan keuangan, pagination
ukuran maksimum, dan diagnostik tabel. Perubahan aplikasi tersebut tidak ada
pada commit pengukuran beku dan menambah regresi tersendiri. Hasil CI commit
gabungan akhir dicatat pada PR, terpisah dari pengukuran pilot ini; angka pilot
tidak boleh diklaim sebagai pengukuran ulang seluruh aplikasi hasil konsolidasi.

Penjadwalan dibatasi hingga enam job integration Windows kampanye aktif, dengan
maksimal dua pasangan baru per batch. Batas ini disesuaikan dari dua pasangan
belum selesai sebelum ada hasil pasangan pertama. Run PR/benchmark pendukung
berjalan bersamaan pada bagian awal kampanye. Dispatch dalam satu pasangan dapat
berjarak beberapa menit karena batas kapasitas; ini bukan eksperimen pada hardware
identik dengan antrean yang dieliminasi. Seluruh percobaan tetap tercatat; tidak
ada retry atau pembatalan kampanye yang disembunyikan.

## Hasil pipeline lengkap

Durasi memakai format menit:detik. Setiap tautan menunjuk run yang diukur.

| Pasangan | Cache | Serial / durasi | Dua shard / durasi | Penurunan |
| --- | --- | --- | --- | --- |
| 1 | restore | [39581693950](https://github.com/cepeter-job/spt-downloader/actions/runs/39581693950) — 18:39 | [39581842960](https://github.com/cepeter-job/spt-downloader/actions/runs/39581842960) — 11:23 | 38,96% |
| 2 | cold | [39582068250](https://github.com/cepeter-job/spt-downloader/actions/runs/39582068250) — 18:30 | [39581965232](https://github.com/cepeter-job/spt-downloader/actions/runs/39581965232) — 11:00 | 40,54% |
| 3 | restore | [39583259921](https://github.com/cepeter-job/spt-downloader/actions/runs/39583259921) — 20:04 | [39583430139](https://github.com/cepeter-job/spt-downloader/actions/runs/39583430139) — 11:19 | 43,60% |
| 4 | cold | [39584725889](https://github.com/cepeter-job/spt-downloader/actions/runs/39584725889) — 20:36 | [39584008276](https://github.com/cepeter-job/spt-downloader/actions/runs/39584008276) — 10:44 | 47,90% |
| 5 | restore | [39584857915](https://github.com/cepeter-job/spt-downloader/actions/runs/39584857915) — 17:55 | [39585431388](https://github.com/cepeter-job/spt-downloader/actions/runs/39585431388) — 10:53 | 39,26% |

| Kondisi cache | Pasangan | Median penurunan pasangan |
| --- | --- | --- |
| restore | 3 | 39,26% |
| cold | 2 | 44,22% |

Mode `restore` diperiksa melalui log dan manifest aktual; kedua cache uv/wheel dan
managed Python hit pada job yang diukur. Mode `cold` menonaktifkan restore di
portable, integration, audit, dan package, bukan menghapus cache repositori.
Manifest cold menyimpan `cache_hit: null` dan `python_cache_hit: "false"`; `null`
tidak dilabeli sebagai cache miss. Seluruh dispatch memakai `save-cache: false`.
Antrean job yang dieksekusi berada pada rentang 2–4 detik menurut
`started_at - created_at` masing-masing job. Antrean yang tumpang tindih tidak
dijumlahkan sebagai tambahan waktu pipeline.

### Waktu runner Windows

| Pasangan | Serial (detik) | Dua shard (detik) | Perubahan |
| --- | --- | --- | --- |
| 1 | 1120 | 1260 | +12,50% |
| 2 | 1111 | 1237 | +11,34% |
| 3 | 1207 | 1151 | -4,64% |
| 4 | 1230 | 1145 | -6,91% |
| 5 | 1078 | 1166 | +8,16% |

Jumlah seluruh lima run serial adalah 5746 runner-seconds Windows;
lima run dua shard berjumlah 5959, atau
+3,71% secara kumulatif. Rasio jumlah ini
berbeda dari median perubahan per pasangan +8,16%;
keduanya ditampilkan agar variasi antar-run tetap terlihat.

### Pemisahan fase

Seluruh angka berikut dalam detik. Pasangan angka pada kolom setup/pytest adalah
shard 0 lalu shard 1; serial hanya satu angka. Setup manifest diukur dari marker
setelah checkout sampai pytest session mulai. Durasi pytest berasal dari jam
monotonik manifest; durasi job/step berasal dari timestamp API Actions dengan
resolusi detik. Package mencakup gate inventory, instalasi, source/frozen self-test,
build, checksum, upload/readback dan cleanup; kolom upload/readback sudah termasuk
di dalamnya. Kolom-kolom ini tidak boleh dijumlahkan untuk menghitung endpoint utama.

| Pasangan / mode | Setup | Pytest | Worker | Package | Upload | Readback |
| --- | --- | --- | --- | --- | --- | --- |
| 1 / serial | 5,77 | 1016,73 | 5 | 48 | 3 | 2 |
| 1 / 2 shard | 6,11 / 5,73 | 547,13 / 582,90 | 4 | 50 | 2 | 3 |
| 2 / serial | 4,75 | 1015,37 | 4 | 38 | 2 | 2 |
| 2 / 2 shard | 5,10 / 5,23 | 555,50 / 561,23 | 5 | 48 | 2 | 4 |
| 3 / serial | 6,61 | 1106,87 | 5 | 43 | 1 | 2 |
| 3 / 2 shard | 4,84 / 4,67 | 586,10 / 448,87 | 5 | 40 | 1 | 1 |
| 4 / serial | 5,18 | 1134,09 | 5 | 48 | 3 | 3 |
| 4 / 2 shard | 5,31 / 4,23 | 549,62 / 479,54 | 4 | 40 | 1 | 2 |
| 5 / serial | 6,45 | 979,53 | 4 | 40 | 2 | 1 |
| 5 / 2 shard | 4,92 / 4,77 | 560,94 / 491,66 | 5 | 41 | 1 | 1 |

## Kelengkapan dan pemeriksaan package

Setiap collector mengamati **3.521 identitas tes** yang sama; serial memilih
seluruhnya, shard memilih **1.791 + 1.730**, dan portable memilih **568**. Dibandingkan
3.409 identitas baseline, terdapat 123 ID baru dan 11 ID lama yang berubah dalam
`test_ci_routing.py`, `test_ci_sharding.py`, dan `test_workflow_contracts.py`
(neto +112 kasus). Seluruh identitas di luar tiga file kontrak CI tersebut tetap
ada. Tidak ada test filtering baru untuk memperkecil beban Windows.

Sebelum build, verifier membaca manifest asli portable dan serial atau kedua
manifest shard dalam direktori terpisah. Ia memeriksa commit, versi Python, run ID,
attempt, platform/workload, exit status integer nol, identitas tanpa duplikasi,
urutan/index/count shard, dan partisi SHA-256 deterministik. Gabungan shard harus
sama persis dengan seluruh collection portable; pilihan portable tetap mengikuti
aturan portable yang ada. Manifest gabungan buatan tidak menggantikan bukti asli.
JUnit juga dicocokkan ke identitas yang dipilih, dengan nol failure/error/skip.

SHA-256 inventory penuh kampanye adalah
`9676a7aae9a66228f4365dc00a8e2ed68e17051b2d3da85586ef2840aff57c4d`; encoding yang digunakan adalah UTF-8 dari identitas terurut,
dipisahkan LF, dengan satu LF terakhir. Angka/hashes ini mengikat pilot, bukan
pengganti collection baru pada commit adopsi.

Managed worker fresh setup dan verified reuse berjalan sekali pada serial atau
shard 0. Dependency audit, source GUI self-test, frozen GUI/build, allowlist lima
file, checksum, serta download dan verifikasi artifact berdasarkan **ID persis**
tetap wajib. Source self-test berhasil menurut step dan perintah pada log runner;
byte laporan source tetap lokal di runner dan tidak diunggah. Laporan frozen
terdapat di artifact dan diperiksa bersama byte payload. Tidak ada akun nyata,
kredensial, data wajib pajak, atau live scrape dalam bukti ini.

### Artifact inventory dan JUnit

Urutan ID per kolom adalah portable, lalu Windows serial atau shard 0 dan shard 1.
Seluruh artifact terikat run di kolom kedua, commit pilot, Python 3.14.8, dan
attempt 1. Ukuran dan digest ZIP unduhan cocok dengan metadata GitHub; identitas
di dalam manifest dan JUnit diperiksa kembali secara offline.

| Pasangan / mode | Run | Inventory artifact ID | JUnit/measurements artifact ID |
| --- | --- | --- | --- |
| 1 / serial | [39581693950](https://github.com/cepeter-job/spt-downloader/actions/runs/39581693950) | 12336811610, 12338966537 | 12336816608, 12338991647 |
| 1 / 2 shard | [39581842960](https://github.com/cepeter-job/spt-downloader/actions/runs/39581842960) | 12336477467, 12339095300, 12337841826 | 12336696953, 12339225225, 12337986811 |
| 2 / serial | [39582068250](https://github.com/cepeter-job/spt-downloader/actions/runs/39582068250) | 12336802173, 12339121906 | 12337171520, 12338537214 |
| 2 / 2 shard | [39581965232](https://github.com/cepeter-job/spt-downloader/actions/runs/39581965232) | 12336707093, 12337876961, 12339425384 | 12336802039, 12338091825, 12339030514 |
| 3 / serial | [39583259921](https://github.com/cepeter-job/spt-downloader/actions/runs/39583259921) | 12338630920, 12338713957 | 12338865916, 12339338870 |
| 3 / 2 shard | [39583430139](https://github.com/cepeter-job/spt-downloader/actions/runs/39583430139) | 12337912201, 12339032555, 12339412242 | 12338396828, 12339047916, 12338822352 |
| 4 / serial | [39584725889](https://github.com/cepeter-job/spt-downloader/actions/runs/39584725889) | 12338843170, 12339866629 | 12339462631, 12339936460 |
| 4 / 2 shard | [39584008276](https://github.com/cepeter-job/spt-downloader/actions/runs/39584008276) | 12338052869, 12338638775, 12339048459 | 12338367623, 12338738410, 12338938286 |
| 5 / serial | [39584857915](https://github.com/cepeter-job/spt-downloader/actions/runs/39584857915) | 12338908153, 12339826376 | 12339147970, 12340001172 |
| 5 / 2 shard | [39585431388](https://github.com/cepeter-job/spt-downloader/actions/runs/39585431388) | 12339058998, 12341005177, 12340660152 | 12339228654, 12340715488, 12340685233 |

### Artifact distribusi

Semua nama berbentuk
`SPTDownloader-Windows-x64-<commit-pilot>-python3.14.8-attempt1`. Masing-masing ZIP
berisi tepat `SPTDownloader.exe`, `LICENSE.txt`, `README.txt`,
`build-selftest.json`, dan `SHA256SUMS.txt`; checksum empat file payload cocok.
Hash di bawah adalah hash ZIP GitHub, terpisah dari hash file di dalam ZIP.

| Run | Artifact ID | Byte ZIP | SHA-256 ZIP |
| --- | --- | --- | --- |
| [39581693950](https://github.com/cepeter-job/spt-downloader/actions/runs/39581693950) | 12338012848 | 28489440 | `994ca87a7329ff5f0a63d7200aa0d261c86d6ad77689467fc3c4250fa8928f03` |
| [39581842960](https://github.com/cepeter-job/spt-downloader/actions/runs/39581842960) | 12337946908 | 28489996 | `aafbcf9a16f9636561ddb5b25ee7d4e1bc6420d2812a3f15360a80e45f75bc94` |
| [39582068250](https://github.com/cepeter-job/spt-downloader/actions/runs/39582068250) | 12339167202 | 28487326 | `c25939ee5ee00fed008bb6d749ccdba7ed04af074205980e52fb2b660602de49` |
| [39581965232](https://github.com/cepeter-job/spt-downloader/actions/runs/39581965232) | 12339310560 | 28490553 | `05392ada8446bd2e707453e605511b8684c75009cdc6f34cbaa87dcb0d630f6f` |
| [39583259921](https://github.com/cepeter-job/spt-downloader/actions/runs/39583259921) | 12338294820 | 28490136 | `4bbb497dec9a333843d56f41733cfa5dde541bbd89029b945f9945db89c83394` |
| [39583430139](https://github.com/cepeter-job/spt-downloader/actions/runs/39583430139) | 12338188828 | 28487496 | `206a58e7ecf8a899a2b04d9524c0f00e1150692c4a9b3585855b492b2164ef6b` |
| [39584725889](https://github.com/cepeter-job/spt-downloader/actions/runs/39584725889) | 12340841085 | 28490547 | `ae55f43265a44dbecf4877bc61e41529ed636785b7feac92898a0848e288715d` |
| [39584008276](https://github.com/cepeter-job/spt-downloader/actions/runs/39584008276) | 12338109272 | 28490872 | `3dea4bb9b8f67e3c6cd3c3c982988fbc93e8365bd36beb390558dfc1267dfb82` |
| [39584857915](https://github.com/cepeter-job/spt-downloader/actions/runs/39584857915) | 12339801644 | 28490067 | `8854a8d6afe0556faf895adb1fbc24ba6008ff9a9afff59d352ec95e1b7ba59d` |
| [39585431388](https://github.com/cepeter-job/spt-downloader/actions/runs/39585431388) | 12339961032 | 28489868 | `b1fc1d0479d56f8a36846bba6e1faa437ad4fd90bced21766bb816fd6cfef39a` |

## Bukti pendukung dan batas klaim

Benchmark baseline [39579737580](https://github.com/cepeter-job/spt-downloader/actions/runs/39579737580) pada commit aplikasi `a7d742e` lulus:
3.409 tes serial dalam 1.075,820 detik versus critical path shard 585,155 detik,
atau 45,61% pengurangan fase pytest. Run PR pilot [39581470149](https://github.com/cepeter-job/spt-downloader/actions/runs/39581470149) dan
benchmark [39581470159](https://github.com/cepeter-job/spt-downloader/actions/runs/39581470159) juga lulus pada head pilot, menggunakan merge
commit `8f1a9ae5196793077f6539e2aea366f0ac945015`. Benchmark pilot mencatat
1.110,493 versus 552,965 detik (50,20% fase pytest). Ketiganya **tidak dimasukkan**
ke lima pasangan pipeline lengkap di atas.

Unduhan lokal pertama artifact distribusi pendukung `12339061685` terpotong.
Unduhan ulang dengan ID yang sama cocok dengan ukuran GitHub 28.489.850 byte dan
SHA-256 `6de64595b2bb6217337f2cdc9dfe595a4f14a498ca7d5965ed29defa86396aa3`.
Pemeriksaan runner sejak awal lulus; ini kegagalan transfer bukti lokal yang
diselesaikan, bukan kegagalan build atau perubahan payload.

Run produksi historis [39570265038](https://github.com/cepeter-job/spt-downloader/actions/runs/39570265038) mencatat 21 menit 1 detik, termasuk
pekerjaan khusus push `main`; angka itu tidak dipakai sebagai denominator
perbandingan dispatch. Attestation terpercaya dan cleanup branch hanya berjalan
pada event yang memenuhi aturan semula. Run dispatch/PR ini tidak membuktikan
eksekusi attestation push `main`; run setelah merge harus memverifikasinya.

Lima pasangan memberi bukti operasional untuk adopsi, bukan jaminan durasi atau
bukti bahwa flake mustahil. Windows runner berbagi infrastruktur GitHub, kondisi
cache nyata dan keseimbangan shard dapat berubah saat tes bertambah. Tidak ada
pytest, import produk, browser fixture, build, self-test, atau EXE yang dijalankan
lokal; pemeriksaan lokal terbatas pada source/AST dan metadata/hash/isi artifact.

## Operasi berikutnya

Validasi commit adopsi melalui seluruh check PR, termasuk dua shard produksi,
portable, audit, source/frozen package dan exact-ID readback, sebelum menandai PR
siap. Setelah merge, periksa run push `main` dan attestation-nya. Untuk diagnosis,
buat dispatch serial pada commit yang sama; untuk rollback default, revert delta
adopsi melalui PR dan jalankan kembali seluruh gate. Jangan melewati shard gagal,
memakai inventory attempt lama, atau mengurangi suite untuk mendapatkan GREEN.

Prioritas 4 dimulai dengan pengukuran startup browser per fixture, lalu uji reuse
proses yang sesuai dengan context baru untuk tiap tes. Setelah itu ganti sleep
yang tidak menguji waktu dengan sinyal readiness eksplisit. Penghematan startup
belum diukur; durasi total testcase bukan waktu startup browser.
