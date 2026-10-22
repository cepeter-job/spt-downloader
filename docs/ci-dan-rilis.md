# CI, penggunaan resource, dan verifikasi rilis

[Kembali ke dokumentasi](README.md)

Sumber konfigurasi adalah [windows-build.yml](../.github/workflows/windows-build.yml). CI memeriksa kode sintetis dan artifact; tidak memakai akun intranet, browser pribadi, atau data wajib pajak.

## Pemicu dan check gabungan

Push ke `main`, PR menuju `main`, dan `workflow_dispatch` menjalankan pemeriksaan yang relevan. Jadwal mingguan Senin pukul **03.17 UTC** memeriksa dependensi pada `main` tanpa mengulang tes GUI atau membuat executable. Branch desktop lama tidak lagi menjadi target terpisah setelah konsolidasi.

Nama check gabungan tetap **Windows tests and dependency audit** agar aturan branch yang sudah mengacu pada nama tersebut tidak perlu mengejar nama matrix. Check ini menggabungkan hasil yang diwajibkan untuk event dan perubahan tersebut. Gagal, dibatalkan, atau terlewatnya job yang seharusnya berjalan tidak boleh dinyatakan berhasil oleh agregator.

Setiap push `main` memakai grup concurrency dengan run ID sendiri. Push dokumentasi
yang tiba sesudah push kode tidak membatalkan build kode yang sedang berjalan atau
menggantikan run kode yang masih mengantre. Pembaruan pada PR yang sama tetap
membatalkan validasi PR yang sudah usang. Dispatch dan jadwal juga punya identitas
run tersendiri; mematikan cancellation saja tidak cukup untuk melindungi antrean
`main` karena satu grup concurrency hanya mempunyai satu slot pending.

Pemilihan perubahan memakai [scripts/ci_route.py](../scripts/ci_route.py). Hanya perubahan dokumentasi yang cocok dengan allowlist aman yang dapat melewati pekerjaan runtime. Perubahan tak dikenal, basis diff yang tidak dapat ditetapkan, atau ketidakpastian klasifikasi menjalankan pemeriksaan lengkap. Perubahan script, lock, requirements, workflow, resource, atau aturan pemilih tes tetap memerlukan gate kode.

