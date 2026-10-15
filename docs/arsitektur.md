# Arsitektur dan kontrak yang harus dipertahankan

[Kembali ke dokumentasi](README.md)

Aplikasi memiliki mesin capture/export yang dipakai bersama oleh CLI dan desktop. Desktop menambahkan pengelolaan runtime, kredensial, kepemilikan proses, progres, dan publikasi ke Downloads. Perubahan antarmuka tidak boleh memperluas kewenangan mesin capture.

## Peta modul

| Modul | Tanggung jawab |
| --- | --- |
| `coretax.py` | Entry point CLI, autentikasi manual CLI, orkestrasi, verifikasi set workbook, staging, dan rollback publikasi lokal. |
| `coretax_browser.py` | Inventaris daftar, pengamatan respons UI, pemeriksaan origin/identitas, navigasi View, paginasi, serta checkpoint detail. |
| `coretax_exporter.py` | Validasi scope dan nilai, deduplikasi ID, susunan workbook, serta tautan relatif. Tidak membuka browser. |
| `spt_gui.py`, `spt_desktop/app.py` | Entry point dan GUI Tkinter, pengaturan, tombol, serta self-test source/frozen. |
| `spt_desktop/controller.py`, `events.py` | Protokol progres/terminal, otorisasi start, Stop, dan pemrosesan event pada thread GUI. |
| `spt_desktop/runtime.py` | Pemilihan interpreter, resource worker eksplisit, fingerprint, setup dependensi, dan verifikasi kesiapan. |
| `spt_desktop/worker.py` | Proses terisolasi untuk capture/export atau pemeriksaan kredensial. |
| `spt_desktop/auth.py`, `credentials.py` | Login pada form yang diperiksa, challenge manual, serta Windows Credential Manager berbasis origin. |
| `spt_desktop/windows.py` | Instance lock dan Windows Job Object untuk kepemilikan pohon proses. |
| `spt_desktop/paths.py`, `output.py` | Known Folders, nama folder yang aman, verifikasi salinan, dan publikasi Excel ke Downloads. |
| `build_desktop.py` | Paket GUI tipis, bundel `uv`, allowlist resource, dan pemeriksaan executable hasil build. |

GUI memakai stdlib/Tkinter dan tidak mengimpor Playwright atau openpyxl ke prosesnya. Worker memasang dependensi pada runtime terisolasi. `WORKER_FILES` merupakan allowlist eksplisit; modul worker baru harus ditambahkan di sana bersama tes kontraknya. Jangan menggantinya dengan penyalinan direktori rekursif, karena checkout dapat berdampingan dengan profil, hasil, atau environment lokal.

## Identitas, scope, dan provenance

`validate_scope` menerima NPWP tepat 16 digit ASCII. Nol awal merupakan bagian dari identitas. Tahun pajak berada dalam rentang 1900 sampai 2100; input GUI/CLI harus memenuhi bentuk empat digit. Jangan menerapkan `strip()`, menghapus pemisah, mengonversi NPWP menjadi angka, atau memilih kecocokan sebagian untuk membantu input yang salah.

Scope terdiri dari NPWP, tahun, dan `year_basis`. Bawaan `period` memakai masa/tahun pajak; `submission` memakai tanggal penyampaian. Metadata periode yang tidak dapat ditafsirkan secara terverifikasi menjadi error. Pola periode migrasi hanya ditafsirkan sesuai pola teramati yang divalidasi, dan nilai aslinya tetap disimpan.

Rantai provenance yang dijaga:

1. Pencarian kembali ke origin HTTPS dan path pencarian yang diizinkan sebelum NPWP dimasukkan.
2. Tepat satu baris dipilih, dengan sel NPWP sama persis dan nama wajib pajak berasal dari baris tersebut.
3. URL daftar membuktikan identitas wajib pajak. Daftar status lain hanya diikuti bila berasal dari wajib pajak yang sama.
4. Respons daftar harus memiliki skema yang didukung, status sukses eksplisit, dan jumlah baris yang cocok dengan DOM. `TotalRecords` direkonsiliasi dengan seluruh halaman.
5. Kontrol View yang dikenali membuka detail; URL detail harus memuat segmen identitas wajib pajak dan SPT yang dipilih.
6. Checkpoint detail harus cocok dengan scope, ID, metadata, posisi/halaman daftar, serta provenance inventaris sebelum digabungkan.

