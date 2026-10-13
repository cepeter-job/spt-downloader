# Pola layar, interaksi, dan status

[Kembali ke panduan](README.md) · [Spesifikasi B-TK-1](../superpowers/specs/2026-10-13-magicpath-b-tkinter-design.md)

**Baseline:** `be67f5153a07ce100048d67191a02ca1d0fca1db`, 13 Oktober 2026. Pedoman ini mempertahankan fitur selection/overwrite/PDF yang sudah ada. Tampilan B, konfirmasi edit Pengaturan, serta penguatan presentasi yang ditetapkan spesifikasi belum diklaim terimplementasi.

## Form unduhan

Label terlihat terus; placeholder tidak menggantikan label. Pengaturan bukan langkah wajib untuk login manual. NPWP/tahun ditampilkan lagi selama proses. Validasi saat blur/submit, bukan memarahi pengguna ketika baru mengetik satu angka.

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

Sumber: [controller](https://github.com/cepeter-job/spt-downloader/blob/be67f5153a07ce100048d67191a02ca1d0fca1db/spt_desktop/controller.py), [events](https://github.com/cepeter-job/spt-downloader/blob/be67f5153a07ce100048d67191a02ca1d0fca1db/spt_desktop/events.py), dan [worker](https://github.com/cepeter-job/spt-downloader/blob/be67f5153a07ce100048d67191a02ca1d0fca1db/spt_desktop/worker.py). View tidak membuat event sukses sendiri.

`verified` pada detail menyatakan capture lengkap di kelompok yang diproses, bukan kebenaran pajak. `processed - verified` bukan jumlah seluruh kegagalan. Counter tidak tersedia bukan nol; saat stage berganti, jangan memakai denominator inventaris sebagai denominator detail.

Progress berbobot tahap, bukan waktu tersisa atau persen dokumen lengkap. Label **Proses keseluruhan**; rincian menjelaskan maknanya. Jangan membuat angka naik saat menunggu consent atau mengubah persen demi animasi. Terminal tidak membawa seluruh counter/manifest: simpan bukti terakhir job yang sama dan sembunyikan metrik yang tidak tersedia.

## Pemilihan SPT

Gunakan dialog native dengan pencarian dan Treeview multi-select: Jenis pajak, Masa pajak, Normal/pembetulan, ID SPT. Nilai sumber tetap literal. Source ID bukan IID widget; gunakan IID lokal yang dipetakan kembali ke ID teramati.

Awal tidak terpilih; **Sedot SPT terpilih** nonaktif sampai pilihan sah ada. Filter memakai query casefold/trim, bukan mengubah NPWP. Mengubah filter mengosongkan pilihan; jangan mengirim hidden selection. Tampilkan jumlah dipilih, terlihat, dan inventaris. Bedakan pencarian tanpa hasil dari inventaris kosong.

Confirm memakai `controller.respond('selection', request_id, {'selected_ids': [...]})`. Payload hanya subset yang terlihat dan dikonfirmasi. X/Escape/Hentikan membatalkan job tanpa memilih semua. Fokus awal pada pencarian; Ctrl/Shift dan keyboard Treeview tetap tersedia.

Request terikat `job_id`/operasi/`request_id`, hanya satu pending dan satu jawaban. Stop/terminal menginvalidasi dialog sebelum callback lain dapat berjalan. Callback lama tidak boleh menyetujui atau menghentikan job baru. Tenggat worker 600 detik, tanpa auto-consent. `respond=False` tidak berarti keputusan diterima. Sumber: [App](https://github.com/cepeter-job/spt-downloader/blob/be67f5153a07ce100048d67191a02ca1d0fca1db/spt_desktop/app.py), [interaction](https://github.com/cepeter-job/spt-downloader/blob/be67f5153a07ce100048d67191a02ca1d0fca1db/spt_desktop/interaction.py).

Daftar besar dirender bertahap tanpa memotong data. Selama generasi filter/render belum selesai, submit nonaktif. Hasil tertunda selalu memeriksa token job/request lagi. Batas dan pengukuran performa mengikuti spesifikasi, bukan klaim baseline sudah diuji dengan semua ukuran daftar.

## Penggantian file

Tampilkan folder persis dari request dan semua path yang akan diganti, termasuk PDF bila ada. Jangan hanya menampilkan basename atau memilih sendiri folder terakhir. Scroll dua arah tersedia. **Jangan ganti** fokus awal; X/Escape sama dengan jawaban `overwrite=False`. **Ganti file tersebut** mengirim `True`. Alt+S tetap Stop langsung.

Jelaskan bahwa file diganti seluruhnya, bukan merge baris. SPT lain dalam file yang diganti tidak otomatis dipertahankan. File masa lain yang tidak diganti tetap ada; `resume.xlsx` baru hanya mengindeks pilihan proses saat ini. Setelah setuju, tunggu terminal dan verifikasi backend; jangan langsung menampilkan sukses.

Worker baseline mengirim `folder`, tetapi dialog lama menerima payload tanpa folder. Spesifikasi mengusulkan menonaktifkan approve pada payload tanpa konteks folder; ini penguatan yang perlu regresi tersendiri, bukan perilaku baseline yang sudah terbukti. Pemeriksaan identitas folder/file, hash, rollback, dan custody PDF tetap milik backend.

## Panel hasil

Buka folder hanya memakai path yang disahkan controller. COMPLETE memerlukan terminal sah, exit code sesuai, output valid, dan cleanup selesai. COMPLETE berlaku untuk subset terpilih, bukan seluruh tahun. Hasil parsial boleh dibuka bila lokasi hasil sah, dengan status belum lengkap yang tetap terlihat. Tanpa output sah, tombol buka tidak tersedia.

Petunjuk hasil: “Simpan seluruh folder hasil beserta subfoldernya. Jangan mengganti nama file agar tautannya tetap berfungsi.” Struktur Excel per masa, sheet form Badan, nilai sumber, dan tautan relatif tidak berubah.

PDF laporan keuangan/auditan Badan dapat ikut disimpan jika tersedia lewat tautan baca yang didukung dan lolos pemeriksaan. BPE/lampiran lain tetap tidak dijanjikan. Metadata bukan bukti byte PDF tersimpan. Jangan menampilkan jumlah PDF atau daftar file aktual tanpa data presentasi yang sah. Kalimat lama yang menolak semua PDF tidak lagi digunakan.

**resume.xlsx** bukan kemampuan resume GUI. Data sementara yang tersedia tetap dipertahankan saat pembatalan, tetapi gagal sejak awal belum tentu membuat checkpoint. Memulai lagi adalah pekerjaan baru.

Folder hilang: jelaskan mungkin dipindahkan/dihapus. Folder ada tetapi gagal dibuka: jelaskan kegagalan membuka. Jangan membuat status COMPLETE baru atau menebak lokasi pengganti.

## Pengaturan dan cek login

Urutan: Situs login, Nama pengguna, Password baru, Browser, checkbox **jalankan proses sedot di background**. Helper menjelaskan browser tetap muncul saat perlu login. Domain berasal dari allowlist, terlihat penuh, bukan URL bebas. Microsoft Edge/Google Chrome dipetakan ke `msedge`/`chrome`.

Password kosong mempertahankan entri sesuai kontrak; perubahan akun yang perlu password baru dijelaskan dekat field. Hapus login hanya menghapus entri aplikasi untuk situs terpilih, bukan akun portal atau seluruh Credential Manager. Jangan menjanjikan transaksi atomik Credential Manager dan file preferensi.

Simpan bukan bukti login berhasil. Cek login nonaktif saat dirty, akun belum tersedia, atau operasi lain aktif. Dirty dihitung dari nilai dibanding preferensi tersimpan ditambah password baru; mengembalikan nilai semula tidak meninggalkan dirty palsu. Cek memakai operasi tersendiri, tidak memerlukan NPWP/tahun, tidak mengambil SPT, dan tidak menimpa hasil ekspor terakhir.

| Status | Label dan arti |
| --- | --- |
| Belum diuji | Login belum dicek, bukan gagal atau berhasil. |
| Aktif | Mengecek login… satu percobaan; Batalkan cek tersedia. |
| `LOGIN_OK` | Login berhasil; akun/password tersimpan dipakai dan akses siap. |
| `LOGIN_UNVERIFIED` | Password belum bisa dipastikan; bukan bukti benar/salah. |
| `LOGIN_MANUAL` | Perlu login di browser saat mulai unduh. |
| `LOGIN_BLOCKED` | Login belum bisa dicek; periksa situs dan akun. |
| `LOGIN_ERROR` / `ERROR` | Cek login belum berhasil; bukan hasil ekspor. |
| Batal diminta | Membatalkan cek login… tunggu cleanup/terminal. |
| `CANCELLED` | Cek login dibatalkan; tidak ada SPT diunduh. |

Jangan mengklasifikasikan sebab melalui substring pesan. Jika reason code aman belum ada, pakai pesan generik. Perubahan protokol alasan membutuhkan rancangan/tes terpisah, bukan diselipkan sebagai copy update.

## Dialog dan fokus

| Pemicu | Judul | Pilihan dan Escape/X |
| --- | --- | --- |
| Tutup saat unduhan aktif | Hentikan unduhan dan tutup aplikasi? | Kembali; Hentikan dan tutup. Escape/X = Kembali. |
| Hapus login | Hapus login yang disimpan? | Batal; Hapus login. Escape/X = Batal. |
| Tutup Pengaturan dirty | Perubahan belum disimpan | Simpan; Abaikan; Kembali. Escape/X = Kembali. |
| Pemilihan SPT | Pilih SPT yang akan diunduh | Sedot SPT terpilih; Hentikan unduhan. Escape/X = Stop. |
| Penggantian | Ganti hasil sebelumnya? | Jangan ganti; Ganti file tersebut. Escape/X = false. |

Pilihan aman fokus awal pada keputusan destruktif. Tidak ada Return global yang menyetujui overwrite. Saat cek login aktif, Escape/Tutup membatalkan cek dulu dan menunggu cleanup. Tombol Stop langsung membatalkan tanpa konfirmasi tambahan. Dialog mengembalikan fokus ke pemicu yang masih valid; progress tidak mencuri fokus. Bersihkan grab, traces, dan after sebelum destroy/job berikutnya.

Konfirmasi edit belum disimpan belum ada pada baseline. Jika Simpan gagal, jangan menutup dialog atau menampilkan sukses. Uji kegagalan kedua penyimpanan dan delete secara terpisah; salah satu write dapat sudah berhasil.

## Aksesibilitas dan performa

Label terlihat dan fokus biru belum membuktikan aksesibilitas native. Uji name/role/value/focus melalui UI Automation, Narrator/NVDA, terutama tabel pilihan, input, modal, dan hasil. Kekurangan kontrol kritis dicatat sebagai blocker, bukan alasan mengganti toolkit diam-diam.

Uji DPI 100/125/150/200%, pembesaran teks, multi-monitor, High Contrast, Tab/Shift+Tab, Enter/Space/Escape, dan shortcut. Reflow harus mempertahankan informasi scope; jangan meluluskan clipping dengan minimum jendela melebihi work area. Sasaran ukuran/performa B-TK-1 adalah target belum terukur.

Ukur GUI terpisah dari worker/browser; batasi event, status history, row-batch, serta callback tertunda. Pertahankan polling baseline dan update widget inkremental. Seluruh pytest, product import, Tk/browser fixture, source/frozen self-test, build, dan EXE hanya di GitHub runner sesuai [AGENTS.md](../../AGENTS.md). Pemeriksaan dokumen lokal bukan bukti runtime atau aksesibilitas.
