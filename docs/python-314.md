# Kebijakan produksi CPython 3.14

[Kembali ke dokumentasi](README.md)

## Versi yang didukung

| Komponen | Pin produksi | Kontrak |
| --- | --- | --- |
| GUI dan executable Windows | **CPython 3.14.8**, Windows x64, GIL aktif | Satu profil: `production`. |
| Worker di mesin pengguna | **Managed CPython 3.14.8**, Windows x64, GIL aktif | Dibuat oleh `uv` di LocalAppData, bukan Python sistem. |
| CLI `setup.cmd` | **Managed CPython 3.14.8**, Windows x64, GIL aktif | Versi sama dengan GUI/worker. |
| `uv` | **0.13.0** | Exact pin untuk katalog managed Python, build, dan instalasi lock. |

Sumber kebenaran adalah `PYTHON_PROFILES`, `UV_VERSION`, `RUNTIME_LOCK`, dan `WORKER_FILES` di [spt_desktop/runtime.py](../spt_desktop/runtime.py). Profil evaluasi `candidate` telah dipensiunkan: tidak boleh menjadi jalur distribusi atau cara diam-diam memilih 3.11. `build_desktop.py`, pemilih matrix `scripts/ci_route.py`, uji worker `scripts/ci_runtime.py`, serta `setup.cmd` memakai satu versi produksi.

Perubahan ini menggantikan profil produksi lama **3.11.17**. Dokumen plan/audit terdahulu boleh tetap mencatat versi saat eksperimen tersebut dilakukan, tetapi tidak menentukan versi distribusi baru.

