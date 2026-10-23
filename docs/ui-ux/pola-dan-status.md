# Pola layar, interaksi, dan status

[Kembali ke panduan](README.md) · [Spesifikasi B-TK-1](../superpowers/specs/2026-10-13-magicpath-b-tkinter-design.md)

**Baseline aktif:** `ecbd9878aa732a379ba94ef848764f9815445003`, 21 Oktober 2026; [matriks existing vs pekerjaan terbuka](baseline-2026-10-21.md). PR #12, #53 dan #58 sudah merged. Shell, dialog Phase 2, konteks folder wajib dan pengurangan delay filter sudah tersedia. Konfirmasi Pengaturan dirty dan batching daftar besar tetap usulan. Tabel judul/status adalah pola presentasi; caption aktual tetap diperiksa di App/view sebelum direvisi.

## Login tersimpan tanpa pilihan origin

Pengaturan hanya meminta akun/password, browser, dan opsi unduh. Navigasi tetap dimulai dari Coretax, lalu aplikasi menunggu form Satu yang dikenali; origin login tidak dipilih pengguna. Kunci Windows Credential Manager untuk login otomatis selalu origin Satu yang persis diizinkan. Preferensi origin Coretax lama diabaikan tanpa membaca, memindahkan, atau menghapus credential lamanya. Jika entri Satu belum tersedia, isi ulang akun/password melalui Pengaturan lalu Simpan.

**Mulai unduh** meneruskan identifier yang dipilih ke worker, menunggu form yang dikenali, dan mencocokkan identifier credential sebelum mengisi form. Untuk akun tersimpan, worker memakai profil sementara baru agar tidak mengunduh dengan sesi akun lama yang identitasnya tidak diketahui. Profil dibersihkan setelah browser ditutup. SSO tanpa pengiriman credential belum membuktikan akun yang dipilih; gunakan mode manual bila identitas sesi tidak dapat dikaitkan.

Akun kosong memilih mode manual tanpa membaca credential tersimpan. Mengosongkan akun lalu Simpan tidak menghapus password; penghapusan tetap melalui tombol khusus dengan konfirmasi. Mode manual dapat memakai profil manual yang sudah ada. Akun baru yang tidak kosong tetap memerlukan password baru. Password tidak diteruskan lewat argv atau disimpan dalam preferensi/log.

Form/challenge tidak aman tetap manual, CAPTCHA/MFA tidak dilewati, dan tidak ada percobaan submit otomatis berulang. Login unduhan diuji dengan fixture browser sintetis; bukti tersebut terpisah dari penerimaan akun intranet nyata.

## Form unduhan

Label terlihat terus; placeholder tidak menggantikan label. Pengaturan bukan langkah wajib untuk login manual. NPWP/tahun ditampilkan lagi selama proses. Validasi existing berjalan pada submit/start dan menaruh error dekat field; jangan mengklaim validasi saat blur sudah ada. Validasi tambahan tidak boleh memarahi pengguna ketika baru mengetik satu angka.

Error berada di field; fokus ke kesalahan pertama dan teks tetap dipertahankan. Tidak menghapus titik/spasi, memperbaiki tahun dua digit, atau menghilangkan nol awal secara otomatis. Klik/Enter/shortcut melewati guard start yang sama; satu pekerjaan aktif.

Teks utama **Mulai unduh** mengikuti Alt+M; Hentikan tetap Alt+S. Pengaturan Alt+P. Jangan menggarisbawahi huruf yang salah; tampilkan shortcut dalam bantuan. Enter global tidak boleh menyetujui dialog penggantian tanpa fokus/aksi yang tepat.

## Tahap proses

Empat penanda B-TK-1: **Masuk ke Coretax · Daftar SPT · Mengambil rincian · Hasil unduhan**. Persiapan masuk tahap pertama; pemilihan berada pada tahap kedua; persetujuan penggantian pada tahap keempat. Penanda bukan tombol navigasi. Idle belum mempunyai tahap yang berjalan.

