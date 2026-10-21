# Evaluasi dua shard Windows setelah optimasi fixture

## Tujuan dan baseline

Evaluasi ini melanjutkan prioritas 3 dari optimasi CI Windows: menjalankan seluruh
suite pada dua runner Windows terisolasi, lalu mempertahankan seluruh pemeriksaan
inventory dan package. Prioritas 1 dan 2 sudah masuk `main` melalui PR #63/#65.

Baseline aplikasi: `a7d742ea887dffe7c37af04a2bd6cfcbfe69af63`. Run produksi
[39570265038](https://github.com/cepeter-job/spt-downloader/actions/runs/39570265038)
lulus dengan 3.409 tes Windows dan 456 tes portable. Sesi pytest Windows tercatat
1.127,276 detik; workflow lengkap 21 menit 1 detik. Ini satu pengamatan, bukan median
atau jaminan durasi.

## Perubahan yang dievaluasi

Workflow build yang sama menyediakan pilihan manual `serial` dan `two-shards`,
agar kedua mode menjalankan package dan pemeriksaan yang sama pada satu commit.
Default produksi tetap serial selama pengumpulan bukti. Setiap shard memakai satu
proses pytest pada runner `windows-2022` tersendiri; tidak memakai `xdist`.

Package harus membaca manifest asli tiap shard dan membuktikan identitas commit,
Python, run, attempt, hasil sukses, partisi deterministik, serta gabungan seluruh
tes yang sama dengan collector portable. Manifest gabungan buatan tidak dapat
menggantikan pemeriksaan bukti tersebut. Pemeriksaan managed worker, source/frozen
GUI, checksum, allowlist lima file dan artifact readback berdasarkan ID tetap ada.
Attestation tetap terbatas pada push `main` yang dipercaya.

## Pengukuran dan keputusan

Status pilot: implementasi disiapkan pada PR #66 dan menunggu verifikasi GitHub.
Pengukuran pipeline lengkap belum selesai; belum ada keputusan adopsi.
Benchmark fase tes baseline berjalan pada
[39579737580](https://github.com/cepeter-job/spt-downloader/actions/runs/39579737580).

1. Bekukan satu commit kandidat setelah regresi dan kontrak workflow lulus.
2. Jalankan sedikitnya lima pasangan serial versus dua shard pada commit itu.
3. Catat hasil cache aktual, antrean, setup, pytest, managed worker, build,
   upload/readback, pemeriksaan akhir dan jumlah runner-seconds; simpan kegagalan
   serta pembatalan bersama hasil sukses.
4. Evaluasi target median waktu pipeline lengkap turun sedikitnya 20%, dengan
   inventory lengkap, hasil konsisten dan biaya runner yang dinyatakan.
5. Adopsi default dua shard hanya setelah bukti mendukung, lalu validasi commit
   akhir dan package-nya melalui GitHub Actions.

Perbandingan dispatch mencakup pipeline sampai package terverifikasi dan check
gabungan. Attestation push `main` tidak berjalan pada dispatch dan harus diverifikasi
tersendiri jika perubahan kemudian digabungkan. Mode cache `restore` bukan bukti
cache hit; pisahkan hasil berdasarkan nilai cache aktual dan pengukuran cold.

Benchmark lama `windows-shard-benchmark.yml` tetap berguna untuk waktu fase tes,
tetapi tidak membuktikan durasi lengkap sampai package. Reuse proses browser dan
penggantian sleep fixture pada prioritas 4 berada di luar perubahan ini.
