# Menulis bahasa antarmuka

**Baseline aktif, 21 Oktober 2026:** `ecbd9878aa732a379ba94ef848764f9815445003`. Permintaan PR #14 sudah terintegrasi: footer nama pribadi dan ID `app.credit` dihapus. Katalog kini berisi **51 ID**, termasuk `app.bugreport`; lima teks pemilik lainnya tetap. Setiap workbook masa/model berisi form model itu saja; Ringkasan/Daftar SPT/Audit ada di `resume.xlsx`. Resume boleh diganti otomatis setelah verifikasi, sedangkan SPT/PDF yang akan tertimpa tetap membutuhkan persetujuan. Lihat [kontrak baseline](baseline-2026-10-21.md).

[Kembali ke panduan](README.md) · [Spesifikasi B-TK-1](../superpowers/specs/2026-10-13-magicpath-b-tkinter-design.md)

Pengaturan menyediakan **Simpan**, **Hapus login**, dan **Tutup**. Simpan mempertahankan dialog dan hanya menyimpan perubahan; login otomatis dilakukan saat **Mulai unduh**. Tombol Cek login/Batalkan cek dan shortcut Alt+C dihapus. `settings.origin.label` tetap ada dalam katalog, tetapi origin Satu ditetapkan aplikasi dan tidak menjadi field bebas.

## Nada yang digunakan

Tulis seperti memberi petunjuk kepada rekan kerja yang sedang memakai aplikasi. Langsung ke hal yang perlu diketahui. Gunakan bahasa Indonesia sehari-hari yang tetap pantas untuk pekerjaan: **sudah**, **belum**, **bisa**, **coba**, **simpan**, dan **buka**. Hindari sapaan berulang, jargon mesin, emoji, atau berpura-pura menjadi manusia dengan berkata “saya sedang bekerja”.

**Pengecualian eksplisit pemilik:** pertahankan judul humor dan kata “Sedot” yang dikunci di bawah. Jangan menghapusnya memakai aturan gaya umum. Humor tidak diperluas ke error, ancaman kehilangan data, atau persetujuan penggantian.

Natural tidak berarti longgar secara fakta. **Belum lengkap** tetap peringatan. **Password belum bisa dipastikan** bukan password salah. Jangan menyebut data aman, benar secara pajak, lengkap untuk seluruh tahun, atau tersimpan jika pemeriksaan belum membuktikannya.