| Bukti/kondisi | Judul utama | Isi/tindakan penting |
| --- | --- | --- |
| Persiapan | Menyiapkan aplikasi | Indeterminate, tanpa ETA; internet diperlukan bila menyiapkan komponen. |
| Progress `authentication` | Memeriksa akses ke Coretax | Stage saja bukan bukti login siap. |
| `login_required` | Lanjutkan login di browser | Login/CAPTCHA/verifikasi di browser; berlanjut setelah akses diperiksa. |
| `inventory` | Membaca daftar SPT | Jumlah masih berubah; unit inventaris bukan total SPT terpilih. |
| `selection_required` | Pilih SPT yang akan diunduh | Dialog sekali untuk request aktif, pilihan awal kosong. |
| `details` | Mengambil rincian SPT | Counter milik subset yang disetujui; tidak mengarang progres PDF. |
| `export` | File Excel sudah dibuat | Event muncul setelah workbook dibuat/diverifikasi. Belum boleh membuka hasil. |
| `publish` | Menyimpan hasil unduhan | Menunggu publikasi dan cleanup; 99% bukan selesai. |
| `overwrite_required` | Ganti hasil sebelumnya? | Folder/file lengkap; keputusan aman default. |
| Stop diminta | Menghentikan unduhan… | Stop berikutnya dikunci; tunggu terminal, bukan CANCELLED buatan view. |
| `COMPLETE` | File Excel sudah siap | Hasil untuk SPT yang dipilih dan cakupan yang didukung. |
| COMPLETE + bukti daftar sah kosong | Tidak ada SPT yang ditemukan | Bukan filter tanpa hasil atau koneksi gagal. |
| `PARTIAL` | Hasil unduhan belum lengkap | Peringatan dan Audit; buka hanya output sah. |
| `CANCELLED` | Unduhan dihentikan | Data sementara yang sudah dibuat tetap ada; mulai lagi bukan resume. |
| `BLOCKED` / `ERROR` | Unduhan belum bisa dilanjutkan / Unduhan belum berhasil | Pesan aman; sebab spesifik hanya bila tersedia, bukan tebakan. |

Sumber: [controller](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/spt_desktop/controller.py), [events](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/spt_desktop/events.py), dan [worker](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/spt_desktop/worker.py). View tidak membuat event sukses sendiri.

`verified` pada detail menyatakan capture lengkap di kelompok yang diproses, bukan kebenaran pajak. `processed - verified` bukan jumlah seluruh kegagalan. Counter tidak tersedia bukan nol; saat stage berganti, jangan memakai denominator inventaris sebagai denominator detail.

Progress berbobot tahap tetap berbeda dari jumlah SPT terpilih, waktu tersisa, atau persen dokumen lengkap. Sesudah reply pemilihan diterima controller, hitungan detail sudah dimulai dari `0/N` dengan `verified=0` untuk N yang disetujui; jangan memulainya dari ukuran inventaris atau menjadikan 0/N sebagai bukti kegagalan. Label **Proses keseluruhan**; rincian menjelaskan maknanya. Jangan membuat angka naik saat menunggu consent atau mengubah persen demi animasi. Terminal tidak membawa seluruh counter/manifest: simpan bukti terakhir job yang sama dan sembunyikan metrik yang tidak tersedia.

## Pemilihan SPT

Gunakan dialog native dengan pencarian dan Treeview multi-select: Jenis pajak, Masa pajak, Normal/pembetulan, ID SPT. Kolom Masa pajak menampilkan **Tahunan** untuk jenis PPh Badan dan nama bulan Indonesia untuk masa bulanan yang dikenali: angka 1–12/01–12, kode `MM` + `MM` + tahun dengan bulan awal/akhir sama, atau caption bulan dan tahun. Rentang atau format yang ambigu tetap tampil literal. Metadata, checkpoint, ekspor, ID dan kunci urutan tetap memakai nilai sumber asli; pencarian menerima label tampilan maupun teks sumber. Source ID bukan IID widget; gunakan IID lokal yang dipetakan kembali ke ID teramati.

Saat dialog dibuka, urutan tampilan default adalah **PPh Badan → PPh Pasal 21/26 → PPh Unifikasi → PPN**, lalu jenis lain. Caption dikenali utuh secara case-insensitive; teks sumber tidak diubah. Dalam setiap jenis, tahun menaik, masa Januari–Desember, lalu Normal → Pembetulan 1 → Pembetulan 2 dan seterusnya mengikuti aturan sorting yang ada. Jenis lain diurutkan berdasarkan caption; kunci yang setara tetap mengikuti urutan inventaris.

