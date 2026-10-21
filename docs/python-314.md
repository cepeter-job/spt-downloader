# Kebijakan produksi CPython 3.14

[Kembali ke dokumentasi](README.md)

Panduan ini memiliki tabel pin, aturan lock, migrasi dan rollback. Untuk perintah setup/test/build gunakan [pengembangan](pengembangan.md); untuk hasil pipeline dan byte distribusi gunakan [verifikasi artifact](ci-dan-rilis.md#memverifikasi-artifact).

## Versi yang didukung

| Komponen | Pin produksi | Kontrak |
| --- | --- | --- |
| GUI dan executable Windows | **CPython 3.14.8**, Windows x64, GIL aktif | Satu profil: `production`. |
| Worker di mesin pengguna | **Managed CPython 3.14.8**, Windows x64, GIL aktif | Dibuat oleh `uv` di LocalAppData, bukan Python sistem. |
| CLI `setup.cmd` | **Managed CPython 3.14.8**, Windows x64, GIL aktif | Versi sama dengan GUI/worker. |
| `uv` | **0.13.4** | Exact pin untuk katalog managed Python, build, dan instalasi lock. |

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

### Memperbarui dependensi dan lock

Semua versi langsung dipin dan lock transitif menggunakan hash SHA-256. Resolusi universal dan persyaratan wheel tidak dilonggarkan hanya karena Python baru. Jika memutakhirkan paket, perbarui keempat lock dengan [scripts/update_locks.py](../scripts/update_locks.py) dan review perubahan secara terpisah. Gunakan `uv==0.13.4`:

```powershell
.venv/Scripts/python.exe -m scripts.update_locks --check
uv pip sync --python .venv/Scripts/python.exe --require-hashes --only-binary :all: locks/build.txt
```

Untuk pembaruan lock yang memang disetujui, jalankan `python -m scripts.update_locks` lalu `--check`; gunakan `--upgrade` hanya ketika versi transitif perlu dinaikkan dengan sengaja. Hash memastikan kesesuaian paket, bukan ketiadaan advisory; pemeriksaan keamanan tetap wajib.

`playwright==1.64.0` memakai `pyee==14.0.0` pada profil produksi CPython 3.14.8. Regenerasi lock menggunakan versi produksi yang tepat supaya tidak menyertakan cabang Python 3.11 yang sudah tidak didukung, tetapi tetap memakai resolusi universal, wheel saja, dan hash SHA-256.

## Verifikasi produksi

Ikuti [setup Windows](pengembangan.md#setup-windows-dengan-powershell),
[workload tes](pengembangan.md#pengujian-lokal), dan [build source/frozen](pengembangan.md#membuat-executable-windows).
Untuk portable saja gunakan [setup Linux](pengembangan.md#linux-atau-container).
Contoh-contoh itu tetap tunduk pada batas eksekusi [AGENTS.md](../AGENTS.md#verification).
Jangan menyalin daftar perintah kedua ke sini ketika memperbarui pin.

Perubahan toolchain juga memerlukan `scripts.ci_runtime --profile production`
melalui interpreter environment build. Pemeriksaan ini menguji fresh managed
install dan ready-state reuse tanpa akun, memakai direktori scratch `RUNNER_TEMP`
milik job Windows. Penanda readiness saja bukan bukti interpreter/paket masih benar.

CI mengikat suite Windows lengkap, subset portable, lock/audit, bootstrap worker,
source/frozen dan artifact readback pada commit yang sama. Linux tidak membuktikan
Tk/Edge, API Windows atau rollback native. Kriteria artifact lengkap dijelaskan
sekali pada [CI dan rilis](ci-dan-rilis.md#memverifikasi-artifact).

## Batas dan langkah kembali

Migrasi teknis tidak sama dengan penerimaan pada portal Coretax aktual. Fixture Edge, self-test GUI, dan workbook sintetis tidak membuktikan akses, login, atau hasil SPT nyata. Penerimaan Windows dan Coretax berizin tetap mengikuti [checklist manual](penerimaan-manual.md), dan boleh dilakukan setelah fitur/UI lain digabung.

Rollback hanya memakai artifact yang telah dipilih dan diverifikasi secara eksplisit untuk scope pemulihan; periksa commit, checksum, kompatibilitas output dan batas fiturnya. Artifact 3.11.17 pada [PR #6](https://github.com/cepeter-job/spt-downloader/pull/6) adalah bukti historis migrasi, bukan rekomendasi otomatis untuk instalasi sekarang atau jaminan unduhannya masih tersedia. Tidak ada profil 3.11 pada build aktif. Hentikan semua job sebelum beralih executable; jangan menyalin environment siap, menghapus profil/hasil/checkpoint, atau mengganti berkas pajak untuk memaksa downgrade.

Executable tidak otomatis memiliki tanda tangan Authenticode. Provenance/checksum tidak menggantikan sertifikat penerbit. Aturan branch, tanda tangan code, dan penerimaan data nyata adalah gate yang berbeda dari keberhasilan unit/CI.
