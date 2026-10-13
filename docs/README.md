# Dokumentasi development

Panduan ini ditujukan bagi kontributor SPT Downloader. Untuk menjalankan aplikasi atau memulihkan hasil CLI, baca [README utama](../README.md). Baca juga [instruksi repositori](../AGENTS.md) sebelum mengubah kode.

## Mulai dari kebutuhan Anda

| Kebutuhan | Panduan |
| --- | --- |
| Menyiapkan checkout Windows dengan `uv`, menjalankan tes, membuat build | [Pengembangan](pengembangan.md) |
| Menulis teks antarmuka, merancang layar, atau menyiapkan fitur baru | [Panduan UI/UX desain B](ui-ux/README.md) |
| Memahami batas GUI/worker, akses baca Coretax, identitas, ekspor, dan Stop | [Arsitektur](arsitektur.md) |
| Memahami job CI, biaya CPU, cache, check wajib, dan artifact | [CI dan rilis](ci-dan-rilis.md) |
| Memperbarui dependensi atau produksi Python 3.14 | [Kebijakan Python dan kompatibilitas](python-314.md) |
| Menjalankan pemeriksaan Coretax aktual dengan izin yang sesuai | [Penerimaan manual](penerimaan-manual.md) |
| Menangani kegagalan setup, browser, output, atau CI | [Pemecahan masalah](pemecahan-masalah.md) |
| Menelusuri alasan perbaikan keamanan sebelumnya | [Audit 12 Oktober 2026](audit-2026-10-12.md) |

Urutan yang disarankan untuk kontributor baru: setup dan tes portable, arsitektur area yang akan diubah, tes Windows yang relevan, kemudian aturan PR/CI. Jangan mencoba akun nyata untuk membuat tes otomatis lulus.

Untuk perubahan antarmuka, arah yang dipilih adalah desain B dengan Tkinter/ttk. Dahulukan kejelasan proses dan hasil; ikuti panduan bahasa serta checklist fitur sebelum menambah layar atau tombol. Panduan desain bukan bukti bahwa redesign sudah diterapkan.

## Sumber kebenaran

Versi, daftar resource, dan pemilihan tes harus mengikuti kode pada commit yang sedang ditinjau. Perintah pada dokumentasi merupakan contoh yang harus tetap selaras dengan sumber berikut.

| Kontrak | Sumber |
| --- | --- |
| Profil interpreter, `uv`, pemeriksaan runtime, dan allowlist worker | [runtime.py](../spt_desktop/runtime.py) dan kebijakan toolchain yang dipakainya |
| Dependensi langsung dan hasil resolusi dengan hash | `requirements*.txt` dan direktori `locks/` |
| Pemisahan tes portable/Windows | [scripts/ci_tests.py](../scripts/ci_tests.py) |
| Keputusan perubahan dokumentasi atau kode | [scripts/ci_route.py](../scripts/ci_route.py) |
| Pemicu, dependency antar-job, cache, dan artifact | [windows-build.yml](../.github/workflows/windows-build.yml) |
| Persyaratan build dan frozen self-test | [build_desktop.py](../build_desktop.py) |

Dokumen audit dan desain bertanggal menyimpan keadaan saat dibuat. Persyaratan aktif dijelaskan dalam panduan di atas; riwayat tersebut tidak menjadi bukti bahwa check repo, penerimaan portal nyata, atau penandatanganan executable sudah dilakukan.