Tidak perlu klik header untuk memakai urutan default. Klik header **Jenis pajak** tetap memakai A–Z, kemudian Z–A; filter/clear mempertahankan urutan aktif. Daftar awal tidak memilih SPT otomatis. Perubahan filter tetap mengosongkan pilihan, dan konfirmasi mengirim ID terpilih menurut urutan inventaris asli—bukan urutan visual atau urutan ekspor.

Awal tidak terpilih; **Sedot SPT terpilih** nonaktif sampai pilihan sah ada. Filter memakai query casefold/trim, bukan mengubah NPWP. Mengubah filter mengosongkan pilihan; jangan mengirim hidden selection. Tampilkan jumlah dipilih, terlihat, dan inventaris. Bedakan pencarian tanpa hasil dari inventaris kosong.

ID baris yang disorot ditampilkan lengkap dalam field readonly; fokus baris bukan persetujuan memilih. Alt+J memakai aksi sorting jenis yang sama dengan header dan mempertahankan pilihan/fokus. Enter di pencarian/tabel atau double-click baris tidak boleh menyetujui; konfirmasi memerlukan aksi pada tombol yang sah.

Confirm memakai `controller.respond('selection', request_id, {'selected_ids': [...]})`. Payload hanya subset yang terlihat dan dikonfirmasi. X/Escape/Hentikan membatalkan job tanpa memilih semua. Fokus awal pada pencarian; Ctrl/Shift dan keyboard Treeview tetap tersedia.

Request terikat `job_id`/operasi/`request_id`, hanya satu pending dan satu jawaban. Stop/terminal menginvalidasi dialog sebelum callback lain dapat berjalan. Callback lama tidak boleh menyetujui atau menghentikan job baru. Tenggat worker 600 detik, tanpa auto-consent. `respond=False` tidak berarti keputusan diterima. Sumber: [App](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/spt_desktop/app.py), [interaction](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/spt_desktop/interaction.py).

**Usulan, belum implemented:** batching render/filter untuk daftar besar. Baseline memasukkan ulang seluruh hasil filter melalui loop sinkron di `selection_dialog.filter_records`; tidak ada worker render/chunk-generation. Jika batching diterapkan kelak, jangan memotong data; kunci submit selama generasi belum selesai dan tolak hasil stale berdasarkan token job/request. Batas dan pengukuran performa mengikuti spesifikasi, bukan klaim baseline sudah diuji untuk semua ukuran daftar.

## Penggantian file

Penggantian `resume.xlsx` saja berlangsung otomatis setelah verifikasi scope dan race. Jika SPT/PDF terpilih akan diganti, tampilkan folder persis dari request dan semua path yang akan diganti, termasuk PDF bila ada. Jangan hanya menampilkan basename atau memilih sendiri folder terakhir. Scroll dua arah tersedia. **Jangan ganti** fokus awal; X/Escape sama dengan jawaban `overwrite=False`. **Ganti file tersebut** mengirim `True`. Alt+S tetap Stop langsung.

Jelaskan bahwa file diganti seluruhnya, bukan merge baris. SPT lain dalam file yang diganti tidak otomatis dipertahankan. File masa/model lain yang tidak diganti tetap ada. Untuk folder existing yang lolos verifikasi, `coretax.write_folder_resume` membuat indeks gabungan hasil baru dan workbook lama yang dipertahankan; bukan hanya daftar pilihan baru. COMPLETE job tetap berlaku untuk pilihan proses saat ini. Jika penggantian ditolak, resume lama juga tidak dipublikasikan ulang. Setelah setuju, tunggu terminal dan verifikasi backend; jangan langsung menampilkan sukses.

**Sudah diimplementasikan:** GUI menolak `folder` yang hilang, bukan string, kosong, atau hanya whitespace sebelum membuat dialog persetujuan. Nilai folder valid tetap ditampilkan persis, termasuk whitespace literal; path panjang dapat diperiksa lewat field readonly dan scrollbar. Jumlah file tidak mengubah izin penggantian per file. Request stale tidak boleh menghentikan job baru. Pemeriksaan identitas folder/file, hash, rollback, dan custody PDF tetap milik backend. Lihat `overwrite_dialog` dan tes `test_desktop_dialog_layout.py`; bukan lagi usulan Phase 2.

## Panel hasil