`RecordId` yang berulang pada beberapa status digabungkan hanya bila metadata konsisten; `source_occurrences` mempertahankan asal kemunculannya. Pembetulan dengan ID berbeda tetap berbeda. Konflik tanggal penyampaian atau metadata lain adalah kegagalan validasi, bukan dasar memilih salah satu nilai.

Metadata scope per-record yang tidak tersedia pada capture lama tidak dapat membuktikan NPWP secara independen. Jangan menyimpulkan provenance legacy yang tidak tersimpan. Capture baru membawa metadata scope; pemeriksaan yang tersedia tetap wajib dilakukan saat ekspor ulang.

## Batas akses baca

`ListObserver` mengamati respons JSON dari tindakan UI milik browser. Ia menyimpan respons terakhir dan nomor urut yang terus bertambah, bukan seluruh riwayat respons dalam RAM. Ia tidak membaca cookie/header autentikasi dan tidak menjalankan request API penulisan tersendiri.

Capture memakai kontrol baca yang sudah dikenali: pencarian wajib pajak, Pilih, navigasi status, View, tab, accordion, ukuran halaman, serta paginasi. Tombol submit, batal SPT, kirim email, pembuatan dokumen, dan aksi baris yang tidak dikenal tidak boleh dijadikan fallback. Bila selector View berubah, hasil tetap terblokir/parsial sampai layout baru diperiksa dan fixture regresinya tersedia.

Konten PDF/BPE/lampiran, pembuatan PDF jarak jauh, serta dialog drill-down tiap baris belum didukung. Tab dinonaktifkan tidak dijelajahi. Capture detail harus memiliki field atau tabel terstruktur yang bermakna; halaman kosong atau layout tak dikenal tidak disertifikasi lengkap.

## Kredensial dan autentikasi desktop

Kredensial hanya boleh diambil dari Windows Credential Manager untuk origin dan akun yang diizinkan. Pengaturan biasa menyimpan browser, headless, origin, dan identifier akun melalui allowlist. Password, token, cookie, atau kode tidak masuk file preferensi maupun event GUI.

Login tersimpan mengikat elemen/form yang telah diperiksa. Origin, identitas kontrol, dan tujuan submit hasil resolusi browser diperiksa kembali sebelum setiap aksi kredensial, dengan pemeriksaan Stop pada batas yang sama. Perubahan form, tujuan, challenge, atau field yang tidak dikenal memerlukan login manual pada browser terlihat.

Rute home Coretax adalah isyarat untuk menuju pencarian, bukan bukti autentikasi. Kontrol pencarian wajib pajak yang terlihat menjadi marker kesiapan. **Cek Kredensial** menggunakan profil sementara, satu percobaan kredensial tersimpan, dan tidak memakai profil ekspor. SSO yang sudah login tidak menguji password tersimpan.

Jangan meneruskan exception browser atau Credential Manager mentah ke log GUI. Diagnostics dapat mengandung sumber halaman, identifier, URL proxy, atau rahasia. Jangan mewariskan flag debug kredensial Playwright.

## Status dan Stop

Run data membedakan kelengkapan inventaris, detail, tabel, dan keseluruhan run. Flag harus berupa boolean yang benar; nilai seperti string `"true"` tidak diterima sebagai bukti COMPLETE. Inventaris parsial, error capture, detail belum lengkap, tabel parsial, dan duplikasi ID eksplisit menghalangi klaim lengkap.

