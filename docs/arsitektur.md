# Arsitektur dan kontrak yang harus dipertahankan

[Kembali ke dokumentasi](README.md)

Aplikasi memiliki mesin capture/export yang dipakai bersama oleh CLI dan desktop. Desktop menambahkan pengelolaan runtime, kredensial, kepemilikan proses, progres, dan publikasi ke Downloads. Perubahan antarmuka tidak boleh memperluas kewenangan mesin capture.

## Peta modul

Untuk menelusuri fungsi dan tes saat mulai mengubah kode, gunakan [peta kode](peta-kode.md).
Bagian ini menjelaskan tanggung jawab modul; bagian berikutnya menetapkan kontraknya.

| Modul | Tanggung jawab |
| --- | --- |
| `coretax.py` | Entry point CLI, autentikasi manual CLI, orkestrasi, verifikasi set workbook, staging, dan rollback publikasi lokal. |
| `coretax_browser.py` | Inventaris daftar, pengamatan respons UI, pemeriksaan origin/identitas, navigasi View, paginasi, serta checkpoint detail. |
| `coretax_resume.py` | Manifest pilihan desktop terikat hash inventaris/scope/urutan/mode; pemulihan CLI tanpa memperluas pilihan. |
| `coretax_inventory.py`, `coretax_json_capture.py` | Bukti filter periode dan katalog, serta pengamatan/penyimpanan respons JSON yang terikat pada record dan percobaan capture. |
| `coretax_exporter.py` | Validasi scope dan nilai, deduplikasi ID, susunan workbook, serta tautan relatif. Tidak membuka browser. |
| `coretax_json.py`, `coretax_masa_json.py` dan modul observer/projection terkait | Binding respons native ke identitas/scope dan proyeksi form; kelayakan diperiksa terpisah dari pilihan mode. |
| `coretax_masa_templates.py`, `coretax_pph21.py`, `coretax_badan_template.py` | Renderer template terverifikasi, angka moneter dan aturan tampilan per jenis/form. |
| `coretax_attachments.py`, `coretax_financial_post.py`, `coretax_pdf.py` | Penemuan href/kontrol PDF yang didukung, POST dokumen yang sudah ada, unduhan terbatas, deklarasi, serta verifikasi byte melalui stream yang tetap dipegang. |
| `spt_gui.py`, `spt_desktop/app.py` | Entry point dan GUI Tkinter, pengaturan, tombol, serta self-test source/frozen. |
| `spt_desktop/controller.py`, `events.py` | Protokol progres/terminal, otorisasi start, Stop, dan pemrosesan event pada thread GUI. |
| `spt_desktop/interaction.py` | Permintaan/jawaban pilihan SPT dan penggantian hasil yang terikat pada job; payload privat terpisah dari sinyal stdout/stdin. |
| `spt_desktop/runtime.py` | Pemilihan interpreter, resource worker eksplisit, fingerprint, setup dependensi, dan verifikasi kesiapan. |
| `spt_desktop/worker.py` | Proses terisolasi untuk autentikasi dan capture/export. |
| `spt_desktop/auth.py`, `credentials.py` | Login pada form yang diperiksa, challenge manual, serta Windows Credential Manager berbasis origin. |
| `spt_desktop/windows.py` | Instance lock dan Windows Job Object untuk kepemilikan pohon proses. |
| `spt_desktop/profile_lifecycle.py` | Profil login sementara dengan penanda identitas dan lease proses; pembersihan konservatif setelah proses berakhir. |
| `spt_desktop/paths.py`, `output.py`, `output_windows.py` | Known Folders, pemeriksaan folder/handle native, verifikasi salinan, serta publikasi Excel dan PDF ke Downloads. |
| `spt_desktop/diagnostics.py`, `diagnostic_store.py` | Event diagnostik dengan field yang diizinkan, antrean terbatas, serta berkas log berotasi. |
| `spt_desktop/build_info.py`, `publication_recovery.py` | Identitas build publik yang divalidasi dan journal pemulihan publikasi privat sebelum pemindahan output. |
| `scripts/ci_route.py`, `ci_tests.py`, `ci_artifact.py` | Routing CI, bukti cakupan tes per runner/shard, dan pemeriksaan isi/hash artifact distribusi. |
| `build_desktop.py` | Paket GUI tipis, bundel `uv`, allowlist resource, dan pemeriksaan executable hasil build. |