Buka folder hanya memakai path yang disahkan controller. COMPLETE memerlukan terminal sah, exit code sesuai, output valid, dan cleanup selesai. COMPLETE berlaku untuk subset terpilih, bukan seluruh tahun. Hasil parsial boleh dibuka bila lokasi hasil sah, dengan status belum lengkap yang tetap terlihat. Tanpa output sah, tombol buka tidak tersedia.

Petunjuk hasil: “Simpan seluruh folder hasil beserta subfoldernya. Jangan mengganti nama file agar tautannya tetap berfungsi.” Struktur Excel adalah per jenis pajak, masa/tahun sumber, dan **Model SPT literal**. Semua form dalam sebuah workbook berasal dari model itu saja. Nilai sumber serta tautan relatif tetap; Normal dan pembetulan yang berbeda tidak digabung di satu workbook. File gabungan lama diverifikasi sebelum memilih folder baru, bukan ditulis ulang/dihapus diam-diam.

PDF laporan keuangan/auditan Badan dapat ikut disimpan jika tersedia lewat tautan baca yang didukung dan lolos pemeriksaan. BPE/lampiran lain tetap tidak dijanjikan. Metadata bukan bukti byte PDF tersimpan. Jangan menampilkan jumlah PDF atau daftar file aktual tanpa data presentasi yang sah. Kalimat lama yang menolak semua PDF tidak lagi digunakan.

**resume.xlsx** bukan kemampuan resume GUI. Data sementara yang tersedia tetap dipertahankan saat pembatalan, tetapi gagal sejak awal belum tentu membuat checkpoint. Memulai lagi adalah pekerjaan baru.

Folder hilang: jelaskan mungkin dipindahkan/dihapus. Folder ada tetapi gagal dibuka: jelaskan kegagalan membuka. Jangan membuat status COMPLETE baru atau menebak lokasi pengganti.

## Pengaturan dan login tersimpan

Urutan widget existing: **Akun / username**, **Password baru**, **Browser**, **Sumber detail SPT**, checkbox **jalankan proses sedot di background**. Sumber detail menyediakan **DOM** dan **JSON-hybrid (pilot)**; profil desktop baru/mode hilang atau tidak sah memakai `json-first`, preferensi `dom` atau `json-first` yang sah dipertahankan. CLI/library tetap default DOM tanpa opsi eksplisit. **Buka folder log** sudah tersedia; tindakan membuka folder tidak mengirim isinya ke pihak lain. Origin Satu ditetapkan aplikasi, bukan combobox atau URL bebas. Helper menjelaskan login otomatis dan mode akun kosong/manual. Microsoft Edge/Google Chrome dipetakan ke `msedge`/`chrome`.

Password kosong mempertahankan entri sesuai kontrak; perubahan akun yang perlu password baru dijelaskan dekat field. Hapus login hanya menghapus entri aplikasi pada origin Satu tetap (`LOGIN_ORIGIN`), bukan pilihan situs pengguna, akun portal, entri legacy Coretax, atau seluruh Credential Manager. Jangan menjanjikan transaksi atomik Credential Manager dan file preferensi.

Simpan mempertahankan dialog dan tidak memulai worker atau membuktikan login berhasil. Tutup Pengaturan lalu pilih Mulai unduh untuk memakai akun tersimpan. Tidak ada tombol Cek login/Batalkan cek atau shortcut Alt+C. Dirty dihitung dari nilai dibanding preferensi tersimpan ditambah password baru; mengembalikan nilai semula tidak meninggalkan dirty palsu. Simpan, ubah akun/password, dan Hapus login mempertahankan hasil ekspor terakhir.

## Dialog dan fokus

| Pemicu | Judul | Pilihan dan Escape/X |
| --- | --- | --- |
| Tutup saat unduhan aktif | Hentikan unduhan dan tutup aplikasi? | Kembali; Hentikan dan tutup. Escape/X = Kembali. |
| Hapus login | Hapus login yang disimpan? | Batal; Hapus login. Escape/X = Batal. |
| Tutup Pengaturan atau aplikasi dengan perubahan | Perubahan belum disimpan | Simpan; Abaikan; Kembali. Fokus awal Kembali; Escape/X = Kembali. |
| Pemilihan SPT | Pilih SPT yang akan diunduh | Sedot SPT terpilih; Hentikan unduhan. Escape/X = Stop. |
| Penggantian | Ganti hasil sebelumnya? | Jangan ganti; Ganti file tersebut. Escape/X = false. |

