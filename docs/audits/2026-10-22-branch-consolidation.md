# Disposisi seluruh branch pada 22 Oktober 2026

[Kembali ke dokumentasi](../README.md)

Peninjauan dimulai dari `main` pada `44969fcd73534153f5b656ec5ee9f5c8f11f42f4`.
Pemilik meminta seluruh pekerjaan yang belum digabung diselesaikan melalui merge,
konsolidasi atau penutupan, kemudian branch dihapus. Tabel ini mencatat keputusan
untuk 27 nama branch selain `main` yang ditemukan secara lokal atau pada origin.
Status merge, run dan penghapusan aktual dicatat pada PR konsolidasi; dokumen ini
tidak mengubah hasil tes historis menjadi bukti untuk tree gabungan.

## Perubahan yang dibawa ke main

| Branch / head yang ditinjau | Disposisi | Isi yang dipertahankan |
| --- | --- | --- |
| `feat/ui-delivery-completion` / `dd3407b` | Konsolidasi PR #71 | Keputusan Simpan/Abaikan/Kembali, penanganan parsial Credential Manager, caption login, ukuran awal dialog dan penjadwalan layout. |
| `fix/coretax-login-dom-badan-feedback` / `9f82db7` | Konsolidasi PR #74 | Inventaris Dilaporkan, aturan workbook Badan, penghentian kegagalan cek login dan diagnostik panel/PDF. |
| `fix/external-audit-followup-20261022` / `1494361` | Konsolidasi PR #75 | Lint correctness dan laporan coverage, kontrak workflow, media type unduhan artifact/release yang tepat dan pengikatan callback self-test. |

Ketiga head disertakan sebagai parent merge agar riwayat dan bukti review tetap
tertelusur. Konflik checklist penerimaan mempertahankan aturan kegagalan pertukaran
kode dari PR #74 dengan caption **Cek login** dari PR #71. Perubahan callback
PR #75 dan caption self-test PR #71 dipertahankan bersama. Runtime produksi dan
allowlist worker tidak diubah oleh penggabungan ini.

## Investigasi yang ditutup

| Branch / head | Disposisi | Alasan |
| --- | --- | --- |
| `feat/tk-accessibility-candidate` / `26cbec9` | Pertahankan dokumentasi; tutup PR #73 tanpa mengadopsi implementasi | Kualifikasi runtime gagal/terblokir: dua error Tk nyata, reader/password privacy, High Contrast, target pembukaan, 200% dan perpindahan DPI belum lulus. |
| `feat/tk-display-diagnostic` / `fe73e40` | Tutup investigasi dan hapus ref | Workflow display dan diagnostik exception tidak menghasilkan perbaikan produk yang terverifikasi. Hasilnya sudah dicatat pada audit kandidat. |

[Audit kandidat](2026-10-22-tk-accessibility-candidate.md), prosedur operator
historis, spesifikasi dan rencananya disimpan sebagai bukti kegagalan serta batas
yang tersisa. Tautan ke implementasi percobaan memakai commit tetap; script,
native runtime, workflow dan tes kandidat tidak menjadi fitur produksi melalui
konsolidasi dokumentasi ini. Source percobaan juga tersimpan pada bundle pemulihan
lokal yang sudah diverifikasi sebelum penghapusan branch.

## Branch lama yang sudah tergabung

Lima head berikut merupakan ancestor dari baseline main.

| Branch | Head lokal | Bukti |
| --- | --- | --- |
| `codex/badan-form-mapping` | `98de5a8` | Ancestor main dan head PR #63. |
| `codex/corporate-scrape-pdf` | `58d1c22` | Head PR #64; sudah terkonsolidasi pada riwayat main. |
| `codex/login-check-blocked-request` | `2f6d325` | Head PR #62 yang telah digabung. |
| `feat/spt-badan-json-first` | `4f010ed` | Head PR #18 yang telah digabung. |
| `fix/dom-default` | `ba16476` | Head merupakan commit main untuk PR #47. |