GUI memakai stdlib/Tkinter dan tidak mengimpor Playwright atau openpyxl ke prosesnya. Worker memasang dependensi pada runtime terisolasi. `WORKER_FILES` merupakan allowlist eksplisit; modul worker baru harus ditambahkan di sana bersama tes kontraknya. Jangan menggantinya dengan penyalinan direktori rekursif, karena checkout dapat berdampingan dengan profil, hasil, atau environment lokal.

## Identitas, scope, dan provenance

`validate_scope` menerima NPWP tepat 16 digit ASCII. Nol awal merupakan bagian dari identitas. Tahun pajak berada dalam rentang 1900 sampai 2100; input GUI/CLI harus memenuhi bentuk empat digit. Jangan menerapkan `strip()`, menghapus pemisah, mengonversi NPWP menjadi angka, atau memilih kecocokan sebagian untuk membantu input yang salah.

Scope terdiri dari NPWP, tahun, dan `year_basis`. Bawaan `period` memakai masa/tahun pajak; `submission` memakai tanggal penyampaian. Metadata periode yang tidak dapat ditafsirkan secara terverifikasi menjadi error. Pola periode migrasi hanya ditafsirkan sesuai pola teramati yang divalidasi, dan nilai aslinya tetap disimpan.

Rantai provenance yang dijaga:

1. Pencarian kembali ke origin HTTPS dan path pencarian yang diizinkan sebelum NPWP dimasukkan.
2. Tepat satu baris dipilih, dengan sel NPWP sama persis dan nama wajib pajak berasal dari baris tersebut.
3. URL daftar membuktikan identitas wajib pajak. Inventaris baru hanya mengikuti satu navigasi SPT Dilaporkan yang teramati dan terikat ke wajib pajak yang sama. Halaman awal setelah Pilih boleh berupa draft, tetapi daftar draft/arsip/status lain tidak dipindai. Navigasi Dilaporkan yang hilang, ambigu atau berpindah identitas tidak disertifikasi sebagai daftar kosong.
4. Respons daftar harus memiliki skema yang didukung, status sukses eksplisit, dan jumlah baris yang cocok dengan DOM. `TotalRecords` direkonsiliasi dengan seluruh halaman.
5. Kontrol View yang dikenali membuka detail; URL detail harus memuat segmen identitas wajib pajak dan SPT yang dipilih.
6. Checkpoint detail harus cocok dengan scope, ID, metadata, posisi/halaman daftar, serta provenance inventaris sebelum digabungkan.

`RecordId` yang berulang pada beberapa status digabungkan hanya bila metadata konsisten; `source_occurrences` mempertahankan asal kemunculannya. Pasangan periode kode/label hanya boleh diterima dengan katalog sumber yang valid, segar dan tidak ambigu; nilai setiap kemunculan tetap literal. [Catatan period-alias](period-metadata-conflict.md) menjelaskan batas bukti tersebut. Pembetulan dengan ID berbeda tetap berbeda. Konflik metadata tanpa bukti ekuivalensi tetap kegagalan validasi, bukan dasar memilih salah satu nilai.

Rekonsiliasi lintas-status tetap diperlukan untuk membaca bukti lama; inventaris
baru tidak memperluas scope ke arsip. Manifest pilihan dan checkpoint lama tidak
ditulis ulang agar terlihat berasal dari pemindaian Dilaporkan yang baru.

Metadata scope per-record yang tidak tersedia pada capture lama tidak dapat membuktikan NPWP secara independen. Jangan menyimpulkan provenance legacy yang tidak tersimpan. Capture baru membawa metadata scope; pemeriksaan yang tersedia tetap wajib dilakukan saat ekspor ulang.

## Batas akses baca

`ListObserver` mengamati respons JSON dari tindakan UI milik browser. Ia menyimpan respons terakhir dan nomor urut yang terus bertambah, bukan seluruh riwayat respons dalam RAM. Ia tidak membaca cookie/header autentikasi dan tidak menjalankan request API penulisan tersendiri.

