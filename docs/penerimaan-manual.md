# Penerimaan manual Coretax dan Excel

[Kembali ke dokumentasi](README.md)

Checklist ini digunakan setelah build dan tes sintetis lulus. Ia **belum merupakan hasil penerimaan yang telah dijalankan**. Pengujian portal aktual memerlukan operator dengan akses sah, NPWP serta tahun yang telah ditentukan, dan izin untuk operasi baca pada scope tersebut. Jangan mengambil akun dari CI, browser pribadi orang lain, atau data contoh buatan untuk mengklaim keberhasilan live.

## Catatan sebelum mulai

Catat build/commit, run ID dan artifact ID bila dari GitHub, profil Python, tanggal, versi Windows/browser/Excel, serta nama operator pada catatan privat yang sesuai. Scope NPWP/tahun dan referensi SPT nyata tetap berada pada catatan privat, bukan issue atau PR publik. Laporan publik cukup merujuk nomor laporan internal dan hasil tanpa identitas wajib pajak.

- [ ] Artifact dipilih dengan sengaja dan lolos [verifikasi distribusi](ci-dan-rilis.md#memverifikasi-artifact); versi pada [kebijakan Python](python-314.md) cocok dengan build yang diperiksa.
- [ ] Operator memang berwenang mengakses NPWP/tahun yang akan diperiksa.
- [ ] NPWP dimasukkan tepat 16 digit, termasuk nol awal; dasar tahun telah dipahami.
- [ ] Browser aplikasi khusus, koneksi intranet, origin login, dan Downloads tersedia.
- [ ] Hasil lama disimpan terpisah dan tidak menjadi target overwrite.

## Login dan kesiapan

- [ ] GUI dapat dibuka tanpa administrator dan persiapan runtime selesai atau menampilkan error yang dapat ditindaklanjuti.
- [ ] Akun/password dimasukkan hanya pada dialog lokal. Tidak muncul pada preferensi, pesan GUI, atau log yang akan dibagikan.
- [ ] Pengaturan hanya menyimpan/menghapus login; tidak ada tombol Cek login/Batalkan cek. Mulai unduh dengan akun tersimpan menggunakan sesi baru dan mencocokkan akun sebelum mengisi form.
- [ ] CAPTCHA/MFA diselesaikan langsung oleh pengguna. Form yang tidak dikenali memerlukan login manual; tidak ada percobaan menebak tombol submit.
- [ ] Setelah login manual, halaman pencarian dengan kontrol NPWP terlihat dan pekerjaan berlanjut segera setelah siap.

## Inventaris dan detail

- [ ] NPWP serta nama wajib pajak pada hasil pencarian cocok dengan scope yang diizinkan.
- [ ] Inventaris baru hanya membaca SPT Dilaporkan; daftar arsip dan status lain tidak dipindai. Jumlah sumber Dilaporkan cocok dengan pemindaian pada Audit. Checkpoint lama tetap menyatakan cakupan asalnya.
- [ ] Ambil sampel minimal satu SPT per jenis yang ada, masa yang berbeda bila tersedia, serta pembetulan yang memiliki ID berbeda. Gunakan data yang memang tersedia, bukan membuat jenis/masa baru.
- [ ] Sampel View membuka wajib pajak dan SPT yang benar; metadata, masa/tahun, status, dan identitas pembetulan cocok dengan halaman sumber.
- [ ] Tab, field, dan tabel yang didukung terambil, termasuk halaman tabel berikutnya. Footer/totals tidak berulang sebagai baris tambahan karena paginasi.
- [ ] Jenis SPT atau tahun yang tidak ada pada scope tidak diberi berkas/data fiktif.
- [ ] Layout yang tidak dikenali, error halaman, atau data berubah di tengah run terlihat sebagai batas/masalah, bukan COMPLETE palsu.

PDF laporan keuangan/auditan hanya boleh diambil dari href baca biasa atau [kontrol Unduh FinancialStatement yang didukung](pdf-keuangan-post.md) pada Induk Badan terverifikasi. Cocokkan deklarasi, byte/hash dan tautan relatif pada Audit resume; metadata saja bukan unduhan. PDF/BPE/lampiran lain, pembuatan dokumen, dan dialog drill-down per baris tetap di luar cakupan. Jangan menekan tombol submit, pembatalan SPT, email, atau pembuatan dokumen untuk melengkapi checklist ini.

- [ ] Pada sampel Badan yang memiliki laporan keuangan PDF, aplikasi mengunduhnya otomatis dari Induk; file dapat dibuka dan isi cocok dengan dokumen sumber yang diizinkan.
- [ ] Tautan PDF pada Excel/resume menuju file COMPLETE yang sama; kegagalan download atau build/kontrol yang belum didukung tetap PARTIAL, tanpa PDF kosong atau sertifikasi palsu.

## Stop dan pemulihan

Jalankan skenario Stop sebagai run terpisah yang disepakati; jangan menginterupsi pekerjaan orang lain.

- [ ] Stop pada tahap yang dipilih menjaga checkpoint lokal dan tidak menampilkan COMPLETE/100%.
- [ ] Event terlambat tidak memulai ulang pekerjaan atau mengubahnya menjadi sukses.
- [ ] Browser/worker milik aplikasi ditutup; aplikasi/browser pribadi lain tetap berjalan.
- [ ] Bila worker tidak merespons, pembersihan setelah tenggat 15 detik dapat diamati tanpa proses milik aplikasi tertinggal.
- [ ] Pemulihan dari checkpoint yang sesuai atau ekspor offline ke folder baru menghasilkan status yang jujur dan tidak mengubah hasil terdahulu.

Kegagalan file terkunci atau listrik padam tidak perlu dibuat pada data nyata. Gunakan fixture sintetis untuk injeksi kegagalan; jika kegagalan alami terjadi, simpan direktori pemulihan privat dan ekspor ulang ke folder baru.

## Pemeriksaan Excel dan publikasi

- [ ] **Buka folder hasil** (atau **Buka hasil sementara** pada PARTIAL yang sah) membuka folder hasil yang disahkan controller di Downloads aktual, termasuk lokasi OneDrive/non-ASCII yang digunakan operator.
- [ ] Folder memakai NPWP, nama wajib pajak yang benar, tahun, serta identitas run baru.
- [ ] Folder distribusi hasil berisi set workbook yang diharapkan; JSON pemulihan dan profil tidak ikut disalin.
- [ ] `resume.xlsx` memiliki Ringkasan, Daftar SPT, Audit, status, dan jumlah yang sesuai.
- [ ] Setiap jenis memakai workbook per **masa/tahun dan Model SPT literal**: Normal dan pembetulan berbeda tidak berbagi workbook. Semua form dalam satu workbook milik model itu; folder jenis serta tautan relatif sesuai [kontrak output](arsitektur.md#kontrak-excel-dan-transaksi-publikasi). Jenis/masa yang tidak ada tidak dibuat.
- [ ] Workbook SPT hanya berisi form, tanpa Ringkasan/Daftar SPT/Audit/banner/header/footer cetak tambahan; field sumber dan header kolom tetap ada.
- [ ] NPWP/ID dan nol awal tetap literal. Slot moneter terverifikasi mengikuti nilai/format numerik yang didukung; nilai malformed atau presisi tidak aman tidak ditebak. Cocokkan kembali dengan sumber, bukan hanya tampilan sel.
- [ ] Pada Badan yang teramati, rentang akuntansi/persentase yang disetujui tampil sesuai; L2 memakai pecahan persentase numerik, dan pengurang akumulasi penyusutan L1-D tampil negatif dengan nilai sumber tetap tersimpan.
- [ ] Total L9 kelompok LAINNYA terikat ke tabel yang benar pada capture baru yang menyimpan pemilik kelompok. Capture lama tanpa bukti pemilik tetap dilaporkan belum terpetakan.
- [ ] L11-B menampilkan label DER, referensi total rata-rata utang/modal, serta rasio dua desimal yang dihitung Excel. Periksa referensi ketika tabel tumbuh; operand hilang/tidak aman atau modal nol tidak menghasilkan rasio fiktif dan memiliki alasan PARTIAL pada Audit.
- [ ] Blok tambahan yang dihilangkan dari L2/L3/L4/L11-A/L11-B tidak menghilangkan checkpoint atau hitungan yang belum terpetakan pada Audit.
- [ ] Bandingkan hasil Badan dengan referensi tampilan bersih yang disetujui: Induk dua kolom, L8 tiga kolom, body tabel mengikuti baris yang berisi nilai (termasuk nol), satu slot untuk tabel kosong, serta header/pemisah/total tetap ada. Periksa footer, merge dan DER setelah tabel dipadatkan maupun diperpanjang; source_total dan proof tetap cocok dengan capture.
- [ ] Seluruh accounting Badan memakai nol desimal; nilai numerik tersimpan tetap sama dengan sumber, termasuk pecahannya. Rasio DER dan tampilan persentase tetap memakai dua desimal.
- [ ] Tautan indeks resume menuju workbook, lembar, dan pembetulan yang tepat; SPT tidak diberi backlink generik ke resume.
- [ ] Pada scope yang sama, hanya resume yang sudah ada diperbarui tanpa dialog; SPT/PDF terpilih yang sudah ada tetap meminta consent. Penolakan membatalkan publikasi tanpa mengubah resume atau file lama.
- [ ] Salinan seluruh folder ke lokasi uji lain tetap memiliki tautan relatif yang berfungsi tanpa mengganti nama berkas.
- [ ] COMPLETE hanya tampil bila inventaris/detail dan publikasi sudah terverifikasi; hasil parsial tetap diberi status serta catatan batas.

## Menyatakan hasil

Gunakan salah satu hasil per skenario: **lulus**, **gagal**, **terblokir**, atau **tidak diuji**. Catat perbedaan yang terlihat, tahap, versi build, dan referensi catatan privat yang dapat diperiksa. Jangan menyalin identitas, isi halaman, cookie, atau password ke ringkasan publik.

Penerimaan produksi perlu mencatat commit, artifact ID, versi GUI dan managed worker yang benar-benar dipakai. Lulus pada satu mesin/scope tidak membuktikan seluruh portal atau semua jenis SPT. Migrasi konfigurasi produksi dapat digabung setelah gate otomatis lengkap; status **penerimaan manual** tetap belum diuji sampai operator melakukannya pada seluruh fitur/UI terkonsolidasi.
