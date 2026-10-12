# Kebijakan Python dan persiapan 3.14

[Kembali ke dokumentasi](README.md)

Sumber pin adalah `PYTHON_PROFILES`, `UV_VERSION`, dan `RUNTIME_LOCK` pada [spt_desktop/runtime.py](../spt_desktop/runtime.py). Persyaratan build dibaca dari sumber yang sama oleh [build_desktop.py](../build_desktop.py). Ubah kebijakan, lock, pengujian, workflow, dan dokumentasi dalam satu perubahan yang dapat ditinjau.

## Kebijakan saat ini

| Komponen | Profil/versi | Makna |
| --- | --- | --- |
| GUI/executable produksi | CPython **3.11.17**, Windows x64, GIL aktif | Profil default `production`. |
| Worker pengguna | Managed CPython **3.11.17**, Windows x64, GIL aktif | Tetap produksi, termasuk saat GUI kandidat dipakai. |
| GUI/executable kandidat | CPython **3.14.8**, Windows x64, GIL aktif | Profil `candidate` khusus evaluasi build/GUI. |
| Worker kandidat di CI | Managed CPython **3.14.8**, Windows x64, GIL aktif | Diuji melalui smoke bootstrap terisolasi; tidak mengganti default worker pengguna. |
| Paket/installer `uv` | **0.12.22** | Versi exact untuk katalog interpreter, lock, CI, dan bundel. |

Versi minor saja tidak cukup. Runtime memeriksa patch version, implementasi, arsitektur 64-bit, status free-threaded, lokasi interpreter dasar di workspace managed, serta versi seluruh dependency yang dikunci. Distribusi free-threaded bukan target saat ini. Request `+gil` membuat pilihan interpreter eksplisit.

