# Penerimaan otomatis sepuluh persyaratan SPT Downloader

**Status:** bukti otomatis terbaru terverifikasi setelah Tugas 5 dibuka kembali untuk celah href/konteks dokumen PDF. Penutupan awal pada commit dokumentasi `584d46902ec21e08a08af65b723c4a634f07f175` belum mencakup celah itu dan tidak boleh dianggap penerimaan final. Pengguna kemudian menyetujui regresi/perbaikan PDF di PR #8; perbaikan teruji pada head di bawah. Tidak ada merge atau klaim penerimaan portal live. Pembaruan laporan ini merupakan koreksi bukti, bukan klaim eksekusi ulang untuk commit dokumentasi sesudahnya.

## Commit dan eksekusi

- Head produk yang diuji pada PR #8: `89a3830d65bae04660f90d75992f06c78003088f`; PR masih draft, terbuka, belum digabung. Commit dokumentasi sesudahnya tidak mengubah kode/tes/CI dan tidak boleh disebut run ulang produk tanpa bukti runner baru.
- [Run 38360875900](https://github.com/cepeter-job/spt-downloader/actions/runs/38360875900): produksi CPython 3.14.8/GIL; Windows **608 lulus dalam 140,04 detik**; portable **367 lulus, 241 deselected dalam 11,31 detik**. Delapan job: enam success, dua skipped; tidak ada tes Windows yang dilewati.
- Merge CI: `f3ef618a1c0d41307bc7fda67c48b9f0ac69fb1d`; tree sama dengan head: `6f4e913372904b9142d40e84bf017df0063c79fa`.
- Inventaris [Windows 11795290497](https://github.com/cepeter-job/spt-downloader/actions/runs/38360875900/artifacts/11795290497) dan [portable 11794920819](https://github.com/cepeter-job/spt-downloader/actions/runs/38360875900/artifacts/11794920819) diunduh berdasarkan ID, hash ZIP dicocokkan ke API, dan node terpilih direkonsiliasi dengan log suite: 608 seluruh node Windows, subset portable 367 node, tanpa duplikat.
- [Audit dependensi 11795091131](https://github.com/cepeter-job/spt-downloader/actions/runs/38360875900/artifacts/11795091131) dibaca kembali: 45 dependensi, 0 kerentanan yang diketahui, 0 dilewati. Ini bukan jaminan ketiadaan semua kerentanan aplikasi.

## Matriks persyaratan

Angka menunjukkan node terpilih pada berkas kontrak yang relevan, bukan jumlah tes baru. Kelompok beririsan; jangan menjumlahkannya sebagai total suite. Seluruh 608 node Windows lulus. Tes workbook benar-benar menulis dan membuka ulang XLSX sintetis pada runner; hasil fixture bukan data wajib pajak.

| No. | Persyaratan | Node relevan lulus | Berkas kontrak |
| --- | --- | ---: | --- |
| 1 | Workbook per masa dan folder jenis terpisah | 24 | `test_period_layout.py`, `test_split_output.py` |
| 2 | Sheet form Badan dan PDF keuangan/auditan | 92 | `test_period_layout.py`, `test_financial_attachments.py`, `test_financial_capture.py`, `test_financial_export.py`, `test_financial_publication.py` |
| 3 | Nama Normal/Pembetulan jelas dan unik | 24 | `test_period_layout.py`, `test_split_output.py` |
| 4 | Excel mudah diolah tanpa mengubah sumber | 79 | `test_period_layout.py`, `test_exporter.py`, `test_export_safety.py` |
| 5 | Pemilihan eksplisit; hanya SPT terpilih | 52 | `test_desktop_selection.py`, `test_desktop_selection_gui.py`, `test_desktop_selection_transport.py`, `test_desktop_selected_capture.py`, `test_desktop_consent_lifecycle.py` |
| 6 | Pengenalan form login yang didukung | 69 | `test_desktop_auth.py`, `test_desktop_login_binding.py`, `test_desktop_login_check.py`, `test_desktop_login_form_readiness.py`, `test_desktop_login_home.py`, `test_desktop_login_home_browser.py`, `test_desktop_lifecycle_audit.py` |
| 7 | Teks background dan binding preferensi | 11 | `test_desktop_requested_text.py` |
| 8 | Konfirmasi penggantian file/folder | 77 | `test_desktop_overwrite.py`, `test_desktop_overwrite_safety.py`, `test_financial_publication.py`, `test_output_safety.py`, `test_desktop_output.py`, `test_desktop_consent_lifecycle.py` |
| 9 | Deskripsi Downloads menggantikan hint lama | 11 | `test_desktop_requested_text.py` |
| 10 | Header nyata serta caption sesuai permintaan | 26 | `test_desktop_requested_text.py`, `test_desktop_build.py` |

Kontrak masa/form dibuktikan melalui jumlah workbook, sheet Normal/Pembetulan, path bagian lengkap, tabel/filter/freeze, tautan relatif, nilai teks mentah, duplikat, dan angka analisis yang tidak kehilangan presisi. Kontrak pemilihan/penggantian memeriksa scope, identitas folder/file, byte lama, pembatalan, dan pemulihan. Kontrak PDF menolak origin/redirect/control tidak didukung, memeriksa MIME/ukuran/tenggat/signature/footer/hash, dan hanya memublikasikan deklarasi COMPLETE yang terikat pada SPT terpilih. Hash menjaga integritas byte, bukan membuktikan keaslian isi laporan atau ACL server.

## RED → GREEN Tugas 3–4

Publikasi PDF Tugas 3 memiliki regresi test-first dan perbaikan direview pada `a6d76eb7fca24be80c438efd2b1e456bceacf9b5`; [run 38338852350](https://github.com/cepeter-job/spt-downloader/actions/runs/38338852350) lulus 563 tes Windows. Suite terbaru 608 tes menjalankan 36 kontrak downloader, 7 capture, 13 metadata/tautan, dan 17 publikasi PDF.

Tugas 4 awal: tes `7ab3f3ba97a6662f53a6e7732d0e3b2e2f990c0f` pada [38342769494](https://github.com/cepeter-job/spt-downloader/actions/runs/38342769494) mereproduksi tujuh kontrak GUI dan dua kesiapan login. Perbaikan/kompatibilitas `1fae14f469f3cedbeb52bf18c9f6085ea98f1785` lulus 596 tes Windows pada [38346910960](https://github.com/cepeter-job/spt-downloader/actions/runs/38346910960).

Empat kontrak tambahan pada `02a0d5e016900010e11efb7bf14d79f4eacba91d` benar-benar RED pada [38352112259](https://github.com/cepeter-job/spt-downloader/actions/runs/38352112259): empat gagal, 596 lulus. Header nyata masih lama, hint hierarki lama masih tampil, dan mutasi header tidak ditolak self-test. Dua file UI diperbaiki setelah RED dan direview independen; head `3cc500e49764b4daa4ad11fcfbcdf8891ee62377` menjadi GREEN 600 tes. Caption OS tidak menggantikan bukti actual `Title.TLabel`. Label diperiksa terlihat/tidak terpotong pada permintaan geometry 540×390 dan 900×700; minimum jendela tetap diturunkan dari kebutuhan konten/font.

## Pembukaan kembali Tugas 5: href browser dan konteks sebelum GET

Pembacaan kembali PR setelah publikasi dokumentasi mengungkap catatan P2 lama yang masih berlaku: href mentah diresolusikan terhadap `page.url`, bukan base dokumen yang dipakai browser. Pemeriksaan scope hanya di awal dan setelah membaca PDF juga tidak mencegah seluruh pergantian detail sebelum GET. Ini berbeda dari dugaan dot-segment yang diregrade NotBug. Investigasi independen `deleg_b93695c6` mengonfirmasi kedua celah; penutupan otomatis awal dikoreksi, bukan diabaikan.

Delapan kasus sintetis dirancang dan direview (`deleg_b64c5b09`) sebelum publikasi test-only `925d29c184e5690e3dc50db940906443ffc9d244`. [Run RED 38359524325](https://github.com/cepeter-job/spt-downloader/actions/runs/38359524325) benar-benar menghasilkan **5 gagal, 603 lulus dalam 160,14 detik**. Lima kegagalan adalah dua base same-origin, base asing dengan href relatif yang salah diterima, serta navigasi detail setelah scan dan tepat sebelum browser fetch. Href absolut yang sah di bawah base asing dan dua guard href mentah tetap lulus.

Perbaikan satu modul `coretax_attachments.py` ditulis setelah RED dan direview (`deleg_f9e2a38f`). Scan menyimpan href mentah, href native browser, dan URL dokumen saat observasi; validasi mentah/origin tetap berlaku. Scope record diperiksa sebelum GET, dan fungsi JS yang memulai fetch memeriksa lokasi dokumen pada giliran sinkron yang sama sebelum request. Pemeriksaan scope sesudah pembacaan, batas byte/tenggat, pembatalan, no-redirect, validasi PDF/hash, dan custody/publikasi tidak dilonggarkan. Head `89a3830d65bae04660f90d75992f06c78003088f` GREEN **608 tes**, termasuk seluruh delapan regresi baru.

## Artifact yang benar-benar diverifikasi

[Artifact 11794902211](https://github.com/cepeter-job/spt-downloader/actions/runs/38360875900/artifacts/11794902211) diunduh ulang. ZIP tepat memuat `SPTDownloader.exe`, `LICENSE.txt`, `README.txt`, `build-selftest.json`, dan `SHA256SUMS.txt`; seluruh empat checksum manifest cocok. Source/frozen self-test serta persiapan worker baru/pemakaian ulang dijalankan pada runner. Frozen melaporkan 17 resource worker eksplisit, termasuk modul PDF yang diperbaiki, tanpa live scrape atau akses kredensial.

```text
ZIP SHA-256: 4705bd07b11faf4ae3d21bf43917a077ebacba872004d5cbb177146ddb81dbf5
EXE SHA-256: 4840b6f6c135de03e500c4e3bd3a1a4b296cfe8ef93f7935d10113d679b72fcc
```

Tiga teks nyata yang di-attest: `Coretax SPT downloader : kalau bisa ribet, kenapa dibikin gampang`, `jalankan proses sedot di background`, dan `Hasil Sedot berada di folder Downloads Windows`. Subtitle `Coretax → Excel · for personal use only` dan kredit `for personal use : punto ap` dipertahankan.

## Batas penerimaan dan tindak lanjut

Tidak ada pytest, product import, Tk/browser fixture, build, atau EXE yang dijalankan di PC pengguna untuk verifikasi ini. Lokal hanya inspeksi source/AST, metadata/hash artifact, dan rekonsiliasi evidence sintetis. CI upstream tidak ditulis ulang oleh agen; enam berkas CI/sharding masuk melalui fast-forward eksternal. Recovery stash dan investigasi lokal tetap dipertahankan.

Pengenalan form Coretax nyata dan kontrol PDF live tetap belum diterima: fixture sintetis membuktikan perilaku form yang didukung, bukan kecocokan semua layout portal. Challenge/field/aksi yang tidak dikenal tetap manual. Kesiapan form awal diperbaiki; jangan mengatribusi perubahan pada loop post-login yang tidak diubah. Tidak ada endpoint PDF yang ditebak atau remote document generation. Capture JSON privat yang diberikan pengguna sebelumnya diperiksa lokal secara baca-saja, tidak diunggah atau dijadikan fixture. Itu berbeda dari eksekusi portal live, yang tidak dilakukan di pekerjaan ini.

Review awal seluruh delta PR #8 dilakukan pada 12 modul produksi (`deleg_7174ba8c`), tetapi melewatkan catatan P2 base/konteks yang kemudian direproduksi dan diperbaiki. Dugaan dot-segment tetap NotBug menurut regrade `deleg_ac415334`; tidak ada bypass origin/filesystem yang dibuktikan dan href tidak menjadi path lokal. Temuan base/konteks yang berbeda ditutup melalui RED/GREEN serta review perbaikan di atas. Tidak ada temuan Critical/Important terbukti yang tertinggal pada lingkup perbaikan itu; ini bukan jaminan ACL server, keaslian isi dokumen, atau seluruh keamanan portal. Dokumentasi tidak mengesahkan merge.

Pilot JSON-first SPT Badan **belum diimplementasikan**. Setelah Tugas 5 ditutup, pilot menjadi pilihan alternatif di samping DOM; respons dari aksi View teramati harus diadaptasikan ke model canonical yang ada. Pagination parsial, provenance, checkpoint, pembatalan, raw values dan PDF tetap wajib; fixture pilot harus sintetis.