Tepat versi patch, CPython, 64-bit, dan GIL aktif wajib dibuktikan. Versi minor saja, interpreter free-threaded, build 32-bit, atau Python sistem yang tersedia di PATH bukan substitusi. `uv` memakai kunci unduhan `cpython-3.14.8-windows-x86_64-none`; saat menemukan interpreter terpasang gunakan request `3.14.8+gil`. Request unduhan dan pencarian tersebut tetap eksplisit; [default Python 3.15 pada uv 0.13.0](https://github.com/astral-sh/uv/releases/tag/0.13.0) tidak mengganti pin produksi aplikasi. Distribusi managed tetap diverifikasi lewat metadata interpreter, bukan hanya nama paket unduhan.

## Migrasi mesin yang sudah memiliki Python 3.11

Tidak perlu menghapus `%LOCALAPPDATA%\\SPTDownloader`, profil browser, checkpoint, atau berkas hasil pajak. Jalankan executable produksi 3.14.8 yang dihasilkan oleh CI sesuai petunjuk [verifikasi artifact](ci-dan-rilis.md#memverifikasi-artifact). Saat aplikasi membutuhkan worker:

1. `ensure_runtime` memeriksa byte sumber worker, lock, versi Python, dan uv, lalu menguji ulang interpreter nyata, versi paket, arsitektur, status GIL, dan lokasi interpreter managed.
2. Worker lama 3.11.17 **tidak** memenuhi profil baru, walaupun file `runtime-ready.txt` masih ada. Penanda siap lama ditolak; worker environment dalam `runtime` dibentuk ulang memakai 3.14.8 dengan `uv venv --clear`.
3. Dependensi diinstal ulang dari `locks/runtime.txt` dengan hash SHA-256 dan wheel saja. Penanda siap baru dibuat **setelah** seluruh verifikasi lolos.
4. Kegagalan/Stop tidak dianggap siap; setup bisa dicoba ulang. Perubahan worker tidak boleh menyingkirkan profil, checkpoint, export, ataupun recovery yang tersimpan di direktori lain.

Pekerjaan yang sudah berjalan sebaiknya diselesaikan atau dihentikan secara normal sebelum mengganti executable. Jangan menjalankan GUI lama dan baru untuk pekerjaan pengguna yang sama secara bersamaan. Perlu koneksi ke unduhan Python/dependensi pada penggunaan pertama setelah promosi.

## Dependensi dan lock

| Input | Lock yang diverifikasi | Tujuan |
| --- | --- | --- |
| `requirements.txt` | `locks/runtime.txt` | Runtime Playwright/openpyxl dan transitif worker. |
| `requirements-test.txt` | `locks/test.txt` | Dependensi suite sintetis. |
| `requirements-build.txt` | `locks/build.txt` | PyInstaller, uv dan seluruh persyaratan build. |
| `requirements-audit.txt` | `locks/audit.txt` | Tool audit terisolasi. |

Semua versi langsung dipin dan lock transitif menggunakan hash SHA-256. Resolusi universal dan persyaratan wheel tidak dilonggarkan hanya karena Python baru. Jika memutakhirkan paket, perbarui keempat lock dengan [scripts/update_locks.py](../scripts/update_locks.py) dan review perubahan secara terpisah. Gunakan `uv==0.13.0`:

```powershell
.venv/Scripts/python.exe -m scripts.update_locks --check
uv pip sync --python .venv/Scripts/python.exe --require-hashes --only-binary :all: locks/build.txt
```

Untuk pembaruan lock yang memang disetujui, jalankan `python -m scripts.update_locks` lalu `--check`; gunakan `--upgrade` hanya ketika versi transitif perlu dinaikkan dengan sengaja. Hash memastikan kesesuaian paket, bukan ketiadaan advisory; pemeriksaan keamanan tetap wajib.

`playwright==1.63.0` [mensyaratkan `pyee>=13,<14`](https://github.com/microsoft/playwright-python/blob/v1.63.0/pyproject.toml), sehingga ketiga lock runtime/test/build tetap memakai `pyee==13.0.1`. Pembaruan ke pyee 14 harus menunggu versi Playwright yang mengizinkannya, lalu melewati resolusi lock dan seluruh gate CI; jangan melonggarkan constraint hanya agar pembaruan transitif dapat dipasang.

## Verifikasi produksi

Pada Windows x64, instal `uv` sesuai pin, lalu dari checkout:

```powershell
uv python install cpython-3.14.8-windows-x86_64-none --no-bin --no-registry
uv venv --managed-python --python 3.14.8+gil .venv
uv pip sync --python .venv/Scripts/python.exe --require-hashes --only-binary :all: locks/build.txt
.venv/Scripts/python.exe -m scripts.update_locks --check
.venv/Scripts/python.exe -m pytest tests -p scripts.ci_tests --ci-workload windows -q --basetemp "$env:TEMP/spt314-tests"
.venv/Scripts/python.exe -m scripts.ci_runtime --profile production
.venv/Scripts/python.exe spt_gui.py --self-test --report "$env:TEMP/spt314-source.json"
.venv/Scripts/python.exe build_desktop.py --python-profile production --output dist
```

`scripts.ci_runtime` membutuhkan `RUNNER_TEMP` pada CI Windows untuk menjalankan bootstrap terisolasi, uji **fresh managed install** dan **ready-state reuse** tanpa akun. Untuk mesin lokal, atur `RUNNER_TEMP` pada direktori scratch yang aman atau gunakan hasil smoke resmi CI. `--basetemp` dapat dibersihkan pytest: jangan arahkan ke folder pengguna yang berisi data.

Di Linux untuk pengujian portable saja:

```bash
uv python install cpython-3.14.8-linux-x86_64-gnu --no-bin --no-registry
uv venv --managed-python --python 3.14.8+gil .venv
uv pip sync --python .venv/bin/python --require-hashes --only-binary :all: locks/test.txt
.venv/bin/python -m pytest tests -p scripts.ci_tests --ci-workload portable -q --basetemp /tmp/spt314-portable-tests
```

CI memakai **satu** entri matrix production 3.14.8 untuk Linux portable, Windows keseluruhan suite, fresh/reused worker, audit terkunci, source/frozen GUI, packaging, pemeriksaan checksum, dan pembacaan kembali artifact berdasarkan ID. Setiap gate harus lulus pada commit yang sama. Runtime Windows/Tk/Edge dan rollback sistem berkas tidak dapat disertifikasi oleh Linux saja. Lihat [CI dan rilis](ci-dan-rilis.md).

## Batas dan langkah kembali

Migrasi teknis tidak sama dengan penerimaan pada portal Coretax aktual. Fixture Edge, self-test GUI, dan workbook sintetis tidak membuktikan akses, login, atau hasil SPT nyata. Penerimaan Windows dan Coretax berizin tetap mengikuti [checklist manual](penerimaan-manual.md), dan boleh dilakukan setelah fitur/UI lain digabung.

Jika build 3.14 bermasalah pada mesin pengguna, gunakan **artifact produksi 3.11.17 yang sebelumnya telah diverifikasi** sebagai jalur pemulihan sementara—misalnya [hasil PR #6, commit c036135](https://github.com/cepeter-job/spt-downloader/actions/runs/38240317586/artifacts/11741888300). Cocokkan SHA, artifact ID, dan checksum sebelum menjalankannya. GUI lama akan meminta worker managed 3.11.17 dan membentuk ulang environment runtime jika perlu; jangan menyalin ulang environment siap, menghapus profil/hasil/checkpoint, atau mengganti file pajak sebagai cara downgrade. Hentikan semua job sebelum beralih versi.

Executable tidak otomatis memiliki tanda tangan Authenticode. Provenance/checksum tidak menggantikan sertifikat penerbit. Aturan branch, tanda tangan code, dan penerimaan data nyata adalah gate yang berbeda dari keberhasilan unit/CI.
