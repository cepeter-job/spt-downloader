# Pola layar, interaksi, dan status

[Kembali ke panduan](README.md) · [Spesifikasi B-TK-1](../superpowers/specs/2026-10-13-magicpath-b-tkinter-design.md)

**Baseline aktif:** `977b06846554ca1f2e5af512a69fb201f2cbe8d1`, 20 Oktober 2026; [matriks existing vs usulan](baseline-2026-10-20.md). Shell B dan modul presentasi sudah ada di `main` setelah PR #12 merged. Pemilihan/sorting, overwrite, sumber detail, login Satu, dan log juga existing. Konfirmasi Pengaturan dirty, batching daftar besar, serta kewajiban konteks folder di GUI overwrite masih usulan; jangan menandainya selesai dari dokumen ini. Tabel judul/status di bawah adalah pola presentasi; caption aktual dapat berbeda dan harus diperiksa di App/view sebelum direvisi.

## Login tersimpan tanpa pilihan origin

Pengaturan hanya meminta akun/password, browser, dan opsi unduh. Navigasi tetap dimulai dari Coretax, lalu aplikasi menunggu form Satu yang dikenali; origin login tidak dipilih pengguna. Kunci Windows Credential Manager untuk login otomatis selalu origin Satu yang persis diizinkan. Preferensi origin Coretax lama diabaikan tanpa membaca, memindahkan, atau menghapus credential lamanya. Jika entri Satu belum tersedia, isi ulang akun/password melalui Pengaturan lalu Simpan.

**Cek Kredensial** menguji satu submit pada profil sementara. **Mulai Unduh** meneruskan identifier yang dipilih (bukan password) ke worker, menunggu form dengan alur kesiapan yang sama, dan mencocokkan identifier credential sebelum mengisi form. Untuk akun tersimpan, worker memakai profil sementara baru agar tidak mengunduh dengan sesi akun lama yang identitasnya tidak diketahui. Profil dibersihkan setelah browser ditutup; hasil cek bukan file penanda password-valid atau izin mempercayai profil lain. SSO tanpa pengiriman credential belum membuktikan akun yang dipilih; gunakan mode manual bila identitas sesi tidak dapat dikaitkan.

Akun kosong memilih mode manual tanpa membaca credential tersimpan. Mengosongkan akun lalu Simpan tidak menghapus password; penghapusan tetap melalui tombol khusus dengan konfirmasi. Mode manual dapat memakai profil manual yang sudah ada. Perubahan akun/password menghapus status cek dari tampilan. Akun baru yang tidak kosong tetap memerlukan password baru. Password tidak diteruskan lewat argv atau disimpan dalam preferensi/log.

Form/challenge tidak aman tetap manual, CAPTCHA/MFA tidak dilewati, dan tidak ada percobaan submit otomatis berulang. Cek yang sukses diikuti unduh pada sesi baru diuji dengan fixture browser sintetis; ini bukan klaim bahwa reload loop intranet sudah diperbaiki. Diagnostik blocking tersedia untuk membuktikan sebab loop tanpa membuka seluruh request.

## Form unduhan

Label terlihat terus; placeholder tidak menggantikan label. Pengaturan bukan langkah wajib untuk login manual. NPWP/tahun ditampilkan lagi selama proses. Validasi existing berjalan pada submit/start dan menaruh error dekat field; jangan mengklaim validasi saat blur sudah ada. Validasi tambahan tidak boleh memarahi pengguna ketika baru mengetik satu angka.

Error berada di field; fokus ke kesalahan pertama dan teks tetap dipertahankan. Tidak menghapus titik/spasi, memperbaiki tahun dua digit, atau menghilangkan nol awal secara otomatis. Klik/Enter/shortcut melewati guard start yang sama; satu pekerjaan aktif.

Teks utama **Mulai unduh** mengikuti Alt+M; Hentikan tetap Alt+S. Pengaturan Alt+P; Cek login Alt+C. Jangan menggarisbawahi huruf yang salah; tampilkan shortcut dalam bantuan. Enter global tidak boleh menyetujui dialog penggantian tanpa fokus/aksi yang tepat.

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

