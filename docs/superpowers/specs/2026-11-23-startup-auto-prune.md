# Pemeriksaan auto-clean saat startup GUI

**Status: usulan + implementasi pada PR ini; belum di-merge.**

## Latar dan bukti

Pada `origin/main` (`4567dd5`), satu-satunya pemicu auto-clean adalah
`JobController._finish()` (`spt_desktop/controller.py:325-339`), yaitu setelah
worker selesai. `App.__init__()` (`spt_desktop/app.py:257-260`) hanya menjadwalkan
`_refresh_storage()`, yang bersifat read-only. Jika aplikasi dibuka ulang dalam
keadaan sudah ada job lama yang memenuhi syarat (misalnya worker pernah gagal
dimulai atau aplikasi ditutup sebelum `worker.finished`), tidak ada pemeriksaan
auto-clean sampai jobs baru selesai.

## Perilaku yang diusulkan

1. Setelah jendela GUI dibangun, App menjadwalkan satu pemeriksaan auto-clean
   asynchronous pada event loop Tk. Pemeriksaan hanya berjalan untuk App yang
   benar-benar memiliki `JobController` (bukan self-test dengan controller
   sintetik).
2. Thread **non-daemon** memanggil `prune_published_jobs(workspace, downloads,
   keep_jobs, exclude=<job aktif>)`. `keep_jobs == 0` melewati pemeriksaan.
3. Kegagalan mendapatkan folder Downloads atau kesalahan OSError/ValueError/
   TypeError/RuntimeError ditelan dengan aman: startup tidak boleh gagal karena
   housekeeping, dan tidak ada status job yang diubah.
4. Tidak ada penghapusan PARTIAL/FAILED, tidak ada penghapusan job aktif, dan
   tidak ada dialog/konfirmasi baru. `prune_published_jobs` tetap melakukan
   verifikasi seal + file publikasi Downloads + batas retensi yang sama.
5. Inventory manual (`inspect_job_storage`) tetap read-only saat startup.
6. `_dispose()` **tidak** melakukan join pada thread Tk; menutup jendela tetap
   responsif. Karena thread non-daemon, proses tetap menunggu sampai
   `prune_published_jobs()` selesai; tidak ada proses yang keluar di tengah
   `_remove_tree()`.

## Yang tidak berubah

- Verifikasi publikasi, batas 16 MiB, `keep_jobs`, dan segel tidak dilonggarkan.
- Job COMPLETE yang kehilangan folder publikasi tetap dilindungi.
- Log diagnosed kosong belum dicatat di PR ini (item P1 terpisah).

## Pengujian

Tes GUI sintetik: menutup aplikasi saat thread startup masih aktif
   menghentikan thread sebelum `_dispose()` selesai (`daemon is False`);
   startup dengan controller milik sendiri memanggil
`prune_published_jobs` tepat sekali dengan `keep_jobs` dan `exclude` yang benar;
`keep_jobs == 0` tidak memanggilnya; self-test dengan controller injeksi tidak
memanggilnya; `delete_incomplete_jobs` tidak pernah dipanggil saat startup.
Hosted CI tetap menjadi otoritas seluruh shard.
