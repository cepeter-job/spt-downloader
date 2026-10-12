# Pola layar, interaksi, dan status

[Kembali ke panduan](README.md)

## Form unduhan

Label terlihat terus; placeholder tidak menggantikan label. Pengaturan bukan langkah wajib untuk pengguna yang ingin login manual. NPWP dan tahun selalu ditampilkan lagi ketika proses berjalan. Validasi berlangsung saat selesai mengisi atau memilih Mulai, bukan memarahi pengguna ketika baru mengetik satu angka.

Pada input salah, letakkan pesan di dekat field dan pindahkan fokus ke field salah pertama. Pertahankan teks yang dimasukkan. Jangan otomatis menghapus titik/spasi, mengubah tahun dua digit, atau menghilangkan nol awal. Aksi Mulai hanya memulai satu pekerjaan. Klik berulang, Enter, dan shortcut harus melewati guard yang sama.

Teks utama **Mulai unduh** tetap cocok dengan Alt+M baseline. Hentikan tetap Alt+S untuk kompatibilitas walaupun huruf S tidak ada pada label Indonesia; tampilkan keterangan shortcut di bantuan/rincian, jangan menggarisbawahi huruf yang salah. Pengaturan Alt+P. Cek login Alt+C. Jalur pointer dan keyboard harus memiliki guard yang sama.

## Tahap proses

B memakai empat penanda: **Masuk ke Coretax**, **Daftar SPT**, **Mengambil rincian**, **Hasil Excel**. Penanda menjelaskan posisi, bukan navigasi yang dapat melompati pemeriksaan. Persiapan runtime termasuk tahap pertama dengan judul proses sendiri.

| Kondisi internal | Judul utama | Isi/tindakan penting |
| --- | --- | --- |
| Persiapan | Menyiapkan aplikasi | Menyiapkan komponen yang dibutuhkan; internet mungkin diperlukan. Indeterminate, tanpa ETA rekaan. |
| `login_required` | Lanjutkan login di browser | Selesaikan login dan verifikasi di browser. Batas login 5 menit; berlanjut setelah akses diperiksa. |
| `inventory` | Membaca daftar SPT | Mencari daftar untuk NPWP/tahun yang dipilih. Jumlah masih bisa berubah. |
| `details` | Mengambil rincian SPT | Pisahkan diproses, lengkap, dan belum pasti lengkap. Jangan samakan dengan persen keseluruhan. |
| Ekspor | Menyiapkan file Excel | Menyusun dan memeriksa file. Hanya tampil bila tahap tersebut dapat dibuktikan oleh event. |
| `publish` | Menyimpan hasil unduhan | Menunggu simpan, pemeriksaan akhir, dan cleanup. Pada 99% belum boleh membuka hasil. |
| Permintaan Stop | Menghentikan unduhan… | Nonaktifkan klik Stop berikutnya, tetap proses event. Jangan langsung menggambar CANCELLED final. |
| `COMPLETE` | File Excel sudah siap | Buka folder hasil; jelaskan batas unduhan dan simpan seluruh file bersama. |
| `COMPLETE`, daftar sah kosong | Tidak ada SPT untuk pilihan ini | Hanya jika inventaris benar-benar lengkap. Koneksi gagal tidak boleh ditafsirkan sebagai hasil kosong. |
| `PARTIAL` | Hasil unduhan belum lengkap | Peringatan, bukan centang sukses. Arahkan ke Audit di resume.xlsx. |
| `CANCELLED` | Unduhan dihentikan | Data sementara tetap disimpan. Mulai lagi membuat unduhan baru. |
| `BLOCKED` | Belum bisa masuk ke Coretax | Periksa situs login, browser, dan intranet. Jangan menjanjikan bypass atau retry otomatis. |
| `ERROR` | Unduhan belum berhasil | Hasil belum pasti lengkap. Gunakan penyebab yang diketahui dan tindakan realistis. |

