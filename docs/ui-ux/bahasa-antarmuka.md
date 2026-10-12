# Menulis bahasa antarmuka

[Kembali ke panduan](README.md)

## Nada yang digunakan

Tulis seperti memberi petunjuk kepada rekan kerja yang sedang memakai aplikasi. Langsung ke hal yang perlu diketahui. Gunakan bahasa Indonesia sehari-hari yang tetap pantas untuk pekerjaan: **sudah**, **belum**, **bisa**, **coba**, **simpan**, dan **buka**. Tidak perlu bahasa gaul, sapaan berulang, humor, emoji, atau meniru manusia dengan berkata “saya sedang bekerja”.

Natural tidak berarti longgar secara fakta. **Belum lengkap** tetap peringatan. **Password belum bisa dipastikan** bukan sinonim password salah. Jangan menyebut data aman, lengkap, benar secara pajak, atau tersimpan jika pemeriksaannya belum membuktikan hal itu.

Petunjuk ini sejalan dengan prinsip pesan langsung, berorientasi tindakan, dan tidak menyalahkan pengguna dalam [panduan penulisan Windows](https://learn.microsoft.com/en-us/windows/apps/design/style/writing-style). Contoh bahasa Indonesia dan pilihan kata di bawah adalah keputusan proyek ini.

## Aturan praktis

Satu pesan memuat satu pokok utama. Judul menjawab apa yang terjadi. Isi menjelaskan dampak atau langkah berikutnya, biasanya cukup satu atau dua kalimat. Tombol menyebut tindakan, bukan **Ya**, **Lanjut**, atau **OK** jika akibatnya belum jelas.

Gunakan sentence case. Label dan tombol tanpa titik; kalimat utuh memakai titik. Hindari judul huruf kapital panjang. Kata “Anda” dipakai bila membantu, tidak harus ada di setiap kalimat. Jangan menambahkan “mohon”, “silakan”, “harap”, atau “dengan demikian” hanya agar terdengar sopan.

Jangan menjanjikan waktu yang tidak diketahui. **Menyimpan hasil unduhan** lebih tepat daripada **Sebentar lagi selesai**. Tenggat login 5 menit adalah batas kesempatan login, bukan perkiraan waktu tunggu. Batas terminasi worker 15 detik bukan janji bahwa seluruh jendela pasti tutup dalam 15 detik.

Istilah pajak dan nama berkas yang membantu pencarian tetap dipertahankan: NPWP, tahun pajak, masa, pembetulan, `resume.xlsx`, dan lembar **Audit**. “Berdasarkan tahun pajak” tidak boleh berubah menjadi “tahun lapor”. File hasil tidak disebut salinan lengkap seluruh Coretax.

## Tiga lapis teks

**Tampilan utama:** bahasa untuk menyelesaikan pekerjaan. Contoh: “Hasil unduhan belum lengkap. Lihat lembar Audit di resume.xlsx untuk rinciannya.”

**Rincian opsional:** kode status, tahap, atau lokasi yang memang diperlukan untuk dukungan. Jelaskan istilahnya. Tidak ada password, token, cookie, isi SPT, atau exception mentah. Kode `PARTIAL` boleh ditampilkan di sini, bukan menjadi satu-satunya label hasil.

**Dokumentasi developer/reviewer:** `job_id`, schema, exit code, cleanup, runtime, invariants, dan instruksi implementasi. Jangan bocorkan kalimat seperti “jangan mengarang persentase” atau “controller harus selesai” ke layar pengguna. Catatan bahwa data mockup hanya contoh ditempatkan pada wadah review, bukan ditiru sebagai fungsi aplikasi produksi.

## Kosakata yang konsisten

| Hindari di layar utama | Gunakan | Catatan |
| --- | --- | --- |
| Cakupan ekspor | Data yang akan diunduh | Cakupan tetap istilah yang sah di dokumen teknis. |
| Origin login | Situs login | Domain sebenarnya tetap terlihat penuh. Jangan menyamarkan tujuan login. |
| Kredensial | Akun dan password; login tersimpan | Pada tombol: **Cek login**, **Hapus login**. |
| Headless | Sembunyikan browser saat mengunduh | Jelaskan browser tetap muncul saat perlu login. |
| Workbook | File Excel | Nama file asli tidak diubah. |
| Checkpoint | Data sementara | Jangan menjanjikan otomatis dilanjutkan. |
| Rekonsiliasi | Mencocokkan atau memeriksa daftar | Dokumentasi tetap menjelaskan syarat teknis sebenarnya. |
| COMPLETE | Selesai | Hanya setelah controller mengesahkan hasil. |
| PARTIAL | Belum lengkap | Jangan diganti “selesai dengan catatan” atau centang hijau. |
| Terverifikasi, untuk hitungan SPT | Lengkap | Hanya jika `capture_complete`/verified benar. Bukan jaminan kebenaran isi pajak. |
| Belum terverifikasi | Belum pasti lengkap | Bukan otomatis gagal atau belum diproses. |
| Satu cakupan. Satu hasil. | Ringkasan unduhan | Hapus slogan yang tidak membantu tugas. |

## Contoh sebelum dan sesudah

| Sebelum | Sesudah |
| --- | --- |
| Ekspor selesai dan terverifikasi | **File Excel sudah siap** |
| Publikasi hasil dan pembersihan proses harus selesai sebelum aplikasi menyatakan COMPLETE. | **Menyimpan file ke Downloads dan menyelesaikan pemeriksaan terakhir.** |
| Checkpoint lokal dipertahankan. | **Data sementara tetap disimpan di komputer.** |
| LOGIN_UNVERIFIED · Belum terbukti | **Password belum bisa dipastikan** |
| Runtime dan dependensi worker disiapkan secara terpisah. | **Menyiapkan komponen yang dibutuhkan.** |
| Periksa origin, ketersediaan kredensial, serta kecocokan akun. | **Periksa situs login dan akun yang disimpan di Pengaturan.** |

## Katalog teks inti

ID di bawah adalah identitas presentasi usulan. Belum ada klaim bahwa ID tersebut sudah digunakan oleh kode Tkinter.

| ID | Teks |
| --- | --- |
| `app.title` | Unduh SPT ke Excel |
| `form.title` | Masukkan NPWP dan tahun pajak |
| `form.help` | Semua masa dan pembetulan yang ditemukan ikut diunduh. |
| `form.npwp.label` | NPWP (16 digit) |
| `form.npwp.help` | Ketik 16 angka, tanpa spasi, titik, atau tanda hubung. |
| `form.npwp.error` | Isi NPWP dengan 16 angka (0–9), tanpa pemisah. |
| `form.year.help` | Pilih tahun pajak, bukan tahun lapor. |
| `form.year.error` | Gunakan 4 angka, dari 1900 sampai 2100. |
| `action.start` | Mulai unduh |
| `action.stop` | Hentikan unduhan |
| `action.open_result` | Buka folder hasil |
| `action.open_partial` | Buka hasil sementara |
| `action.new` | Unduh SPT lain |
| `action.details` | Lihat rincian |
| `settings.origin.label` | Situs login |
| `settings.account.label` | Nama pengguna |
| `settings.password.help` | Kosongkan jika tidak diganti |
| `settings.check` | Cek login |
| `settings.cancel_check` | Batalkan cek |
| `settings.delete` | Hapus login |
| `download.complete.title` | File Excel sudah siap |
| `download.partial.title` | Hasil unduhan belum lengkap |
| `download.stopping.title` | Menghentikan unduhan… |
| `download.cancelled.title` | Unduhan dihentikan |
| `download.error.title` | Unduhan belum berhasil |
| `login.unverified.title` | Password belum bisa dipastikan |

Untuk hasil parsial, **Buka hasil sementara** hanya tampil bersama judul **Hasil unduhan belum lengkap** dan penjelasan Audit. “Sementara” berarti hasil yang sudah tersedia, bukan file yang otomatis diperbarui atau pasti dilengkapi nanti. Jika tidak ada output yang lolos pemeriksaan, jangan tampilkan tombol buka.

## Pesan bersyarat, bukan dugaan

Jika jumlah lengkap benar-benar tersedia: “{processed} dari {total} SPT sudah diproses. Kelengkapan {verified} SPT sudah diperiksa.” Jangan memasukkan nilai kosong sebagai `0` atau menyebut jumlah yang belum final sebagai total pasti.

`LOGIN_UNVERIFIED` memiliki lebih dari satu penyebab. Jika penyebab SSO diketahui, gunakan “Coretax sudah terbuka lewat SSO. Password yang disimpan belum diuji.” Jika batas waktu diketahui, gunakan “Pemeriksaan belum selesai dalam batas waktu. Ini tidak berarti password salah.” Jika kode belum menyediakan alasan yang aman dan terstruktur, gunakan “Pemeriksaan belum memastikan password. Ini tidak berarti password salah.” Jangan menebak alasan dari URL atau exception mentah.

Pada kegagalan dua penyimpanan, jangan memakai “Tidak ada perubahan tersimpan” tanpa bukti. Gunakan “Sebagian perubahan mungkin belum tersimpan. Periksa akses penyimpanan Windows, lalu simpan lagi.” Dialog harus tetap terbuka agar pengguna bisa memeriksa kondisinya.

## Pemeriksaan naskah

Baca teks dengan suara biasa. Apakah orang yang tidak mengenal kode akan tahu harus berbuat apa? Hapus istilah internal, pengulangan, slogan, permintaan maaf otomatis, dan janji yang tidak bisa dibuktikan. Setelah kata diganti, periksa lebar tombol, baris pesan, shortcut, fokus, serta versi jendela kecil. Jangan meloloskan pesan yang enak dibaca tetapi salah arti.
