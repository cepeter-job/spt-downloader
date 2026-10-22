# Pemeliharaan workspace dan data pemulihan

[Kembali ke dokumentasi](README.md)

**Tutup pekerjaan aktif sebelum menilai ruang atau memindahkan data.** Folder
`%LOCALAPPDATA%\SPTDownloader` dapat memuat sesi browser, inventaris, capture,
checkpoint, dan bahan pemulihan. Umur folder atau status COMPLETE saja tidak
memberikan izin menghapusnya.

## Inventaris yang aman

| Kelompok | Lokasi relatif workspace | Perlakuan |
| --- | --- | --- |
| Pekerjaan dan capture | `jobs\<job-id>` | Privat; pertahankan scope/manifest, JSON, PDF dan hierarkinya bersama. |
| Pemulihan publikasi | `jobs\.spt-publish-*` dan notice di job asal | Pertahankan sampai pemulihan diverifikasi; jangan pisahkan backup dari journal. |
| Profil utama | `profile` | Sesi privat yang masih dipakai; jangan hapus sebagai cache biasa. |
| Profil sementara | `cache\login-check-*`, `cache\login-run-*` | Pembersihan aplikasi hanya berlaku untuk profil berpenanda kepemilikan sah dan lease tidak aktif. Folder lama/tidak dikenal perlu pemeriksaan manual. |
| Runtime, download cache dan log | `runtime`, `python`, `cache`, `logs` sesuai versi | Log memiliki retensi terbatas; lokasi lain bukan bukti data aman dihapus. Jangan membersihkan seluruh `cache` karena dapat berisi profil sesi. |

Periksa **Properties/Properti** masing-masing folder lewat Explorer untuk ukuran
dan jumlah file. Catat hanya kategori, jumlah job dan ukuran total pada catatan
dukungan umum. Nama folder output, nama WP, path lengkap, JSON dan isi workbook
tetap privat. Lokasi Downloads dapat berada di volume berbeda; periksa ruang kosong
workspace dan Downloads sebelum pekerjaan besar atau pemulihan.

## Prosedur pemeliharaan

1. Hentikan job melalui **Stop**, tunggu status terminal dan penutupan proses milik aplikasi, lalu tutup aplikasi. Jangan memindahkan profil/job yang masih aktif.
2. Daftarkan job yang masih PARTIAL, notice `publication-recovery-*.json`, serta folder `.spt-publish-*`. Tandai semuanya sebagai **dipertahankan** sampai dipulihkan atau dibatalkan secara sadar oleh pemilik data.
3. Buat salinan seluruh job dan bahan pemulihannya ke penyimpanan privat terenkripsi yang disetujui instansi. Pertahankan hierarki, akses yang dibatasi dan checkpoint asli; jangan unggah ke repository atau penyimpanan publik.
4. Uji salinan pada lingkungan yang diizinkan: rebuild offline ke folder baru atau jalankan prosedur pemulihan publikasi, lalu cocokkan jumlah, scope, hash dan tautan. Salinan yang belum pernah dipulihkan belum menjadi bukti backup yang dapat digunakan.
5. Hapus hanya folder job tertentu yang telah disetujui pemilik data dan sudah memiliki salinan terverifikasi, menggunakan tindakan manual yang menampilkan path tepat. Jangan memakai wildcard umur, recursive cleanup seluruh workspace, atau penghapusan otomatis bahan pemulihan.

Pembersihan profil sementara oleh aplikasi tidak menghapus job, capture, output,
profil utama atau folder tidak dikenal. Folder yang terkunci/berubah/berupa reparse
point ditinggalkan untuk diperiksa, bukan dipaksa dihapus. Kegagalan pembersihan
tidak boleh mengubah pembatalan menjadi COMPLETE.

## Catatan penerimaan operasional

Catat tanggal, operator, build commit/run/artifact, tujuan backup yang disetujui,
dan hasil restore tanpa isi pajak. Pemeriksaan yang harus dilakukan pada endpoint
nyata meliputi pembatasan ACL akun, enkripsi volume, kebijakan sinkronisasi Downloads,
ruang cadangan, serta restore dari backup. Tes sintetis di GitHub tidak menetapkan
konfigurasi endpoint pengguna.

Maintainer **@cepeter** memeriksa kegagalan Actions dan alert keamanan. Pastikan
langganan notifikasi benar-benar diterima pada akun maintainer dengan pemeriksaan
terjadwal; keberadaan workflow atau daftar penanggung jawab bukan bukti pengiriman.
Pedoman pelaporan privat ada pada [SECURITY.md](../SECURITY.md).
