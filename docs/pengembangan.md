# Pengembangan dan kontribusi

[Kembali ke dokumentasi](README.md)

Panduan ini menjelaskan alur kontribusi dan referensi perintah yang dipakai runner.
Mulai dari [peta kode](peta-kode.md) untuk menemukan pemilik perilaku yang akan diubah.
Kebijakan versi/lock ada pada [kebijakan Python](python-314.md); verifikasi distribusi
ada pada [CI dan rilis](ci-dan-rilis.md#memverifikasi-artifact).

**Untuk pekerjaan berotorisasi yang disebut pada [AGENTS.md](../AGENTS.md#verification),
pytest, import produk, native/Tk/browser, source/frozen self-test, build dan EXE hanya
dijalankan pada GitHub runner.** Lokal dipakai untuk menyunting dan memeriksa
source/dokumen/AST serta hash/metadata. Pemeriksaan tersebut tidak membuktikan perilaku
runtime. Contoh perintah runner di bawah tidak mengubah batas eksekusi ini.

## Prasyarat dan checkout

Untuk menyiapkan perubahan, gunakan editor, Git, dan akses ke repository. GitHub CLI
`gh` dengan akses repository dapat dipakai untuk membaca PR/run dan meminta dispatch.
Runner Windows x64 memverifikasi GUI Tk, Edge, Credential Manager, Known Folders, Job
Objects, dan executable frozen; runner Linux menjalankan subset portable. Akses
intranet atau akun Coretax tidak diperlukan untuk development sintetis.

Gunakan profil `production` CPython x64/GIL dan pin uv pada [tabel versi](python-314.md#versi-yang-didukung). Contoh perintah berikut mengikuti pin tersebut; saat memutakhirkan toolchain, cocokkan contoh dengan `runtime.py`. Jangan memakai `latest`, minor saja, atau Python sistem sebagai pengganti pin.

Clone repositori dan buat branch perubahan dari `main` yang sudah diperbarui. Nama seperti `fix/checkpoint-scope` atau `feat/export-layout` cukup menjelaskan maksudnya. Jangan memindahkan profil browser, capture JSON, workbook nyata, atau kredensial ke checkout. Simpan data dan ruang tes di direktori terpisah.

## Pemilik konfigurasi tooling

Default pytest dan metadata proyek berada di `pyproject.toml`; pilihan lint
berada di `ruff.toml`. Coverage hanya memakai `.coveragerc`, dengan pilihan
eksplisit `--rcfile=.coveragerc` pada seluruh perintah CI run/XML/JSON.
`RUNNER_TEMP` wajib tersedia agar berkas data tetap di scratch runner;
konfigurasi mempertahankan branch coverage, omit yang ada dan `fail_under=0`.
Laporan portable belum mewakili coverage Windows/browser/native/worker.
Jangan menambahkan salinan `[tool.coverage.*]` yang melewatkan kontrak ini.

## Alur verifikasi melalui GitHub Actions

1. Tentukan modul, kontrak, dan tes terkait melalui [peta kode](peta-kode.md) serta
   [arsitektur](arsitektur.md). Untuk perubahan perilaku, siapkan reproduksi sintetis.
2. Sunting perubahan, periksa diff dan tautan, lalu catat SHA penuh dari `git rev-parse HEAD`
   setelah commit. AST dapat membandingkan struktur kode untuk perubahan komentar;
   jangan mengimpor produk hanya untuk membaca konstanta atau menghitung tes.
3. Ajukan PR menuju `main`. Workflow berjalan pada peristiwa PR; push ke branch
   perubahan tanpa PR tidak otomatis memicu workflow build. Baca hasil dengan
   [perintah PR/run](ci-dan-rilis.md#menjalankan-dan-membaca-verifikasi).
4. Cocokkan head PR, commit yang benar-benar diuji, run ID, attempt, dan gate yang
   diwajibkan. Perubahan `.py`, termasuk komentar, tetap menjalankan jalur kode penuh.
   Jalur dokumentasi aman dapat melewati runtime sesuai pemilih CI.
5. Untuk perubahan yang menghasilkan executable, lanjutkan sampai
   [artifact dibaca kembali dan diverifikasi](ci-dan-rilis.md#memverifikasi-artifact).
   Catat scope yang dibuktikan dan pisahkan dari penerimaan portal nyata.

CI normal menjalankan suite Windows lengkap melalui dua shard, serta subset
portable, audit, bootstrap worker, source/frozen self-test, build, dan verifikasi
artifact. Dispatch manual tersedia untuk pemeriksaan tambahan atau kontrol serial;
jangan mengubah workflow atau selector untuk membuat hasil menjadi hijau.

## Referensi perintah pada runner

Bagian ini membantu membaca atau mendiagnosis langkah CI. Jalankan melalui pekerjaan
GitHub runner yang sesuai dengan scope perubahan. Sumber lengkap, termasuk manifest
koleksi, JUnit, cache, dan guard kegagalan, tetap
[windows-build.yml](../.github/workflows/windows-build.yml). Menjalankan satu perintah
referensi tidak menggantikan seluruh gate workflow.

### Setup Windows dengan PowerShell

Workflow menyiapkan `uv` yang dipin dari distribusi resmi. Contoh berikut memakai
root checkout di runner Windows; pastikan versi `uv` sesuai kebijakan:

```powershell
uv --version
uv python install cpython-3.14.8-windows-x86_64-none --no-bin --no-registry
uv venv --python 3.14.8+gil --managed-python .venv
uv pip sync --python .venv/Scripts/python.exe --require-hashes --only-binary :all: locks/test.txt
.venv/Scripts/python.exe --version
```

Managed Python menghindari ketergantungan pada installer Windows Python lama. `--no-bin` dan `--no-registry` mencegah registrasi interpreter/global executable oleh langkah instalasi ini. `uv pip sync` membuat paket environment cocok dengan lock, termasuk dependensi transitif dan hash. Jangan menambahkan `--trusted-host` atau menonaktifkan verifikasi TLS ketika unduhan gagal.

`setup.cmd` adalah jalur setup CLI pengguna dan memasang dependensi runtime. Script tersebut memeriksa versi `uv` exact lalu membentuk ulang `.venv` khusus checkout; jangan menyimpan pekerjaan atau data di dalam `.venv`. Untuk development, gunakan `locks/test.txt`; untuk packaging gunakan `locks/build.txt`. Build lock juga menyediakan dependensi pengujian. Perubahan lock dijelaskan di [kebijakan Python](python-314.md#memperbarui-dependensi-dan-lock).

Pemeriksaan otomatis Tk dan GUI tanpa akun memakai fixture suite serta
[source/frozen self-test](#membuat-executable-windows).

<a id="pengujian-lokal"></a>

### Pengujian pada runner

`--basetemp` harus menunjuk direktori scratch khusus di luar repositori. Pytest dapat
mengosongkan direktori tersebut; jangan menunjuk folder profil, Downloads, atau
checkpoint. Contoh memakai `RUNNER_TEMP` milik job Windows:

```powershell
$SptTestTemp = Join-Path $env:RUNNER_TEMP "spt-pytest-reference"
.venv/Scripts/python.exe -m pytest tests -p scripts.ci_tests --ci-workload portable -q --basetemp "$SptTestTemp/portable"
.venv/Scripts/python.exe -m pytest tests -p scripts.ci_tests --ci-workload windows -q --basetemp "$SptTestTemp/windows"
```

Workload portable memberi feedback awal. Workload Windows tanpa `--ci-shard`
menjalankan seluruh suite, termasuk logika portable, lalu browser/Tk/native yang
nyata bila tesnya memerlukan hal tersebut; fixture dan payload tetap sintetis.
Contoh Windows di atas adalah bentuk serial. CI reguler memberi masing-masing
runner `--ci-shard 0/2` atau `--ci-shard 1/2`, disertai `--ci-manifest`, lalu
memverifikasi gabungan inventory sebelum packaging. Jangan menjalankan beberapa
tes GUI/Job Object sekaligus pada workspace atau profil yang sama.

Perintah workload `windows` di atas mencakup suite lengkap dalam mode serial;
tidak perlu menjalankan ulang suite tanpa selector untuk menduplikasi hasil.
Kelulusan perintah itu saja belum menggantikan bukti inventory, artifact, dan
seluruh gate workflow.

Untuk diagnosis terarah pada runner yang disiapkan bagi pemeriksaan tersebut,
contoh pemilihan kasus ekspor adalah sebagai berikut. Gate CI tetap memerlukan
suite lengkap:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_export_safety.py tests/test_output_safety.py tests/test_split_output.py -q --basetemp "$SptTestTemp/export"
```

#### Apa yang dibuktikan tiap lapisan

| Lapisan | Membuktikan | Batas bukti |
| --- | --- | --- |
| Tes portable | Scope, nilai literal, ekspor, protokol, runtime sintetis, dan logika tanpa kebutuhan native. | Tidak membuktikan Edge, Tk, Credential Manager, atau proses Windows aktual. |
| Browser fixture | Playwright mengendalikan Edge pada HTML/respons lokal yang terkontrol; selector, paginasi, dan binding diuji. | Tidak membuktikan layout portal intranet terkini. |
| GUI/native Windows | Perilaku Tk, Known Folders, junction, lock, proses anak, dan lifecycle sesuai kasus tes. | Tidak membuktikan kredensial/akun nyata. |
| Source self-test | GUI dan resource source dapat dibuka, kontrol tersedia, Known Folder dapat diresolusi. | Tidak memasang worker atau mengambil data Coretax nyata. |
| Frozen self-test | Executable hasil packaging dapat dibuka dan berisi resource serta `uv` yang diwajibkan. | Tidak menggantikan acceptance runtime/bootstrap dan portal nyata. |
| Penerimaan manual berizin | Alur pada mesin, browser, portal, serta Excel aktual dengan scope yang disepakati. | Berlaku pada build, waktu, akun, dan scope yang diperiksa. |

Tes yang dilewati karena platform bukan kegagalan, tetapi juga bukan bukti lulus untuk platform tersebut. Catat lingkungan dan batas verifikasi di PR. Tes baru selalu terjangkau suite Windows penuh; tambahkan ke subset portable setelah dependensi/fixture dan kebutuhan platformnya ditinjau.

#### Merawat kontrak tes

Ekspektasi katalog UI disimpan sebagai nilai literal yang ditinjau di `tests/test_desktop_ui_copy.py`, bukan dibaca dari tabel atau nomor bab dokumen desain. Dokumen menjelaskan keputusan; perubahan format Markdown tidak boleh mengubah hasil tes produk. Perubahan kata yang disengaja harus memperbarui implementasi, ekspektasi tes, dan dokumentasi terkait dalam PR yang sama. Jangan menghasilkan ekspektasi saat tes berjalan dari `COPY` milik aplikasi, karena itu tidak mendeteksi regresi.

Konsolidasi hanya kasus yang benar-benar identik: tulis di PR tes yang dihapus, tes penerusnya, serta kesamaan input, setup, dan assertion. Satu pemanggilan source self-test yang berhasil dapat memeriksa beberapa bagian laporan tanpa menjalankan GUI yang sama lagi. Pertahankan kasus negatif, pengujian widget nyata, isolasi kredensial/proses, dan self-test executable frozen secara terpisah. Jumlah tes boleh berkurang; kontrak perilaku dan gate CI tidak boleh melemah.

### Linux atau container

Runner Linux memberi bukti untuk logika portable. Instal interpreter produksi dan
lock tes ke `.venv`, lalu jalankan workload portable dari root checkout:

```bash
uv python install cpython-3.14.8-linux-x86_64-gnu --no-bin --no-registry
uv venv --python 3.14.8+gil --managed-python .venv
uv pip sync --python .venv/bin/python --require-hashes --only-binary :all: locks/test.txt
.venv/bin/python -m pytest tests -p scripts.ci_tests --ci-workload portable -q --basetemp "$RUNNER_TEMP/spt-pytest-portable"
```

Direktori di bawah `RUNNER_TEMP` hanya untuk tes job tersebut. Jangan menghapus
kegagalan tes dengan mengubah selector atau mock semata-mata karena Edge/display
tidak tersedia. Lapisan Windows tetap dijalankan oleh job Windows pada CI.

### Membuat executable Windows

Pada runner Windows, sinkronkan build lock, periksa GUI source, lalu bangun
executable produksi:

```powershell
uv pip sync --python .venv/Scripts/python.exe --require-hashes --only-binary :all: locks/build.txt
.venv/Scripts/python.exe spt_gui.py --self-test --report "$env:RUNNER_TEMP/source-selftest.json"
.venv/Scripts/python.exe build_desktop.py --python-profile production --output dist
```

`build_desktop.py` memeriksa platform/interpreter/toolchain, membuat executable windowed, dan menjalankan frozen `--self-test`. Build harus gagal bila GUI, resource worker, bundel `uv`, atau pemeriksaan self-test tidak sesuai. Tes/build tidak memakai akun nyata. Folder `dist` dan output sementara tidak masuk version control.

Output build belum menjadi artifact distribusi yang terverifikasi sampai workflow
menambahkan manifest checksum, mengunggah set berkas yang tepat, dan membaca kembali
byte dari artifact ID tersebut. Ikuti [CI dan rilis](ci-dan-rilis.md) untuk
pemeriksaannya. Jangan mengemas seluruh `dist`, workspace, atau folder hasil capture
secara rekursif.

Executable produksi dan worker wajib memenuhi pin produksi yang sama. Lihat [verifikasi produksi](python-314.md#verifikasi-produksi) dan [langkah pemulihan](python-314.md#batas-dan-langkah-kembali).

## Kontribusi dan review

Satu PR sebaiknya menyelesaikan satu masalah yang dapat diperiksa. Jelaskan masalah dan dampaknya, perubahan perilaku, alasan desain, bukti verifikasi, serta batas yang masih tersisa. Bila UI hanya berubah pada teks atau tata letak, jangan memperluas scope capture atau protokol worker tanpa kebutuhan yang jelas.

Untuk bug perilaku, buat reproduksi sintetis yang menunjukkan kegagalan sebelumnya dan menguji hasil yang diharapkan. Pilih assertion pada kontrak: NPWP tetap teks, ID pembetulan berbeda, byte hasil lama pulih setelah gagal, Stop tidak memulai ulang worker, atau status COMPLETE benar. Hindari tes yang hanya menyalin implementasi. Perubahan dokumentasi/komentar sederhana cukup diperiksa diff, tautan, dan kesetaraan logika bila perlu.

### Komentar kode dalam bahasa Indonesia

Gunakan komentar `#` untuk menjelaskan alasan keputusan, aturan yang harus tetap
benar, atau batas proses/sumber data yang mudah terlewat. Tempatkan dekat guard atau
langkah yang bergantung pada alasan itu. Contoh: `# Periksa ulang scope karena folder
dapat berubah setelah persetujuan pengguna.` Komentar seperti `# Tambah satu` di atas
`count += 1` tidak membantu pembaca memahami kontrak.

Pertahankan nama API, identifier, kunci protokol, serta status literal seperti
`COMPLETE` dan `PARTIAL`. Perbarui komentar ketika perilaku berubah dan tautkan
penjelasan lintas modul ke [peta kode](peta-kode.md) atau panduan pemilik kontraknya.
Untuk perubahan komentar saja, pertahankan statement, signature, dan nilai string
program; bandingkan AST bila perlu dan laporkan pemeriksaan tersebut sebagai bukti
source. CI tetap memilih workload berdasarkan path yang berubah.

### Checklist PR

Sebelum meminta penggabungan PR:

1. Baca [arsitektur](arsitektur.md) pada area yang berubah dan pertahankan [LICENSE](../LICENSE).
2. Jalankan verifikasi melalui CI; perubahan browser/Tk/native memerlukan bukti Windows. Perubahan toolchain memerlukan suite dan build profil produksi, serta bukti instalasi worker baru/pakai ulang. Tunggu check gabungan **Windows tests and dependency audit**, check wajib lain seperti **CodeQL**, dan review yang dipersyaratkan pada revisi PR yang akan digabungkan. Simpan tautan run serta identitas head/merge, attempt, dan artifact yang relevan.
3. Perbarui dokumentasi jika command, output, runtime, resource, atau kontrak berubah.
4. Jalankan `git diff --check`, `git status --short`, dan tinjau diff. Tinjau juga `git diff --cached --name-only` serta konten staged sebelum push.
5. Pastikan tidak ada NPWP nyata, JSON capture, workbook/PDF, cookie, log rahasia, profil, environment, sertifikat privat, atau token dalam perubahan.

`main` merupakan branch integrasi untuk CLI dan desktop. Setelah PR tergabung dan commit/artifact yang dimaksud terverifikasi, hapus hanya branch perubahan yang sudah terintegrasi dan tidak lagi dipakai. Jangan menghapus branch yang memiliki commit unik, menjadi dasar PR aktif, atau menyimpan pekerjaan orang lain. Status perlindungan branch merupakan pengaturan GitHub tersendiri; keberadaan workflow tidak mengaktifkan ruleset secara otomatis.

## Menganalisis kinerja

Pisahkan waktu setup/unduhan, navigasi browser, capture, verifikasi Excel, dan publikasi. Gunakan fixture sintetis yang sama, versi toolchain yang sama, serta jumlah SPT/halaman yang sama untuk perbandingan. Catat waktu, beban CPU/memori bila diukur, dan status hasil.

Hindari paralelisasi browser yang berbagi sesi atau menaikkan worker pytest tanpa mengukur dampaknya. Optimasi progres tidak boleh menghapus pemeriksaan akhir atas checkpoint, scope, atau file. Dokumentasikan pengurangan pekerjaan yang benar-benar terjadi; jangan mengklaim persentase percepatan tanpa benchmark sebelum/sesudah yang sebanding.


## Fixture pengujian bersama

Helper yang dipakai lintas modul pengujian berada di `tests/support_*.py`, bukan
`test_*.py`. Gunakan owner yang sesuai: data run sintetis, bukti PDF, template,
protokol browser, laporan build, atau GUI. Modul support tidak berisi tes yang
ikut dikoleksi dan tidak membuka browser, koneksi, atau window ketika diimpor.
Pada pemindahan helper tanpa optimasi perilaku, pertahankan scope dan teardown
semula; jangan memindahkan guard autouse lokal ke seluruh suite. Modul data tidak
boleh menarik dependensi Tk atau Playwright hanya karena helper GUI memakai data
yang sama.

Untuk optimasi browser sintetis, ukur setup, eksekusi, dan teardown bersama-sama.
`support_isolated_browser` memakai satu proses Edge per modul, tetapi membuat
context baru untuk setiap kasus dan menutupnya melalui `finally`, termasuk popup
saat kasus gagal. Gunakan pola ini untuk modul yang tidak menguji penghentian
proses browser itu sendiri. Kesiapan fixture dapat ditunggu melalui sinyal
permintaan yang selesai; respons gagal tetap harus mencapai pemeriksaan penolakan
yang sesuai. Jeda yang sengaja menguji timeout atau kondisi terlambat tetap diperlukan.

Daftarkan fixture `browser` dan dependensi fixture lain secara eksplisit pada
setiap modul consumer; mengimpor fungsi helper atau fixture `page` saja tidak
mendaftarkan seluruh dependensinya. Minta browser hanya pada tes yang memakainya,
agar tes data dan ekspor tetap tidak membuka proses browser. Helper yang membuat
context sendiri harus menerima browser secara eksplisit dan menutup context dalam
`finally`. Pertahankan opsi khusus seperti timezone, level route page/context,
timeout, dan metrik per pemakaian. Monkeypatch kelas Playwright tetap berscope
fungsi; bila satu tes membuka beberapa helper, batasi patch dengan
`monkeypatch.context()` dan tutup context browser sebelum patch dipulihkan.

Pada pemindahan owner, pertahankan identitas kelas dan arah monkeypatch. Contoh:
`support_browser_protocol.META` dan `View` harus dipakai oleh simulator yang sama;
menambal modul pengujian lama tidak boleh menjadi mekanisme kompatibilitas.
Jangan menggabungkan byte PDF atau konstanta template berbeda hanya karena
nama variabelnya sama. Buktikan bahwa node ID, parameter, assertion, dan fixture
teardown tetap sama melalui suite Windows lengkap serta inventory CI.
