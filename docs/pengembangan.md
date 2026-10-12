# Pengembangan dan kontribusi

[Kembali ke dokumentasi](README.md)

## Prasyarat dan checkout

Gunakan Windows x64 untuk memverifikasi GUI Tk, Edge, Credential Manager, Known Folders, Job Objects, dan executable frozen. Tes portable dapat dijalankan di Linux. Akses intranet atau akun Coretax tidak diperlukan untuk development sintetis.

Toolchain produksi memakai CPython **3.11.17 x64 dengan GIL** dan `uv` **0.12.22**. CPython **3.14.8** dipakai sebagai kandidat kompatibilitas. Versi tersebut harus mengikuti [kebijakan Python](python-314.md) dan sumber kebijakan pada commit yang sedang dikerjakan; jangan mengganti pin dengan `latest` atau sekadar `3.11`.

Clone repositori dan buat branch perubahan dari `main` yang sudah diperbarui. Nama seperti `fix/checkpoint-scope` atau `feat/export-layout` cukup menjelaskan maksudnya. Jangan memindahkan profil browser, capture JSON, workbook nyata, atau kredensial ke checkout. Simpan data dan ruang tes di direktori terpisah.

## Setup Windows dengan PowerShell

Pasang `uv` dari distribusi resmi yang diverifikasi, lalu pastikan versi yang aktif sesuai kebijakan. Perintah ini dijalankan dari root repositori:

```powershell
uv --version
uv python install 3.11.17+gil --no-bin --no-registry
uv venv --python 3.11.17+gil --managed-python .venv
uv pip sync --python .venv/Scripts/python.exe --require-hashes --only-binary :all: locks/test.txt
.venv/Scripts/python.exe --version
```

Managed Python menghindari ketergantungan pada installer Windows Python lama. `--no-bin` dan `--no-registry` mencegah registrasi interpreter/global executable oleh langkah instalasi ini. `uv pip sync` membuat paket environment cocok dengan lock, termasuk dependensi transitif dan hash. Jangan menambahkan `--trusted-host` atau menonaktifkan verifikasi TLS ketika unduhan gagal.