Status internal dan syaratnya mengikuti [controller](https://github.com/cepeter-job/spt-downloader/blob/e99464a2b23c812acfaa4f39499cb5658dbc50c2/spt_desktop/controller.py) dan [events](https://github.com/cepeter-job/spt-downloader/blob/e99464a2b23c812acfaa4f39499cb5658dbc50c2/spt_desktop/events.py). View tidak membuat event sukses sendiri.

`verified` pada tahap detail berarti SPT yang sudah diproses dan lulus pemeriksaan kelengkapan capture. `processed - verified` hanya berarti belum pasti lengkap di kelompok yang diproses, bukan jumlah seluruh kegagalan. Penanda “Lengkap” tidak menilai kebenaran hukum atau perhitungan pajaknya.

Progress adalah proporsi berbobot tahap pada baseline, bukan waktu tersisa atau persentase dokumen lengkap. Tampilkan **Proses keseluruhan**. Penjelasan perbedaan dapat ada pada Lihat rincian. Jangan mengubah angka untuk membuat animasi lebih mulus jika itu menyiratkan pekerjaan yang belum terjadi. 100 hanya untuk COMPLETE.

## Panel hasil

Buka folder hanya memakai path yang telah diloloskan controller. Judul **File Excel sudah siap** memerlukan hasil COMPLETE yang sah, bukan sekadar file ada. Hasil parsial yang lolos verifikasi lokasi boleh dibuka, tetapi status belum lengkap terus terlihat. Hasil lama tidak dihapus ketika memulai pekerjaan baru.

Jelaskan di hasil lengkap: “Data SPT yang bisa dibaca aplikasi sudah diperiksa. Unduhan ini tidak mencakup PDF, BPE, atau isi lampiran.” Ini membatasi klaim, bukan pemberitahuan bahwa data sengaja dibuang. Nama workbook, identitas, isi sumber, dan tautan relatif tidak berubah. **resume.xlsx** bukan tombol atau bukti kemampuan melanjutkan unduhan.

Pada folder hilang, gunakan “Folder hasil mungkin sudah dipindahkan atau dihapus. Periksa folder Downloads yang digunakan saat mengunduh.” Jangan menambah status COMPLETE baru atau menebak lokasi pengganti. Jika folder ada tetapi gagal dibuka, jelaskan kegagalan membuka, bukan folder hilang.

## Pengaturan dan cek login

Urutan: Situs login, Nama pengguna, Password baru, Browser, pilihan sembunyikan browser. Domain yang diperbolehkan harus berasal dari allowlist, terlihat lengkap, dan tidak dapat diedit sembarang. Nama browser yang dibaca pengguna adalah Microsoft Edge/Google Chrome; nilai internal tetap `msedge`/`chrome`.

Password kosong mempertahankan password tersimpan sesuai kontrak baseline. Perubahan akun yang membutuhkan password baru harus dijelaskan dekat field. Hapus login berarti menghapus entri aplikasi untuk situs terpilih, bukan menghapus akun portal atau mengosongkan seluruh Credential Manager.

Pisahkan status **pengaturan disimpan** dari **login berhasil**. Simpan tidak berarti password valid. Cek login dinonaktifkan saat ada perubahan belum disimpan, akun belum tersedia, atau operasi lain aktif. Cek menggunakan operasi tersendiri tanpa NPWP/tahun, tidak menimpa hasil ekspor, dan tidak mengambil SPT.

| Status internal | Label pengguna | Arti yang harus tetap |
| --- | --- | --- |
| Belum dicek | Login belum dicek | Bukan gagal dan bukan berhasil. |
| Aktif | Mengecek login… | Satu percobaan. Batalkan cek tersedia. |
| `LOGIN_OK` | Login berhasil | Akun/password tersimpan benar-benar dipakai dan akses siap. |
| `LOGIN_UNVERIFIED` | Password belum bisa dipastikan | SSO atau timeout tidak membuktikan password benar/salah. |
| `LOGIN_MANUAL` | Perlu login di browser | Login manual saat mulai unduh; CAPTCHA/MFA tidak dilewati. |
| `LOGIN_BLOCKED` | Login belum bisa dicek | Periksa situs dan kecocokan akun; bukan otomatis password salah. |
| `LOGIN_ERROR` | Cek login belum berhasil | Koneksi/browser/penyimpanan perlu diperiksa sesuai bukti. |
| Permintaan batal | Membatalkan cek login… | Tunggu terminal dan cleanup, jangan berpura-pura proses sudah hilang. |
| `CANCELLED` | Cek login dibatalkan | Tidak ada SPT yang diunduh. |

Jangan memetakan pesan internal dengan replace teks bebas. Pakai jenis operasi + status + alasan terstruktur yang tersedia. Tambahan kode alasan yang belum ada memerlukan rancangan protokol terpisah, bukan dimasukkan diam-diam sebagai perubahan copy.

## Dialog dan fokus

| Pemicu | Judul | Pilihan |
| --- | --- | --- |
| Tutup ketika unduhan aktif | Hentikan unduhan dan tutup aplikasi? | Kembali; Hentikan dan tutup |
| Hapus login | Hapus login yang disimpan? | Batal; Hapus login |
| Tutup Pengaturan dengan edit | Perubahan belum disimpan | Simpan; Kembali; Abaikan |
| Folder hasil tidak ada | Folder hasil tidak ditemukan | Tutup |
| Penyimpanan tidak tuntas | Pengaturan belum berhasil disimpan | Kembali ke Pengaturan |

Pilihan aman mendapat fokus awal pada dialog destruktif. Escape membatalkan keputusan, bukan menjalankan aksi destruktif. Saat cek login aktif, Escape/Tutup meminta pembatalan dulu dan menunggu cleanup sesuai kontrak baseline. Tombol Hentikan unduhan langsung mengirim pembatalan, tanpa dialog tambahan. Menutup dialog mengembalikan fokus ke pemicunya. Teks status yang berubah tidak boleh mencuri fokus.

Konfirmasi edit belum disimpan adalah desain yang disetujui arahnya, tetapi belum diimplementasikan pada baseline. Jika Simpan gagal, jangan menutup dialog atau menampilkan sukses. Uji kegagalan kedua penyimpanan secara terpisah. Tidak ada janji operasi atomik untuk Credential Manager dan file preferensi.

## Aksesibilitas dan performa

Nama, peran, nilai, dan kondisi nonaktif harus bisa diperiksa melalui teknologi bantu Windows. Label terlihat belum membuktikan hubungan label-input terbaca oleh Narrator. Hindari custom widget tanpa bukti keyboard dan pembaca layar. Jangan menyebut lulus aksesibilitas hanya karena ada fokus biru pada mockup.

Uji 100/125/150/200% DPI, pembesaran teks, perpindahan monitor, High Contrast, Tab/Shift+Tab, Enter, Space, Escape, dan shortcut. Rancangan 640 DIP bukan minimum final sebelum diuji. Ukur startup, feedback input/Stop, CPU idle, RAM GUI terpisah dari worker/browser, serta pertumbuhan setelah pekerjaan berulang pada mesin yang sama. Target audit sebelumnya adalah usulan, bukan hasil ukur atau jaminan.
