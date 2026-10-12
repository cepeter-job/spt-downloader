# CI, penggunaan resource, dan verifikasi rilis

[Kembali ke dokumentasi](README.md)

Sumber konfigurasi adalah [windows-build.yml](../.github/workflows/windows-build.yml). CI memeriksa kode sintetis dan artifact; tidak memakai akun intranet, browser pribadi, atau data wajib pajak.

## Pemicu dan check gabungan

Push ke `main`, PR menuju `main`, dan `workflow_dispatch` menjalankan pemeriksaan yang relevan. Jadwal mingguan Senin pukul **03.17 UTC** memeriksa dependensi pada `main` tanpa mengulang tes GUI atau membuat executable. Branch desktop lama tidak lagi menjadi target terpisah setelah konsolidasi.

Nama check gabungan tetap **Windows tests and dependency audit** agar aturan branch yang sudah mengacu pada nama tersebut tidak perlu mengejar nama matrix. Check ini menggabungkan hasil yang diwajibkan untuk event dan perubahan tersebut. Gagal, dibatalkan, atau terlewatnya job yang seharusnya berjalan tidak boleh dinyatakan berhasil oleh agregator.

Pemilihan perubahan memakai [scripts/ci_route.py](../scripts/ci_route.py). Hanya perubahan dokumentasi yang cocok dengan allowlist aman yang dapat melewati pekerjaan runtime. Perubahan tak dikenal, basis diff yang tidak dapat ditetapkan, atau ketidakpastian klasifikasi menjalankan pemeriksaan lengkap. Perubahan script, lock, requirements, workflow, resource, atau aturan pemilih tes tetap memerlukan gate kode.