`setup.cmd` adalah jalur setup CLI pengguna dan memasang dependensi runtime. Script tersebut memeriksa versi `uv` exact lalu membentuk ulang `.venv` khusus checkout; jangan menyimpan pekerjaan atau data di dalam `.venv`. Untuk development, gunakan `locks/test.txt`; untuk packaging gunakan `locks/build.txt`. Build lock juga menyediakan dependensi pengujian. Perubahan lock dijelaskan di [kebijakan Python](python-314.md#memperbarui-dependensi-dan-lock).

Periksa Tk dan jalankan GUI source di Windows:

```powershell
.venv/Scripts/python.exe -m tkinter
.venv/Scripts/python.exe spt_gui.py
```

Tutup jendela demo Tk setelah terlihat. Membuka GUI tidak memulai scraping; tombol **Mulai** memulai operasi nyata sesuai pengaturan pengguna. Untuk pemeriksaan otomatis tanpa akun, gunakan self-test di bagian build.

## Pengujian lokal

`--basetemp` harus menunjuk direktori scratch khusus di luar repositori. Pytest dapat mengosongkan direktori tersebut; jangan menunjuk folder profil, Downloads, atau checkpoint. Contoh memakai nama unik per sesi:

```powershell
$SptTestTemp = Join-Path $env:TEMP ("spt-downloader-tests-" + [guid]::NewGuid().ToString("N"))
.venv/Scripts/python.exe -m pytest tests -p scripts.ci_tests --ci-workload portable -q --basetemp "$SptTestTemp/portable"
.venv/Scripts/python.exe -m pytest tests -p scripts.ci_tests --ci-workload windows -q --basetemp "$SptTestTemp/windows"
```

Gunakan portable untuk feedback awal. Workload Windows menjalankan seluruh suite, termasuk logika portable, lalu browser/Tk/native yang nyata bila tesnya memerlukan hal tersebut; fixture dan payload tetap sintetis. Pada mesin Windows yang siap, perintah Windows saja cukup untuk gate suite lengkap. Jangan menjalankan beberapa tes GUI/Job Object sekaligus pada workspace atau profil yang sama.

Untuk seluruh suite pada Windows yang telah memiliki Edge:

```powershell
.venv/Scripts/python.exe -m pytest tests -q --basetemp "$SptTestTemp/full"
```

Untuk perubahan terbatas, mulai dari perilaku yang relevan sebelum menjalankan gate lengkap:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_export_safety.py tests/test_output_safety.py tests/test_split_output.py -q --basetemp "$SptTestTemp/export"
```

### Apa yang dibuktikan tiap lapisan

| Lapisan | Membuktikan | Batas bukti |
| --- | --- | --- |
| Tes portable | Scope, nilai literal, ekspor, protokol, runtime sintetis, dan logika tanpa kebutuhan native. | Tidak membuktikan Edge, Tk, Credential Manager, atau proses Windows aktual. |
| Browser fixture | Playwright mengendalikan Edge pada HTML/respons lokal yang terkontrol; selector, paginasi, dan binding diuji. | Tidak membuktikan layout portal intranet terkini. |
| GUI/native Windows | Perilaku Tk, Known Folders, junction, lock, proses anak, dan lifecycle sesuai kasus tes. | Tidak membuktikan kredensial/akun nyata. |
| Source self-test | GUI dan resource source dapat dibuka, kontrol tersedia, Known Folder dapat diresolusi. | Tidak memasang worker atau mengambil data Coretax nyata. |
| Frozen self-test | Executable hasil packaging dapat dibuka dan berisi resource serta `uv` yang diwajibkan. | Tidak menggantikan acceptance runtime/bootstrap dan portal nyata. |
| Penerimaan manual berizin | Alur pada mesin, browser, portal, serta Excel aktual dengan scope yang disepakati. | Berlaku pada build, waktu, akun, dan scope yang diperiksa. |

Tes yang dilewati karena platform bukan kegagalan, tetapi juga bukan bukti lulus untuk platform tersebut. Catat lingkungan dan batas verifikasi di PR. Tes baru selalu terjangkau suite Windows penuh; tambahkan ke subset portable setelah dependensi/fixture dan kebutuhan platformnya ditinjau.

### Linux atau container

Linux cukup untuk perubahan logika portable. Instal interpreter produksi dan lock tes ke `.venv`, lalu jalankan workload portable:

```bash
uv python install 3.11.17+gil --no-bin
uv venv --python 3.11.17+gil --managed-python .venv
uv pip sync --python .venv/bin/python --require-hashes --only-binary :all: locks/test.txt
.venv/bin/python -m pytest tests -p scripts.ci_tests --ci-workload portable -q --basetemp /tmp/spt-downloader-tests-portable
```

Path `/tmp/spt-downloader-tests-portable` hanya untuk tes ini. Jangan menghapus kegagalan tes dengan mengubah selector atau mock semata-mata karena Edge/display tidak tersedia. Jalankan lapisan Windows yang sesuai melalui CI atau mesin Windows.

## Membuat executable Windows

Sinkronkan build lock, periksa GUI source, lalu bangun executable produksi:

```powershell
uv pip sync --python .venv/Scripts/python.exe --require-hashes --only-binary :all: locks/build.txt
.venv/Scripts/python.exe spt_gui.py --self-test --report "$env:TEMP/spt-source-selftest.json"
.venv/Scripts/python.exe build_desktop.py --output dist
```

`build_desktop.py` memeriksa platform/interpreter/toolchain, membuat executable windowed, dan menjalankan frozen `--self-test`. Build harus gagal bila GUI, resource worker, bundel `uv`, atau pemeriksaan self-test tidak sesuai. Tes/build tidak memakai akun nyata. Folder `dist` dan output sementara tidak masuk version control.

Build lokal bukan artifact rilis terverifikasi dari GitHub. Workflow menambahkan manifest checksum dan publikasi artifact dengan identitas commit; ikuti [CI dan rilis](ci-dan-rilis.md) untuk pemeriksaannya. Jangan mengemas seluruh `dist`, workspace, atau folder hasil capture secara rekursif.

Build kandidat Python 3.14 memakai environment serta output terpisah; lihat [langkah kandidat](python-314.md#menguji-kandidat-python-314).

## Kontribusi dan review

Satu PR sebaiknya menyelesaikan satu masalah yang dapat diperiksa. Jelaskan masalah dan dampaknya, perubahan perilaku, alasan desain, bukti verifikasi, serta batas yang masih tersisa. Bila UI hanya berubah pada teks atau tata letak, jangan memperluas scope capture atau protokol worker tanpa kebutuhan yang jelas.

Untuk bug perilaku, buat reproduksi sintetis yang menunjukkan kegagalan sebelumnya dan menguji hasil yang diharapkan. Pilih assertion pada kontrak: NPWP tetap teks, ID pembetulan berbeda, byte hasil lama pulih setelah gagal, Stop tidak memulai ulang worker, atau status COMPLETE benar. Hindari tes yang hanya menyalin implementasi. Perubahan dokumentasi/komentar sederhana cukup diperiksa diff, tautan, dan kesetaraan logika bila perlu.

Sebelum mengajukan PR:

1. Baca [arsitektur](arsitektur.md) pada area yang berubah dan pertahankan [LICENSE](../LICENSE).
2. Jalankan tes relevan; perubahan browser/Tk/native memerlukan bukti Windows. Perubahan toolchain memerlukan kedua profil Python dan build yang sesuai.
3. Perbarui dokumentasi jika command, output, runtime, resource, atau kontrak berubah.
4. Jalankan `git diff --check`, `git status --short`, dan tinjau diff. Tinjau juga `git diff --cached --name-only` serta konten staged sebelum push.
5. Pastikan tidak ada NPWP nyata, JSON capture, workbook/PDF, cookie, log rahasia, profil, environment, sertifikat privat, atau token dalam perubahan.
6. Tunggu check gabungan **Windows tests and dependency audit** dan review yang dipersyaratkan kebijakan repo pada commit PR yang akan digabungkan.

`main` merupakan branch integrasi untuk CLI dan desktop. Setelah PR tergabung dan commit/artifact yang dimaksud terverifikasi, hapus hanya branch perubahan yang sudah terintegrasi dan tidak lagi dipakai. Jangan menghapus branch yang memiliki commit unik, menjadi dasar PR aktif, atau menyimpan pekerjaan orang lain. Status perlindungan branch merupakan pengaturan GitHub tersendiri; keberadaan workflow tidak mengaktifkan ruleset secara otomatis.

## Menganalisis kinerja

Pisahkan waktu setup/unduhan, navigasi browser, capture, verifikasi Excel, dan publikasi. Gunakan fixture sintetis yang sama, versi toolchain yang sama, serta jumlah SPT/halaman yang sama untuk perbandingan. Catat waktu, beban CPU/memori bila diukur, dan status hasil.

Hindari paralelisasi browser yang berbagi sesi atau menaikkan worker pytest tanpa mengukur dampaknya. Optimasi progres tidak boleh menghapus pemeriksaan akhir atas checkpoint, scope, atau file. Dokumentasikan pengurangan pekerjaan yang benar-benar terjadi; jangan mengklaim persentase percepatan tanpa benchmark sebelum/sesudah yang sebanding.
