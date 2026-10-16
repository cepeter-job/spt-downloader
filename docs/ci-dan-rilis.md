# CI, penggunaan resource, dan verifikasi rilis

[Kembali ke dokumentasi](README.md)

Sumber konfigurasi adalah [windows-build.yml](../.github/workflows/windows-build.yml). CI memeriksa kode sintetis dan artifact; tidak memakai akun intranet, browser pribadi, atau data wajib pajak.

## Pemicu dan check gabungan

Push ke `main`, PR menuju `main`, dan `workflow_dispatch` menjalankan pemeriksaan yang relevan. Jadwal mingguan Senin pukul **03.17 UTC** memeriksa dependensi pada `main` tanpa mengulang tes GUI atau membuat executable. Branch desktop lama tidak lagi menjadi target terpisah setelah konsolidasi.

Nama check gabungan tetap **Windows tests and dependency audit** agar aturan branch yang sudah mengacu pada nama tersebut tidak perlu mengejar nama matrix. Check ini menggabungkan hasil yang diwajibkan untuk event dan perubahan tersebut. Gagal, dibatalkan, atau terlewatnya job yang seharusnya berjalan tidak boleh dinyatakan berhasil oleh agregator.

Pemilihan perubahan memakai [scripts/ci_route.py](../scripts/ci_route.py). Hanya perubahan dokumentasi yang cocok dengan allowlist aman yang dapat melewati pekerjaan runtime. Perubahan tak dikenal, basis diff yang tidak dapat ditetapkan, atau ketidakpastian klasifikasi menjalankan pemeriksaan lengkap. Perubahan script, lock, requirements, workflow, resource, atau aturan pemilih tes tetap memerlukan gate kode.