Pengaturan ruleset/branch protection di GitHub terpisah dari YAML. Maintainer perlu memastikan check gabungan dan PR benar-benar diwajibkan pada `main`. Jangan menyimpulkan perlindungan aktif hanya karena workflow tersedia atau berwarna hijau. Lihat [aktivasi aturan repo](#aktivasi-aturan-repository) untuk prasyarat admin yang masih terpisah dari CI.

## Pembagian pekerjaan

| Kelompok pekerjaan | Lingkungan dan isi | Kebijakan resource |
| --- | --- | --- |
| `route` | Memutuskan dokumentasi aman atau pemeriksaan kode lengkap; memvalidasi workflow. | Pekerjaan kecil, tanpa instalasi stack aplikasi. |
| `portable` | Matrix CPython 3.11.17 dan 3.14.8 pada Linux; logika tanpa browser/Tk/native Windows. | Satu proses pytest per runner, maksimal dua entri matrix bersamaan. |
| `windows` | Seluruh suite pada kedua versi Python; Edge fixture, GUI Tk, batas native, dan bootstrap worker nyata. | Tes berurutan dalam satu runner; maksimal dua entri matrix bersamaan. |
| `dependency-audit` | Environment build pada Python produksi Windows dan tool audit terisolasi. | Satu runner; jadwal mingguan menjalankan audit tanpa build. |
| `package` | Profil produksi dan kandidat setelah semua gate tes/audit; self-test source kemudian frozen. | Maksimal dua build bersamaan, output terpisah. |
| Pemeriksaan artifact | File allowlist, laporan self-test, checksum, dan identitas run/commit/artifact. | Hanya set distribusi yang diunggah dan dibaca kembali. |
| `attest` | Provenance executable dan manifest pada push `main` tepercaya setelah artifact diverifikasi. | Izin OIDC/attestation hanya tersedia di job ini. |
| `validate` | Check **Windows tests and dependency audit** untuk hasil seluruh job yang diwajibkan. | Tetap muncul juga ketika jalur dokumentasi aman dipilih. |
| `cleanup` | Pembersihan branch selesai setelah check gabungan `main` berhasil. | Job tersendiri dengan izin penghapusan dan pemeriksaan SHA. |

Profil Python 3.14 merupakan gate kompatibilitas yang menghalangi penggabungan bila gagal. Artifact kandidat tetap dibedakan dari produksi. Lulus matrix tidak otomatis mengubah versi bawaan aplikasi; proses promosi dijelaskan pada [kebijakan Python](python-314.md).

Pemilih [scripts/ci_tests.py](../scripts/ci_tests.py) memilih subset portable untuk feedback awal dan kompatibilitas Linux. Workload Windows menjalankan **seluruh suite**, termasuk tes portable yang memiliki cabang perilaku Windows. Pengulangan ini disengaja agar perilaku seperti junction tidak hilang dari cakupan. Manifest collection harus membuktikan subset portable benar, inventaris Windows lengkap, serta versi Python/commit sesuai. Tes baru selalu terjangkau suite Windows, lalu dapat dimasukkan ke subset portable setelah ditinjau.

## Cache dan CPU

Cache menyimpan unduhan/paket `uv` serta interpreter managed. Kunci memisahkan OS, arsitektur, versi Python, peran workload, serta isi lock dan requirements. Cache tidak menjadi bukti bahwa environment sudah terverifikasi: instalasi tetap memakai lock dan hash, dan runtime memeriksa kesiapan aktual.

PR dapat memulihkan cache, tetapi penulisan cache dibatasi pada push tepercaya ke `main`. `.venv`, profil/cookie browser, data pajak, checkpoint, output tes, Downloads, dan executable browser tidak disimpan dalam cache. Jangan menambahkan seluruh workspace ke cache demi mempercepat setup.

Beberapa keputusan menjaga beban tetap terukur:

- Perubahan dokumentasi yang terbukti aman tidak menjalankan semua interpreter, browser, dan build.
- Subset Linux memberi feedback portable tanpa browser/GUI; suite Windows penuh mempertahankan seluruh perilaku target.
- Satu proses pytest per runner menghindari perkalian proses browser dan perebutan resource Tk/Windows Job Object.
- Fase tes dibatasi pada dua runner portable, dua Windows, dan satu audit; dua runner build dimulai setelah gate tersebut. Run usang dibatalkan sesuai `concurrency` workflow.
- Audit mingguan tidak membuat ulang executable dan tidak menjalankan suite browser.
- Artifact executable yang sudah terkompresi diunggah tanpa kompresi tambahan.
- Durasi job dan keadaan cache perlu dibandingkan pada scope yang setara sebelum menyatakan penghematan numerik.

Pengurangan kerja tersebut bukan jaminan persentase percepatan. Catat waktu total, CPU bila diukur, jumlah job, hit/miss cache, dan ukuran artifact saat menilai optimasi. Jangan mempercepat CI dengan menghapus pemeriksaan asal data atau kelengkapan hasil.

## Dependensi dan izin workflow

Instalasi runtime/test/build memakai `uv pip sync --require-hashes --only-binary :all:` terhadap lock sesuai peran. Audit memeriksa environment dependensi yang dipakai serta tool auditnya dengan mode strict; layanan advisory yang tidak tersedia tidak boleh dianggap hasil aman. Toolchain audit dipisahkan agar dependency tool audit tidak diam-diam menjadi dependency aplikasi. Lock saat ini tidak memakai marker Python yang membedakan versi paket, sehingga satu environment build Windows mengaudit gabungan versi kedua profil. Jika marker/versi berbeda diperkenalkan, cakupan audit harus diperluas.

Actions dipin dengan commit SHA penuh. Checkout tidak menyimpan kredensial Git. Job tes/build memakai token baca. Job `attest` pada push `main` mendapat `id-token: write` dan `attestations: write`; job `cleanup` sesudah gate mendapat `contents: write` serta akses baca PR. Secret penandatanganan penerbit tidak tersedia pada run PR.

Tidak ada capture, profil, log pribadi, atau hasil wajib pajak dalam artifact. Laporan self-test hanya memuat fakta non-rahasia tentang interpreter, resource, GUI, dan apakah akses kredensial/live scrape dilakukan.

## Memverifikasi artifact

Nama artifact menyertakan commit penuh dan versi interpreter:

```text
SPTDownloader-Windows-x64-<commit>-python<versi>
```

Produksi memakai `python3.11.17`; kandidat memakai `python3.14.8`. Nama berkas executable di dalamnya sama, sehingga kedua artifact perlu diekstrak ke direktori berbeda.

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
.venv/Scripts/python.exe -m scripts.ci_artifact verify "C:/folder-artifact-yang-diekstrak" --python-version 3.11.17
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

Aktivasi ini membutuhkan akses admin yang sesuai dan tetap tertunda sampai hasil remote dapat dibaca kembali. Keberhasilan CI, merge, atau keberadaan JSON saja tidak menutup prasyarat tersebut.

## Pembersihan branch selesai

Job `cleanup` berjalan hanya pada push `main` setelah check gabungan sukses. [scripts/cleanup_branches.py](../scripts/cleanup_branches.py) secara bawaan hanya membuat pratinjau. Untuk inspeksi manual gunakan SHA main yang telah diuji:

```powershell
.venv/Scripts/python.exe scripts/cleanup_branches.py --repository cepeter-job/spt-downloader --base main --expected-base SHA_MAIN_YANG_TELAH_DIUJI
```

Kandidat harus berasal dari PR tertutup di repo yang sama, bukan branch default/protected atau head maupun base PR terbuka, dan SHA branch saat ini harus sama dengan head PR. Perlindungan base juga berlaku untuk PR dari fork. Riwayat harus membuktikan head tersebut ancestor dari main yang diuji. Branch hasil squash/rebase yang belum memiliki bukti ancestry dipertahankan. Main yang berubah membuat cleanup berhenti.

Opsi `--apply` mengaktifkan penghapusan dan memerlukan `GH_TOKEN` dengan `contents: write`. Jangan menulis nilai token ke command, file, atau log. Script mengecek kembali metadata dan memakai Git `--force-with-lease=<ref>:<sha>` pada penghapusan, sehingga push baru pada branch yang sama ditolak oleh server alih-alih ikut terhapus. Tidak ada penghapusan branch berdasarkan umur atau status PR tertutup saja.

## Menutup tindak lanjut audit

Audit bertanggal menyimpan rekomendasi saat baseline masih memiliki dua branch dan satu job Windows. Untuk menutup tindak lanjut pada commit baru, sertakan bukti konkret: aturan branch aktif, hasil lock/hash dan audit, gate Windows kedua profil, artifact yang dibaca kembali, serta penerimaan manual bila dilakukan. Status lulus sintetis, signing, dan penerimaan live harus tetap dicatat terpisah.
