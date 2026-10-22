# Tindak lanjut audit eksternal 22 Oktober 2026

Audit eksternal diperiksa terhadap upstream
[`44969fcd73534153f5b656ec5ee9f5c8f11f42f4`](https://github.com/cepeter-job/spt-downloader/commit/44969fcd73534153f5b656ec5ee9f5c8f11f42f4).
Build `main` [39728441622](https://github.com/cepeter-job/spt-downloader/actions/runs/39728441622)
berhasil setelah PR #72 digabung. Catatan ini memisahkan perubahan repository,
pengaturan yang benar-benar dibaca, dan bukti operasional yang masih diperlukan.

## Pengaturan yang diverifikasi

Pemeriksaan administratif pada 22 Oktober 2026 menemukan hasil berikut. Angka
alert adalah snapshot saat pemeriksaan, bukan jaminan tidak ada temuan baru.

| Kontrol | Hasil pemeriksaan |
| --- | --- |
| Private vulnerability reporting | Semula nonaktif; diaktifkan dan dibaca ulang sebagai `enabled: true`. |
| Dependabot alerts | Aktif; endpoint pemeriksaan mengembalikan HTTP 204. Tidak ada alert terbuka. |
| Dependabot security updates | Sudah aktif. |
| Secret scanning dan push protection | Keduanya sudah aktif. Tidak ada alert secret scanning terbuka. |
| CodeQL | Default setup untuk Python dan Actions, query suite `default`; tidak ada alert terbuka. |
| Izin default Actions | `read`; `GITHUB_TOKEN` workflow tidak diizinkan memberi approval PR. |
| Registrasi workflow lama | Enam workflow tanpa berkas pada semua branch saat pemeriksaan dinonaktifkan; readback masing-masing `disabled_manually`. |

Registrasi yang dinonaktifkan adalah `browser-fixture-profile.yml`,
`p2-dialog-evidence.yml`, `p2-performance-evidence.yml`,
`pr20-50-reconciliation-evidence.yml`, `sso-fixture-diagnostic.yml`, dan
`t5-native-visual-probe.yml`. Tidak ada run aktif saat penonaktifan. Riwayat run
tetap disimpan. Workflow UI yang masih ada pada branch pekerjaan, build produksi,
promosi release, serta benchmark manual tetap tersedia.

Preferensi notifikasi akun, penerimaan email/web yang nyata, maintainer cadangan,
dan pemeriksaan form dari akun pelapor eksternal belum diverifikasi. Koneksi
administratif tidak mempunyai akses notifikasi akun; tidak ada perluasan scope
credential otomatis. Gunakan [prosedur notifikasi dalam SECURITY.md](../../SECURITY.md#notifikasi-dan-bukti-penerimaan)
untuk menutup bukti tersebut. Pengaturan scanning aktif tidak membuktikan bahwa
seseorang menerima atau menindaklanjuti notifikasinya.

## Perubahan repository dan batas penerimaan

PR tindak lanjut menambah lint nama Python yang tidak terdefinisi, laporan coverage
subset portable tanpa ambang persentase, serta capture eksplisit variabel callback
self-test GUI. Dependensi alat dipin dan memakai hash; pemeriksaan kesegaran lock,
inventory lengkap, kedua shard Windows, packaging, serta provenance tetap menjadi
gate. Tes mutasi workflow menolak penghilangan lint, pemilihan tes yang berubah,
exit yang disembunyikan, laporan hilang, dan path artifact yang terlalu luas.

Hasil runner pada head PR adalah bukti penerimaan perubahan ini. AST, pembacaan
source, dan pemeriksaan hash lokal tidak menggantikan pytest, self-test, build,
atau eksekusi EXE pada GitHub runner.

Percobaan kandidat release pertama,
[39734888768](https://github.com/cepeter-job/spt-downloader/actions/runs/39734888768),
memakai `publish=false` dan gagal saat mengunduh ZIP sebelum verifikasi signature.
Probe read-only atas artifact yang sama mereproduksi HTTP 415 untuk header
`Accept: application/octet-stream`. Header `application/vnd.github+json`
berhasil mengunduh 28.631.766 byte dengan SHA-256
`0c169e36bfb2dd6b3ac1045676359e155c5938983ce69697869a42d601b245c2`,
sesuai metadata artifact sumber. Endpoint Actions dan endpoint asset release
memerlukan perlakuan media yang berbeda; header biner tetap diperlukan untuk
asset release, sesuai [dokumentasi Actions](https://docs.github.com/en/rest/actions/artifacts#download-an-artifact)
dan [asset release](https://docs.github.com/en/rest/releases/assets#get-a-release-asset).

Kegagalan pertama tidak menghasilkan release atau tag. Bukti penerimaan perbaikan
harus mencakup run verifikasi nyata dan readback artifact kandidat; koordinat hasil
terakhir dicatat pada [checklist PR #75](https://github.com/cepeter-job/spt-downloader/pull/75).
Publikasi serta penerimaan live tetap mempunyai bukti terpisah.

## Disposisi temuan eksternal

| Temuan | Tindak lanjut |
| --- | --- |
| U-1: jalur disclosure tidak aktif | Pengaturan diperbaiki; bukti akun pelapor dan notifikasi tetap terbuka. |
| U-2: distribusi sementara | Kandidat memakai sumber `main` yang persis; belum dianggap terbit hanya karena workflow tersedia. |
| U-3: tidak ada approval independen | Memerlukan reviewer kedua yang memenuhi izin dan menyetujui peran. Tidak menambah gate yang tidak dapat dipenuhi. |
| U-4: kontrol administratif tidak diketahui | Status scanning, alert, dan izin Actions telah diperiksa; pengiriman notifikasi dan cadangan masih terbuka. |
| U-5: biaya CI dan branch WIP | Pembatalan push sudah ada pada workflow kandidat; kegagalan WIP tidak disamakan dengan kegagalan `main`. |
| U-6: workflow lama dan CodeQL | Enam registrasi lama dinonaktifkan. Default setup CodeQL dipertahankan setelah konfigurasi diverifikasi. |
| U-7: lint dan coverage | Perubahan terfokus dalam PR; tidak melakukan format ulang atau refactor massal demi metrik. |
| U-8: kepemilikan dukungan | Identitas orang tidak disimpulkan dari alamat email/handle. Kontak aplikasi yang disetujui dipertahankan. |
| U-9: Authenticode | Identitas signing resmi masih diperlukan sesuai kebijakan distribusi. |
| U-10: berkas komunitas | Informasional; panduan kontributor tersedia melalui README dan indeks docs. |
| U-11: referensi nama repository | Informasional; perubahan menunggu kebutuhan transfer atau rename yang nyata. |
| U-12: hygiene campuran | Capture lambda diperjelas; fixture workbook independen dipertahankan; update versi dinilai dari kompatibilitas/advisory. |

`WORKER_FILES` berisi 43 elemen, termasuk `RUNTIME_LOCK`. Artifact benchmark
berumur 7 hari, bukan 14 hari seperti distribusi. Fixture workbook yang identik
memiliki hash referensi dan pemeriksaan kesamaan terhadap resource produksi;
menghapus salinan referensi tanpa pengganti akan mengurangi independensi tes.

Tidak ditemukannya pola secret atau telemetry dalam audit statis bukan bukti
ketiadaannya secara universal. SBOM menginventaris native bytes; audit paket
Python tidak mengaudit kerentanan semua komponen native. Lima prasyarat di luar
PR mengacu pada [peta remediasi](2026-10-22-devops-remediation.md#controls-requiring-evidence-outside-this-pr).