Pilihan aman fokus awal pada keputusan destruktif. Tidak ada Return global yang menyetujui overwrite. Tombol Stop langsung membatalkan tanpa konfirmasi tambahan. Dialog mengembalikan fokus ke pemicu yang masih valid; progress tidak mencuri fokus. Setelah terminal ekspor, App mengarahkan fokus ke Buka hasil jika tersedia atau Mulai unduh, bukan Entry yang bisa tergulir keluar viewport. Bersihkan grab, traces, dan after sebelum destroy/job berikutnya.

Perubahan browser, akun, sumber detail, pilihan background, atau password baru memerlukan keputusan **Simpan / Abaikan / Kembali** saat Pengaturan maupun aplikasi ditutup. Kembali, Escape, dan X mempertahankan edit serta membatalkan penutupan aplikasi. Simpan hanya menutup setelah penyimpanan berhasil; kegagalan mempertahankan dialog.

Windows Credential Manager dan preferensi merupakan dua penyimpanan terpisah. Setelah password berhasil disimpan, field password segera dikosongkan; retry preferensi tidak menulis ulang password. Setelah login berhasil dihapus, kegagalan preferensi dilaporkan sebagai penghapusan yang sudah terjadi dan preferensi yang masih perlu disimpan. Abaikan membuang edit yang belum tersimpan, tetapi tidak membatalkan perubahan Credential Manager yang sudah berhasil; dialog menyebut batas ini. Akun yang telah dihapus tidak boleh dipilih lagi tanpa password baru.

## Aksesibilitas dan performa

Label terlihat dan fokus biru belum membuktikan aksesibilitas native. Uji name/role/value/focus melalui UI Automation, Narrator/NVDA, terutama tabel pilihan, input, modal, dan hasil. Kekurangan kontrol kritis dicatat sebagai blocker, bukan alasan mengganti toolkit diam-diam.

Uji DPI 100/125/150/200%, pembesaran teks, multi-monitor, High Contrast, Tab/Shift+Tab, Enter/Space/Escape, dan shortcut. Reflow harus mempertahankan informasi scope; jangan meluluskan clipping dengan minimum jendela melebihi work area. Ukuran normal/compact penuh pada 200% belum terverifikasi pada layar yang cukup besar; screenshot 200% yang tersedia menguji ukuran ter-clamp dan minimum. Jangan menamai hasil ini kepatuhan DPI menyeluruh.

PR #58 menggunakan callback idle milik dialog untuk mapping awal/perubahan konten, mengabaikan notifikasi Configure redundan berdasar ukuran viewport aktual, dan tetap menggabungkan resize nyata melalui callback 75 ms. Tidak ada thread Tk baru, batching row atau batas jumlah record baru. Seluruh callback harus dibatalkan saat Stop/terminal/close; jangan membatalkan timer root yang bukan milik dialog.

Pada pasangan sintetis Windows yang dilaporkan, median filter 1/100/1.000 SPT menjadi 4,86/9,55/15,73 ms; median opening masih 137–185 ms dan semua 40 sampelnya di atas 100 ms. Sorting tidak seluruhnya lebih cepat. Cancellation maksimum 73,33 ms berlaku untuk sampel tersebut, bukan jaminan semua mesin. Lihat [metodologi dan bukti PR #58](../superpowers/reports/2026-10-21-phase2-performance-evidence.md); pengukuran ini bukan throughput Coretax/Excel/PDF.

Ukur GUI terpisah dari worker/browser; batasi event, status history, row-batch, serta callback tertunda. Pertahankan polling baseline dan update widget inkremental. Seluruh pytest, product import, Tk/browser fixture, source/frozen self-test, build, dan EXE hanya di GitHub runner sesuai [AGENTS.md](../../AGENTS.md). Pemeriksaan dokumen lokal bukan bukti runtime atau aksesibilitas.

Kontrak workbook terkonsolidasi: Ringkasan, Daftar SPT, dan Audit hanya berada di `resume.xlsx`. Workbook SPT terpisah per masa/tahun dan Model SPT literal, berisi worksheet form/tab untuk model itu saja, tanpa banner/header/footer administratif atau sheet administratif tersembunyi. Hyperlink dari resume menuju form tetap relatif.