Capture memakai kontrol baca yang sudah dikenali: pencarian wajib pajak, Pilih, navigasi status, View, tab, accordion, ukuran halaman, serta paginasi. Tombol submit, batal SPT, kirim email, pembuatan dokumen, dan aksi baris yang tidak dikenal tidak boleh dijadikan fallback. Bila selector View berubah, hasil tetap terblokir/parsial sampai layout baru diperiksa dan fixture regresinya tersedia.

PDF keuangan/auditan didukung melalui href baca biasa atau kontrol Unduh pada grid FinancialStatement yang teramati pada Induk Badan terverifikasi. [Adapter POST](pdf-keuangan-post.md) memverifikasi source pin, kepemilikan kontrol serta request akhir, membatalkan request aplikasi sebelum satu replay stream terbatas, dan menolak perpindahan scope/redirect. Identitas, origin, byte, ukuran, signature/hash dan custody tetap diperiksa; metadata saja bukan unduhan. PDF/BPE/lampiran lain, pembuatan dokumen jarak jauh dan drill-down per baris tetap di luar cakupan. Tab dinonaktifkan tidak dijelajahi. Capture detail harus memiliki field atau tabel terstruktur yang bermakna; halaman kosong atau layout tak dikenal tidak disertifikasi lengkap.

## Kredensial dan autentikasi desktop