Python 3.11 telah masuk fase pemeliharaan keamanan; installer Windows Python.org 3.11 terakhir adalah 3.11.9. Karena itu, menerima interpreter sistem 3.11 apa saja akan mempertahankan patch lama. Jalur produksi menggunakan distribusi managed melalui `uv` pada versi patch yang dipin. Kandidat 3.14 disiapkan bersamaan, dengan gate yang harus lulus sebelum promosi. Rujukan upstream: [rilis Python](https://www.python.org/downloads/), [Python 3.11.9](https://www.python.org/downloads/release/python-3119/), dan [versi serta distribusi Python pada uv](https://docs.astral.sh/uv/concepts/python-versions/).

`uv` membawa katalog interpreter yang terkait dengan versinya. Mengganti pin Python harus memastikan versi `uv` tersebut dapat menemukan distribusi yang tepat, termasuk Tcl/Tk untuk GUI Windows. Memasang runtime GIL tidak membuktikan Tcl/Tk, wheel native, atau PyInstaller telah bekerja; semuanya memiliki gate tersendiri.

## Runtime terisolasi dan fingerprint

Worker memakai interpreter managed di `%LOCALAPPDATA%\SPTDownloader\python` dan environment di `runtime`. Tidak ada ketergantungan pada Python sistem, registrasi global, atau perubahan PATH untuk menjalankan worker. Persiapan menggunakan `--no-bin` dan `--no-registry`.

Fingerprint mencakup byte resource worker, lock runtime, profil/versi Python, dan versi `uv`. Penanda siap hanya ditulis setelah interpreter dan seluruh paket terkunci diverifikasi. Penanda yang ada tidak dipercaya sendirian: interpreter, lokasi base, import paket, versi, dan fingerprint diperiksa kembali. Kegagalan atau Stop menghapus kesempatan menganggap setup selesai dan tetap dapat dicoba ulang.

`locks/runtime.txt` masuk `WORKER_FILES`. Jangan memperbarui requirements tanpa lock, menghapus hash agar instalasi lewat, atau menyalin environment siap dari mesin lain. Perubahan resource/lock harus menyebabkan pemeriksaan ulang yang benar tanpa memasukkan profil/output ke paket.

## Memperbarui dependensi dan lock

| Input | Lock teresolusi | Isi |
| --- | --- | --- |
| `requirements.txt` | `locks/runtime.txt` | Playwright/openpyxl dan seluruh dependensi transitif worker. |
| `requirements-test.txt` | `locks/test.txt` | Runtime dan dependency tes. |
| `requirements-build.txt` | `locks/build.txt` | Runtime, tes, `uv`, dan PyInstaller beserta transitifnya. |
| `requirements-audit.txt` | `locks/audit.txt` | Tool audit yang terisolasi dari aplikasi. |

Input memuat pin langsung yang ditinjau. Lock memuat hasil resolusi lengkap dan hash SHA-256. Script [scripts/update_locks.py](../scripts/update_locks.py) membuat lock universal dengan batas Python yang didukung, wheel saja, serta constraint berantai runtime → test → build. Seluruh resolusi harus berhasil sebelum berkas lock yang ada diganti.

Dengan `uv` 0.12.22 pada PATH, jalankan dari root checkout:

```powershell
.venv/Scripts/python.exe -m scripts.update_locks
.venv/Scripts/python.exe -m scripts.update_locks --check
```

Perintah pertama mempertahankan versi transitif yang sudah dipilih selama masih sesuai dengan input. `--check` melakukan resolusi pembanding tanpa menulis lock dan gagal bila ditemukan drift. Untuk memperbarui transitif yang diizinkan pin langsung, gunakan perubahan terpisah yang disengaja:

```powershell
.venv/Scripts/python.exe -m scripts.update_locks --upgrade
```

`--offline` hanya sesuai bila metadata yang diperlukan sudah ada di cache. Mode ini tidak menggantikan audit advisory terkini. Tinjau diff versi, semua hash, serta alasan upgrade, kemudian instal ulang environment dari lock:

```powershell
uv pip sync --python .venv/Scripts/python.exe --require-hashes --only-binary :all: locks/build.txt
```

`--only-binary :all:` membuat wheel yang tidak tersedia menjadi kegagalan eksplisit. Jangan menurunkan syarat tersebut untuk membangun sdist secara tidak sengaja pada mesin pengguna. Audit runtime/build dan jalankan matrix kedua versi Python setelah pembaruan; hash memastikan paket sesuai lock, bukan membuktikan paket bebas kerentanan.

## Menguji kandidat Python 3.14

Gunakan environment dan output baru di luar checkout agar profil produksi tetap dapat direproduksi. Contoh PowerShell:

```powershell
$SptCandidateRoot = Join-Path $env:LOCALAPPDATA "SPTDownloader-Dev/python314"
uv python install 3.14.8+gil --no-bin --no-registry
uv venv --managed-python --python 3.14.8+gil "$SptCandidateRoot/venv"
uv pip sync --python "$SptCandidateRoot/venv/Scripts/python.exe" --require-hashes --only-binary :all: locks/build.txt
& "$SptCandidateRoot/venv/Scripts/python.exe" -m pytest tests -p scripts.ci_tests --ci-workload portable -q --basetemp "$SptCandidateRoot/tests-portable"
& "$SptCandidateRoot/venv/Scripts/python.exe" -m pytest tests -p scripts.ci_tests --ci-workload windows -q --basetemp "$SptCandidateRoot/tests-windows"
& "$SptCandidateRoot/venv/Scripts/python.exe" spt_gui.py --self-test --report "$SptCandidateRoot/source-selftest.json"
& "$SptCandidateRoot/venv/Scripts/python.exe" build_desktop.py --python-profile candidate --output "$SptCandidateRoot/dist"
```

`--python-profile candidate` memilih interpreter untuk **build/GUI**. Executable tersebut masih menyiapkan worker produksi 3.11.17 ketika pengguna menekan Mulai; ia tidak menyediakan tombol umum untuk mengganti worker. Laporan frozen mencatat interpreter GUI, `build_profile`, serta `worker_python`, sehingga perbedaan ini dapat diperiksa.

CI juga menjalankan [scripts/ci_runtime.py](../scripts/ci_runtime.py) dengan masing-masing `--profile production` dan `--profile candidate`. Script membuat workspace sementara Windows, menjalankan setup worker nyata, mengimpor seluruh paket terkunci, memeriksa exact version/x64/GIL/lokasi managed, lalu mengulang setup untuk membuktikan reuse penanda siap. Tidak ada browser akun atau capture live. Script membutuhkan `RUNNER_TEMP` dari lingkungan CI dan tidak dimaksudkan sebagai launcher pekerjaan Coretax pengguna.

## Gate promosi menjadi produksi

Promosi ke Python 3.14 baru dapat diputuskan setelah bukti berikut tersedia pada commit kandidat yang sama:

| Gate | Bukti yang harus diperiksa |
| --- | --- |
| Resolusi dan supply chain | Semua lock cocok dengan input; hash/wheel tersedia untuk Windows x64 kedua profil; audit dependency berhasil. |
| Logika portable | Scope, preservasi data, export/rollback, event, dan tes runtime sintetis lulus. |
| Browser | Playwright dan dependency native mengimpor serta menjalankan Edge fixture, termasuk provenance, binding login, paginasi, dan pembatalan. |
| GUI/native Windows | Tk tersedia, form/Stop bekerja pada fixture, Known Folder dan Job Object memenuhi kontrak. |
| Bootstrap worker nyata | Fresh managed install dan reuse tervalidasi pada profil kandidat tanpa akun. |
| Packaging | Source self-test dan frozen self-test lulus, interpreter/profil/resource/Tcl/Tk benar, exact artifact dibaca kembali. |
| Penerimaan mesin target | Checklist Windows, login berizin, scope SPT yang disepakati, dan Excel aktual selesai atau keterbatasannya dinyatakan. |
| Keputusan rilis | Default worker/build, pin, fingerprint, label artifact, dokumentasi, dan langkah kembali ke produksi lama diubah bersama setelah review. |

Klasifikasi dukungan Python pada halaman package adalah petunjuk untuk penelitian, bukan pengganti gate aplikasi. Lihat [catatan perubahan PyInstaller](https://pyinstaller.org/en/stable/CHANGES.html), [Playwright 1.63.0](https://pypi.org/project/playwright/1.63.0/), [greenlet 3.5.6](https://pypi.org/project/greenlet/3.5.6/), dan [build Windows python-build-standalone](https://github.com/astral-sh/python-build-standalone/blob/main/cpython-windows/build.py) saat mengevaluasi dependency/runtime.

Jika satu gate gagal, perbaiki ketidakcocokan spesifik dan ulangi bagian yang relevan. Jangan meloloskan matrix kandidat dengan mengabaikan kegagalan atau mengubah default pengguna sebelum bukti lengkap. Simpan artifact produksi yang telah diverifikasi untuk pemulihan; kembali ke versi sebelumnya tidak boleh menimpa profil atau hasil pajak secara sembarang.

## Batas yang tetap memerlukan tindakan eksternal

Kesiapan kode dan CI bukan bukti bahwa ruleset repository sudah aktif, executable memiliki Authenticode, atau portal aktual sudah diuji. Aktivasi ruleset memerlukan admin repository yang terautentikasi. Signing memerlukan identitas/sertifikat penerbit yang dikelola maintainer. Acceptance live memerlukan operator dan NPWP/tahun yang memang diizinkan. Ketiganya dicatat terpisah dari status matrix; lihat [CI dan rilis](ci-dan-rilis.md) serta [penerimaan manual](penerimaan-manual.md).
