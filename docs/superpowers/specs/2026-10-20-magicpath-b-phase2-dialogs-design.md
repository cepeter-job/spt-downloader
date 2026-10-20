# MagicPath B — Tahap 2: dialog pilihan SPT dan penggantian hasil

**Revisi:** B-TK-P2-D1 · 20 Oktober 2026. **Status:** usulan desain untuk review pemilik; belum persetujuan implementasi.

**Baseline produk:** `main@977b06846554ca1f2e5af512a69fb201f2cbe8d1`. [Baseline UI/UX yang telah direview](https://github.com/cepeter-job/spt-downloader/blob/7a36b2e6c1c5d0490652be0db15ae94d50f12f42/docs/ui-ux/baseline-2026-10-20.md) berada pada PR #50 yang saat penulisan masih terbuka. Spesifikasi ini berdiri sendiri di atas source `main`; tidak menggabungkan PR #50 atau PR produk lain.

**Tujuan pengguna:** memilih SPT dengan yakin dan memahami file mana yang akan diganti, tanpa mencari tombol yang tergulir keluar layar atau kehilangan identitas pilihan. Tetap **MagicPath B**, **Tkinter/ttk**, satu pekerjaan aktif, bahasa Indonesia yang wajar, dan seluruh fungsi bisnis yang sudah ada. “Done” terakhir menutup review baseline; bukan persetujuan atas kode, merge, atau rancangan baru ini.

## 1. Keputusan inti dan batas tahap

Rekomendasi: **rapikan dua dialog existing dan wajibkan konteks folder sebelum persetujuan overwrite**. Jangan membangun ulang shell B, selection, sorting, JSON-hybrid, login, atau output pajak. Keputusan yang masih memerlukan review adalah delta pada tabel berikut.

| Delta yang diusulkan | Alasan | Yang tidak ikut berubah |
| --- | --- | --- |
| Layout dialog mengikuti tema B, work area, dan ukuran teks yang terukur | Dialog masih memakai minimum dan wraplength tetap; keberadaan widget bukan bukti isinya terlihat | Native Toplevel/Treeview, empat kolom pilihan, perilaku modal dan satu request aktif |
| Konteks pekerjaan, hitungan pilihan, serta ID baris yang disorot mudah diperiksa | Pilihan visual harus jelas sebelum mengambil rincian | Record ID/nilai sumber literal; bukan verifikasi baru NPWP atau akun portal |
| Folder overwrite wajib tersedia dan ditampilkan lengkap | GUI masih menerima key `folder` yang tidak ada; worker produksi sudah mengirimnya | Tidak menebak Downloads/folder terbaru atau mengubah snapshot/publikasi backend |
| Keyboard dan pesan tindakan diselaraskan | Escape/Alt+S berbeda makna antara dua dialog; persetujuan tidak boleh terpicu tidak sengaja | Search menghapus pilihan; sort mempertahankannya; penolakan tetap menunggu terminal worker |
| Pengukuran render sebelum optimisasi | Filter existing memasukkan ulang row secara sinkron, belum ada bukti latensi pada dataset target | Tidak langsung menambah batching, thread, pagination, atau batas jumlah record baru |

**Di luar tahap ini:** konfirmasi Pengaturan dirty, perubahan caption Settings/login, perubahan sumber detail/default, migrasi toolkit, multijob, antrean, resume checkpoint lewat GUI, dark mode, backend/Excel/PDF, penambahan daftar pajak, rilis/deployment, dan benchmark aplikasi menyeluruh. Pemisahan workbook per masa/tahun **dan Model SPT literal**, indeks resume folder yang terverifikasi, kontak bugreport, serta penghapusan footer nama pribadi tetap berlaku.

### Pilihan pendekatan

| Pendekatan | Trade-off | Keputusan |
| --- | --- | --- |
| Delta layout dan validasi pada dialog yang ada | Perubahan kecil; mempertahankan lifecycle serta tes publik App, tetapi metode App belum dipecah besar-besaran | **Direkomendasikan untuk irisan pertama tahap 2** |
| Sekaligus memindahkan semua dialog/state ke subsistem baru | Mungkin merapikan file besar, tetapi menambah perpindahan callback/ownership sebelum kebutuhan terbukti | Ditunda; tidak menjadi syarat visual |
| Menambah batching/virtualisasi dan kontrol pilihan baru sekaligus | Dapat membantu dataset besar, tetapi berisiko mengubah identitas, urutan, dan timing persetujuan | Hanya lewat delta terpisah setelah pengukuran |

## 2. Kontrak baseline yang harus dipertahankan

Dialog berasal dari `App.selection_dialog` dan `App.overwrite_dialog`. App membaca data melalui `controller.read_request(event)`, bukan metadata event stdout. Event membawa identitas job/request; data privat memakai berkas request/reply terikat job. Batas transport existing **16 MiB** tetap milik `interaction.py`; ID record unik, nonkosong, maksimum **512 karakter**. ID Tcl tetap ordinal lokal seperti `record-0`, bukan record ID dari sumber.

| Kontrak existing | Tetap setelah tahap 2 |
| --- | --- |
| Selection reply | Tepat `{'selected_ids': [...]}`; minimal satu ID unik dari inventaris; susunan reply mengikuti inventaris asli, bukan tampilan tersortir |
| Overwrite reply | Tepat `{'overwrite': True}` atau `{'overwrite': False}`; nilai bool sebenarnya, bukan 0/1/string; keputusan berlaku untuk seluruh daftar snapshot, bukan per-file |
| Awal pemilihan | Nol pilihan, tombol **Sedot SPT terpilih** nonaktif; tidak ada pilih semua otomatis |
| Pencarian | Substring casefold dari nilai tampilan/ID; query pencarian boleh di-trim untuk pencocokan, nilai sumber tidak diubah; setiap perubahan pencarian menghapus pilihan termasuk ketika query dinormalisasi sama |
| Sorting | Awal Badan → Pasal 21/26 → Unifikasi → PPN → lainnya; klik Jenis pajak mengganti A–Z/Z–A jenis saja, kronologi/model dan stable source ties tetap sesuai baseline |
| Consent stale/berulang | Job/request asing atau sudah dipakai tidak membuka dialog baru, tidak mengirim ulang reply, dan tidak menghentikan job berikutnya |
| Hasil `respond=False` | Tutup/dismiss sesuai lifecycle; jangan menciptakan 0/N, progress, terminal, atau memanggil stop tambahan dari view karena mengira respons berhasil |
| Penolakan overwrite | `cancellation_pending` bukan terminal; worker memutus publikasi dan mengirim status akhir; file lama termasuk resume tidak ditulis ulang karena penolakan |
| Stop dan timeout | Stop tetap menang; deadline request existing 600 detik dan polling GUI 100 ms tidak diubah; UI tidak membuat countdown/deadline baru dari waktu dialog dibuka |

Validasi GUI adalah lapisan presentasi, bukan pengganti pemeriksaan controller, berkas privat, atau snapshot tujuan pada backend. Kata “scope/identitas terverifikasi” tidak boleh ditambahkan hanya karena NPWP/tahun berhasil ditampilkan.

## 3. Dialog pemilihan SPT

### Susunan tampilan

Urutan area: **instruksi dan konteks pekerjaan → pencarian → tabel → ID SPT yang disorot → hitungan/pesan pilihan → tindakan**. Treeview merupakan area yang paling banyak mengambil ruang; action bar tetap di luar viewport yang dapat digulir. Titlebar native menggunakan `selection.title`; tidak mengulang judul humor aplikasi sebagai heading besar di dalam modal.

Konteks menampilkan NPWP dan tahun dari snapshot job aktif `App._ui_state` yang identitasnya cocok dengan request. Bukan dari StringVar formulir yang mungkin sudah berubah, bukan dari nama folder, dan bukan dari metadata request yang ditambah-tambahkan. Labelnya **NPWP permintaan** / **Tahun pajak permintaan** untuk membedakan permintaan dari bukti identitas hasil. Jika snapshot tidak tersedia, tampilkan **Konteks permintaan tidak tersedia**; jangan menebak. Validitas record/consent tetap diputuskan lapisan existing.

Empat kolom tetap **Jenis pajak**, **Masa pajak**, **Normal / pembetulan**, **ID SPT**. Jangan mengganti teks `Model SPT` sumber dengan nama baru untuk keperluan grouping, membuang nol awal, merangkum beberapa record menjadi satu, atau menyisipkan tipe yang tidak teramati. Kolom dapat diubah lebarnya dan digulir horizontal/vertikal; tidak ada jumlah row yang dipotong agar terlihat cepat.

Di bawah tabel, satu field read-only **ID SPT yang disorot** menampilkan record ID literal dari `tree.focus()` yang masih terlihat. Ini bukan selected-ID list dan bukan kontrol pemilihan baru. Field boleh dipilih/disalin oleh pengguna melalui perilaku Entry read-only; tidak menyalin otomatis atau mencatat ID ke log. Jika fokus bukan baris visible yang valid, field kosong. Multi-selection tetap Ctrl/Shift seperti baseline; menyorot row atau menyalin ID tidak otomatis menyetujuinya.

### Pencarian, urutan, dan konfirmasi

Gunakan hitungan existing `selection.summary`: **N dipilih**, **V terlihat**, **I inventaris**. Nol hasil pencarian dibedakan dari inventaris kosong. Setelah pencarian menghapus pilihan yang pernah ada, gunakan `selection.filter_reset`; pesan dihapus ketika pengguna membuat pilihan baru, bukan akibat event internal pengosongan row. Tidak ada pilihan tersembunyi yang dikirim.

`Jenis pajak ▲/▼` tetap indikator sort. Tambahkan **Alt+J** pada dialog untuk memanggil handler `sort_type` yang sama; tidak menambah sorting kolom lain. Tampilkan hint **Urutkan jenis: Alt+J**. Sorting tidak menghapus query, selection, atau focused row; bila row fokus dipindah keluar viewport, pastikan row itu dapat terlihat tanpa mengganti fokus pengguna ke kontrol lain. Di dalam jenis, urutan tahun/bulan/model, unknown-last, dan source ties tidak berubah.

Tombol **Sedot SPT terpilih** hanya aktif bila pilihan nonkosong yang masih visible dan request aktif. Klik atau aktivasi keyboard **pada tombol itu** memakai jalur konfirmasi yang sama. Enter di kolom pencarian atau Treeview tidak menyetujui unduhan; double-click row juga bukan persetujuan. Ketika reply diterima controller, tutup dialog dan pertahankan immediate progress 0/N yang sudah tersedia. Ketika reply ditolak, jangan membuat progress seolah rincian mulai diambil.

| Keadaan | Informasi utama | Tindakan yang tersedia |
| --- | --- | --- |
| Belum memilih | Hitungan 0/V/I, petunjuk pilih satu/beberapa | Cari, sort, sorot/pilih, Hentikan; submit nonaktif |
| Pilihan valid | N/V/I dan ID row fokus dapat diperiksa | Submit atau Hentikan |
| Pencarian tanpa hasil | Tidak ada SPT yang cocok; pilihan tetap kosong | Edit/hapus query, Hentikan; submit nonaktif |
| Inventaris kosong | Daftar ini tidak memuat SPT yang bisa dipilih | Hentikan; jangan menyatakan sukses atau memilih semua |
| Payload invalid / tidak bisa dibaca | Pesan masalah pada shell dan proses penghentian existing | Tidak membuat modal pilihan yang bisa disetujui |
| Stale / Stop / worker selesai | Modal dilepas tanpa reply baru | Controller menentukan status akhir dan tindakan shell |

## 4. Dialog penggantian hasil

### Informasi sebelum keputusan

Urutan area: **penjelasan dampak → folder tepat → daftar file beserta jumlah → penjelasan penolakan → tindakan**. Folder ditampilkan dalam Entry read-only yang memungkinkan memilih dan menggulir teks penuh; pengguna tidak dapat mengedit tujuan dari dialog. Daftar tetap Treeview read-only dengan dua scrollbar, tidak menjadi checklist file. Lebar kolom/scroll harus membuat path panjang dapat diinspeksi penuh, bukan hanya basename atau elipsis tanpa akses ke nilai lengkap.

Daftar adalah snapshot `files` yang diberikan request privat. **Worker produksi saat ini mengecualikan `resume.xlsx` dari daftar persetujuan**, karena indeks diperbarui setelah validasi terpisah. UI tidak menambahkan resume ke daftar, tidak menghitung daftar baru dari folder, dan tidak menghilangkan entri payload yang ada. Jumlah adalah jumlah entry daftar, bukan jumlah SPT atau jumlah workbook di folder.

Teks harus mengatakan file dalam daftar **diganti seluruhnya**, bukan baris Excel digabung. File lain dipertahankan sesuai pemeriksaan backend. Indeks resume folder dapat memuat hasil sah lama dan baru; itu bukan klaim semua data dalam folder merupakan unduhan job saat ini.

### Delta fail-closed untuk folder

Sebelum membuat dialog interaktif, `folder` **wajib ada**, bertipe string, dan memiliki paling sedikit satu karakter bukan whitespace. Pemeriksaan `strip()` hanya untuk mendeteksi kosong; teks asli tidak dipangkas atau dinormalisasi. `files` mempertahankan validasi existing: list nonkosong berisi string nonkosong. Jangan memperluas batas ini menjadi pemindahan validasi filesystem/snapshot ke GUI.

Folder hilang, `None`, `''`, whitespace-only, atau bukan string menghasilkan error melalui `_interaction_error` **hanya bila job yang memintanya masih aktif**. Tidak ada tombol persetujuan, `overwrite=True`, `overwrite=False` buatan, atau pilihan folder pengganti. Gunakan pesan **Folder hasil sebelumnya belum tersedia. Keputusan penggantian belum dikirim.** Jalur existing kemudian meminta Stop dan menunggu terminal; jangan menyebut cleanup sudah selesai. Error request lama tidak boleh menghentikan job baru.

Folder valid tidak berarti path sudah disahkan oleh UI. Controller/worker/output tetap memeriksa snapshot dan filesystem ketika diperlukan; jangan menambahkan `.resolve()`, enumerasi folder, hash workbook, atau tautan membuka lokasi dari nilai payload ke callback Tk.

### Makna tombol dan pembatalan

**Jangan ganti** tetap mendapat fokus awal. Hanya **Ganti file tersebut** yang mengirim `True`; pilihannya mencakup seluruh daftar. Enter tidak di-bind global sebagai approve. Tidak ada checkbox “ingat pilihan”, auto-overwrite, tombol choose-folder, atau persetujuan tambahan yang menggantikan snapshot.

| Aksi | Selection | Overwrite |
| --- | --- | --- |
| Escape atau X titlebar | Stop job aktif, tanpa selected_ids | Kirim `overwrite=False` jika request masih aktif |
| Alt+S | Stop job aktif tanpa reply | Stop job aktif tanpa reply; bukan sama dengan `False` |
| Tombol aman | Hentikan unduhan | Jangan ganti |
| Tombol utama dengan keyboard/klik | Kirim selected_ids valid sekali | Kirim True sekali setelah konteks valid |
| Callback lama / request sudah selesai | Dismiss saja; tidak stop job baru | Dismiss saja; tidak memberikan jawaban baru |

Tidak menambah pertanyaan kedua ketika pengguna menolak/menghentikan. Jangan memunculkan “file berhasil dipertahankan” sebelum status akhir yang relevan; view mengakui keputusan, bukan menyertifikasi publikasi.

## 5. Copy yang diusulkan

Caption tombol pemilik tidak diganti. ID existing di bawah harus dipakai nilainya secara persis; ID baru hanya ditambahkan pada implementasi yang disetujui, bukan oleh dokumen ini. Pesan internal controller/worker tidak diubah untuk memperoleh tampilan baru.

| ID | Status | Teks/ketentuan |
| --- | --- | --- |
| `selection.title` | Existing | Pilih SPT yang akan diunduh |
| `selection.confirm` | Existing, terkunci | Sedot SPT terpilih |
| `action.stop` | Existing | Hentikan unduhan |
| `selection.summary` | Existing | `{selected} SPT dipilih · {visible} dari {inventory} SPT ditampilkan.` |
| `selection.no_match` | Existing | Tidak ada SPT yang cocok dengan pencarian. |
| `selection.filter_reset` | Existing | Pencarian berubah. Pilih lagi SPT yang akan diunduh. |
| `selection.help` | Usulan baru | Pilih SPT yang ingin diunduh. Rincian hanya diambil setelah Anda mengonfirmasi pilihan. |
| `selection.search.label` | Usulan baru | Cari jenis pajak, masa, pembetulan, atau ID SPT |
| `selection.empty` | Usulan baru | Daftar ini tidak memuat SPT yang bisa dipilih. |
| `selection.focused_id` | Usulan baru | ID SPT yang disorot |
| `selection.keyboard_hint` | Usulan baru | Pilih beberapa SPT dengan Ctrl atau Shift. Urutkan jenis: Alt+J. |
| `overwrite.title` | Existing | Ganti hasil sebelumnya? |
| `overwrite.decline` | Existing | Jangan ganti |
| `overwrite.confirm` | Existing | Ganti file tersebut |
| `overwrite.folder.label` | Usulan baru | Folder hasil sebelumnya |
| `overwrite.help` | Usulan baru | File dalam daftar ini akan diganti seluruhnya. Isi file lama tidak digabung dengan hasil baru. |
| `overwrite.files_count` | Usulan baru | `{count} file akan diganti.` |
| `overwrite.keep_hint` | Usulan baru | Pilih Jangan ganti untuk menghentikan publikasi dan mempertahankan hasil sebelumnya. |
| `overwrite.context_missing` | Usulan baru | Folder hasil sebelumnya belum tersedia. Keputusan penggantian belum dikirim. |

`copy_text` saat ini hanya menerima parameter hitungan integer non-boolean. Satu template hitungan baru `overwrite.files_count` dapat diperluas secara eksplisit dalam `_COUNT_PARAMETERS`; jangan memasukkan NPWP/tahun/path ke formatter hitungan itu. Data konteks dan ID fokus tetap raw StringVar/read-only field, terpisah dari copy. Semua contoh pengujian memakai NPWP sintetis `0000000000000001`, tahun `2025`, ID buatan, serta path `C:\Users\SYNTHETIC_USER\Downloads\SYNTHETIC_EXPORT`; jangan memakai data pengguna nyata.

## 6. Layout, aksesibilitas, dan ownership

Sasaran client dialog: selection **920×600 DIP**, overwrite **800×520 DIP** bila work area cukup. Variasi acceptance: **640×560** dan **540×390 DIP** untuk keduanya. Angka ini target desain, bukan klaim hasil pengukuran. Ukuran awal dan minimum tidak boleh melebihi work area monitor parent; native borders diukur. Jangan menggunakan `minsize(620,360)` atau `wraplength=620/540` sebagai konstanta global tanpa adaptasi.

Gunakan named fonts/warna sistem yang sudah dibuat root lewat `ui_theme`. Jangan memanggil konfigurasi shell yang mengubah root menjadi 1120×800 hanya untuk menata modal. Skala DIP ke pixel sekali melalui helper existing; font point tidak ikut dikali dua. Tabel memakai row height sesuai font terukur, dan label melipat mengikuti lebar client. Kolom/path memiliki scrollbar; jika ruang terlalu pendek, body dapat digulir sementara tombol aman/utama tetap terlihat. Pada compact tidak wajib seluruh petunjuk dan row tampil serentak; pengguna harus dapat mencapai seluruh data lewat keyboard tanpa menutup dialog.

Fokus awal: search pada selection, **Jangan ganti** pada overwrite. Tab/Shift+Tab menjangkau pencarian, tabel, field ID/folder read-only, dan tombol; urutannya mengikuti tugas, bukan posisi pembentukan widget. Focus pada read-only field tidak menyetujui apa pun. Alt+J hanya aktif di modal selection; Alt+S tetap terikat pada interaksi aktif. Setelah close/terminal, kembalikan fokus valid dengan aturan App; tombol hasil/Mulai pada terminal shell tidak boleh dikalahkan oleh callback reflow modal yang terlambat.

Gunakan reflow debounce **75 ms**, maksimum satu timer tertunda per dialog dan satu `<Configure>` handler per sumber yang diperlukan. Setiap callback memeriksa `_interaction_current` sebelum menyentuh widget atau mengirim keputusan. Daftarkan hanya timer/binding/trace milik modal pada interaction dan lepaskan ketika close. Invalidate interaction terlebih dahulu, lalu batalkan timer, hapus trace/binding, release grab, destroy, restore focus. Jangan membatalkan semua timer root atau membuat nested mainloop untuk menunggu layout. Resize tidak menghapus pencarian, selection, focused ID, atau reply state.

Tidak ada base-class dialog universal, event bus, cache global, atau abstraksi generik baru untuk dua kasus ini. Pertahankan metode publik App dan pemilik consent. Jika dibutuhkan helper layout kecil, hanya fungsi spesifik di `ui_theme` tanpa mengambil otoritas job atau menyimpan request global.

## 7. Performa: ukur sebelum batching

Synchronous filter/sort dipertahankan pada irisan pertama; pengukuran adalah deliverable, bukan alasan mengasumsikan daftar besar sudah lancar. Pada GitHub Windows runner yang sama, bandingkan baseline dan kandidat dengan inventaris sintetis **1, 100, dan 1.000 record** serta path overwrite panjang. Catat ukuran payload, Python/Tcl/Tk, ukuran jendela, median/p95 dan maksimum durasi buka dialog, filter, sort, serta jeda layanan timer pembatalan. Jalankan 10 pengulangan setelah warm-up terpisah; jangan menyebut 10 pengulangan sebagai benchmark statistik menyeluruh.

Sasaran UX awal adalah feedback aksi/pembatalan ≤100 ms, bukan ETA pekerjaan portal. Angka adalah target evaluasi, bukan assertion wall-clock keras pada shared CI. Jika jeda >100 ms berulang pada minimal dua pengulangan yang terukur, laporkan gap dan ajukan delta batching terpisah sebelum mengklaim sasaran performa terpenuhi. Bukan otomatis izin mengubah controller/I/O. Jangan mengurangi jumlah row, melemahkan validasi payload 16 MiB, atau menyembunyikan path agar target tampak lulus. Catatan performa yang belum memenuhi target tidak boleh dilabeli “telah optimal”.

## 8. Peta perubahan dan tes (bukan rencana eksekusi)

| Berkas yang mungkin berubah saat implementasi | Batas tanggung jawab |
| --- | --- |
| `spt_desktop/app.py` | Susunan dua dialog, validasi folder sebelum modal, penggunaan copy, keyboard, cleanup callback modal; public consent methods tetap |
| `spt_desktop/ui_copy.py` | Hanya ID usulan dan satu formatter count; teks pemilik/default login tidak diubah |
| `spt_desktop/ui_theme.py` | Helper skala/style/dialog yang benar-benar diperlukan; konfigurasi shell/awareness proses tidak diganti |
| `tests/test_desktop_selection_gui.py`, `tests/test_desktop_selection_sorting.py` | Regresi publik App, keyboard, exact folder dan malformed request; fixture valid harus diberi folder sintetis eksplisit |
| `tests/test_desktop_ui_copy.py`, baru `tests/test_desktop_dialog_layout.py` | Kontrak copy dan layout/fokus/cleanup kedua modal pada ukuran target |
| `tests/support_gui.py` | Hanya dukungan observasi fixture jika dibutuhkan; jangan menyisipkan folder default yang menyamarkan request invalid |
| `spt_gui.py` | Hanya penyesuaian self-test jika kontrol aktual berubah; tidak menambah screenshot/export machinery pada executable |

Controller, worker, `interaction.py`, `ui_state.py`, source capture, output, format workbook/PDF, filesystem approval, dependency, runtime allowlist, dan CI bukan sasaran refactor ini. Tes transport/lifecycle/output tetap dijalankan sebagai regresi existing. Jika kebutuhan implementasi nyata mengharuskan perubahan kontraknya, revisi desain dahulu; jangan menyelipkannya sebagai perapian UI.

**Migrasi fixture penting:** banyak tes overwrite valid sekarang hanya mengirim `{'files': [...]}`. Ketika folder diwajibkan, tambahkan folder sintetis pada tiap fixture valid secara eksplisit dan tambah fixture invalid terpisah yang sengaja menghilangkannya. `support_gui.window` saat ini mengharapkan tepat satu modal; kasus fail-closed membutuhkan setup App yang mengamati **nol modal**, bukan menghapus assertion positif lama. Jangan membuat helper secara diam-diam memperbaiki payload sebelum masuk App.

### Kriteria penerimaan

Semua baris berikut adalah tes/pemeriksaan yang harus dibuat atau dipertahankan **setelah desain dan rencana disetujui**, bukan hasil lulus pekerjaan dokumentasi ini.

| ID | Kontrak yang harus dibuktikan | Bukti minimum |
| --- | --- | --- |
| P2-01 | Scope berasal dari snapshot job yang cocok, raw NPWP/tahun tidak berubah; konteks hilang bukan identitas palsu | App tests, termasuk perubahan StringVar setelah start |
| P2-02 | Awal 0 pilihan, empty inventory/no-match beda, submit nonaktif | Regresi selection existing + caption/state baru |
| P2-03 | Search menghapus hidden selection dan memberi informasi reset yang benar | Search ulang, query kosong, effective-query sama, tanpa reply otomatis |
| P2-04 | Sort header/Alt+J memakai urutan existing, menjaga raw strings, pilihan, fokus, query dan original reply order | Seluruh tes sorting/kronologi/alias tetap lulus + shortcut |
| P2-05 | ID fokus lengkap dapat diperiksa tanpa mengubah selection; raw ID bukan Tcl iid | ID dengan spasi/kurung/semicolon/Unicode dan panjang 512; read-only field |
| P2-06 | Click/Enter/Space hanya pada tombol submit menyetujui sekali; search/tree double-click bukan approval | Keyboard/click serta duplicate callback App tests |
| P2-07 | Folder hilang/None/kosong/whitespace/bukan-string menolak membuka dialog dan meminta Stop hanya job yang benar | Nol modal, nol reply, stale malformed event tidak menghentikan job baru |
| P2-08 | Folder valid dan setiap relative path tampil literal; daftar tidak direkonstruksi atau ditambah resume | Long folder/path, leading spaces literal, jumlah file sesuai payload |
| P2-09 | Safe focus dan perbedaan Escape/X vs Alt+S tetap sesuai tabel aksi | Tests untuk kedua jenis dialog, termasuk False/cancellation_pending |
| P2-10 | `respond=False`/exception tidak menciptakan progress/terminal baru; Stop/worker exit menutup modal | Existing lifecycle/transport + response-failure tests |
| P2-11 | Request stale/asing/berulang tidak reopen atau authorize job baru | Existing consent tests tetap; callback sesudah close/reflow ditolak |
| P2-12 | Trace/binding/timer/grab milik dialog dilepas, timer root lain tetap bekerja | 25 open/close cycles sintetis, no Tcl callback error dan no net live handles; bukan klaim 100-job RAM benchmark |
| P2-13 | Data/tombol aman dapat diakses pada 920×600/800×520, 640×560, 540×390 dan work area kecil | Real Windows geometry + screenshot native, nilai pixel/DIP/scale dicatat |
| P2-14 | DPI efektif 100/150/200% pada area layar yang cukup tidak memotong label/aksi atau menggandakan skala | Windows runs yang benar-benar mengubah scaling; tanpa bukti, tandai belum terverifikasi |
| P2-15 | Keyboard/fokus bertahan melalui filter/sort/resize; callback modal tidak menggulir atau mengambil fokus shell setelah terminal | App-level tests yang menunggu seluruh timer selesai + inspeksi fokus |
| P2-16 | Performa baseline/kandidat dilaporkan untuk tiga ukuran inventaris, tanpa klaim batching sudah ada | Artifact hasil timing sintetis dan keputusan ada/tidaknya delta performa |
| P2-17 | Source/frozen dan seluruh tes Windows tetap lulus; penolakan overwrite menjaga output lama | Existing full suite/output contracts + exact head/merge/run/artifact/checksum readback |
| P2-18 | Lima teks pemilik dan bugreport tetap; JSON-hybrid/saved DOM/CLI defaults, origin Satu, grouping masa/model tidak berubah | Scope diff dan regresi existing; tidak memulihkan footer pribadi |

Tes existing yang paling menentukan: `test_closing_selection_cancels_without_implicitly_selecting_every_record`, `test_closing_overwrite_preserves_existing_files`, `test_rejected_consent_dismisses_without_cancelling_terminal_cleanup`, `test_chronology_preserves_filtered_selection_focus_and_inventory_order_reply`, `test_ready_reply_arriving_after_the_deadline_cannot_authorize_overwrite`, `test_workbook_changed_while_consent_is_open_is_not_replaced`, dan `test_captured_consent_never_switches_to_a_newer_export_folder`. Nilai expected-nya tidak boleh dilonggarkan agar view baru lolos.

## 9. Usulan pembagian implementasi setelah persetujuan

Urutkan pekerjaan menjadi **dialog selection → dialog overwrite/fail-closed → verifikasi gabungan**, masing-masing memakai tes kontrak RED→GREEN pada runner. Ini pembagian desain, belum checklist per-commit atau perintah eksekusi. Cakupan fitur selection/sorting dan workbook tetap, sehingga rencana berikutnya harus menjelaskan delta pada file yang benar, bukan mengimplementasikan daftar lama dari awal.

Persetujuan dokumen ini mengizinkan penyusunan rencana implementasi tertulis, bukan langsung mengubah produk. Metode eksekusi, merge, rilis/deployment, dan akses akun tetap keputusan terpisah. Tidak ada waktu/persentase selesai fase 2 atau biaya performa yang telah diukur pada saat menulis spesifikasi.

## 10. Sumber dan status bukti

Semua source/test dipin ke baseline; temuan merupakan inspeksi statis, bukan reproduksi visual aplikasi Oktober 20.

| Sumber | Kontrak yang dirujuk |
| --- | --- |
| [App](https://github.com/cepeter-job/spt-downloader/blob/977b06846554ca1f2e5af512a69fb201f2cbe8d1/spt_desktop/app.py) | Dialog, filter/sort, validation folder opsional, reply/dismiss/Stop/fokus |
| [Controller](https://github.com/cepeter-job/spt-downloader/blob/977b06846554ca1f2e5af512a69fb201f2cbe8d1/spt_desktop/controller.py) dan [interaction](https://github.com/cepeter-job/spt-downloader/blob/977b06846554ca1f2e5af512a69fb201f2cbe8d1/spt_desktop/interaction.py) | Private request/reply, boolean response, lifecycle/deadline dan batas payload |
| [Worker](https://github.com/cepeter-job/spt-downloader/blob/977b06846554ca1f2e5af512a69fb201f2cbe8d1/spt_desktop/worker.py) | Selected scope, overwrite snapshot/folder, resume dikecualikan dari consent list |
| [Tema](https://github.com/cepeter-job/spt-downloader/blob/977b06846554ca1f2e5af512a69fb201f2cbe8d1/spt_desktop/ui_theme.py) dan [copy](https://github.com/cepeter-job/spt-downloader/blob/977b06846554ca1f2e5af512a69fb201f2cbe8d1/spt_desktop/ui_copy.py) | Native fonts/metrics; catalogue serta counter-only template |
| [GUI selection](https://github.com/cepeter-job/spt-downloader/blob/977b06846554ca1f2e5af512a69fb201f2cbe8d1/tests/test_desktop_selection_gui.py), [sorting](https://github.com/cepeter-job/spt-downloader/blob/977b06846554ca1f2e5af512a69fb201f2cbe8d1/tests/test_desktop_selection_sorting.py), [support](https://github.com/cepeter-job/spt-downloader/blob/977b06846554ca1f2e5af512a69fb201f2cbe8d1/tests/support_gui.py) | Observable App behavior dan fixture valid/malformed |
| [Transport](https://github.com/cepeter-job/spt-downloader/blob/977b06846554ca1f2e5af512a69fb201f2cbe8d1/tests/test_desktop_selection_transport.py), [deadline selection](https://github.com/cepeter-job/spt-downloader/blob/977b06846554ca1f2e5af512a69fb201f2cbe8d1/tests/test_desktop_selection.py), [consent lifecycle](https://github.com/cepeter-job/spt-downloader/blob/977b06846554ca1f2e5af512a69fb201f2cbe8d1/tests/test_desktop_consent_lifecycle.py), [overwrite safety](https://github.com/cepeter-job/spt-downloader/blob/977b06846554ca1f2e5af512a69fb201f2cbe8d1/tests/test_desktop_overwrite_safety.py) | No auto-consent, stale/Stop/deadline, snapshot/race/rollback |

B-TK-1 dan T5 Oktober 13 tetap arsip. Prototipe MagicPath B menetapkan arah visual, bukan skema IPC atau jaminan bahwa mockup lama memuat dialog terbaru. **Dokumen ini tidak memperbarui komponen MagicPath**, tidak membuat screenshot Windows baru, dan tidak menjalankan pytest/product import/Tk/browser/build/EXE/benchmark/portal live. Bukti baru harus dibuat saat implementasi menggunakan kebijakan GitHub-runner-only pada [AGENTS.md](../../../AGENTS.md). Historical docs, PR #50, codebase, test suite, dependency, dan CI tidak diubah oleh usulan ini.