Sumber: [controller](https://github.com/cepeter-job/spt-downloader/blob/977b06846554ca1f2e5af512a69fb201f2cbe8d1/spt_desktop/controller.py), [events](https://github.com/cepeter-job/spt-downloader/blob/977b06846554ca1f2e5af512a69fb201f2cbe8d1/spt_desktop/events.py), dan [worker](https://github.com/cepeter-job/spt-downloader/blob/977b06846554ca1f2e5af512a69fb201f2cbe8d1/spt_desktop/worker.py). View tidak membuat event sukses sendiri.

`verified` pada detail menyatakan capture lengkap di kelompok yang diproses, bukan kebenaran pajak. `processed - verified` bukan jumlah seluruh kegagalan. Counter tidak tersedia bukan nol; saat stage berganti, jangan memakai denominator inventaris sebagai denominator detail.

Progress berbobot tahap tetap berbeda dari jumlah SPT terpilih, waktu tersisa, atau persen dokumen lengkap. Sesudah reply pemilihan diterima controller, hitungan detail sudah dimulai dari `0/N` dengan `verified=0` untuk N yang disetujui; jangan memulainya dari ukuran inventaris atau menjadikan 0/N sebagai bukti kegagalan. Label **Proses keseluruhan**; rincian menjelaskan maknanya. Jangan membuat angka naik saat menunggu consent atau mengubah persen demi animasi. Terminal tidak membawa seluruh counter/manifest: simpan bukti terakhir job yang sama dan sembunyikan metrik yang tidak tersedia.

## Pemilihan SPT

Gunakan dialog native dengan pencarian dan Treeview multi-select: Jenis pajak, Masa pajak, Normal/pembetulan, ID SPT. Nilai sumber tetap literal. Source ID bukan IID widget; gunakan IID lokal yang dipetakan kembali ke ID teramati.

Saat dialog dibuka, urutan tampilan default adalah **PPh Badan → PPh Pasal 21/26 → PPh Unifikasi → PPN**, lalu jenis lain. Caption dikenali utuh secara case-insensitive; teks sumber tidak diubah. Dalam setiap jenis, tahun menaik, masa Januari–Desember, lalu Normal → Pembetulan 1 → Pembetulan 2 dan seterusnya mengikuti aturan sorting yang ada. Jenis lain diurutkan berdasarkan caption; kunci yang setara tetap mengikuti urutan inventaris.

Tidak perlu klik header untuk memakai urutan default. Klik header **Jenis pajak** tetap memakai A–Z, kemudian Z–A; filter/clear mempertahankan urutan aktif. Daftar awal tidak memilih SPT otomatis. Perubahan filter tetap mengosongkan pilihan, dan konfirmasi mengirim ID terpilih menurut urutan inventaris asli—bukan urutan visual atau urutan ekspor.

Awal tidak terpilih; **Sedot SPT terpilih** nonaktif sampai pilihan sah ada. Filter memakai query casefold/trim, bukan mengubah NPWP. Mengubah filter mengosongkan pilihan; jangan mengirim hidden selection. Tampilkan jumlah dipilih, terlihat, dan inventaris. Bedakan pencarian tanpa hasil dari inventaris kosong.

Confirm memakai `controller.respond('selection', request_id, {'selected_ids': [...]})`. Payload hanya subset yang terlihat dan dikonfirmasi. X/Escape/Hentikan membatalkan job tanpa memilih semua. Fokus awal pada pencarian; Ctrl/Shift dan keyboard Treeview tetap tersedia.

Request terikat `job_id`/operasi/`request_id`, hanya satu pending dan satu jawaban. Stop/terminal menginvalidasi dialog sebelum callback lain dapat berjalan. Callback lama tidak boleh menyetujui atau menghentikan job baru. Tenggat worker 600 detik, tanpa auto-consent. `respond=False` tidak berarti keputusan diterima. Sumber: [App](https://github.com/cepeter-job/spt-downloader/blob/977b06846554ca1f2e5af512a69fb201f2cbe8d1/spt_desktop/app.py), [interaction](https://github.com/cepeter-job/spt-downloader/blob/977b06846554ca1f2e5af512a69fb201f2cbe8d1/spt_desktop/interaction.py).

**Usulan, belum implemented:** batching render/filter untuk daftar besar. Baseline memasukkan ulang seluruh hasil filter melalui loop sinkron di `selection_dialog.filter_records`; tidak ada worker render/chunk-generation. Jika batching diterapkan kelak, jangan memotong data; kunci submit selama generasi belum selesai dan tolak hasil stale berdasarkan token job/request. Batas dan pengukuran performa mengikuti spesifikasi, bukan klaim baseline sudah diuji untuk semua ukuran daftar.

## Penggantian file

Penggantian `resume.xlsx` saja berlangsung otomatis setelah verifikasi scope dan race. Jika SPT/PDF terpilih akan diganti, tampilkan folder persis dari request dan semua path yang akan diganti, termasuk PDF bila ada. Jangan hanya menampilkan basename atau memilih sendiri folder terakhir. Scroll dua arah tersedia. **Jangan ganti** fokus awal; X/Escape sama dengan jawaban `overwrite=False`. **Ganti file tersebut** mengirim `True`. Alt+S tetap Stop langsung.

Jelaskan bahwa file diganti seluruhnya, bukan merge baris. SPT lain dalam file yang diganti tidak otomatis dipertahankan. File masa/model lain yang tidak diganti tetap ada. Untuk folder existing yang lolos verifikasi, `coretax.write_folder_resume` membuat indeks gabungan hasil baru dan workbook lama yang dipertahankan; bukan hanya daftar pilihan baru. COMPLETE job tetap berlaku untuk pilihan proses saat ini. Jika penggantian ditolak, resume lama juga tidak dipublikasikan ulang. Setelah setuju, tunggu terminal dan verifikasi backend; jangan langsung menampilkan sukses.

Worker baseline mengirim `folder`, tetapi dialog lama menerima payload tanpa folder. Spesifikasi mengusulkan menonaktifkan approve pada payload tanpa konteks folder; ini penguatan yang perlu regresi tersendiri, bukan perilaku baseline yang sudah terbukti. Pemeriksaan identitas folder/file, hash, rollback, dan custody PDF tetap milik backend.

## Panel hasil

Buka folder hanya memakai path yang disahkan controller. COMPLETE memerlukan terminal sah, exit code sesuai, output valid, dan cleanup selesai. COMPLETE berlaku untuk subset terpilih, bukan seluruh tahun. Hasil parsial boleh dibuka bila lokasi hasil sah, dengan status belum lengkap yang tetap terlihat. Tanpa output sah, tombol buka tidak tersedia.

Petunjuk hasil: “Simpan seluruh folder hasil beserta subfoldernya. Jangan mengganti nama file agar tautannya tetap berfungsi.” Struktur Excel adalah per jenis pajak, masa/tahun sumber, dan **Model SPT literal**. Semua form dalam sebuah workbook berasal dari model itu saja. Nilai sumber serta tautan relatif tetap; Normal dan pembetulan yang berbeda tidak digabung di satu workbook. File gabungan lama diverifikasi sebelum memilih folder baru, bukan ditulis ulang/dihapus diam-diam.

PDF laporan keuangan/auditan Badan dapat ikut disimpan jika tersedia lewat tautan baca yang didukung dan lolos pemeriksaan. BPE/lampiran lain tetap tidak dijanjikan. Metadata bukan bukti byte PDF tersimpan. Jangan menampilkan jumlah PDF atau daftar file aktual tanpa data presentasi yang sah. Kalimat lama yang menolak semua PDF tidak lagi digunakan.

**resume.xlsx** bukan kemampuan resume GUI. Data sementara yang tersedia tetap dipertahankan saat pembatalan, tetapi gagal sejak awal belum tentu membuat checkpoint. Memulai lagi adalah pekerjaan baru.

Folder hilang: jelaskan mungkin dipindahkan/dihapus. Folder ada tetapi gagal dibuka: jelaskan kegagalan membuka. Jangan membuat status COMPLETE baru atau menebak lokasi pengganti.

## Pengaturan dan cek login

Urutan widget existing: **Akun / username**, **Password baru**, **Browser**, **Sumber detail SPT**, checkbox **jalankan proses sedot di background**. Sumber detail menyediakan **DOM** dan **JSON-hybrid (pilot)**; profil desktop baru/mode hilang atau tidak sah memakai `json-first`, preferensi `dom` atau `json-first` yang sah dipertahankan. CLI/library tetap default DOM tanpa opsi eksplisit. **Buka folder log** sudah tersedia; tindakan membuka folder tidak mengirim isinya ke pihak lain. Origin Satu ditetapkan aplikasi, bukan combobox atau URL bebas. Helper menjelaskan login otomatis dan mode akun kosong/manual. Microsoft Edge/Google Chrome dipetakan ke `msedge`/`chrome`.

Password kosong mempertahankan entri sesuai kontrak; perubahan akun yang perlu password baru dijelaskan dekat field. Hapus login hanya menghapus entri aplikasi pada origin Satu tetap (`LOGIN_ORIGIN`), bukan pilihan situs pengguna, akun portal, entri legacy Coretax, atau seluruh Credential Manager. Jangan menjanjikan transaksi atomik Credential Manager dan file preferensi.

Simpan bukan bukti login berhasil. Cek login nonaktif saat dirty, akun belum tersedia, atau operasi lain aktif. Dirty dihitung dari nilai dibanding preferensi tersimpan ditambah password baru; mengembalikan nilai semula tidak meninggalkan dirty palsu. Cek memakai operasi tersendiri, tidak memerlukan NPWP/tahun, tidak mengambil SPT, dan tidak menimpa hasil ekspor terakhir.

| Status | Label dan arti |
| --- | --- |
| Belum diuji | Login belum dicek, bukan gagal atau berhasil. |
| Aktif | Mengecek login… satu percobaan; Batalkan cek tersedia. |
| `LOGIN_OK` | Login berhasil; akun/password tersimpan dipakai dan akses siap. |
| `LOGIN_UNVERIFIED` | Password belum bisa dipastikan; bukan bukti benar/salah. |
| `LOGIN_MANUAL` | Perlu login di browser saat mulai unduh. |
| `LOGIN_BLOCKED` | Login belum bisa dicek; periksa akses Coretax/Satu dan akun. |
| `LOGIN_ERROR` / `ERROR` | Cek login belum berhasil; bukan hasil ekspor. |
| Batal diminta | Membatalkan cek login… tunggu cleanup/terminal. |
| `CANCELLED` | Cek login dibatalkan; tidak ada SPT diunduh. |

Jangan mengklasifikasikan sebab melalui substring pesan. Jika reason code aman belum ada, pakai pesan generik. Perubahan protokol alasan membutuhkan rancangan/tes terpisah, bukan diselipkan sebagai copy update.

## Dialog dan fokus

| Pemicu | Judul | Pilihan dan Escape/X |
| --- | --- | --- |
| Tutup saat unduhan aktif | Hentikan unduhan dan tutup aplikasi? | Kembali; Hentikan dan tutup. Escape/X = Kembali. |
| Hapus login | Hapus login yang disimpan? | Batal; Hapus login. Escape/X = Batal. |
| Tutup Pengaturan dirty (**usulan**) | Perubahan belum disimpan | Sasaran: Simpan; Abaikan; Kembali. Escape/X = Kembali. Belum ada pada baseline. |
| Pemilihan SPT | Pilih SPT yang akan diunduh | Sedot SPT terpilih; Hentikan unduhan. Escape/X = Stop. |
| Penggantian | Ganti hasil sebelumnya? | Jangan ganti; Ganti file tersebut. Escape/X = false. |

Pilihan aman fokus awal pada keputusan destruktif. Tidak ada Return global yang menyetujui overwrite. Saat cek login aktif, Escape/Tutup membatalkan cek dulu dan menunggu cleanup. Tombol Stop langsung membatalkan tanpa konfirmasi tambahan. Dialog mengembalikan fokus ke pemicu yang masih valid; progress tidak mencuri fokus. Setelah terminal ekspor, App mengarahkan fokus ke Buka hasil jika tersedia atau Mulai unduh, bukan Entry yang bisa tergulir keluar viewport. Bersihkan grab, traces, dan after sebelum destroy/job berikutnya.

Konfirmasi edit belum disimpan belum ada pada baseline: `settings.refresh`/`check` menghitung dirty untuk menonaktifkan pengecekan, tetapi `settings.close` saat idle langsung membersihkan variabel/password lalu menutup dialog tanpa keputusan Simpan/Abaikan. Saat cek aktif, close membatalkan cek dan menunggu cleanup; jalur tersebut harus dipertahankan dalam usulan berikutnya. Jika Simpan gagal, jangan menutup dialog atau menampilkan sukses. Uji kegagalan kedua penyimpanan dan delete secara terpisah; salah satu write dapat sudah berhasil.

## Aksesibilitas dan performa

Label terlihat dan fokus biru belum membuktikan aksesibilitas native. Uji name/role/value/focus melalui UI Automation, Narrator/NVDA, terutama tabel pilihan, input, modal, dan hasil. Kekurangan kontrol kritis dicatat sebagai blocker, bukan alasan mengganti toolkit diam-diam.

Uji DPI 100/125/150/200%, pembesaran teks, multi-monitor, High Contrast, Tab/Shift+Tab, Enter/Space/Escape, dan shortcut. Reflow harus mempertahankan informasi scope; jangan meluluskan clipping dengan minimum jendela melebihi work area. Sasaran ukuran/performa B-TK-1 adalah target belum terukur.

Ukur GUI terpisah dari worker/browser; batasi event, status history, row-batch, serta callback tertunda. Pertahankan polling baseline dan update widget inkremental. Seluruh pytest, product import, Tk/browser fixture, source/frozen self-test, build, dan EXE hanya di GitHub runner sesuai [AGENTS.md](../../AGENTS.md). Pemeriksaan dokumen lokal bukan bukti runtime atau aksesibilitas.

Kontrak workbook terkonsolidasi: Ringkasan, Daftar SPT, dan Audit hanya berada di `resume.xlsx`. Workbook SPT terpisah per masa/tahun dan Model SPT literal, berisi worksheet form/tab untuk model itu saja, tanpa banner/header/footer administratif atau sheet administratif tersembunyi. Hyperlink dari resume menuju form tetap relatif.
