# Desain sorting pemilihan SPT: jenis, masa, dan pembetulan

**Status: usulan desain untuk review; belum merupakan implementasi.**

PR ini hanya menambahkan dokumen ini. Tidak mengubah kode aplikasi, tes, CI,
checkpoint, scraping, format ekspor, atau PR lain. Persetujuan/merge dokumen
bukan bukti fitur telah diterapkan atau diuji dan bukan izin scrape live.

## Tujuan dan baseline

Permintaan pemilik: ketika daftar SPT diurutkan menurut jenis, masa juga
berurutan Januari sampai Desember; dalam setiap masa tampil Normal, kemudian
Pembetulan 1, Pembetulan 2, dan seterusnya.

Baseline yang diperiksa: `main` pada
`a3f998352b9e5f046f856333c9ecaaf667a668e8`.
`App.selection_dialog` di `spt_desktop/app.py` sudah memiliki header
**Jenis pajak** yang mengurutkan caption jenis secara case-insensitive.
Sort saat ini belum menambahkan kunci masa dan nomor pembetulan.
Pemeriksaan ini berdasarkan source, bukan pengujian runtime baru.

> Pembaruan kontrak default: ketentuan urutan awal pada butir 1 di bawah adalah desain historis. Permintaan berikutnya menetapkan Badan → 21 → Unifikasi → PPN sejak dialog dibuka; lihat [perilaku UI saat ini](../../ui-ux/pola-dan-status.md). Sorting manual, kronologi, dan kontrak persetujuan tetap dipertahankan.

## Perilaku yang diusulkan

1. Saat dialog pertama dibuka, pertahankan urutan inventaris dan pilihan kosong.
   Klik pertama pada **Jenis pajak** menerapkan jenis A–Z, lalu tahun menaik,
   masa Januari–Desember, dan model Normal sebelum pembetulan numerik.
2. Klik berikutnya hanya membalik urutan **jenis** A–Z/Z–A. Tahun, bulan, dan
   nomor pembetulan di dalam jenis yang sama selalu menaik. Indikator panah
   pada header hanya menyatakan arah jenis; tidak ada header/tombol baru.
3. Jenis dengan caption yang sama setelah casefold memakai kelompok sort yang
   sama. Bila seluruh kunci sort setara, pertahankan urutan inventaris asli,
   termasuk setelah klik berulang atau perubahan filter.
4. Mengurutkan tampilan tidak mengubah teks sumber, record ID, jumlah record,
   cakupan, pilihan, fokus item, atau persetujuan. Urutan pengiriman
   `selected_ids` tetap mengikuti inventaris asli, bukan urutan visual.
5. Filter aktif tetap berlaku; sort tidak memilih record tersembunyi. Mengubah
   filter tetap mengosongkan pilihan sesuai kontrak yang ada. Hasil kosong,
   metadata tidak dikenal, dan callback dialog yang sudah ditutup tetap aman.

## Aturan tahun, masa, dan model

Kunci hanya untuk presentasi, bukan normalisasi data atau validasi identitas.
Pengenalan harus cocok terhadap seluruh bentuk yang didukung; jangan menebak
bulan/tahun/model dari potongan angka, tanggal penyampaian, atau record ID.

| Nilai sumber | Kunci presentasi yang diusulkan |
| --- | --- |
| `Januari 2025` sampai `Desember 2025` | Tahun empat digit dan indeks bulan Indonesia 1–12; tahun dahulu, kemudian bulan. |
| `2025` atau `Januari - Desember 2025` | Masa tahunan yang dikenali; setelah seluruh masa bulanan pada tahun yang sama. |
| Rentang lain, format ambigu, kosong, atau tahun tidak dikenali | Setelah masa yang dikenali dalam jenis yang sama; pertahankan urutan inventaris, tanpa mengurutkan model dari masa yang tidak dapat dibandingkan. |
| `Normal` | Sebelum model pembetulan dalam masa yang sama. |
| `Pembetulan N`, `Pembetulan ke-N`, atau `Amendment N` | N berupa satu atau lebih digit ASCII; bandingkan nilai numeriknya. Bentuk ini mencakup caption publik/sintetis yang telah ada, bukan klaim semua alias portal didukung. |
| Model tidak dikenal atau kosong | Setelah model yang dikenali dalam masa yang sama; stabil menurut inventaris. |

