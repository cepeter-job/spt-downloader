# PDF laporan keuangan melalui POST

[Kembali ke arsitektur](arsitektur.md)

Induk Badan dapat menampilkan dokumen yang sudah ada melalui tombol **Unduh**,
tanpa href PDF permanen. URL `blob:` dibuat di browser setelah respons diterima;
URL tersebut bukan alamat sumber yang dapat dipakai ulang pada sesi berikutnya.

## Binding sumber yang ditinjau

Pada bundle corporate `525.ec1edffbb4a91d20.js`, komponen
`rshshr-citr-main-form` memasang koleksi `FinancialStatement` pada
`ui-grid-documents`. Event `buttonDownloadClick` menyerahkan baris ke
`onDownloadDocuments`; handler membentuk `DocumentId` dari baris dan
`TaxpayerAggregateIdentifier` dari wajib pajak terpilih. Service pada bundle
`main.cccfdb820c20596c.js` mengirim POST `/documentmanagement/api/download`
dengan respons blob. Interceptor menambahkan autentikasi dan `Request_From`,
serta dapat mengganti identitas wajib pajak pada konfigurasi portal.

| Bundle | SHA-256 yang ditinjau |
| --- | --- |
| `525.ec1edffbb4a91d20.js` | `fcd6d4a9244d6562a294675e802732562a9510621fbb9abbe651fa4de143048d` |
| `main.cccfdb820c20596c.js` | `696ac66dc2897c937c7df7b466382dffdf25651837a20e0a4d4235787f3c9afd` |

Handler yang sama juga melayani lampiran lain. Nama endpoint, teks Unduh, ikon,
ekstensi file, atau URL blob saja tidak membuktikan kepemilikan laporan keuangan.
Pemeriksaan sumber statis menjelaskan maksud klien; hasil unduhan nyata tetap
memerlukan pemeriksaan sesi, identitas dan byte pada setiap pengambilan.

## Batas adapter

Kolektor harus lebih dahulu berhasil membaca panel Induk yang terlihat dan
terikat ke tab/view saat ini. Jika penantian Induk gagal, Audit mencatat kegagalan
panel dan lampiran PARTIAL; alur POST belum dijalankan. Bedakan kondisi ini dari
penolakan kontrol/build atau respons PDF setelah discovery.

Penantian panel memakai satu tenggat 30 detik. Setiap pembacaan locator mendapat
sisa waktu yang tersedia, maksimum satu detik, dengan pemeriksaan Stop sebelum
setiap pembacaan. Pembacaan terakhir yang selesai sesudah tenggat tidak boleh
mengizinkan capture. Ini menghindari pengulangan batas mikro 100 ms pada Induk
yang sibuk tanpa memperpanjang tenggat total atau melonggarkan binding panel.
Setelah tenggat habis, satu probe struktur memiliki batas terpisah satu detik;
hasilnya hanya membantu diagnosis dan tidak mengizinkan unduhan.

Adapter hanya mengaktifkan tombol yang terikat ke tabel laporan keuangan pada
Induk Badan yang sedang diverifikasi. Bundle yang digunakan halaman harus cocok
dengan pin di atas. Kontrol atau build yang tidak didukung tetap PARTIAL.
Detail dari SPT Dilaporkan memakai path yang teramati
`/returnsheets/id-ID/corporate-income-tax-return/{taxpayer}/{record}/ICT_RCIT/{context}`.
Adapter mengikat posisi taxpayer dan record ke pilihan terverifikasi; context
harus satu segmen UUID yang sudah ada pada URL aktif. Context tidak dibentuk
atau ditebak. Detail submitted tersebut mendukung query mode baca yang teramati
secara literal `?view=true`, selain bentuk tanpa query yang sudah didukung.
Duplikat, parameter tambahan, encoding alternatif, kapitalisasi lain dan nilai
selain `true` ditolak. Route lama `corporatereturnsheets/{taxpayer}/{record}`
tetap didukung tanpa query. Jenis route/form lain, fragment, segmen tambahan,
atau perpindahan URL lengkap sesudah discovery tidak mengizinkan POST.
`Request_From` tetap harus sama persis dengan URL dokumen, termasuk query mode
baca. Flag ini tidak memberikan izin POST untuk endpoint atau scope lain.
Konteks browser milik desktop/CLI dibuat dengan Service Worker diblokir agar
request tidak dapat melewati route pemeriksaan. POST pada konteks reuse/CDP
yang kebijakannya tidak dibuktikan tetap tidak didukung; href biasa tetap dapat
melalui pemeriksaan GET yang sudah ada.

Request aplikasi ditangkap dan dibatalkan sebelum dikirim. Adapter memeriksa
method POST, frame utama, origin dan path persis, dua field body yang ditinjau,
identitas wajib pajak akhir, serta `Request_From` yang cocok dengan detail aktif.
Request ganda, perpindahan scope dan tindakan tulis lain membatalkan pengambilan.
Body dan header autentikasi yang diperlukan hanya hidup sementara dalam memori;
keduanya tidak masuk log, checkpoint atau laporan riset.

Satu replay memakai browser terautentikasi yang sama dan reader stream PDF yang
sudah ada. Redirect ditolak, ukuran dokumen yang diterima dibatasi 20 MiB,
MIME harus PDF, dan signature, trailer serta SHA-256 harus valid. Batas reader
bukan jaminan bahwa browser tidak melakukan buffering jaringan internal.
Stop tetap diperiksa sebelum request, selama pembacaan dan sebelum penyimpanan.
Route sementara, reader dan envelope request selalu dibersihkan.

Callback route mencatat penolakan pertama sebagai `pdf.request_rejected`
sebelum error lanjutan melaporkan state invalid. Field `pdf_guard` hanya menerima
enam tahap tetap: `context`, `route`, `count`, `body`, `authentication`, dan
`replay`. Frame module/function/baris yang diizinkan menunjuk pemeriksaan awal;
pemeriksaan field, nilai, identitas akhir dan header tetap terpisah agar lokasi
penolakannya dapat dibedakan tanpa mencatat nilainya. Pesan exception, traceback
mentah, URL, header, body, nama file dan identifier tidak disimpan. Exception
diringkas saat callback masih berjalan, tanpa menahannya untuk log berikutnya.
Event ini hanya bukti diagnosis; semua izin request dan syarat byte COMPLETE
tetap berlaku, dan Stop tetap cancellation.

Hanya byte yang lolos seluruh pemeriksaan menjadi deklarasi COMPLETE. Nama
file, tautan relatif, penahanan stream, pemeriksaan salinan dan publikasi memakai
kontrak PDF yang sama dengan href biasa. Kegagalan atau kontrol yang tidak dikenal
tetap PARTIAL. Adapter tidak memberi izin umum untuk POST, tidak membuat dokumen
jarak jauh, dan tidak menebak identifier dokumen.

## Verifikasi

Fixture sintetis Edge pada GitHub runner memeriksa binding kontrol, autentikasi,
satu replay, penolakan scope/body/build yang salah, redirect, byte tidak valid,
batas ukuran dan Stop. Hasil sintetis dan artifact CI tidak membuktikan bahwa
akun nyata sudah berhasil mengunduh laporan keuangan. Operator berizin tetap
memeriksa hasil live melalui [penerimaan manual](penerimaan-manual.md), tanpa
mengirim data wajib pajak atau kredensial ke repository.