Pengaturan ruleset/branch protection di GitHub terpisah dari YAML. Maintainer perlu memastikan check gabungan dan PR benar-benar diwajibkan pada `main`. Jangan menyimpulkan perlindungan aktif hanya karena workflow tersedia atau berwarna hijau. Bagian [aturan repo](#aktivasi-aturan-repository) menyimpan verifikasi bertanggal; periksa ulang metadata remote sebelum mengandalkannya untuk perubahan sekarang.

## Menjalankan dan membaca verifikasi

Untuk batas kerja [AGENTS.md](../AGENTS.md#verification), seluruh eksekusi produk,
pytest, Tk/browser, self-test, build dan EXE dilakukan pada GitHub runner. Perintah
`gh` berikut membaca atau memicu pekerjaan remote; lingkungan lokal cukup untuk
menyiapkan source/dokumen dan memeriksa hash/metadata. Referensi langkah di dalam
runner berada pada [panduan pengembangan](pengembangan.md#referensi-perintah-pada-runner).

### PR menuju main

Setelah branch perubahan dipush dan PR menuju `main` dibuat, peristiwa PR memicu
workflow. Push branch fitur tanpa PR tidak memicu workflow build karena trigger
`push` hanya mencakup `main`. Gunakan GitHub CLI yang sudah memiliki akses repository.
Contoh PowerShell berikut memakai nomor PR yang Anda pilih:

```powershell
$SptRepo = "cepeter-job/spt-downloader"
$SptPr = "GANTI_DENGAN_NOMOR_PR"
$SptPrInfo = gh pr view $SptPr --repo $SptRepo --json number,headRefName,headRefOid,baseRefName,url | ConvertFrom-Json
$SptPrInfo
gh pr checks $SptPr --repo $SptRepo --required
gh pr checks $SptPr --repo $SptRepo --required --watch --fail-fast
gh run list --repo $SptRepo --workflow windows-build.yml --event pull_request --branch $SptPrInfo.headRefName --limit 10 --json databaseId,event,headBranch,headSha,attempt,status,conclusion,url
```

`--required` mengikuti aturan repository saat diperiksa. Pastikan check gabungan
**Windows tests and dependency audit** serta check wajib lain seperti **CodeQL**
tercakup. Status pending belum berarti lulus; daftar check kosong juga bukan bukti
verifikasi. Opsi dan status dijelaskan pada manual resmi
[gh pr checks](https://cli.github.com/manual/gh_pr_checks) dan
[gh run list](https://cli.github.com/manual/gh_run_list).

Pilih `databaseId` dari run yang event, branch, revisi dan waktunya sesuai. Simpan
attempt yang sedang diperiksa; jangan memilih run hanya karena berada di urutan
terbaru. Ganti kedua placeholder berikut dengan identitas dari hasil pembacaan:

```powershell
$SptRunId = "GANTI_DENGAN_RUN_ID"
$SptAttempt = "GANTI_DENGAN_ATTEMPT"
gh run watch $SptRunId --repo $SptRepo --exit-status --interval 20
gh run view $SptRunId --repo $SptRepo --attempt $SptAttempt --json databaseId,event,headBranch,headSha,attempt,status,conclusion,jobs,url
```

`gh run watch` memantau run yang dipilih sampai selesai. Jika akses `watch` tidak
didukung oleh kredensial yang tersedia, gunakan `gh run view` untuk membaca
statusnya. Pembacaan dengan `--attempt` mengikat laporan ke percobaan yang dimaksud;
catat lagi identitasnya setelah selesai. Lihat
[gh run watch](https://cli.github.com/manual/gh_run_watch) dan
[gh run view](https://cli.github.com/manual/gh_run_view).

**Head PR dan commit yang diuji perlu dicatat terpisah.** Pada event `pull_request`,
checkout bawaan memakai merge ref; `github.sha` menunjuk commit gabungan itu,
sedangkan `headRefOid` menunjuk commit branch perubahan. Inventory dan nama artifact
workflow ini memakai `github.sha`. Cocokkan commit checkout dari log/summary serta
inventory, bukan menganggapnya selalu sama dengan head PR. Perilaku event ini
dijelaskan pada [dokumentasi GitHub](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request).

### Dispatch tambahan bila diperlukan

PR biasa memakai pemeriksaan otomatis di atas. Untuk pemeriksaan penuh tambahan,
gunakan branch remote yang telah dipush dan catat SHA penuh yang diharapkan.
Dispatch selalu memilih mode `full`, termasuk ketika perubahan hanya dokumentasi.
Contoh ini memakai default dua shard dan restore cache:

```powershell
$SptRepo = "cepeter-job/spt-downloader"
$SptBranch = "GANTI_DENGAN_BRANCH_TERPUSH"
$SptCommit = "GANTI_DENGAN_SHA_BRANCH_40_KARAKTER"
gh workflow run windows-build.yml --repo $SptRepo --ref $SptBranch -f windows_mode=two-shards -f cache_mode=restore
gh run list --repo $SptRepo --workflow windows-build.yml --event workflow_dispatch --branch $SptBranch --commit $SptCommit --limit 10 --json databaseId,event,headBranch,headSha,attempt,status,conclusion,url
```

`--ref` memilih branch/tag remote, dan run harus dibaca kembali untuk memastikan
SHA-nya cocok dengan commit yang hendak diverifikasi. Jika branch bergerak sebelum
dispatch, run pada commit lain tidak membuktikan commit yang diharapkan. Pilih run
dari daftar lalu gunakan `watch`/`view` di atas. Sintaks input berasal dari
[gh workflow run](https://cli.github.com/manual/gh_workflow_run); nama dan nilai
input ditetapkan oleh [workflow aktif](../.github/workflows/windows-build.yml).

Gunakan `windows_mode=serial` hanya untuk kontrol atau diagnosis yang memerlukan
suite pada satu runner; `cache_mode=cold` untuk perbandingan cache dingin. Kedua
mode tetap melewati portable, suite Windows lengkap, audit, bootstrap worker,
source/frozen self-test, packaging, inventory dan artifact readback. Dispatch
tidak menerbitkan attestation `main`. Jalur dokumentasi aman pada PR/push cukup
dengan gate yang ditetapkan router; tidak perlu memaksa build hanya karena
dokumentasi berubah. Komentar dalam `.py` tetap termasuk perubahan kode.

## Pembagian pekerjaan

| Kelompok pekerjaan | Lingkungan dan isi | Kebijakan resource |
| --- | --- | --- |
| `route` | Memutuskan dokumentasi aman atau pemeriksaan kode lengkap; memvalidasi workflow. | Pekerjaan kecil, tanpa instalasi stack aplikasi. |
| `portable` | CPython 3.14.8 produksi pada Linux; logika tanpa browser/Tk/native Windows. | Satu proses pytest pada satu runner. |
| `windows` | Suite produksi CPython 3.14.8; Edge fixture, GUI Tk, batas native, dan bootstrap worker nyata. | Dua runner terisolasi, satu proses pytest per shard; dispatch manual juga menyediakan kontrol serial. |
| `dependency-audit` | Environment build pada Python produksi Windows dan tool audit terisolasi. | Satu runner; jadwal mingguan menjalankan audit tanpa build. |
| `package` | Satu executable produksi 3.14.8 setelah tes/audit; self-test source kemudian frozen. | Satu build, artifact diverifikasi ulang. |
| Pemeriksaan artifact | File allowlist, laporan self-test, checksum, dan identitas run/commit/artifact. | Hanya set distribusi yang diunggah dan dibaca kembali. |
| `attest` | Provenance executable dan manifest pada push `main` tepercaya setelah artifact diverifikasi. | Izin OIDC/attestation hanya tersedia di job ini. |
| `validate` | Check **Windows tests and dependency audit** untuk hasil seluruh job yang diwajibkan. | Tetap muncul juga ketika jalur dokumentasi aman dipilih. |
| `cleanup` | Pembersihan branch selesai setelah check gabungan `main` berhasil. | Job tersendiri dengan izin penghapusan dan pemeriksaan SHA. |

CPython 3.14.8 sudah menjadi satu-satunya profil produksi; tidak ada build kandidat maupun pekerjaan matrix 3.11. Kegagalan worker/GUI/packaging pada 3.14 tetap menghalangi penggabungan. Prosedur migrasi/rollback dijelaskan pada [kebijakan Python](python-314.md).

Pemilih [scripts/ci_tests.py](../scripts/ci_tests.py) memilih subset portable untuk feedback awal dan kompatibilitas Linux. Workload Windows menjalankan **seluruh suite**, termasuk tes portable yang memiliki cabang perilaku Windows. Pengulangan ini disengaja agar perilaku seperti junction tidak hilang dari cakupan. Manifest collection harus membuktikan subset portable benar, inventaris Windows lengkap, serta versi Python/commit sesuai. Setiap tes yang dipilih harus mempunyai tepat satu status `passed` untuk setup, call, dan teardown. Skip, xfail/xpass, fase yang hilang, laporan ganda, atau outcome untuk node yang tidak dipilih ditolak sebelum packaging walaupun exit pytest bernilai nol. Inventory hanya menyimpan status; alasan skip dan pesan kegagalan tidak disalin. Tes baru selalu terjangkau suite Windows, lalu dapat dimasukkan ke subset portable setelah ditinjau.

## Batas waktu job Windows

Job `windows` memiliki batas **30 menit** untuk seluruh pekerjaan, termasuk
setup, bagian suite pada shard tersebut, pemeriksaan bootstrap worker, upload bukti dan
cleanup. Batas ini bukan target durasi tes maupun klaim percepatan. Job package
terpisah tetap memiliki batas 20 menit; job lain tidak berubah.

Perubahan ini menanggapi [run 39455415374](https://github.com/cepeter-job/spt-downloader/actions/runs/39455415374)
pada `3c7f119`: seluruh **3.352 tes Windows lulus dalam 1.172,46 detik**, tetapi
job dibatalkan saat batas 20 menit tercapai dan package tidak dijalankan.
JUnit serta inventory yang tersimpan membuktikan hasil tes, bukan keberhasilan
pipeline atau executable untuk run tersebut.

Headroom tetap dibatasi: pembagian dua shard wajib mencakup seluruh inventory;
tidak ada pengurangan tes, `continue-on-error`, perubahan dependensi atau
penghapusan pemeriksaan artifact. Kontrol serial manual memakai batas yang sama.
Jika durasi mendekati batas baru, gunakan pengukuran per tahap dan durasi tes
untuk mencari penyebabnya; jangan menaikkan batas terus-menerus tanpa bukti.

## Benchmark opsional pembagian tes Windows

[windows-shard-benchmark.yml](../.github/workflows/windows-shard-benchmark.yml)
berjalan hanya melalui `workflow_dispatch`: buka **Actions → Benchmark Windows
test sharding → Run workflow**. PR, push, dan jadwal tidak menjalankan benchmark.
Gunakan saat menyelidiki perubahan Python/runner, cache, atau pembagian shard,
serta ketika membutuhkan perbandingan performa yang terukur. Validasi PR rutin
tetap memakai workflow build produksi. Benchmark
tidak mengganti job `windows`, check gabungan, packaging
atau artifact readback. Profil Python dibaca dari sumber yang sama dengan CI utama.

Satu runner mengerjakan suite serial, dua runner lain masing-masing satu shard,
tetap satu proses pytest per runner. Partisi hash node ID harus deterministik,
disjoint dan bergabung tepat menjadi koleksi serial; identitas commit, versi,
run/attempt, jumlah, hasil dan payload inventory wajib cocok. Batas job benchmark
30 menit mengikuti anggaran produksi agar serial tidak dibatalkan oleh batas
20 menit yang lebih pendek. Tidak ada `xdist` atau akun nyata.

Laporan membandingkan pytest, setup + pytest, serta jumlah runner-seconds shard.
Itu bukan waktu CI total. Dispatch `cache_mode=restore` tidak menjamin hit; mode
`cold` melewati restore tanpa menghapus cache repo, dan benchmark tidak menulis cache.

Keputusan adopsi memakai sedikitnya lima perbandingan pipeline lengkap pada commit
yang sama, kondisi cache terpisah, serta antre/setup/build/readback dari metadata
Actions. Tinjauan juga mencakup flake, kelengkapan inventory dan biaya runner.
Sasaran median CI kandidat turun setidaknya 20% adalah target evaluasi, bukan gate
benchmark. [Evaluasi 16 Oktober](audits/2026-10-16-optimization-completion.md)
adalah keputusan historis untuk tetap serial berdasarkan bukti saat itu;
[evaluasi 21 Oktober](audits/2026-10-21-windows-shard-evaluation.md) menyimpan bukti
pipeline lengkap dan keputusan terbaru.

### Perbandingan pipeline lengkap

Dispatch [workflow build](../.github/workflows/windows-build.yml) menerima
`windows_mode=serial` atau `two-shards` dan `cache_mode=restore` atau `cold`.
Push, PR, dan default dispatch memakai dua shard. Kedua pilihan manual
menjalankan portable, audit, managed worker, source/frozen GUI, build, upload,
artifact readback dan check gabungan yang sama. Run manual memiliki grup concurrency
tersendiri agar pasangan pada satu commit dapat dibandingkan tanpa saling membatalkan.
Pembatalan validasi PR yang sudah usang tetap berlaku; setiap push `main` dipertahankan.

Dalam mode dua shard, job package membaca kedua manifest asli dari direktori
terpisah. Verifier menolak shard hilang/ganda, partisi yang salah, hasil pytest
gagal, perbedaan commit/Python/run/attempt, atau gabungan identitas tes yang tidak
sama dengan collector portable. Bootstrap worker berjalan pada serial atau shard
0. Setiap shard menyimpan inventory, JUnit dan hasil pengukurannya sendiri.

`cache_mode=cold` melewati restore pada pekerjaan pipeline tanpa menghapus cache
repository. Run manual tidak menulis cache; pada push `main`, hanya serial atau
shard 0 yang dapat menulis cache integration bersama. Catat hit/miss aktual untuk
kedua cache, bukan hanya pilihan input. Attestation tetap khusus push `main` dan
tidak menjadi bagian hasil waktu dispatch.

Hasil dan keputusan adopsi dicatat pada
[evaluasi 21 Oktober](audits/2026-10-21-windows-shard-evaluation.md).

Untuk membandingkan atau mendiagnosis masalah, buat dispatch baru pada commit yang
sama dengan `windows_mode=serial`; ini tidak mengubah default PR/push. Jika perlu
mengembalikan default produksi, revert perubahan adopsi lewat PR dan jalankan
kembali seluruh gate. Jangan melewati shard yang gagal atau memakai artifact lama
untuk melanjutkan packaging.

Nama artifact menyertakan attempt agar rerun lengkap tidak menimpa bukti sebelumnya.
Jika verifikasi inventory perlu diulang, jalankan ulang seluruh workflow atau
buat dispatch baru. Rerun sebagian yang mencampur manifest dari attempt lama dan
baru akan ditolak oleh pemeriksaan provenance.

## Lint Python dan coverage subset portable

Job `portable` menjalankan Ruff yang dipin dalam `requirements-test.txt` dan lock
test/build setelah pemeriksaan kesegaran lock. Aturan dalam `ruff.toml` hanya
menolak nama, ekspor, atau variabel lokal yang tidak terdefinisi (`F821`, `F822`,
`F823`). Pelanggaran membuat job dan gate gabungan gagal. Gate ini tidak
memformat ulang kode atau memaksakan anotasi tipe dan batas kompleksitas.

Pemanggilan pytest portable dibungkus `coverage run` dengan `.coveragerc`; pilihan
tes, inventory, JUnit, serta propagasi kegagalan pytest tetap sama. Coverage
mengukur baris dan cabang kode aplikasi dalam proses tes Linux beserta thread yang
diukur. Ia tidak otomatis mencakup proses worker terpisah, browser, atau seluruh
perilaku native Windows. Angka yang rendah pada laporan ini bukan ukuran coverage
suite Windows lengkap. Jumlah tes yang benar-benar dijalankan tetap dibuktikan
oleh inventory dan outcome per fase, bukan oleh persentase coverage.

Artifact `test-results-portable-python<versi>-<commit>-attempt<nomor>` juga menyimpan
`coverage-portable.xml` dan `coverage-portable.json`. Pembuatan dan upload laporan
tetap dicoba jika pytest gagal. Kedua laporan bersifat informasional tanpa ambang
persentase; kegagalan menghasilkan laporan tetap terlihat sebagai kegagalan job.
Data pengukuran sementara berada di `RUNNER_TEMP`, sedangkan kode tes dan virtual
environment dikecualikan dari laporan. Tidak ada telemetry atau upload ke layanan
coverage lain.

Ruff dan coverage hanya dependensi pengembangan yang terkunci dan ikut audit
dependensi; keduanya bukan dependensi runtime worker. Perubahan ini tidak
menjalankan benchmark, mengubah pemilihan suite Windows, atau mengganti fixture workbook
yang menjadi referensi independen.

## Bukti waktu dan kegagalan tes

Job portable, Windows produksi, serta setiap varian benchmark menyimpan JUnit
`test-results.xml` dan ringkasan `test-measurements.json` dalam artifact diagnostik
terpisah. Inventory tetap memakai nama dan format pokok yang dikonsumsi gate
packaging. Upload inventory dan diagnostik tetap dicoba ketika langkah pytest
gagal, termasuk kegagalan assertion, fixture, atau collection; kegagalan tersebut
tetap membuat job gagal. Artifact distribusi memakai tujuh berkas eksplisit di bawah.

Inventory sekarang mencatat exit status dan durasi setiap sesi pytest, bukan
hanya benchmark. Identitas commit, run ID, attempt, dan hit/miss kedua cache ikut
tersimpan. Setup diukur dengan timestamp Unix wall-clock sejak setelah checkout hingga
awal sesi pytest. Python bawaan runner dan Python managed dapat memakai clock
monotonik Windows yang berbeda; durasi setup tidak boleh mengurangkan kedua
clock tersebut. Durasi sesi pytest tetap memakai satu clock monotonik. Perubahan
jam sistem dapat memengaruhi setup; durasi negatif/tidak valid ditolak. Pengukuran ini tidak mencakup antre runner, checkout, upload, worker
bootstrap setelah tes, packaging, atau provenance. Tidak ada angka perkiraan yang
ditambahkan untuk waktu yang tidak terukur. Bukti yang hilang ditampilkan sebagai
`unavailable`, bukan dianggap sukses atau berdurasi nol.

JUnit berasal dari fixture sintetis di runner GitHub; logging stdout/stderr ke
JUnit dimatikan. Ringkasan hanya memuat identitas tes, durasi, jumlah outcome dan
metadata run, tanpa menyalin pesan assertion atau captured log. Traceback sintetis
masih dapat berada dalam JUnit. Tidak ada folder workspace, profil, cookie, output
pajak, atau log aplikasi pribadi yang diunggah. Penghentian keras runner dapat
mencegah penulisan atau upload; tidak ada jaminan laporan untuk proses yang dibunuh.

## Cache dan CPU

Cache menyimpan unduhan/paket `uv` serta interpreter managed. Kunci memisahkan OS, arsitektur, versi Python, peran workload, serta isi lock dan requirements. Cache tidak menjadi bukti bahwa environment sudah terverifikasi: instalasi tetap memakai lock dan hash, dan runtime memeriksa kesiapan aktual.

[uv 0.13.0 mengubah format sebagian entri cache](https://github.com/astral-sh/uv/releases/tag/0.13.0). Setelah pembaruan, unduhan pertama dapat mengisi ulang entri yang tidak dapat dipakai kembali; versi uv berbeda tetap dapat berbagi direktori cache. Cache awal yang dingin bukan kegagalan verifikasi dan tidak memerlukan pelonggaran hash atau penghapusan cache pengguna.

PR dapat memulihkan cache, tetapi penulisan cache dibatasi pada push tepercaya ke `main`. `.venv`, profil/cookie browser, data pajak, checkpoint, output tes, Downloads, dan executable browser tidak disimpan dalam cache. Jangan menambahkan seluruh workspace ke cache demi mempercepat setup.

Pada Windows, [scripts/ci_python_cache.py](../scripts/ci_python_cache.py) memeriksa alias minor Python setelah restore cache dan sebelum `uv python install`. Penanganan ini berasal dari kegagalan yang diamati pada uv 0.12.22: alias seperti `cpython-3.14-windows-x86_64-none` dipulihkan sebagai file atau symlink, sementara uv mengharapkan direktori/junction dan gagal dengan `os error 267`. Helper tetap menjadi bagian jalur bootstrap pada [pin uv produksi](python-314.md#versi-yang-didukung); nomor versi lama pada catatan insiden bukan pin aktif. Helper stdlib dijalankan terisolasi sebelum `.venv` tersedia. Root harus tepat `RUNNER_TEMP/uv-python-dir` tanpa pengalihan; hanya alias minor untuk versi yang dipin boleh dilepas sebagai entry file/symlink. Direktori interpreter patch, direktori nyata, target link, dan cache paket tidak dihapus. uv tetap memasang/memilih interpreter exact dan instalasi paket tetap memverifikasi hash.

Tes regresi membuktikan file/tautan alias dapat dibersihkan tanpa menyentuh interpreter atau target di luar cache. Job Windows produksi 3.14.8 juga menguji instalasi baru, arsip/pemulihan dengan GNU tar milik Git for Windows, lalu penggunaan ulang interpreter yang dipulihkan secara offline. Job audit dan build memakai restore serta helper yang sama; pengujian arsip besar tidak diulang pada semua job. Diagnostik hanya mencatat nama alias dan tipe/atribut entry, bukan isi data pengguna atau target tautan.

Beberapa keputusan menjaga beban tetap terukur:

- Perubahan dokumentasi yang terbukti aman tidak menjalankan semua interpreter, browser, dan build.
- Subset Linux memberi feedback portable tanpa browser/GUI; suite Windows penuh mempertahankan seluruh perilaku target.
- Satu proses pytest per runner menghindari perkalian proses browser dan perebutan resource Tk/Windows Job Object.
- Fase tes memakai satu runner portable, dua runner shard Windows (satu untuk dispatch serial), dan satu audit; satu runner build dimulai setelah gate tersebut. Run PR usang dibatalkan; push `main` memakai grup per run agar bukti build kode tidak hilang.
- Audit mingguan tidak membuat ulang executable dan tidak menjalankan suite browser.
- Artifact executable yang sudah terkompresi diunggah tanpa kompresi tambahan.
- Durasi job dan keadaan cache perlu dibandingkan pada scope yang setara sebelum menyatakan penghematan numerik.

Pengurangan kerja tersebut bukan jaminan persentase percepatan. Catat waktu total, CPU bila diukur, jumlah job, hit/miss cache, dan ukuran artifact saat menilai optimasi. Jangan mempercepat CI dengan menghapus pemeriksaan asal data atau kelengkapan hasil.

## Dependensi dan izin workflow

Instalasi runtime/test/build memakai `uv pip sync --require-hashes --only-binary :all:` terhadap lock sesuai peran. Audit memeriksa environment dependensi yang dipakai serta tool auditnya dengan mode strict; layanan advisory yang tidak tersedia tidak boleh dianggap hasil aman. Toolchain audit dipisahkan agar dependency tool audit tidak diam-diam menjadi dependency aplikasi. Lock saat ini tidak memakai marker Python yang membedakan paket menurut versi interpreter. Satu environment build Windows 3.14.8 mengaudit paket produksi; bila kelak diperkenalkan profil/marker lain, cakupan audit harus ditinjau ulang.

Actions dipin dengan commit SHA penuh. Checkout tidak menyimpan kredensial Git. Job tes/build memakai token baca. Job `attest` pada push `main` mendapat `id-token: write` dan `attestations: write`; job `cleanup` sesudah gate mendapat `contents: write` serta akses baca PR. Secret penandatanganan penerbit tidak tersedia pada run PR.

Bootstrap `setup-uv` juga memeriksa SHA-256 arsip upstream **uv 0.13.4** yang
ditinjau, selain pin action dan versi. Nilai berasal dari
[release upstream](https://github.com/astral-sh/uv/releases/tag/0.13.4):

| Runner | Arsip | SHA-256 |
| --- | --- | --- |
| Ubuntu x64 | `uv-x86_64-unknown-linux-gnu.tar.gz` | `2b428396f12572d4429cf210ca234dd599a33b3af0958a4d5ed569d63e3f344f` |
| Windows x64 | `uv-x86_64-pc-windows-msvc.zip` | `ccec7508a07d9933d7cb1261880633efcf1f30d6e6eddab21823f1dae6f23225` |

Pembaruan uv harus meninjau versi dan kedua digest bersama. Binary uv yang dibundel
tetap berasal dari paket build yang terkunci dengan hash dan diperiksa versinya.
`distribution-sbom.json` menggunakan CycloneDX 1.6: hash executable akhir,
identitas build, hash/ukuran setiap binary native dalam CArchive PyInstaller,
versi CPython/Tcl/Tk/uv yang diamati, versi PE bila tersedia, serta pin dan digest
lock worker yang diunduh terpisah. Versi native yang tidak tersedia tidak ditebak.
Inventaris ini **bukan audit kerentanan native**; pip-audit memeriksa paket Python,
dan Edge merupakan prasyarat eksternal yang dikelola pengguna. Hash executable
mencakup bootloader PyInstaller; tidak ada klaim penilaian kerentanan bootloader
tersendiri.

Tidak ada capture, profil, log pribadi, atau hasil wajib pajak dalam artifact. Laporan self-test hanya memuat fakta non-rahasia tentang interpreter, resource, GUI, dan apakah akses kredensial/live scrape dilakukan.

## Memverifikasi artifact

Nama artifact menyertakan commit penuh dan versi interpreter:

```text
SPTDownloader-Windows-x64-<commit>-python<versi>-attempt<nomor>
```

Produksi menggunakan `python3.14.8` saja. Artifact 3.11.17 dari run terdahulu tetap dapat disimpan terpisah sebagai opsi rollback yang diverifikasi, bukan artifact produksi baru. Workflow promosi meminta `source_python_version` secara eksplisit sesuai build/receipt asal; versi tersebut tidak diganti otomatis dengan pin produksi saat ini. Promosi terkelola tetap memerlukan format tujuh berkas dan seluruh provenance yang dijelaskan dalam [panduan promosi dan rollback](promosi-dan-rollback.md).

1. Buka run workflow yang dimaksud. Cocokkan repository, event, branch, commit penuh, dan kesimpulan seluruh gate. Untuk rilis produksi gunakan commit `main` yang telah disetujui.
2. Catat **run ID, attempt, head PR/branch, commit checkout yang diuji, artifact ID, nama artifact, dan profil Python**. Pada PR, commit checkout dapat berupa merge commit seperti dijelaskan di [alur verifikasi](#menjalankan-dan-membaca-verifikasi). Unduh artifact berdasarkan ID/run tersebut; jangan memilih hanya berdasarkan nama atau waktu terbaru.
3. Pastikan set berkas hanya `SPTDownloader.exe`, `LICENSE.txt`, `README.txt`, `build-selftest.json`, `build-info.json`, `distribution-sbom.json`, dan `SHA256SUMS.txt`. Folder internal build, source capture, profil, dan log pribadi tidak termasuk distribusi.
4. Hitung SHA-256 tiap berkas yang disebut dalam manifest dan cocokkan seluruh nilainya. Perbedaan apa pun berarti artifact belum layak digunakan.
5. Baca `build-selftest.json`: `ok` dan `frozen` harus benar, bitness 64, profil/interpreter sesuai build, resource lengkap, serta `credentials_accessed` dan `live_scrape` salah. `build-info.json` harus mencatat schema 1, commit penuh, run ID dan attempt yang sama; SBOM harus mengikat identitas tersebut dan hash executable. Laporan source self-test terpisah dari laporan frozen yang didistribusikan.
6. Pembukaan GUI dan penerimaan pada mesin Windows target mengikuti scope operator yang berizin. Untuk pekerjaan yang dibatasi AGENTS, eksekusi EXE tetap pada runner. Bedakan hasil self-test sintetis dari [penerimaan Coretax/Excel aktual](penerimaan-manual.md); tandai penerimaan yang belum dilakukan secara eksplisit.

Contoh pemeriksaan manual di PowerShell dari direktori ekstraksi:

```powershell
Get-Content -LiteralPath .\SHA256SUMS.txt
Get-FileHash -Algorithm SHA256 -LiteralPath .\SPTDownloader.exe, .\LICENSE.txt, .\README.txt, .\build-selftest.json, .\build-info.json, .\distribution-sbom.json
Get-Content -LiteralPath .\build-selftest.json | ConvertFrom-Json
Get-AuthenticodeSignature -LiteralPath .\SPTDownloader.exe | Select-Object Status, SignerCertificate
```

Cocokkan hash berdasarkan nama file, bukan urutan tampilan. Perintah PowerShell
di atas membaca berkas/metadata tanpa menjalankan EXE. Verifier repository berikut
merupakan **referensi langkah runner** dari checkout commit yang sesuai: modulnya
mengimpor runtime produk, sehingga tetap tunduk pada batas eksekusi AGENTS.

```powershell
.venv/Scripts/python.exe -m scripts.ci_artifact verify "$env:RUNNER_TEMP/artifact-readback" --python-version 3.14.8
```

Setiap job package CI mengunduh ulang hasil upload menggunakan **artifact ID yang persis**, memeriksa tujuh berkas, hash, identitas build, SBOM dan laporan frozen. Executable hasil readback kemudian menjalankan bootstrap worker dingin, reuse dan cancellation sintetis dengan uv bundel, tanpa uv dari PATH. Laporan `packaged-bootstrap.json` mengikat hash EXE ke artifact ID/run/attempt/commit dan disimpan terpisah. Kegagalan smoke tersebut menggagalkan package; artifact yang sudah terunggah belum otomatis layak rilis. Manifest koleksi tes, laporan audit dan bootstrap merupakan artifact diagnostik terpisah dari tujuh berkas distribusi.

Checksum dalam arsip yang sama tidak sendirian membuktikan identitas penerbit. Pernyataan berhasil di PR/release perlu menyebut run, commit, dan artifact yang benar-benar dibaca kembali.

## SHA-256, provenance, dan Authenticode

| Mekanisme | Fungsi | Batas |
| --- | --- | --- |
| `SHA256SUMS.txt` | Membuktikan byte cocok dengan manifest yang dibandingkan. | Manifest dan executable dapat diganti bersama jika sumber unduh tidak tepercaya. |
| Provenance/attestation build | Mengaitkan digest artifact dengan workflow, repository, dan commit pembuatnya bila diverifikasi. | Tidak sama dengan tanda tangan publisher Windows dan tidak menyatakan aplikasi telah menjalani acceptance nyata. |
| Authenticode | Memungkinkan verifikasi identitas penerbit dan integritas executable melalui sertifikat penandatanganan kode. | Memerlukan identitas, sertifikat, private key, kebijakan timestamp, serta proses signing yang dikelola maintainer. |

Executable saat ini belum ditandatangani dengan sertifikat penerbit tepercaya. Jangan menyebut manifest atau attestation sebagai Authenticode, memakai sertifikat buatan sebagai pengganti identitas tepercaya, atau menyarankan menonaktifkan Defender/TLS agar aplikasi berjalan.

Pada push kode ke `main`, job `attest` membaca ulang artifact run yang sama,
memeriksa isinya tanpa mengeksekusinya, lalu membuat attestation untuk executable,
manifest, build-info dan SBOM. Attestation kelima mengikat digest ZIP asli dari
output `upload-artifact`, agar rollback dapat membuktikan byte arsip asli setelah
artifact Actions kedaluwarsa. PR/manual dispatch build tidak menerbitkan
attestation `main`. Contoh verifikasi executable dan manifest dengan commit yang
telah dicocokkan pada run:

```powershell
$SptVerifiedCommit = "GANTI_DENGAN_SHA_MAIN_40_KARAKTER"
gh attestation verify .\SPTDownloader.exe --repo cepeter-job/spt-downloader --signer-workflow cepeter-job/spt-downloader/.github/workflows/windows-build.yml --source-ref refs/heads/main --source-digest $SptVerifiedCommit --signer-digest $SptVerifiedCommit --deny-self-hosted-runners
gh attestation verify .\SHA256SUMS.txt --repo cepeter-job/spt-downloader --signer-workflow cepeter-job/spt-downloader/.github/workflows/windows-build.yml --source-ref refs/heads/main --source-digest $SptVerifiedCommit --signer-digest $SptVerifiedCommit --deny-self-hosted-runners
```

Perintah mengikat identitas repo/workflow, ref, commit sumber, dan digest artifact; lihat [manual resmi GitHub CLI](https://cli.github.com/manual/gh_attestation_verify). Laporan sukses run yang sebenarnya tetap diperlukan untuk menyatakan attestation tersedia dan lolos verifikasi.

[Promosi dan rollback](promosi-dan-rollback.md) menggunakan dispatch terpisah yang
secara default hanya memverifikasi kandidat. ZIP asli dan kelima bundle provenance
dipertahankan sebagai aset release setelah publikasi eksplisit. Penyimpanan
artifact Actions selama 14 hari tetap untuk bukti CI sementara; itu bukan kanal
distribusi atau penyimpanan rollback jangka panjang.

Sebelum signing produksi diaktifkan, maintainer perlu menetapkan pemilik sertifikat, penyimpanan key, akses job tepercaya, layanan timestamp, dan verifikasi signature setelah signing. Urutannya harus menghasilkan checksum/provenance untuk **byte akhir setelah signing**. Self-test perlu tetap memeriksa executable yang benar-benar didistribusikan. Pengadaan identitas signing dan kebijakan distribusi adalah prasyarat di luar perubahan kode biasa.

## Aktivasi aturan repository

Template `.github/rulesets/main.json` disiapkan sebagai konfigurasi yang dapat ditinjau, bukan bukti bahwa aturan remote sudah aktif. Targetnya `main`, PR wajib, check gabungan CI dan CodeQL wajib, serta larangan force-push/penghapusan main. Jumlah approval manusia wajib adalah **0** untuk workflow maintainer tunggal; PR dan pemeriksaan tetap diwajibkan.

Admin repository yang terautentikasi dapat membuka **Settings → Rulesets → New ruleset → Import a ruleset**, memilih JSON, meninjau target/check/bypass, lalu membuat dan mengaktifkan aturan. Cocokkan nama check persis dengan check run yang terdaftar sebelum aktivasi. Periksa status enforcement dan aturan efektif setelah tersimpan. Langkah resmi tersedia pada [panduan impor ruleset GitHub](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/managing-rulesets-for-a-repository#importing-a-ruleset).

Pada **12 Oktober 2026**, [ruleset main ID 24914050](https://github.com/cepeter-job/spt-downloader/rules/24914050) telah dibaca kembali melalui API: enforcement `active`, target `refs/heads/main`, tanpa bypass, serta larangan penghapusan dan force-push. PR wajib dengan 0 approval manusia; `Windows tests and dependency audit` dari GitHub Actions dan `CodeQL` dari GitHub Advanced Security wajib lulus. Kebijakan strict mengharuskan branch PR mengikuti main terbaru. Metadata branch juga menyatakan `protected: true`. Ini catatan verifikasi pada tanggal tersebut, bukan jaminan konfigurasi tidak akan berubah.

## Pembersihan branch selesai

Job `cleanup` berjalan hanya pada push `main` setelah check gabungan sukses. [scripts/cleanup_branches.py](../scripts/cleanup_branches.py) secara bawaan hanya membuat pratinjau. Untuk inspeksi manual gunakan SHA main yang telah diuji:

```powershell
.venv/Scripts/python.exe scripts/cleanup_branches.py --repository cepeter-job/spt-downloader --base main --expected-base SHA_MAIN_YANG_TELAH_DIUJI
```

Kandidat harus berasal dari PR tertutup di repo yang sama, bukan branch default/protected atau head maupun base PR terbuka, dan SHA branch saat ini harus sama dengan head PR. Perlindungan base juga berlaku untuk PR dari fork. Riwayat harus membuktikan head tersebut ancestor dari main yang diuji. Branch hasil squash/rebase yang belum memiliki bukti ancestry dipertahankan. Main yang berubah membuat cleanup berhenti.

Jika API memberikan SHA `main` lain yang valid, cleanup berhenti dengan kode keluar
0 dan hasil `status: stopped`, `reason: base_changed`. Hasil tersebut tetap mencatat
penghapusan yang sudah terkonfirmasi sebelum perubahan teramati; tidak ada
penghapusan lanjutan. Push baru dengan demikian tidak mengubah build lama yang
sudah terverifikasi menjadi run gagal hanya karena cleanup tidak lagi sesuai.
SHA yang hilang/tidak valid, kegagalan API/autentikasi dan penolakan deletion lease
tetap menghasilkan kode keluar 1; penghentian aman ini bukan pengabaian error.

Opsi `--apply` mengaktifkan penghapusan dan memerlukan `GH_TOKEN` dengan `contents: write`. Jangan menulis nilai token ke command, file, atau log. Script mengecek kembali metadata dan memakai Git `--force-with-lease=<ref>:<sha>` pada penghapusan, sehingga push baru pada branch yang sama ditolak oleh server alih-alih ikut terhapus. Tidak ada penghapusan branch berdasarkan umur atau status PR tertutup saja.

## Menutup tindak lanjut audit

Tindak lanjut audit harus mengacu ke commit, run, artifact dan scope pemeriksaan
baru. [Indeks catatan historis](README.md#catatan-teknis-dan-bukti-historis) menyimpan
asal keputusan; hasil lama tidak menggantikan verifikasi ulang. Ikuti
[verifikasi artifact](#memverifikasi-artifact) dan pisahkan bukti sintetis, signing
serta penerimaan live.

## Kontrak struktur workflow

`tests/test_workflow_contracts.py` memeriksa struktur YAML melalui parser PyYAML
terkunci di environment test/build, bukan melalui pencarian teks seluruh file.
Runtime aplikasi tidak bergantung pada parser tersebut. Pemeriksaan mengikat
job yang benar, dependency packaging, urutan self-test/checksum/upload/readback,
artifact ID, izin per job, check gabungan yang selalu berjalan, dan setiap upload
diagnostik ketika pytest gagal. Komentar tidak dapat menggantikan perintah build.

Kasus mutasi membuktikan dependency hilang, urutan salah, izin berlebih, matrix
shard yang tidak lengkap, dan upload bukti tanpa failure guard tetap ditolak.
Bentuk flow/block YAML, urutan `needs`, serta pembungkus ekspresi yang ekuivalen
diterima. Key `on` tetap berupa nama event dan duplicate key ditolak. Helper ini
bukan interpreter Bash/PowerShell atau evaluator ekspresi Actions; actionlint dan
hasil runner tetap diperlukan untuk sintaks, eksekusi, dan verifikasi artifact.


## Hasil evaluasi optimasi 16 Oktober 2026

Hasil lengkap dan batas pengukuran tetap berada pada
[laporan optimasi](audits/2026-10-16-optimization-completion.md).
Kebijakan eksperimen yang masih berlaku dijelaskan pada
[benchmark opsional](#benchmark-opsional-pembagian-tes-windows), bukan disalin
menjadi hasil baru setiap kali panduan CI diperbarui.