Pengaturan ruleset/branch protection di GitHub terpisah dari YAML. Maintainer perlu memastikan check gabungan dan PR benar-benar diwajibkan pada `main`. Jangan menyimpulkan perlindungan aktif hanya karena workflow tersedia atau berwarna hijau. [Aturan repo](#aktivasi-aturan-repository) telah dibaca kembali dan diverifikasi aktif; periksa ulang metadata remote bila konfigurasi berubah.

## Pembagian pekerjaan

| Kelompok pekerjaan | Lingkungan dan isi | Kebijakan resource |
| --- | --- | --- |
| `route` | Memutuskan dokumentasi aman atau pemeriksaan kode lengkap; memvalidasi workflow. | Pekerjaan kecil, tanpa instalasi stack aplikasi. |
| `portable` | CPython 3.14.8 produksi pada Linux; logika tanpa browser/Tk/native Windows. | Satu proses pytest pada satu runner. |
| `windows` | Suite produksi CPython 3.14.8; Edge fixture, GUI Tk, batas native, dan bootstrap worker nyata. | Seluruh tes berurutan dalam satu runner. |
| `dependency-audit` | Environment build pada Python produksi Windows dan tool audit terisolasi. | Satu runner; jadwal mingguan menjalankan audit tanpa build. |
| `package` | Satu executable produksi 3.14.8 setelah tes/audit; self-test source kemudian frozen. | Satu build, artifact diverifikasi ulang. |
| Pemeriksaan artifact | File allowlist, laporan self-test, checksum, dan identitas run/commit/artifact. | Hanya set distribusi yang diunggah dan dibaca kembali. |
| `attest` | Provenance executable dan manifest pada push `main` tepercaya setelah artifact diverifikasi. | Izin OIDC/attestation hanya tersedia di job ini. |
| `validate` | Check **Windows tests and dependency audit** untuk hasil seluruh job yang diwajibkan. | Tetap muncul juga ketika jalur dokumentasi aman dipilih. |
| `cleanup` | Pembersihan branch selesai setelah check gabungan `main` berhasil. | Job tersendiri dengan izin penghapusan dan pemeriksaan SHA. |

CPython 3.14.8 sudah menjadi satu-satunya profil produksi; tidak ada build kandidat maupun pekerjaan matrix 3.11. Kegagalan worker/GUI/packaging pada 3.14 tetap menghalangi penggabungan. Prosedur migrasi/rollback dijelaskan pada [kebijakan Python](python-314.md).

Pemilih [scripts/ci_tests.py](../scripts/ci_tests.py) memilih subset portable untuk feedback awal dan kompatibilitas Linux. Workload Windows menjalankan **seluruh suite**, termasuk tes portable yang memiliki cabang perilaku Windows. Pengulangan ini disengaja agar perilaku seperti junction tidak hilang dari cakupan. Manifest collection harus membuktikan subset portable benar, inventaris Windows lengkap, serta versi Python/commit sesuai. Tes baru selalu terjangkau suite Windows, lalu dapat dimasukkan ke subset portable setelah ditinjau.

## Benchmark opsional pembagian tes Windows

Workflow [windows-shard-benchmark.yml](../.github/workflows/windows-shard-benchmark.yml) hanya aktif lewat `workflow_dispatch` atau PR yang mengubah konfigurasi benchmark/CI terkait. Benchmark ini **tidak mengganti** job `windows`, check wajib `Windows tests and dependency audit`, urutan packaging, maupun verifikasi artifact produksi.

Benchmark menjalankan tiga environment Windows 2022 dengan CPython 3.14.8 dan lock yang sama: satu suite penuh secara serial, dua job lain masing-masing mengeksekusi satu shard. Semua job memakai **satu proses pytest berurutan per runner**, tanpa `xdist`, data wajib pajak, atau akun Coretax. Hash stabil atas node ID mendistribusikan test secara deterministik; manifest menyimpan semua node ID, subset aktual, SHA, platform, status akhir dan durasi pytest.

Job perbandingan menolak manifest yang tidak cocok atau tidak lengkap: seluruh node pada dua shard harus disjoint, bergabung tepat menjadi suite serial, dan mengikuti pembagian hash yang ditetapkan. Ringkasan menunjukkan waktu pytest serial versus durasi shard terlama. Itu **bukan** percepatan CI total: waktu antre runner, setup, build dan attestation belum dihitung. Jangan mengganti jalur produksi dengan shard tanpa bukti eksekusi Windows nyata, pengukuran berulang dan peninjauan khusus.

## Bukti waktu dan kegagalan tes

Job portable, Windows produksi, serta setiap varian benchmark menyimpan JUnit
`test-results.xml` dan ringkasan `test-measurements.json` dalam artifact diagnostik
terpisah. Inventory tetap memakai nama dan format pokok yang dikonsumsi gate
packaging. Upload inventory dan diagnostik tetap dicoba ketika langkah pytest
gagal, termasuk kegagalan assertion, fixture, atau collection; kegagalan tersebut
tetap membuat job gagal. Artifact distribusi tetap hanya lima berkas yang lama.

Inventory sekarang mencatat exit status dan durasi setiap sesi pytest, bukan
hanya benchmark. Identitas commit, run ID, attempt, dan hit/miss kedua cache ikut
tersimpan. Setup diukur dengan jam monotonik sejak setelah checkout hingga awal
sesi pytest. Pengukuran ini tidak mencakup antre runner, checkout, upload, worker
bootstrap setelah tes, packaging, atau provenance. Tidak ada angka perkiraan yang
ditambahkan untuk waktu yang tidak terukur. Bukti yang hilang ditampilkan sebagai
`unavailable`, bukan dianggap sukses atau berdurasi nol.

JUnit berasal dari fixture sintetis di runner GitHub; logging stdout/stderr ke
JUnit dimatikan. Ringkasan hanya memuat identitas tes, durasi, jumlah outcome dan
metadata run, tanpa menyalin pesan assertion atau captured log. Traceback sintetis
masih dapat berada dalam JUnit. Tidak ada folder workspace, profil, cookie, output
pajak, atau log aplikasi pribadi yang diunggah. Penghentian keras runner dapat
mencegah penulisan atau upload; tidak ada jaminan laporan untuk proses yang dibunuh.

Benchmark membaca pin Python produksi dari sumber yang sama dengan CI utama,
bukan konstanta YAML kedua. Dispatch manual menyediakan `cache_mode=restore`
(default) atau `cold`; restore yang diminta belum tentu menghasilkan cache hit,
sehingga hit/miss aktual tetap harus dibaca. Benchmark tidak menulis cache. Mode
cold hanya melewati restore pada runner baru, tanpa menghapus cache milik repo.

Perbandingan menyajikan durasi pytest, setup + pytest, serta jumlah runner-seconds
kedua shard. Nilai tersebut bukan waktu CI total. Sebelum PR terpisah boleh
mengaktifkan sharding produksi, kumpulkan sedikitnya lima perbandingan pada commit
yang sama, pisahkan kondisi cache, ukur antre/setup/build/readback dari metadata
Actions, pastikan inventory lengkap tanpa duplikasi, dan tinjau flake serta biaya
runner. Sasaran evaluasi adalah penurunan median waktu CI kandidat sekurangnya
20%, bukan syarat lulus benchmark ini. Produksi tetap serial dan seluruh gate tetap.

## Cache dan CPU

Cache menyimpan unduhan/paket `uv` serta interpreter managed. Kunci memisahkan OS, arsitektur, versi Python, peran workload, serta isi lock dan requirements. Cache tidak menjadi bukti bahwa environment sudah terverifikasi: instalasi tetap memakai lock dan hash, dan runtime memeriksa kesiapan aktual.

[uv 0.13.0 mengubah format sebagian entri cache](https://github.com/astral-sh/uv/releases/tag/0.13.0). Setelah pembaruan, unduhan pertama dapat mengisi ulang entri yang tidak dapat dipakai kembali; versi uv berbeda tetap dapat berbagi direktori cache. Cache awal yang dingin bukan kegagalan verifikasi dan tidak memerlukan pelonggaran hash atau penghapusan cache pengguna.

PR dapat memulihkan cache, tetapi penulisan cache dibatasi pada push tepercaya ke `main`. `.venv`, profil/cookie browser, data pajak, checkpoint, output tes, Downloads, dan executable browser tidak disimpan dalam cache. Jangan menambahkan seluruh workspace ke cache demi mempercepat setup.

Pada Windows, [scripts/ci_python_cache.py](../scripts/ci_python_cache.py) memeriksa alias minor Python setelah restore cache dan sebelum `uv python install`. Penanganan ini berasal dari kegagalan yang diamati pada uv 0.12.22: alias seperti `cpython-3.14-windows-x86_64-none` dipulihkan sebagai file atau symlink, sementara uv mengharapkan direktori/junction dan gagal dengan `os error 267`. Helper tetap dipakai saat memverifikasi instalasi dan penggunaan ulang cache dengan uv 0.13.0. Helper stdlib dijalankan terisolasi sebelum `.venv` tersedia. Root harus tepat `RUNNER_TEMP/uv-python-dir` tanpa pengalihan; hanya alias minor untuk versi yang dipin boleh dilepas sebagai entry file/symlink. Direktori interpreter patch, direktori nyata, target link, dan cache paket tidak dihapus. uv tetap memasang/memilih interpreter exact dan instalasi paket tetap memverifikasi hash.

Tes regresi membuktikan file/tautan alias dapat dibersihkan tanpa menyentuh interpreter atau target di luar cache. Job Windows produksi 3.14.8 juga menguji instalasi baru, arsip/pemulihan dengan GNU tar milik Git for Windows, lalu penggunaan ulang interpreter yang dipulihkan secara offline. Job audit dan build memakai restore serta helper yang sama; pengujian arsip besar tidak diulang pada semua job. Diagnostik hanya mencatat nama alias dan tipe/atribut entry, bukan isi data pengguna atau target tautan.

Beberapa keputusan menjaga beban tetap terukur:

- Perubahan dokumentasi yang terbukti aman tidak menjalankan semua interpreter, browser, dan build.
- Subset Linux memberi feedback portable tanpa browser/GUI; suite Windows penuh mempertahankan seluruh perilaku target.
- Satu proses pytest per runner menghindari perkalian proses browser dan perebutan resource Tk/Windows Job Object.
- Fase tes memakai satu runner portable, satu Windows, dan satu audit; satu runner build dimulai setelah gate tersebut. Run usang dibatalkan sesuai `concurrency` workflow.
- Audit mingguan tidak membuat ulang executable dan tidak menjalankan suite browser.
- Artifact executable yang sudah terkompresi diunggah tanpa kompresi tambahan.
- Durasi job dan keadaan cache perlu dibandingkan pada scope yang setara sebelum menyatakan penghematan numerik.

Pengurangan kerja tersebut bukan jaminan persentase percepatan. Catat waktu total, CPU bila diukur, jumlah job, hit/miss cache, dan ukuran artifact saat menilai optimasi. Jangan mempercepat CI dengan menghapus pemeriksaan asal data atau kelengkapan hasil.

## Dependensi dan izin workflow

Instalasi runtime/test/build memakai `uv pip sync --require-hashes --only-binary :all:` terhadap lock sesuai peran. Audit memeriksa environment dependensi yang dipakai serta tool auditnya dengan mode strict; layanan advisory yang tidak tersedia tidak boleh dianggap hasil aman. Toolchain audit dipisahkan agar dependency tool audit tidak diam-diam menjadi dependency aplikasi. Lock saat ini tidak memakai marker Python yang membedakan paket menurut versi interpreter. Satu environment build Windows 3.14.8 mengaudit paket produksi; bila kelak diperkenalkan profil/marker lain, cakupan audit harus ditinjau ulang.

Actions dipin dengan commit SHA penuh. Checkout tidak menyimpan kredensial Git. Job tes/build memakai token baca. Job `attest` pada push `main` mendapat `id-token: write` dan `attestations: write`; job `cleanup` sesudah gate mendapat `contents: write` serta akses baca PR. Secret penandatanganan penerbit tidak tersedia pada run PR.

Tidak ada capture, profil, log pribadi, atau hasil wajib pajak dalam artifact. Laporan self-test hanya memuat fakta non-rahasia tentang interpreter, resource, GUI, dan apakah akses kredensial/live scrape dilakukan.

## Memverifikasi artifact

Nama artifact menyertakan commit penuh dan versi interpreter:

```text
SPTDownloader-Windows-x64-<commit>-python<versi>
```

Produksi menggunakan `python3.14.8` saja. Artifact 3.11.17 dari run terdahulu tetap dapat disimpan terpisah sebagai opsi rollback yang diverifikasi, bukan artifact produksi baru.

1. Buka run workflow yang dimaksud. Cocokkan repository, event, branch, commit penuh, dan kesimpulan seluruh gate. Untuk rilis produksi gunakan commit `main` yang telah disetujui.
2. Catat **run ID, head SHA, artifact ID, nama artifact, dan profil Python**. Unduh artifact berdasarkan ID/run tersebut; jangan memilih hanya berdasarkan nama atau waktu terbaru.
3. Pastikan set berkas hanya `SPTDownloader.exe`, `LICENSE.txt`, `README.txt`, `build-selftest.json`, dan `SHA256SUMS.txt`. Folder internal build, source capture, profil, dan log pribadi tidak termasuk distribusi.
4. Hitung SHA-256 tiap berkas yang disebut dalam manifest dan cocokkan seluruh nilainya. Perbedaan apa pun berarti artifact belum layak digunakan.
5. Baca `build-selftest.json`: `ok` dan `frozen` harus benar, bitness 64, profil/interpreter sesuai build, resource lengkap, serta `credentials_accessed` dan `live_scrape` salah. Laporan source self-test terpisah dari laporan frozen yang didistribusikan.
6. Pada mesin Windows target, lakukan pembukaan GUI dan penerimaan yang relevan. Bedakan hasil self-test sintetis dari [penerimaan Coretax/Excel aktual](penerimaan-manual.md).

Contoh pemeriksaan manual di PowerShell dari direktori ekstraksi:

```powershell
Get-Content -LiteralPath .\SHA256SUMS.txt
Get-FileHash -Algorithm SHA256 -LiteralPath .\SPTDownloader.exe, .\LICENSE.txt, .\README.txt, .\build-selftest.json
Get-Content -LiteralPath .\build-selftest.json | ConvertFrom-Json
Get-AuthenticodeSignature -LiteralPath .\SPTDownloader.exe | Select-Object Status, SignerCertificate
```

Cocokkan hash berdasarkan nama file, bukan urutan tampilan. Kontributor juga dapat menjalankan verifier dari checkout commit yang sesuai:

```powershell
.venv/Scripts/python.exe -m scripts.ci_artifact verify "C:/folder-artifact-yang-diekstrak" --python-version 3.14.8
```

Setiap job package CI mengunduh ulang hasil upload menggunakan **artifact ID yang persis**, memeriksa lima berkas, hash, dan laporan frozen, lalu menulis run/commit/artifact/version pada summary. Manifest koleksi tes dan laporan audit sintetis merupakan artifact diagnostik terpisah dari lima berkas distribusi.

Checksum dalam arsip yang sama tidak sendirian membuktikan identitas penerbit. Pernyataan berhasil di PR/release perlu menyebut run, commit, dan artifact yang benar-benar dibaca kembali.

## SHA-256, provenance, dan Authenticode

| Mekanisme | Fungsi | Batas |
| --- | --- | --- |
| `SHA256SUMS.txt` | Membuktikan byte cocok dengan manifest yang dibandingkan. | Manifest dan executable dapat diganti bersama jika sumber unduh tidak tepercaya. |
| Provenance/attestation build | Mengaitkan digest artifact dengan workflow, repository, dan commit pembuatnya bila diverifikasi. | Tidak sama dengan tanda tangan publisher Windows dan tidak menyatakan aplikasi telah menjalani acceptance nyata. |
| Authenticode | Memungkinkan verifikasi identitas penerbit dan integritas executable melalui sertifikat penandatanganan kode. | Memerlukan identitas, sertifikat, private key, kebijakan timestamp, serta proses signing yang dikelola maintainer. |

Executable saat ini belum ditandatangani dengan sertifikat penerbit tepercaya. Jangan menyebut manifest atau attestation sebagai Authenticode, memakai sertifikat buatan sebagai pengganti identitas tepercaya, atau menyarankan menonaktifkan Defender/TLS agar aplikasi berjalan.

Pada push kode ke `main`, job `attest` membaca ulang artifact run yang sama, memeriksa isinya tanpa mengeksekusinya, lalu membuat attestation untuk executable dan manifest. PR/manual dispatch tidak menerbitkan attestation `main`. Verifikasi keduanya dengan commit penuh yang telah Anda cocokkan pada run:

```powershell
$SptVerifiedCommit = "GANTI_DENGAN_SHA_MAIN_40_KARAKTER"
gh attestation verify .\SPTDownloader.exe --repo cepeter-job/spt-downloader --signer-workflow cepeter-job/spt-downloader/.github/workflows/windows-build.yml --source-ref refs/heads/main --source-digest $SptVerifiedCommit
gh attestation verify .\SHA256SUMS.txt --repo cepeter-job/spt-downloader --signer-workflow cepeter-job/spt-downloader/.github/workflows/windows-build.yml --source-ref refs/heads/main --source-digest $SptVerifiedCommit
```

Perintah mengikat identitas repo/workflow, ref, commit sumber, dan digest artifact; lihat [manual resmi GitHub CLI](https://cli.github.com/manual/gh_attestation_verify). Laporan sukses run yang sebenarnya tetap diperlukan untuk menyatakan attestation tersedia dan lolos verifikasi.

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

Opsi `--apply` mengaktifkan penghapusan dan memerlukan `GH_TOKEN` dengan `contents: write`. Jangan menulis nilai token ke command, file, atau log. Script mengecek kembali metadata dan memakai Git `--force-with-lease=<ref>:<sha>` pada penghapusan, sehingga push baru pada branch yang sama ditolak oleh server alih-alih ikut terhapus. Tidak ada penghapusan branch berdasarkan umur atau status PR tertutup saja.

## Menutup tindak lanjut audit

Audit bertanggal menyimpan rekomendasi saat baseline masih memiliki dua branch dan satu job Windows. Untuk menutup tindak lanjut pada commit baru, sertakan bukti konkret: aturan branch aktif, hasil lock/hash dan audit, gate Windows profil produksi 3.14.8, artifact yang dibaca kembali, serta penerimaan manual bila dilakukan. Status lulus sintetis, signing, dan penerimaan live harus tetap dicatat terpisah.
