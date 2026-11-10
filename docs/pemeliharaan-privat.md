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

## Retensi job otomatis (mulai versi dengan segel publikasi)

Di Pengaturan, isi **Jumlah job disimpan**. Nilai awal **10** berarti
aplikasi menjaga **10 direktori job terbaru** (termasuk PARTIAL dan gagal),
lalu setelah worker berhenti mencoba menghapus job yang lebih lama **hanya**
jika sebelumnya berhasil mencapai COMPLETE dan memiliki segel lokal
.spt-published-prune-v1.json yang diterbitkan sesudah publikasi terverifikasi.
Isi **0** untuk mematikan pruning otomatis; rentang angka 0–100. Pekerjaan
baru yang sudah selesai namun tanpa segel, pekerjaan sebelum versi ini,
checkpoint PARTIAL/ERROR/CANCELLED/BLOCKED, atau folder yang terdeteksi
memerlukan pemulihan **selalu dipertahankan**.

Sebelum menghapus setiap kandidat, aplikasi memeriksa kembali fingerprint
keseluruhan pohon privat, hash manifest asli, daftar dan hash seluruh file
publikasi yang tercatat di Downloads. Setiap file hasil publikasi dipegang
dengan handle Windows yang menolak penulisan dan penggantian/penghapusan
selama pemeriksaan sampai **seluruh** penghapusan pohon privat selesai.
Jika pengguna/Excel sudah memegang output untuk ditulis, pruning ditolak;
tidak ada fallback berbasis nama path atau hash sekali pakai.
Output yang hilang/ditimpa/berubah,
reparse point, hardlink, file terkunci, identitas folder yang berubah,
notice recovery, atau symlink menyebabkan pruning ditolak. Pruning
berjalan di thread terpisah setelah worker dan pembaca selesai; kegagalan
pruning tidak mengubah status terminal. Tidak ada pruning folder acak
berdasarkan umur atau nama, tidak menghapus arsip hasil di Downloads,
dan tidak menghapus profile, cache sesi atau runtime.

**Penting:** hasil terpublikasi di Downloads bukan salinan seluruh
bukti mentah (respons JSON, inventaris checkpoint, atau riwayat audit).
Pruning sebuah job menghilangkan sumber privat yang diperlukan untuk
rebuild offline atau audit lebih lanjut. Sebelum memanfaatkan retensi
otomatis, organisasi wajib menilai kebutuhan penyimpanan dan backup
terenkripsi secara terpisah. Pengaturan ini **tidak** menyatakan
backup telah berhasil atau kewajiban retensi instansi sudah terpenuhi.
Job historis tetap memerlukan prosedur backup dan penghapusan manual.

## Pemangkasan manual dari Pengaturan

Klik **Pangkas job lama** setelah menyimpan pengaturan retensi (1–100; 10
secara default). Aplikasi terlebih dahulu melakukan **pratinjau tanpa
menghapus**: jumlah job lama yang masih memiliki segel COMPLETE yang sah
serta perkiraan ukuran data privat yang dapat dibebaskan (MiB). Tinjauan
berjalan di thread terpisah, sementara aplikasi tidak memulai job baru
atau menyimpan perubahan pengaturan. Jumlah yang bisa dihapus dapat
berkurang jika file berubah, dikunci, atau hilang setelah pratinjau.
Pratinjau yang terhenti karena batas waktu atau gagal memeriksa satu kandidat
**tidak dapat dikonfirmasi**; tidak ada penghapusan. Hanya kandidat yang
terdaftar pada pratinjau lengkap yang dapat dihapus setelah konfirmasi;
pekerjaan lain yang baru memenuhi syarat tidak ikut dihapus.

Hanya setelah dialog konfirmasi eksplisit diterima, aplikasi mengulang
pemeriksaan keseluruhan: status COMPLETE, segel dan hash pohon sumber,
identitas direktori, checksum semua output Downloads dengan handle Windows
yang menolak perubahan, dan recovery. Sumber dipin dengan handle direktori
sebelum membaca segel hingga penghapusan selesai. Daftar file dan identitas
hasil verifikasi dicocokkan ulang sebelum penghapusan; file baru yang muncul
di tengah operasi **tidak** termasuk dalam daftar hapus. Jika ada perubahan
yang tak bisa dibuktikan aman, pekerjaan dipertahankan atau penghapusan
dilaporkan belum tuntas. Ketika sebagian file telah terhapus lalu Windows
menolak kelanjutannya, UI memberikan peringatan; tidak menyatakan semua job
berhasil dibersihkan. Tenggat pemeriksaan diperiksa di antara blok pembacaan
file; pembacaan I/O yang sedang terblokir tidak dapat dihentikan tepat pada
milidetik batas waktu.
Tidak ada nama NPWP, job ID,
path privat, atau data transaksi dalam pratinjau/diagnostik. Jika salah
satu syarat gagal, job tersebut tidak dihapus. Tindakan ini tidak
menghapus hasil Downloads, profil atau sandi. Nilai **0** menonaktifkan
pemangkasan otomatis maupun manual. *Perkiraan* ukuran tidak termasuk
biaya metadata filesystem dan bukan janji jumlah byte yang pasti dibebaskan.