Pencocokan caption boleh case-insensitive untuk kunci; nilai yang ditampilkan
harus tetap persis aslinya. `Pembetulan 01` dan `Pembetulan 1` memiliki peringkat
numerik sama tetapi tetap record terpisah, urutan relatif asli, dan teks asli.
`Pembetulan 0` tetap pembetulan, bukan alias Normal. Jangan memakai urutan
leksikografis yang menempatkan Pembetulan 10 sebelum Pembetulan 2.

Untuk dua bentuk tahunan yang memiliki tahun sama, keduanya memperoleh masa
sort tahunan yang sama, tanpa menggabungkan record atau mengubah caption.
Model menjadi pembanding berikutnya; ties tetap mengikuti inventaris.
Bentuk masa baru harus diperluas secara eksplisit dengan fixture sintetis,
bukan melalui parser tanggal bebas atau penebakan alias.

## Contoh hasil

Contoh berikut ilustrasi sintetis untuk satu jenis SPT dan tahun yang sama,
bukan hasil scraping atau bukti runtime:

| Jenis | Masa | Model |
| --- | --- | --- |
| PPN | Januari 2025 | Normal |
| PPN | Januari 2025 | Pembetulan 1 |
| PPN | Januari 2025 | Pembetulan 2 |
| PPN | Januari 2025 | Pembetulan 10 |
| PPN | Februari 2025 | Normal |
| PPN | Februari 2025 | Pembetulan 1 |
| PPN | Desember 2025 | Normal |

Bulan yang tidak terdapat dalam inventaris tidak dibuat. Bila ada beberapa
tahun dalam inventaris yang sah, Desember 2024 mendahului Januari 2025.
Sorting tidak memperluas atau mengganti cakupan tahun job.

## Batas implementasi mendatang

Perubahan nantinya dibatasi pada kunci sort dan perpindahan item di dialog
pemilihan. Pertahankan opaque Tk item IDs (`record-<ordinal>`), pemetaan ke
record ID literal, filtering, seleksi, dan IPC. Gunakan stdlib; tidak perlu
dependensi, abstraksi generik, atau perubahan collector/controller/worker.

Area yang perlu ditinjau pada PR implementasi terpisah: `spt_desktop/app.py`,
`tests/test_desktop_selection_sorting.py`, dan bukti kontrol sorting dalam
self-test source/frozen jika diperlukan. Dokumen ini tidak menambahkan atau
mengubah file-file tersebut. Tidak mengubah urutan scraping, penamaan/susunan
Excel/PDF, JSON-hybrid, reuse checkpoint, atau logging.

## Kriteria penerimaan untuk PR implementasi berikutnya

Seluruh butir di bawah **belum diuji oleh PR desain ini**.

| ID | Bukti perilaku yang harus disediakan |
| --- | --- |
| S1 | Campuran beberapa jenis dan seluruh 12 bulan terurut jenis → tahun → bulan, bukan alfabet bulan. |
| S2 | Dalam satu masa: Normal → Pembetulan 0/1/2/10 secara numerik, termasuk bentuk `ke-N`, `Amendment N`, leading zeroes dan stable ties. |
| S3 | Klik A–Z/Z–A hanya membalik jenis; tahun, masa, dan model tetap menaik. Klik berulang tidak mengacak ties. |
| S4 | Tahun lintas batas, kedua bentuk masa tahunan, serta format masa/model tidak dikenal mengikuti kebijakan eksplisit tanpa mengubah nilai literal. |
| S5 | Pilihan, fokus, filter, jumlah terpilih dan ID berkarakter khusus tetap benar; konfirmasi mengirim subset tepat dalam urutan inventaris asli. |
| S6 | Mengubah filter tetap menghapus consent; daftar kosong/tanpa hasil/metadata kosong tidak mengaktifkan konfirmasi tanpa pilihan. |
| S7 | Source dan frozen self-test memakai kontrol Tk aktual; regression test gagal untuk sort lama sebelum implementasi dan lulus sesudahnya. |
| S8 | Suite yang diwajibkan repositori, source/frozen checks dan artifact terkait diverifikasi pada GitHub runner; tidak memakai akun/portal nyata atau mengubah CI untuk mendapatkan GREEN. |

Implementasi memerlukan pekerjaan terpisah: kontrak tes → RED aktual → perubahan
minimal → GREEN dan review. Dokumen ini tidak mengklaim suite sudah lulus untuk
perilaku baru dan tidak mengotorisasi merge otomatis.