Petunjuk langsung, berorientasi tindakan, dan tidak menyalahkan pengguna sejalan dengan [panduan penulisan Windows](https://learn.microsoft.com/en-us/windows/apps/design/style/writing-style). Pilihan kata Indonesia dan pengecualian pemilik adalah keputusan proyek ini.

## Aturan praktis

Satu pesan memuat satu pokok utama. Judul menjawab apa yang terjadi. Isi menjelaskan dampak atau langkah berikutnya, biasanya satu atau dua kalimat. Tombol menyebut tindakan, bukan **Ya**, **Lanjut**, atau **OK** jika akibatnya belum jelas.

Gunakan sentence case; label/tombol tanpa titik, kalimat utuh memakai titik. Kata “Anda” tidak harus ada di setiap kalimat. Jangan menambahkan “mohon”, “silakan”, “harap”, atau “dengan demikian” hanya agar terdengar sopan. Teks pemilik yang dikunci mempertahankan kapitalisasi dan tanda baca aslinya.

Jangan menjanjikan waktu yang tidak diketahui. **Menyimpan hasil unduhan** lebih tepat daripada **Sebentar lagi selesai**. Tenggat login 5 menit berlaku pada kesempatan login manual, bukan perkiraan durasi pekerjaan. Consent memiliki tenggat 600 detik pada worker; tidak berarti GUI mengetahui countdown exact. Batas terminasi worker 15 detik bukan janji seluruh jendela pasti tutup dalam 15 detik.

Istilah pajak dan nama berkas yang membantu pencarian tetap dipertahankan: NPWP, tahun pajak, masa, pembetulan, `resume.xlsx`, dan **Audit**. Tahun pajak bukan tahun pelaporan. Nilai metadata tabel tetap literal. COMPLETE berlaku untuk pilihan saat ini serta cakupan yang didukung, bukan salinan lengkap seluruh Coretax.

## Tiga lapis teks

**Tampilan utama:** bahasa untuk menyelesaikan pekerjaan. Contoh: “Hasil unduhan belum lengkap. Lihat lembar Audit di resume.xlsx untuk rinciannya.”

**Rincian opsional:** kode status, tahap, atau konteks aman yang diperlukan untuk dukungan. Tidak ada password, token, cookie, isi SPT, atau exception mentah. Kode `PARTIAL` boleh tampil di sini, bukan satu-satunya label hasil. Path/ID yang diperlukan dialog persetujuan tetap hanya pada jendela lokal, bukan log publik.

**Dokumentasi developer/reviewer:** `job_id`, `request_id`, schema, exit code, cleanup, runtime, dan invariants. Jangan bocorkan kalimat “controller harus selesai” ke layar pengguna. Watermark data contoh dan pemilih skenario MagicPath bukan fungsi aplikasi produksi.

## Teks khusus yang tidak diganti

| ID | Teks exact |
| --- | --- |
| `app.title` | Coretax SPT downloader : kalau bisa ribet, kenapa dibikin gampang |
| `settings.background.label` | jalankan proses sedot di background |
| `results.location_hint` | Hasil Sedot berada di folder Downloads Windows |
| `app.subtitle` | Coretax → Excel · for personal use only |
| `app.bugreport` | bugreport : sharmila@kemenkeu.go.id |
| `selection.confirm` | Sedot SPT terpilih |

Title harus ada pada caption dan satu `Title.TLabel` yang nyata, bukan hanya disisipkan ke metadata. `results.location_hint` tampil tepat sekali. Checkbox mempertahankan binding `headless`. Sumber: [tes requested text](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/tests/test_desktop_requested_text.py) dan [tes pemilihan](https://github.com/cepeter-job/spt-downloader/blob/ecbd9878aa732a379ba94ef848764f9815445003/tests/test_desktop_selection_gui.py).

## Kosakata yang konsisten

| Istilah teknis | Teks pengguna | Catatan |
| --- | --- | --- |
| Cakupan ekspor | Data yang akan diunduh | Sesudah inventaris, pengguna memilih SPT. |
| Origin login | Login melalui Coretax → Satu | Origin tetap milik aplikasi; tidak ada URL bebas atau pilihan situs pada Pengaturan saat ini. |
| Kredensial | Akun dan password; login tersimpan | **Hapus login** menghapus entri aplikasi dengan konfirmasi; **Simpan** menyimpan perubahan. |
| Headless | Gunakan checkbox pemilik yang dikunci | Tambahkan: “Jika memungkinkan. Browser tetap muncul saat perlu login.” |
| Workbook | File Excel | Nama dan subfolder asli tidak diubah. |
| Checkpoint | Data sementara | Tidak menjanjikan otomatis dilanjutkan atau selalu sudah dibuat. |
| COMPLETE | Selesai | Hanya setelah controller mengesahkan hasil subset. |
| PARTIAL | Belum lengkap | Bukan “selesai dengan catatan” atau centang hijau. |
| Verified, hitungan SPT | Lengkap | Pemeriksaan kelengkapan capture, bukan kebenaran pajak. |
| Belum terverifikasi | Belum pasti lengkap | Bukan otomatis gagal atau belum diproses. |
| Ringkasan pekerjaan | Ringkasan unduhan | NPWP/tahun, jumlah pilihan hanya bila diketahui. |

## Katalog teks inti

Tabel ini menyalin nilai ID yang ada, bukan inventaris widget yang semuanya sudah digunakan. Teks pada source di luar katalog dan penggantian labelnya harus direview bersama self-test.

| ID | Teks |
| --- | --- |
| `form.title` | Masukkan NPWP dan tahun pajak |
| `form.help` | Setelah daftar muncul, pilih SPT yang ingin diunduh. |
| `form.npwp.label` | NPWP (16 digit) |
| `form.npwp.help` | Ketik 16 angka, tanpa spasi, titik, atau tanda hubung. |
| `form.npwp.error` | Isi NPWP dengan 16 angka (0–9), tanpa pemisah. |
| `form.year.help` | Gunakan tahun pajak, bukan tahun pelaporan. |
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
| `settings.delete` | Hapus login |
| `download.exported.title` | File Excel sudah dibuat |
| `download.complete.title` | File Excel sudah siap |
| `download.complete.body` | Hasil untuk SPT yang dipilih sudah disimpan dan diperiksa. |
| `download.partial.title` | Hasil unduhan belum lengkap |
| `download.stopping.title` | Menghentikan unduhan… |
| `download.cancelled.title` | Unduhan dihentikan |
| `download.error.title` | Unduhan belum berhasil |

### ID lainnya pada katalog yang sama

Baris berikut melengkapi katalog 51 ID, termasuk dialog yang sudah diimplementasikan. Placeholder nama/jumlah harus mengikuti pemeriksaan `copy_text`; jangan mengubah nilai tidak diketahui menjadi nol.

| ID | Teks exact |
| --- | --- |
| `selection.title` | Pilih SPT yang akan diunduh |
| `selection.help` | gunakan SHIFT untuk ngeblok SPT, dan CTRL untuk memilih multi SPT<br><br>Pilih SPT yang ingin diunduh. Rincian hanya diambil setelah Anda mengonfirmasi pilihan. |
| `selection.search.label` | Cari jenis pajak, masa, pembetulan, atau ID SPT |
| `selection.empty` | Daftar ini tidak memuat SPT yang bisa dipilih. |
| `selection.focused_id` | ID SPT yang disorot |
| `selection.keyboard_hint` | Pilih beberapa SPT dengan Ctrl atau Shift. Urutkan jenis: Alt+J. |
| `selection.summary` | {selected} SPT dipilih · {visible} dari {inventory} SPT ditampilkan. |
| `selection.no_match` | Tidak ada SPT yang cocok dengan pencarian. |
| `selection.filter_reset` | Pencarian berubah. Pilih lagi SPT yang akan diunduh. |
| `download.details.body` | {processed} dari {total} SPT sudah diproses. Kelengkapan {verified} SPT sudah diperiksa. |
| `download.publish.title` | Menyimpan hasil unduhan |
| `overwrite.title` | Ganti hasil sebelumnya? |
| `overwrite.folder.label` | Folder hasil sebelumnya |
| `overwrite.help` | File dalam daftar ini akan diganti seluruhnya. Isi file lama tidak digabung dengan hasil baru. |
| `overwrite.files_count` | {count} file akan diganti. |
| `overwrite.keep_hint` | Pilih Jangan ganti untuk menghentikan publikasi dan mempertahankan hasil sebelumnya. |
| `overwrite.context_missing` | Folder hasil sebelumnya belum tersedia. Keputusan penggantian belum dikirim. |
| `overwrite.decline` | Jangan ganti |
| `overwrite.confirm` | Ganti file tersebut |
| `settings.background.help` | Jika memungkinkan. Browser tetap muncul saat perlu login. |
| `settings.dirty.title` | Perubahan belum disimpan |

Sumber aktif adalah `spt_desktop/ui_copy.py` pada commit baseline, bukan daftar usulan ID di spesifikasi historis. Perubahan copy ID yang sama harus selaras; jangan membuat ID baru hanya karena susunan kata diperbaiki.

## Sumber detail, browser, dan bantuan yang sudah tersedia

Caption Pengaturan saat ini: **Sumber detail SPT**, nilai **DOM** / **JSON-hybrid (pilot)**, serta **Buka folder log**. Nilai internal mode adalah `dom` / `json-first`, bukan `json-hybrid`. Default desktop baru JSON-hybrid tidak mengubah default CLI/library tanpa opsi (DOM) dan tidak menimpa pilihan sah yang tersimpan. Jangan menampilkan “semua data berasal dari JSON”, menyebut fallback sebagai sukses JSON, atau menjanjikan kecepatan tanpa bukti. Mode capture bukan izin melewati login/CAPTCHA/MFA.

Browser ditampilkan sebagai nilai `msedge` / `chrome` pada widget existing; nama manusiawi Microsoft Edge / Google Chrome adalah kandidat penyelarasan, bukan perilaku yang sudah diterapkan. `app.bugreport` hanya teks bantuan yang sudah dikontrak, bukan tombol yang otomatis mengirim email atau log.

## Pesan bersyarat, bukan dugaan

Jika counter detail valid: “{processed} dari {total} SPT sudah diproses. Kelengkapan {verified} SPT sudah diperiksa.” Jangan memasukkan nilai kosong sebagai `0` atau memakai jumlah unit inventaris sebagai total SPT. Terminal tidak membawa manifest file/PDF: jangan membuat counter PDF dari perkiraan.

Untuk hasil parsial, **Buka hasil sementara** hanya tampil bersama judul **Hasil unduhan belum lengkap** dan penjelasan Audit. “Sementara” tidak berarti otomatis diperbarui atau pasti dilengkapi nanti. Tanpa output yang disahkan controller, tombol buka tidak tersedia.

Petunjuk hasil: “Simpan seluruh folder hasil beserta subfoldernya. Jangan mengganti nama file agar tautannya tetap berfungsi.” PDF keuangan/auditan Badan ikut hanya jika tersedia melalui tautan yang didukung dan lolos pemeriksaan. BPE/lampiran lain tidak dijanjikan. Hapus kalimat lama yang mengecualikan seluruh PDF; jangan menggantinya dengan janji semua PDF tersedia.

Penggantian: “File di bawah akan diganti seluruhnya dengan hasil pilihan kali ini. SPT lain yang sebelumnya berada dalam file yang sama tidak ikut dipertahankan. File lain yang tidak tercantum tetap ada.” Jangan menyebut merge data atau semua hasil lama pasti tetap ada. Pada folder yang sudah ada dan lolos verifikasi, `resume.xlsx` baru mengindeks hasil baru bersama workbook sah yang dipertahankan. Status unduhan saat ini tetap hanya menyatakan pilihan job ini; jangan menyebut isi seluruh indeks sebagai data yang baru diunduh.


Pada kegagalan dua penyimpanan, jangan mengatakan “Tidak ada perubahan tersimpan” tanpa bukti. Gunakan “Sebagian perubahan mungkin belum tersimpan. Periksa akses penyimpanan Windows, lalu simpan lagi.” Dialog tetap terbuka. Pembatalan memakai “Data sementara yang sudah dibuat tetap disimpan di komputer”, bukan jaminan checkpoint selalu ada.

## Pemeriksaan naskah

Baca teks dengan suara biasa. Apakah pengguna tahu harus berbuat apa? Hapus jargon, pengulangan, slogan baru yang tidak membantu, permintaan maaf otomatis, dan janji yang tidak bisa dibuktikan. Pertahankan pengecualian pemilik yang dikunci. Sesudah teks berubah, periksa lebar tombol, wrap, shortcut, fokus, serta compact. Jangan meloloskan pesan yang enak dibaca tetapi salah arti. Tes/self-test yang mengikat label lama diperbarui secara eksplisit bersama implementasi, bukan dihapus untuk meloloskan perubahan.