Untuk tiga belas branch berikut, patch keseluruhan dari merge-base ke head lokal
sama persis dengan patch squash commit pada main menurut `git patch-id --stable`.
Commit individual yang tidak menjadi ancestor bukan perubahan yang hilang.

| Branch | Head lokal | PR / squash pada main |
| --- | --- | --- |
| `diagnostics/induk-panel-timeout` | `ac820a9` | #55 / `df8e758` |
| `feat/default-spt-type-order` | `1403296` | #32 / `b8bd3dd` |
| `feat/inventory-year-filter` | `0375cd4` | #34 / `10b0da6` |
| `feat/unified-satu-login` | `3c2b63c` | #33 / `1fb7e6c` |
| `feat/unifikasi-native-json` | `f338f4d` | #40 / `af3f1bf` |
| `fix/corporate-missing-period-metadata` | `8872bf7` | #42 / `cb5acdf` |
| `fix/inventory-list-binding` | `b76fb05` | #35 / `5202112` |
| `fix/inventory-native-readiness` | `7eb08de` | #44 / `bd08b53` |
| `fix/masa-capture-layout-recovery` | `2cc65a1` | #43 / `7822e79` |
| `fix/pagination-benchmark-json-default` | `bee47c7` | #41 / `2b03463` |
| `fix/period-metadata-conflict` | `b5d10e7` | #49 / `977b068` |
| `fix/pph21-dom-mapping` | `1224cc1` | #36 / `4482063` |
| `fix/ppn-numeric-layout` | `75622bf` | #29 / `b0598db` |

## Ref pemulihan yang dapat dipensiunkan

| Branch | Head | Bukti / disposisi |
| --- | --- | --- |
| `pr18-flat-pdf-verified-merge-bc3cc40b0059` | `d510043` | Tree identik dengan parent kedua `bc3cc40`, yang merupakan ancestor main. |
| `pr18-ppn-unifikasi-merge-5815f74` | `26f72fa` | Tree identik dengan parent kedua `8a7ee83`, yang merupakan ancestor main. |
| `pr18-template21-merge-f842` | `794f773` | Tree identik dengan parent kedua `f842a33`, yang merupakan ancestor main. |
| `fix/masa-template-capture-contract` | `acf77a1` | PR #20 sengaja ditutup dan telah digantikan; riwayat disimpan untuk pemulihan. |

[Laporan pensiun PR #20](../superpowers/reports/2026-10-21-pr20-retirement.md)
memetakan 31 skenario lama, tiga characterization test yang diekstrak melalui
PR #60, serta satu batas cakupan negatif government-alias yang tetap dicatat.
Implementasi lama tidak digabung ulang. Seluruh ref pada tabel memiliki salinan
pemulihan lokal; bundle tidak dipublikasikan karena dapat membawa riwayat lokal
yang bukan bagian distribusi produk.

## Verifikasi dan batas yang tetap berlaku

Tree gabungan wajib melewati seluruh tes Windows, subset portable, lint, audit
dependensi, pemeriksaan workflow, source/frozen self-test, bootstrap executable
dan pembacaan ulang artifact berdasarkan ID serta hash. Semua eksekusi produk
tetap di runner GitHub. Penghapusan branch dilakukan setelah merge terkonfirmasi;
worktree dan file pemulihan privat dipertahankan.

Konsolidasi tidak menyatakan penerimaan Coretax/Excel live, signing, aksesibilitas
reader/password, actual 200%/mixed DPI atau target pembukaan di bawah 100 ms sudah
lulus. Penyebab transport cek login, bentuk kontrol PDF live dan jeda awal Induk
masih memerlukan bukti baru. Capture lama L9 tanpa metadata pemilik tidak diberi
pemetaan hasil tebakan. Batas tersebut tetap tercatat dalam audit terkait dan
checklist penerimaan.
