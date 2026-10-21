# Audit dokumentasi pengembangan dan komentar kode — 21 Oktober 2026

[Kembali ke dokumentasi](../README.md) · [Peta kode](../peta-kode.md)

## Basis dan cakupan

Audit memakai `main` pada `310ba143b1f3eb9739a29620ce3931e82fa5fd14`, setelah
konsolidasi PR #66. Pemeriksaan mencakup README, indeks dokumentasi, panduan
pengembangan, kebijakan Python, arsitektur, CI/rilis, serta implementasi dan tes
yang dirujuk oleh panduan tersebut. Pada saat audit dimulai, PR #67 menangani
fixture login; perubahan fixture itu berada di luar cakupan audit ini.

Panduan aktif sudah menjelaskan sebagian besar kontrak data dan keselamatan.
Koreksi difokuskan pada petunjuk yang tertinggal dan hubungan antara panduan
dengan fungsi yang benar-benar dijalankan. Spesifikasi, benchmark, dan laporan
acceptance historis dipertahankan sebagai bukti pada revisinya masing-masing.

## Temuan dan perubahan

| Temuan pada baseline | Dampak bagi kontributor | Perubahan yang dilakukan |
| --- | --- | --- |
| README masih menyebut persiapan Python 3.14; contoh artifact belum memuat suffix attempt yang dipakai workflow. | Tahap migrasi dan artifact yang harus dipilih menjadi tidak jelas. | README menunjuk kebijakan Python produksi dan nama artifact lengkap; pemilihan menyertakan run/attempt serta artifact ID. |
| Panduan menyebut batas GitHub-runner-only tetapi alur utamanya langsung berupa pengujian/build lokal. | Pembaca dapat mengikuti contoh pada lingkungan yang tidak diizinkan oleh AGENTS.md. | [Pengembangan](../pengembangan.md) mendahulukan PR, checks, run, dan dispatch; perintah lingkungan/test/build menjadi referensi runner. |
| Panduan artifact dan pembaruan lock belum cukup membedakan inspeksi file lokal dari helper yang mengimpor produk. | Verifier atau updater dapat disangka pemeriksaan sumber yang boleh dijalankan lokal. | [CI/rilis](../ci-dan-rilis.md) dan [kebijakan Python](../python-314.md) menjelaskan konteks runner dan interpreter; hash/metadata tetap dibedakan dari eksekusi. |
| Peta modul belum mencakup beberapa pemilik bukti dan belum menghubungkan fungsi dengan alur/pengujian. | Kontributor harus menelusuri banyak file sebelum tahu tempat perubahan, terutama batas GUI/worker dan dua tahap publikasi. | [Arsitektur](../arsitektur.md) melengkapi pemilik modul; [peta kode](../peta-kode.md) menghubungkan entry point, fungsi, bentuk data, dan tes. |
| Alasan di balik sebagian cabang penting masih tersirat atau hanya dijelaskan dalam komentar Inggris. | Refactor berisiko salah memahami fallback, kelengkapan, Stop, kepemilikan file/proses, atau cakupan shard. | Komentar `#` bahasa Indonesia menjelaskan invariant terpilih pada capture/export, desktop, dan helper CI. |

## Batas perubahan kode

Perubahan pada berkas Python hanya komentar `#`. Docstring, signature, impor,
nilai default, algoritme, schema, exception, dan perintah tetap sama. Tidak ada
perubahan fixture, dependensi, resource template, atau workflow. Komentar dipilih
untuk menjelaskan maksud dan alasan, bukan menerjemahkan setiap baris kode.

Pemeriksaan struktur AST dan token nonkomentar membandingkan file yang berubah
dengan baseline tanpa mengimpor modul produk. Kesetaraan ini membuktikan cakupan
edit sumber; bukan bukti bahwa pytest, browser, GUI, build, atau acceptance live
telah dijalankan. Komentar dalam `.py` tetap memicu jalur CI penuh, dan perubahan
byte resource worker tetap mengubah fingerprint sumber.

## Verifikasi dan pemeliharaan

Review memeriksa kecocokan nama fungsi/tes, path dan anchor lokal, pin serta bentuk
artifact terhadap sumber, dan `git diff --check`. Hasil CI kandidat harus dibaca
pada PR/run yang memuat perubahan ini; hasil run baseline atau laporan lama
tidak diwariskan sebagai bukti kandidat. Bedakan SHA head PR dari SHA merge yang
di-checkout workflow, dan catat nomor attempt.

Pemeriksaan sumber pada 21 berkas Python memastikan AST, token nonkomentar,
dan seluruh baris nonkomentar identik dengan baseline. Pemeriksaan tautan mencakup
265 path/anchor lokal dalam sembilan dokumen yang berubah. Review independen
memperjelas satu komentar pada catatan observasi JSON: `request_json` tetap
menyimpan metadata request terbatas; yang tidak ditahan pada catatan tersebut
adalah objek request/response driver dan byte body respons.

Jika kontrak berubah lagi, perbarui panduan pemilik topik, peta fungsi yang
terpengaruh, dan komentar yang menjelaskan invariant tersebut pada PR yang sama.
Jangan memperbarui snapshot historis agar tampak seperti hasil versi terbaru.
