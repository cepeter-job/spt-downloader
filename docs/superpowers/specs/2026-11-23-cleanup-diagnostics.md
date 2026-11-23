# Diagnostik pembersihan job: PARTIAL/FAILED dan auto-clean nol

**Status: usulan + implementasi pada PR ini; belum di-merge.**

## Latar

Pada `origin/main` (`4567dd5`), event yang terdaftar hanya `jobs.pruned`,
`jobs.prune_preview`, dan `jobs.manual_pruned`. Tidak ada catatan untuk
pembersihan manual PARTIAL/FAILED, dan auto-clean yang menghapus nol job
tidak menghasilkan event sama sekali. Log tidak bisa menjawab berapa job
dipilih, berapa berhasil, berapa ditolak, atau mengapa auto-clean tidak
menghapus apa pun.

## Perilaku yang diusulkan

1. `jobs.incomplete_cleanup` mencatat tiga counter: `selected`, `removed`,
   dan `rejected` (= `selected - removed`, jumlah **job** yang ditolak, bukan
   jumlah baris alasan). Event ini dipancarkan sekali setelah konfirmasi dan
   penghapusan sederhana selesai, bukan saat pratinjau.
2. `jobs.incomplete_rejected` mencatat satu field enum `reason` tanpa ID job,
   path, atau pesan bebas. Kategori: `active`, `unknown`, `global_recovery`,
   `deadline`, `seal_or_recovery`, `no_terminal`, `wrong_status`, `recovery`,
   `changed`, `error`, `disabled`. Tidak ada kategori agregat
   `partial_delete`: keadaan sebagian dinyatakan oleh `removed < selected`
   dan `incomplete`, bukan oleh alasan per job.
3. `delete_incomplete_jobs(..., report_reasons=True)` mengembalikan field
   tambahan `rejected` berupa tuple kategori; pemanggil lama tanpa opsi ini
   tetap menerima bentuk hasil yang sama persis.
4. `jobs.prune_attempt` dicatat oleh `prune_published_jobs()` untuk setiap
   pemanggilan, termasuk ketika `removed == 0`. Field: `removed`, `eligible`,
   dan enum `reason`: `removed`, `no_candidates`, `no_eligible_candidates`,
   `verification_failed`, `disabled`. Pemanggilan manual dengan
   `allowed_ids=()` juga tercatat sebagai `no_candidates`.
5. Semua field baru masuk allowlist COUNTERS/ENUMS di `diagnostics.py` dan
   didokumentasikan di `docs/diagnostik.md`. Tidak ada field yang membawa
   nilai, path, ID job, atau alasan bebas.

## Yang tidak berubah

- Tidak ada ambang penghapusan, verifikasi publikasi, retensi, atau segel yang
  diubah. Tidak ada job COMPLETE tanpa bukti publikasi yang dihapus.
- `jobs.pruned`, `jobs.prune_preview`, `jobs.manual_pruned` tetap dipancarkan
   seperti sebelumnya.
- Pemicu startup auto-clean (PR terpisah) tidak diubah di PR ini; karena
  pencatatan berada di dalam `prune_published_jobs()`, kedua pemicu akan
   tercatat setelah PR tersebut di-merge.

## Pengujian

Tes offline: alasan penolakan untuk snapshot yang berubah; event
`jobs.incomplete_cleanup` + `jobs.incomplete_rejected` pada alur UI; serta
`jobs.prune_attempt` dengan `removed=0` dan alasan `no_eligible_candidates`.
Hosted CI tetap menjadi otoritas seluruh shard.