Kredensial desktop hanya boleh diambil dari Windows Credential Manager untuk `LOGIN_ORIGIN` Satu yang tetap dan identifier akun terpilih. Pengguna tidak memilih URL origin. Preferensi allowlist menyimpan browser, headless, identifier dan mode sumber detail; nilai `login_origin` dipaksa ke konstanta aplikasi. Akun kosong memilih login manual tanpa membaca credential tersimpan. Password, token dan cookie tidak masuk file preferensi atau event GUI. Urutan tindakan pengguna ada pada [README](../README.md#login-tersimpan); caption/fokus Pengaturan ada pada [pola UI](ui-ux/pola-dan-status.md#pengaturan-dan-login-tersimpan).

Login tersimpan mengikat elemen/form yang telah diperiksa. Origin, identitas kontrol, dan tujuan submit hasil resolusi browser diperiksa kembali sebelum setiap aksi kredensial, dengan pemeriksaan Stop pada batas yang sama. Perubahan form, tujuan, challenge, atau field yang tidak dikenal memerlukan login manual pada browser terlihat.

Rute home Coretax adalah isyarat untuk menuju pencarian, bukan bukti autentikasi. Kontrol pencarian wajib pajak yang terlihat menjadi marker kesiapan. Autentikasi berjalan melalui `authenticate_owned` saat Mulai unduh. Setiap unduhan dengan akun tersimpan menggunakan profil sementara baru dan mencocokkan identifier sebelum mengisi form; sesi SSO yang belum terkait akun tersebut ditolak untuk login otomatis. Akun kosong memakai alur manual. Tidak ada operasi pemeriksaan kredensial terpisah, command `--check-login`, atau penerimaan event `login_check` pada controller.

Profil sementara `login-check` dari versi lama tetap dapat dibersihkan oleh reaper setelah kepemilikan dan akhir proses terverifikasi. Schema diagnostik lama tetap dapat dibaca, tetapi alur produk baru tidak memancarkan operasi tersebut.

Jangan meneruskan exception browser atau Credential Manager mentah ke log GUI. Diagnostics dapat mengandung sumber halaman, identifier, URL proxy, atau rahasia. Jangan mewariskan flag debug kredensial Playwright.

## Status dan Stop

Run data membedakan kelengkapan inventaris, detail, tabel, dan keseluruhan run. Flag harus berupa boolean yang benar; nilai seperti string `"true"` tidak diterima sebagai bukti COMPLETE. Inventaris parsial, error capture, detail belum lengkap, tabel parsial, dan duplikasi ID eksplisit menghalangi klaim lengkap.

| Kanal | Status/kode |
| --- | --- |
| CLI | COMPLETE `0`, PARTIAL `2`, terblokir `1`, interupsi `130`. |
| Worker ekspor desktop | COMPLETE `0`, PARTIAL `2`, BLOCKED `3`, CANCELLED `4`, ERROR `1`. |

Jangan menyamakan exit code CLI dengan worker. Controller memerlukan event terminal yang sesuai dengan `job_id`, operasi, exit code, hasil yang diverifikasi, dan selesainya pembersihan proses. Exit `0` saja tidak berarti berhasil. Progres tahap merupakan informasi pekerjaan; persentase 100 hanya muncul pada COMPLETE final.

Worker menunggu izin `start` melalui protokol parent. Anak proses Windows dibuat suspended, dimasukkan ke Job Object, baru dilanjutkan. Ini penting karena launcher virtualenv dapat membuat interpreter anak sebelum kode Python mulai berjalan. Memindahkan assignment ke dalam worker akan membuka celah kepemilikan proses.

Stop memiliki prioritas atas start/progres yang terlambat. Pembatalan kooperatif diperiksa di batas capture dan publikasi; `CaptureCancelled` melewati penanganan `Exception` per-record. Setelah tenggat 15 detik, controller menutup pohon proses miliknya. UI tetap memproses pembaca sampai EOF, kemudian menguras event akhir. Semua callback Tk berjalan pada thread utama. Jangan menghentikan browser pribadi atau proses lain di mesin.

## Kontrak Excel dan transaksi publikasi

`coretax_exporter` memvalidasi scope, completion dan nilai sebelum menghasilkan workbook. Checkpoint tidak diubah oleh renderer. Identitas dan teks biasa tetap literal, termasuk nol awal dan string yang menyerupai formula. Slot moneter terverifikasi pada template dapat ditulis sebagai angka Excel dengan aturan id-ID dan pemeriksaan presisi sebelum konversi; teks malformed atau presisi tidak aman tetap literal, bukan ditebak/dibulatkan. Hitungan turunan tetap numerik. Nilai yang melanggar batas representasi Excel ditolak. Hanya URL HTTP/HTTPS menjadi hyperlink aktif.

Set hasil terdiri dari `resume.xlsx` dan workbook per jenis pajak, masa/tahun sumber literal, dan `Model SPT` literal. Normal dan setiap nomor pembetulan selalu memiliki file terpisah. Folder masa tetap `SPT Masa 21`, `SPT Masa Unifikasi`, dan `SPT Masa PPN`; Badan dan jenis lainnya juga menyertakan masa/model pada nama file. Ringkasan, Daftar SPT, dan Audit hanya berada di resume; setiap file SPT berisi seluruh form teramati milik modelnya tanpa banner/tautan umum/header/footer cetak tambahan. Sheet memakai nama form sederhana dan suffix angka minimal untuk benturan lokal; caption sumber lengkap tetap dipertahankan. Tautan resume relatif mengikat file model dan sheet pertama yang tepat. Benturan nama file tanpa membedakan kapital ditolak berdasarkan identitas jenis/masa/model asli, bukan label pembetulan turunan.

Ketika publikasi mempertahankan workbook lama, indeks resume mencakup seluruh workbook yang terverifikasi dalam folder, sedangkan laporan pemetaan pada Audit hanya mencakup pengambilan terbaru. Proof workbook versi 1 tidak menyimpan laporan pemetaan lama. Periksa checkpoint asal untuk menilai pemetaan file yang dipertahankan; laporan yang tidak tercantum tidak membuktikan nol field belum terpetakan atau pemetaan COMPLETE.

PPh Pasal 21/26 memakai template yang disetujui hanya untuk Induk, L-IA, L-IB, L-II, dan L-III yang teramati. Form tersebut tidak menampilkan blok sumber mentah tambahan. Checkpoint tetap utuh; field/header/kelompok ambigu, footer tidak didukung, dan tabel tidak lengkap tetap dilaporkan belum terpetakan/PARTIAL pada Audit resume untuk pengambilan tersebut. Form yang tidak didukung tetap memakai renderer generik. Penghilangan blok tampilan tidak mengubah kelengkapan capture atau kelayakan native JSON.

Template Badan yang telah disanitasi berada di `resources/corporate_format.xlsx`; `coretax_badan_template.py` menyalin hanya lampiran referensi yang benar-benar teramati. Referensi tampilan bersih yang disetujui operator menambahkan Induk dua kolom dan L8 tiga kolom melalui caption/style statis dalam source, tanpa menyalin workbook pribadi. Induk mengikat field melalui identitas field, caption dan kelompok yang unik; L8 memerlukan kelompok dan header teramati yang sesuai. Nama literal L10-B/L10-D dikecualikan dari workbook baru, bukan dari checkpoint. Pembacaan proof dan tautan workbook lama memakai namespace sheet fisik yang tersimpan, tanpa menerapkan pengecualian baru pada file lama.

Pemetaan tabel memerlukan header yang sesuai; header berulang L1-D/L9 juga memerlukan komponen pemilik dan kelompok dari `source_structure`. Metadata itu hanya ditambahkan setelah kepemilikan form DOM teramati, tidak memberikan kelayakan native JSON. Checkpoint lama tanpa pembeda struktur tidak boleh diperkaya dengan tebakan urutan atau nilai. Baris ambigu, footer tidak didukung, dan field tanpa slot tetap terlihat sebagai bukti mentah dengan laporan pemetaan belum lengkap. Nilai moneter id-ID yang aman memakai angka Excel; angka dengan presisi tidak aman tetap literal. Total berasal dari footer tangkapan, bukan penjumlahan ulang.

Footer Badan memakai posisi fisik dan colspan sumber. Label total boleh berada setelah sel kosong di dalam rentang merge template yang sama, tetapi label bertentangan atau colspan tidak sesuai tetap ditolak. Kode akun footer L1-D dipertahankan sebagai teks; total terakhir tetap pada baris 101 untuk kapasitas referensi. L3 mendukung tiga footer teramati: JUMLAH, KREDIT PAJAK LUAR NEGERI, dan JUMLAH KREDIT PAJAK, tanpa menghitung ulang nilainya. Pertumbuhan baris menggeser footer bersama layout.

Sesuai pengecualian tampilan yang disetujui, Induk, L1-D, L2, L3, L4, L6, L7, L8, L9, L10-A, L10-C, L11-A, dan L11-B tidak menampilkan blok tambahan/belum dipetakan maupun salinan teks halaman. Checkpoint tetap utuh dan Audit pada resume tetap melaporkan field/tabel/baris yang belum terikat; penghilangan tampilan tidak menjadikannya COMPLETE. Lampiran Badan lainnya tetap menampilkan bukti mentah yang belum didukung.

Kapasitas body tabel referensi dipadatkan menjadi jumlah baris tangkapan yang berisi nilai, dengan satu slot body untuk tabel kosong. Nol dan False tetap merupakan isi. Hanya rentang body yang diketahui boleh dipadatkan; header, total tangkapan, pemisah, merge dan style tetap dipertahankan. Footer dan formula DER mengikuti pemadatan maupun pertumbuhan. L1-D menghilangkan tiga baris judul/identitas tampilan beserta satu baris kosong sebelum header pertama; metadata sumber tetap berada dalam checkpoint dan proof workbook. Induk menghilangkan field kosong tanpa mengisi default; tiga baris pemisah identitas/perhitungan tetap ada bila kedua blok berisi data. Seluruh accounting Badan memakai nol desimal sesuai ketentuan operator terbaru, termasuk style referensi dan slot moneter baru. Nilai numerik tersimpan tetap persis tanpa dibulatkan; rasio DER dan tampilan persentase tetap memakai dua desimal. Pemadatan tidak mengubah jumlah/source_total atau bukti kelengkapan capture.

Rentang moneter yang disetujui pada L1-D, L2, L3, L6, L7, L9, L10-A, L11-A, dan L11-B memakai format akuntansi pada sel yang dapat ditulis. Header, kode, dan nilai yang tidak aman tetap literal. Persentase L2 pada kolom yang terikat ke header persentase memakai pecahan numerik dengan pemeriksaan sintaks dan presisi; pemberian format persen pada sel teks tidak mengubah teks menjadi angka. Penambahan baris menyalin format aslinya dan mempertahankan merge label.

Normalisasi negatif L1-D hanya berlaku untuk caption pengurang akumulasi penyusutan yang cocok tepat pada kelompok sumber yang terverifikasi. L9 menerima caption kelompok `LAINNYA` dan `KELOMPOK LAINNYA` di bawah pemilik komponen yang sesuai; capture lama tanpa bukti pemilik tetap belum terpetakan. Nilai sumber dan checkpoint tidak diubah oleh aturan tampilan tersebut.

PERHITUNGAN DER pada L11-B merujuk total rata-rata utang dan modal yang teramati dan berhasil dipetakan secara unik. Referensi rumus mengikuti perpindahan baris ketika tabel tumbuh. Rasio hanya tersedia bila kedua operand numerik aman dan modal bukan nol. Operand hilang/tidak aman atau modal nol menghasilkan alasan DER parsial tersendiri pada audit, tanpa menambah hitungan field/tabel/baris sumber yang belum terpetakan secara fiktif.

Pada Unifikasi, seluruh form referensi yang disetujui dan teramati, termasuk Induk, memakai tampilan bersih tanpa blok mentah tambahan. Checkpoint dan hitungan unresolved tetap dipertahankan. Kolom tarif DAFTAR-I menyimpan pecahan Excel berformat persen; nilai sumber `2,50` menjadi `0.025`, bukan `2.5`. Spacer tidak diperlakukan sebagai tarif/footer. Pertahankan pemisah kosong sebelum kelompok BPNR dan tepat satu baris kosong sebelum total LAMPIRAN-I; posisi mengikuti jumlah baris data yang teramati. Aturan tampilan ini tidak mengubah kelengkapan capture atau kelayakan native JSON.

Pada form PPN A-2, sel B15 memakai perataan tengah.

Identitas form seluruh jenis memakai path bagian sumber lengkap. `Induk / Rincian` dan `L1-D / Rincian` tetap menjadi sheet terpisah walaupun nama akhirnya sama; subbagian pada form yang sama tetap berada di sheet form itu. Caption sumber lengkap dan baris duplikat tetap disimpan; nama pendek sheet hanya membantu navigasi.

SPT forms-only memakai JSON berversi dalam `Workbook.properties.identifier` (core document properties), bukan sheet tersembunyi. Deklarasi menyimpan NPWP/tahun/dasar tahun/status, metadata dan ID record, scope, nama bagian sumber lengkap, serta deklarasi PDF. Pembaca menolak schema/tipe/key duplikat yang salah dan memeriksa nama/urutan/visibility sheet fisik; verifier output baru mencocokkan seluruh proof dengan capture terpilih. Pembaca overwrite masih mendukung workbook lama tanpa proof melalui header/index/Audit fisik. Bukti ini bukan autentikasi data: stream PDF tetap dipegang dan ukuran/signature/hash-nya diperiksa secara independen.

Renderer generik memakai tabel berfilter/freeze panes tanpa menggabungkan sel data; template yang disetujui mempertahankan style, merge, dimensi dan page layout aslinya. Kolom analisis generik dan slot moneter template memakai aturan masing-masing, bukan konversi semua teks menjadi angka. Kolom numerik opsional hanya tersedia untuk label/format yang didukung dan presisi yang dapat dipertahankan. Nilai `Decimal` sumber dibandingkan dengan representasi 15 digit yang didukung sebelum angka turunan diterima, agar konversi ke `float` tidak lebih dulu menyembunyikan pembulatan. Bila tidak lolos, nilai analisis tidak diisi dan teks sumber tetap utuh. Caption sumber disimpan terpisah bila header filter perlu disambiguasi. Header sumber yang kebetulan sama dengan suffix hasil disambiguasi juga tetap menghasilkan nama kolom tabel yang unik.

Publikasi lokal oleh `coretax.save_output` mengikuti urutan berikut:

1. Periksa scope run serta proof fisik workbook baru atau header workbook lama secara independen dari `run.json`.
2. Tulis set baru ke direktori staging. Pemindaian menyamakan bentuk path relatif/absolut secara leksikal sebelum mengecualikan staging, tanpa mengikuti symlink atau junction untuk menutupi path yang tidak sah.
3. Baca ulang set, jumlah, tipe sel identitas, status, serta tautan workbook/pembetulan. Pemeriksaan tetap berjalan dengan `python -O` karena menggunakan exception eksplisit.
4. Buat backup dan ganti seluruh workbook serta `run.json`.
5. Bila penggantian gagal, coba rollback. Pertahankan staging/backup bila publikasi atau pemulihan tidak selesai.

Unduhan PDF keuangan baru memakai nama file datar `LK_<record-key>_<document-key>.pdf` langsung berdampingan dengan Excel di folder hasil, tanpa subfolder `attachments`. Kunci record dan dokumen menjaga keunikan lintas SPT; `relative_path` tetap menjadi target tautan dan deklarasi byte yang sama, tanpa mengubah penyalin atau writer Excel. Proof/capture lama dengan path bersubfolder tetap dapat dibaca tanpa ditulis ulang; bila unduhan datar baru bertemu hasil lama dengan PDF bersubfolder, validasi semua deklarasi COMPLETE lama lalu pilih folder hasil baru, bukan memindahkan file lama.

Desktop menyalin set Excel serta PDF COMPLETE yang dideklarasikan ke staging di Downloads, mencocokkan SHA-256 setiap salinan dan memegang stream PDF yang diverifikasi, lalu memverifikasi ulang workbook sebelum publikasi. Target baru memakai folder final baru; target lama mengganti hanya file terpilih melalui journal/rollback native. Path harus tetap berada dalam Downloads hasil Known Folder setelah resolusi; junction/symlink tidak boleh mengalihkan publikasi ke luar tujuan. JSON pemulihan dan profil tetap berada di LocalAppData.

Hasil gabungan lama tetap dibaca melalui proof/header/index/Audit fisik serta tautan resume yang cocok; scope yang salah ditolak. Untuk layout lama yang terverifikasi, desktop memilih folder baru tanpa mengganti workbook/PDF lama; CLI meminta folder baru bila set nama berbeda. Pada target dengan layout terpisah yang lolos pemeriksaan, resume mengindeks workbook lama yang sah bersama hasil baru; COMPLETE job tetap hanya untuk pilihan saat ini, bukan bukti file lama diunduh ulang. Penggantian resume saja tidak meminta consent. Penggantian file SPT/PDF terpilih tetap meminta consent; worker tidak mencantumkan resume pada daftar consent tersebut. Snapshot folder/file, fingerprint, revalidation, native directory guards, Stop dan rollback tetap berlaku pada jalur otomatis. Penolakan consent membatalkan seluruh publikasi dan tidak memperbarui resume.

Bila ID SPT yang sama sudah berada pada nama workbook dengan periode literal berbeda, desktop memvalidasi seluruh scope, tautan indeks dan deklarasi PDF COMPLETE lama lalu memilih folder baru. File lama tetap utuh; resume baru hanya mengindeks hasil job baru, termasuk status PARTIAL yang sebenarnya. Identitas jenis pajak/model yang berubah atau bukti fisik lama yang tidak valid tetap ditolak. Jalur ini tidak menyamakan dua periode dan tidak mengendurkan consent untuk penggantian nama file yang sama; lihat [bukti alias periode](period-metadata-conflict.md).

Rollback menangani kegagalan penggantian biasa dan exception. Sebelum pemindahan pertama, backup privat di-flush dan journal serta notice ditulis atomik. Setiap entri dengan fingerprint lama/baru dan nama pemulihan satu volume disimpan sebelum file dipindahkan; index dipublikasikan terakhir. `recover_publication` dapat memulihkan journal `pending` setelah proses mati, hanya bila scope, direktori, file lama, backup dan file terpasang tetap cocok. Perubahan bersamaan menyebabkan penolakan dan seluruh bukti dipertahankan. Journal `committed` memverifikasi hasil yang sudah selesai, tanpa menggantinya dengan versi lama. Journal `restored` dapat diverifikasi ulang. Lihat [prosedur pemulihan](pemulihan-publikasi.md).

Penggantian beberapa berkas tetap bukan transaksi filesystem atomik saat listrik padam atau kegagalan penyimpanan. Journal membantu pemulihan process death yang diuji; ia tidak mengautentikasi private state terhadap administrator yang menguasai akun. Jangan menghapus data pemulihan untuk membuat direktori terlihat bersih. Bila pemeriksaan menolak, pertahankan semua versi, rebuild capture ke folder baru dan lakukan pemeriksaan privat.

## Saat mengubah perilaku

Tambahkan fixture sintetis untuk kondisi yang berubah, lalu verifikasi invariant yang relevan: identitas, scope, byte/nilai output setelah gagal, tautan pembetulan, COMPLETE/PARTIAL, Stop, dan kepemilikan proses. Perbaikan tampilan tidak perlu mengubah kontrak event atau capture. Perubahan resource/dependensi harus disertai pembaruan fingerprint, allowlist, dan tes readiness bila kontraknya berubah. Lihat [pengembangan](pengembangan.md) dan [kebijakan Python](python-314.md).