| Kanal | Status/kode |
| --- | --- |
| CLI | COMPLETE `0`, PARTIAL `2`, terblokir `1`, interupsi `130`. |
| Worker ekspor desktop | COMPLETE `0`, PARTIAL `2`, BLOCKED `3`, CANCELLED `4`, ERROR `1`. |
| Worker Cek Kredensial | LOGIN_OK `0`, LOGIN_UNVERIFIED `5`, LOGIN_MANUAL `6`, LOGIN_BLOCKED `3`, LOGIN_ERROR `1`, CANCELLED `4`. |

Jangan menyamakan exit code CLI dengan worker. Controller memerlukan event terminal yang sesuai dengan `job_id`, operasi, exit code, hasil yang diverifikasi, dan selesainya pembersihan proses. Exit `0` saja tidak berarti berhasil. Progres tahap merupakan informasi pekerjaan; persentase 100 hanya muncul pada COMPLETE final.

Worker menunggu izin `start` melalui protokol parent. Anak proses Windows dibuat suspended, dimasukkan ke Job Object, baru dilanjutkan. Ini penting karena launcher virtualenv dapat membuat interpreter anak sebelum kode Python mulai berjalan. Memindahkan assignment ke dalam worker akan membuka celah kepemilikan proses.

Stop memiliki prioritas atas start/progres yang terlambat. Pembatalan kooperatif diperiksa di batas capture dan publikasi; `CaptureCancelled` melewati penanganan `Exception` per-record. Setelah tenggat 15 detik, controller menutup pohon proses miliknya. UI tetap memproses pembaca sampai EOF, kemudian menguras event akhir. Semua callback Tk berjalan pada thread utama. Jangan menghentikan browser pribadi atau proses lain di mesin.

## Kontrak Excel dan transaksi publikasi

`coretax_exporter` memvalidasi scope, completion, dan seluruh nilai sebelum menghasilkan workbook. Teks sumber selalu ditulis literal, termasuk string yang menyerupai formula. Angka sumber yang telah berupa teks tetap teks; hitungan turunan tetap numerik. Nilai yang tidak dapat diwakili Excel secara persis ditolak. Hanya URL HTTP/HTTPS menjadi hyperlink aktif.

Set hasil terdiri dari `resume.xlsx` dan workbook per jenis pajak, masa/tahun sumber literal, dan `Model SPT` literal. Normal dan setiap nomor pembetulan selalu memiliki file terpisah. Folder masa tetap `SPT Masa 21`, `SPT Masa Unifikasi`, dan `SPT Masa PPN`; Badan dan jenis lainnya juga menyertakan masa/model pada nama file. Ringkasan, Daftar SPT, dan Audit hanya berada di resume; setiap file SPT berisi seluruh form teramati milik modelnya tanpa banner/tautan umum/header/footer cetak tambahan. Sheet memakai nama form sederhana dan suffix angka minimal untuk benturan lokal; caption sumber lengkap tetap dipertahankan. Tautan resume relatif mengikat file model dan sheet pertama yang tepat. Benturan nama file tanpa membedakan kapital ditolak berdasarkan identitas jenis/masa/model asli, bukan label pembetulan turunan.

Identitas form seluruh jenis memakai path bagian sumber lengkap. `Induk / Rincian` dan `L1-D / Rincian` tetap menjadi sheet terpisah walaupun nama akhirnya sama; subbagian pada form yang sama tetap berada di sheet form itu. Caption sumber lengkap dan baris duplikat tetap disimpan; nama pendek sheet hanya membantu navigasi.

SPT forms-only memakai JSON berversi dalam `Workbook.properties.identifier` (core document properties), bukan sheet tersembunyi. Deklarasi menyimpan NPWP/tahun/dasar tahun/status, metadata dan ID record, scope, nama bagian sumber lengkap, serta deklarasi PDF. Pembaca menolak schema/tipe/key duplikat yang salah dan memeriksa nama/urutan/visibility sheet fisik; verifier output baru mencocokkan seluruh proof dengan capture terpilih. Pembaca overwrite masih mendukung workbook lama tanpa proof melalui header/index/Audit fisik. Bukti ini bukan autentikasi data: stream PDF tetap dipegang dan ukuran/signature/hash-nya diperiksa secara independen.

