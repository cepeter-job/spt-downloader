# Penerimaan manual Coretax dan Excel

[Kembali ke dokumentasi](README.md)

Checklist ini digunakan setelah build dan tes sintetis lulus. Ia **belum merupakan hasil penerimaan yang telah dijalankan**. Pengujian portal aktual memerlukan operator dengan akses sah, NPWP serta tahun yang telah ditentukan, dan izin untuk operasi baca pada scope tersebut. Jangan mengambil akun dari CI, browser pribadi orang lain, atau data contoh buatan untuk mengklaim keberhasilan live.

## Catatan sebelum mulai

Catat build/commit, run ID dan artifact ID bila dari GitHub, profil Python, tanggal, versi Windows/browser/Excel, serta nama operator pada catatan privat yang sesuai. Scope NPWP/tahun dan referensi SPT nyata tetap berada pada catatan privat, bukan issue atau PR publik. Laporan publik cukup merujuk nomor laporan internal dan hasil tanpa identitas wajib pajak.

- [ ] Artifact produksi atau kandidat telah dipilih dengan sengaja dan hash-nya cocok.
- [ ] Operator memang berwenang mengakses NPWP/tahun yang akan diperiksa.
- [ ] NPWP dimasukkan tepat 16 digit, termasuk nol awal; dasar tahun telah dipahami.
- [ ] Browser aplikasi khusus, koneksi intranet, origin login, dan Downloads tersedia.
- [ ] Hasil lama disimpan terpisah dan tidak menjadi target overwrite.

## Login dan kesiapan

- [ ] GUI dapat dibuka tanpa administrator dan persiapan runtime selesai atau menampilkan error yang dapat ditindaklanjuti.
- [ ] Akun/password dimasukkan hanya pada dialog lokal. Tidak muncul pada preferensi, pesan GUI, atau log yang akan dibagikan.
- [ ] Bila Cek Kredensial dipakai, pemeriksaan memakai sesi baru dan tidak memulai ekspor. Catat apakah password benar-benar diuji atau hanya SSO yang sudah siap.
- [ ] CAPTCHA/MFA diselesaikan langsung oleh pengguna. Form yang tidak dikenali memerlukan login manual; tidak ada percobaan menebak tombol submit.
- [ ] Setelah login manual, halaman pencarian dengan kontrol NPWP terlihat dan pekerjaan berlanjut segera setelah siap.
- [ ] Pembatalan Cek Kredensial menghentikan proses miliknya sebelum pengaturan ditutup.

## Inventaris dan detail

- [ ] NPWP serta nama wajib pajak pada hasil pencarian cocok dengan scope yang diizinkan.
- [ ] Daftar status yang tersedia telah dibaca dan setiap jumlah sumber cocok dengan hasil pemindaian yang tercatat di Audit.
- [ ] Ambil sampel minimal satu SPT per jenis yang ada, masa yang berbeda bila tersedia, serta pembetulan yang memiliki ID berbeda. Gunakan data yang memang tersedia, bukan membuat jenis/masa baru.
- [ ] Sampel View membuka wajib pajak dan SPT yang benar; metadata, masa/tahun, status, dan identitas pembetulan cocok dengan halaman sumber.
- [ ] Tab, field, dan tabel yang didukung terambil, termasuk halaman tabel berikutnya. Footer/totals tidak berulang sebagai baris tambahan karena paginasi.
- [ ] Jenis SPT atau tahun yang tidak ada pada scope tidak diberi berkas/data fiktif.
- [ ] Layout yang tidak dikenali, error halaman, atau data berubah di tengah run terlihat sebagai batas/masalah, bukan COMPLETE palsu.

PDF laporan keuangan/auditan hanya boleh diambil dari href baca biasa yang sudah terlihat pada Induk Badan terverifikasi. Cocokkan deklarasi, byte/hash dan tautan relatif pada Audit resume; metadata saja bukan unduhan. PDF/BPE/lampiran lain, pembuatan dokumen, dan dialog drill-down per baris tetap di luar cakupan. Jangan menekan tombol submit, pembatalan SPT, email, atau pembuatan dokumen untuk melengkapi checklist ini.

