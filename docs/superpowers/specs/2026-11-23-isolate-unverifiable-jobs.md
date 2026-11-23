# Isolasi job yang gagal diverifikasi dalam inventaris pembersihan manual

**Status: usulan + implementasi pada PR ini; belum di-merge.** PR ini tidak
mengubah kontrak penghapusan otomatis, tidak menyentuh data job nyata, dan
tidak menjalankan scrape live.

## Latar dan bukti

Review pembersihan job 23 November 2026 mencatat dua `run.json` berukuran
44,9 MiB dan 58,0 MiB. Pemeriksaan source pada `origin/main` (`717ef88`)
mengonfirmasi batas baca metadata:

- `spt_desktop/job_maintenance.py:93-94` membaca `run.json` dengan
  `max_bytes=16 * 1024 * 1024`.
- `spt_desktop/job_pruning.py:237,306` memakai batas yang sama untuk seal dan
  penghapusan PUBLISHED otomatis.
- `inspect_job_storage()` menandai `scan_complete=False` bila *job mana pun*
  gagal dibaca, lalu mengosongkan `removable` secara keseluruhan
  (`job_maintenance.py:178-182`).
- UI `_remove_incomplete_jobs` menghentikan pembersihan bila
  `scan_complete=False` (`app.py:730-734`), sehingga satu job berukuran besar
  menghalangi semua kandidat PARTIAL/FAILED lain yang sebenarnya terverifikasi.

Storage KRUCIL saat implementasi sudah berisi 4 job bersegel (pembersihan manual oleh
pemilik), jadi angka 39 job pada review bukan snapshot berjalan. Perbaikan ini
ditujukan pada sifat kode yang tetap dapat terulang, bukan pada data lama.

## Perilaku yang diubah

1. `inspect_job_storage()` tetap menghitung `scan_complete=False` bila ada job
   yang tidak dapat diverifikasi, tetapi **tidak lagi mengosongkan** `removable`.
   Kandidat yang berhasil melewati seluruh pemeriksaan tetap dikembalikan.
2. Job yang gagal dibaca/dipindai tetap dihitung sebagai `protected`; tidak ada
   status, ukuran, atau izin hapus yang ditebak dari metadata yang gagal dibaca.
3. UI pembersihan PARTIAL/FAILED tetap menampilkan peringatan bahwa sebagian
   job tidak terverifikasi dan tetap dilindungi, lalu memperlihatkan hanya
   kandidat terverifikasi untuk dipilih. Tanpa kandidat, alur lama tetap
   berhenti dengan pesan inventaris belum lengkap.
4. `delete_incomplete_jobs()` tidak berubah: setiap approval diverifikasi ulang
   (marker terminal, status, recovery, seal, digest snapshot, job aktif) tepat
   sebelum penghapusan native. Persetujuan eksplisit dan konfirmasi default-No
   tetap wajib.

## Yang tidak berubah

- Auto-clean (`prune_published_jobs` / `preview_published_jobs`) tetap
  fail-closed: `scan_complete=False` tetap menghalangi penghapusan COMPLETE.
- Batas 16 MiB, `MAX_KEEP_JOBS`, retensi `keep_jobs`, dan verifikasi publikasi
  Downloads tidak dilonggarkan. Job COMPLETE dengan folder publikasi hilang
  tetap dilindungi (P1, di luar lingkup PR ini).
- Tidak ada event diagnostik baru pada PR ini (P1, terpisah).
- Tidak ada perubahan pada file hasil ekspor di Downloads.

## Pengujian

Tes sintetik offline: satu job dengan `run.json` melebihi batas bersama satu
PARTIAL yang valid; pastikan `scan_complete=False`, `removable` berisi hanya
job valid, job besar tetap ada, dan penghapusan approval hanya menghapus job
valid. Tes UI: inventaris sebagian dengan kandidat membuka picker setelah
peringatan; inventaris sebagian tanpa kandidat tetap berhenti. Hosted CI tetap
menjadi otoritas untuk shards penuh.