Data field dan tabel disajikan tanpa sel data gabungan, dengan filter tabel dan freeze panes. Nilai sumber tetap literal; kolom numerik opsional hanya tersedia untuk angka dengan label/format yang didukung dan presisi yang dapat dipertahankan. Nilai `Decimal` sumber dibandingkan dengan representasi 15 digit yang didukung sebelum angka turunan diterima, agar konversi ke `float` tidak lebih dulu menyembunyikan pembulatan. Bila tidak lolos, nilai analisis tidak diisi dan teks sumber tetap utuh. Caption sumber disimpan terpisah bila header filter perlu disambiguasi. Header sumber yang kebetulan sama dengan suffix hasil disambiguasi juga tetap menghasilkan nama kolom tabel yang unik.

Publikasi lokal oleh `coretax.save_output` mengikuti urutan berikut:

1. Periksa scope run serta proof fisik workbook baru atau header workbook lama secara independen dari `run.json`.
2. Tulis set baru ke direktori staging. Pemindaian menyamakan bentuk path relatif/absolut secara leksikal sebelum mengecualikan staging, tanpa mengikuti symlink atau junction untuk menutupi path yang tidak sah.
3. Baca ulang set, jumlah, tipe sel identitas, status, serta tautan workbook/pembetulan. Pemeriksaan tetap berjalan dengan `python -O` karena menggunakan exception eksplisit.
4. Buat backup dan ganti seluruh workbook serta `run.json`.
5. Bila penggantian gagal, coba rollback. Pertahankan staging/backup bila publikasi atau pemulihan tidak selesai.

Desktop menyalin set Excel serta PDF COMPLETE yang dideklarasikan ke staging di Downloads, mencocokkan SHA-256 setiap salinan dan memegang stream PDF yang diverifikasi, lalu memverifikasi ulang workbook sebelum publikasi. Target baru memakai folder final baru; target lama mengganti hanya file terpilih melalui journal/rollback native. Path harus tetap berada dalam Downloads hasil Known Folder setelah resolusi; junction/symlink tidak boleh mengalihkan publikasi ke luar tujuan. JSON pemulihan dan profil tetap berada di LocalAppData.

Hasil gabungan lama tetap dibaca melalui proof/header/index/Audit fisik serta tautan resume yang cocok; scope yang salah ditolak. Untuk layout lama yang terverifikasi, desktop memilih folder baru tanpa mengganti workbook/PDF lama; CLI meminta folder baru bila set nama berbeda. Pada target dengan layout terpisah yang lolos pemeriksaan, penggantian resume saja tidak meminta consent. Penggantian file SPT/PDF terpilih tetap meminta consent; worker tidak mencantumkan resume pada daftar consent tersebut. Snapshot folder/file, fingerprint, revalidation, native directory guards, Stop dan rollback tetap berlaku pada jalur otomatis. Penolakan consent membatalkan seluruh publikasi dan tidak memperbarui resume.

Rollback menangani kegagalan penggantian biasa dan exception. Penggantian beberapa berkas bukan transaksi filesystem atomik saat process kill atau listrik padam. Jangan menghapus data pemulihan untuk membuat direktori terlihat bersih. Pulihkan ke folder baru dan periksa hasilnya.

## Saat mengubah perilaku

Tambahkan fixture sintetis untuk kondisi yang berubah, lalu verifikasi invariant yang relevan: identitas, scope, byte/nilai output setelah gagal, tautan pembetulan, COMPLETE/PARTIAL, Stop, dan kepemilikan proses. Perbaikan tampilan tidak perlu mengubah kontrak event atau capture. Perubahan resource/dependensi harus disertai pembaruan fingerprint, allowlist, dan tes readiness bila kontraknya berubah. Lihat [pengembangan](pengembangan.md) dan [kebijakan Python](python-314.md).