## Stop dan pemulihan

Jalankan skenario Stop sebagai run terpisah yang disepakati; jangan menginterupsi pekerjaan orang lain.

- [ ] Stop pada tahap yang dipilih menjaga checkpoint lokal dan tidak menampilkan COMPLETE/100%.
- [ ] Event terlambat tidak memulai ulang pekerjaan atau mengubahnya menjadi sukses.
- [ ] Browser/worker milik aplikasi ditutup; aplikasi/browser pribadi lain tetap berjalan.
- [ ] Bila worker tidak merespons, pembersihan setelah tenggat 15 detik dapat diamati tanpa proses milik aplikasi tertinggal.
- [ ] Pemulihan dari checkpoint yang sesuai atau ekspor offline ke folder baru menghasilkan status yang jujur dan tidak mengubah hasil terdahulu.

Kegagalan file terkunci atau listrik padam tidak perlu dibuat pada data nyata. Gunakan fixture sintetis untuk injeksi kegagalan; jika kegagalan alami terjadi, simpan direktori pemulihan privat dan ekspor ulang ke folder baru.

## Pemeriksaan Excel dan publikasi

- [ ] **Buka Hasil** membuka Downloads aktual, termasuk bila diarahkan ke OneDrive/lokasi non-ASCII yang digunakan operator.
- [ ] Folder memakai NPWP, nama wajib pajak yang benar, tahun, serta identitas run baru.
- [ ] Folder distribusi hasil berisi set workbook yang diharapkan; JSON pemulihan dan profil tidak ikut disalin.
- [ ] `resume.xlsx` memiliki Ringkasan, Daftar SPT, Audit, status, dan jumlah yang sesuai.
- [ ] SPT Badan memiliki workbook tersendiri; SPT Masa memiliki satu workbook per masa literal dalam folder jenis. Setiap form/tab teramati dan pembetulan memiliki sheet sendiri. Workbook jenis/masa yang tidak ada tidak dibuat.
- [ ] Workbook SPT hanya berisi form, tanpa Ringkasan/Daftar SPT/Audit/banner/header/footer cetak tambahan; field sumber dan header kolom tetap ada.
- [ ] Sampel NPWP/identifier dengan nol awal, teks angka Indonesia, dan nilai sumber tetap persis ketika diperiksa di Excel.
- [ ] Tautan indeks resume menuju workbook, lembar, dan pembetulan yang tepat; SPT tidak diberi backlink generik ke resume.
- [ ] Pada scope yang sama, hanya resume yang sudah ada diperbarui tanpa dialog; SPT/PDF terpilih yang sudah ada tetap meminta consent. Penolakan membatalkan publikasi tanpa mengubah resume atau file lama.
- [ ] Salinan seluruh folder ke lokasi uji lain tetap memiliki tautan relatif yang berfungsi tanpa mengganti nama berkas.
- [ ] COMPLETE hanya tampil bila inventaris/detail dan publikasi sudah terverifikasi; hasil parsial tetap diberi status serta catatan batas.

## Menyatakan hasil

Gunakan salah satu hasil per skenario: **lulus**, **gagal**, **terblokir**, atau **tidak diuji**. Catat perbedaan yang terlihat, tahap, versi build, dan referensi catatan privat yang dapat diperiksa. Jangan menyalin identitas, isi halaman, cookie, atau password ke ringkasan publik.

Penerimaan produksi Python 3.14.8 perlu mencatat commit, artifact ID, versi GUI, serta versi managed worker. Lulus pada satu mesin/scope tidak membuktikan seluruh portal atau semua jenis SPT. Migrasi konfigurasi produksi dapat digabung setelah gate otomatis lengkap; status **penerimaan manual** tetap belum diuji sampai operator melakukannya pada seluruh fitur/UI terkonsolidasi.
