# Penerimaan otomatis sepuluh persyaratan SPT Downloader

**Status:** sepuluh kontrak dan bukti otomatis Tugas 1–5 terverifikasi; review kode/keamanan dan dokumentasi sudah ditutup. Pengguna menyetujui commit/push lima dokumen Task 5 ke draft PR #8 saja, tanpa merge. Bukti eksekusi di bawah tetap terikat pada head produk yang disebutkan, bukan klaim eksekusi ulang untuk perubahan dokumentasi. Tidak ada klaim penerimaan live.

## Commit dan eksekusi

- Head produk yang diuji pada PR #8: `3cc500e49764b4daa4ad11fcfbcdf8891ee62377`; PR masih draft, terbuka, belum digabung. Commit dokumentasi setelah head ini tidak mengubah kode/tes/CI, dan tidak boleh disebut sebagai run ulang produk tanpa bukti runner baru.
- [Run 38353364106](https://github.com/cepeter-job/spt-downloader/actions/runs/38353364106): produksi CPython 3.14.8/GIL; Windows **600 lulus dalam 144,59 detik**; portable **367 lulus, 233 deselected dalam 11,60 detik**. Delapan job: enam success, dua skipped; tidak ada tes Windows yang dilewati.
- Merge CI: `11e3cc16984efcb610ec7c43a8a50f44ab7e5ca7`; tree sama dengan head: `73cda4d0e9029105e82abd865e52ec9f79fe060e`.
- Inventaris [Windows 11791852781](https://github.com/cepeter-job/spt-downloader/actions/runs/38353364106/artifacts/11791852781) dan [portable 11792160210](https://github.com/cepeter-job/spt-downloader/actions/runs/38353364106/artifacts/11792160210) diunduh berdasarkan ID, hash ZIP dicocokkan ke API, dan node terpilih direkonsiliasi dengan log suite.
- [Audit dependensi 11791877147](https://github.com/cepeter-job/spt-downloader/actions/runs/38353364106/artifacts/11791877147) dibaca kembali: 45 dependensi, 0 kerentanan yang diketahui, 0 dilewati. Ini bukan jaminan ketiadaan semua kerentanan aplikasi.

## Matriks persyaratan

Angka menunjukkan node terpilih pada berkas kontrak yang relevan, bukan jumlah tes baru. Kelompok beririsan; jangan menjumlahkannya sebagai total suite. Seluruh 600 node Windows lulus. Tes workbook benar-benar menulis dan membuka ulang XLSX sintetis pada runner; hasil fixture bukan data wajib pajak.

| No. | Persyaratan | Node relevan lulus | Berkas kontrak |
| --- | --- | ---: | --- |
| 1 | Workbook per masa dan folder jenis terpisah | 24 | `test_period_layout.py`, `test_split_output.py` |
| 2 | Sheet form Badan dan PDF keuangan/auditan | 84 | `test_period_layout.py`, `test_financial_attachments.py`, `test_financial_capture.py`, `test_financial_export.py`, `test_financial_publication.py` |
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

Publikasi PDF Tugas 3 memiliki regresi test-first dan perbaikan direview pada `a6d76eb7fca24be80c438efd2b1e456bceacf9b5`; [run 38338852350](https://github.com/cepeter-job/spt-downloader/actions/runs/38338852350) lulus 563 tes Windows. Suite terbaru 600 tes kembali menjalankan 28 kontrak downloader, 7 capture, 13 metadata/tautan, dan 17 publikasi PDF.

Tugas 4 awal: tes `7ab3f3ba97a6662f53a6e7732d0e3b2e2f990c0f` pada [38342769494](https://github.com/cepeter-job/spt-downloader/actions/runs/38342769494) mereproduksi tujuh kontrak GUI dan dua kesiapan login. Perbaikan/kompatibilitas `1fae14f469f3cedbeb52bf18c9f6085ea98f1785` lulus 596 tes Windows pada [38346910960](https://github.com/cepeter-job/spt-downloader/actions/runs/38346910960).

Empat kontrak tambahan pada `02a0d5e016900010e11efb7bf14d79f4eacba91d` benar-benar RED pada [38352112259](https://github.com/cepeter-job/spt-downloader/actions/runs/38352112259): empat gagal, 596 lulus. Header nyata masih lama, hint hierarki lama masih tampil, dan mutasi header tidak ditolak self-test. Dua file UI diperbaiki setelah RED dan direview independen; head `3cc500e49764b4daa4ad11fcfbcdf8891ee62377` menjadi GREEN 600 tes. Caption OS tidak menggantikan bukti actual `Title.TLabel`. Label diperiksa terlihat/tidak terpotong pada permintaan geometry 540×390 dan 900×700; minimum jendela tetap diturunkan dari kebutuhan konten/font.

## Artifact yang benar-benar diverifikasi

[Artifact 11791354479](https://github.com/cepeter-job/spt-downloader/actions/runs/38353364106/artifacts/11791354479) diunduh ulang. ZIP tepat memuat `SPTDownloader.exe`, `LICENSE.txt`, `README.txt`, `build-selftest.json`, dan `SHA256SUMS.txt`; seluruh empat checksum manifest cocok. Source/frozen self-test serta persiapan worker baru/pemakaian ulang dijalankan pada runner. Frozen melaporkan 17 resource worker eksplisit, tanpa live scrape atau akses kredensial.

```text
ZIP SHA-256: 77208668f046fc5af0b27bd7c3d3df7b32c9108c155a1024699b8e8fbb563b9c
EXE SHA-256: e308c0cf31eb3034746b854be1eb097cb6cbc4d5547c941e2eec0811159f641a
```

Tiga teks nyata yang di-attest: `Coretax SPT downloader : kalau bisa ribet, kenapa dibikin gampang`, `jalankan proses sedot di background`, dan `Hasil Sedot berada di folder Downloads Windows`. Subtitle `Coretax → Excel · for personal use only` dan kredit `for personal use : punto ap` dipertahankan.

## Batas penerimaan dan tindak lanjut

Tidak ada pytest, product import, Tk/browser fixture, build, atau EXE yang dijalankan di PC pengguna untuk verifikasi ini. Lokal hanya inspeksi source/AST, metadata/hash artifact, dan rekonsiliasi evidence sintetis. CI upstream tidak ditulis ulang oleh agen; enam berkas CI/sharding masuk melalui fast-forward eksternal. Recovery stash dan investigasi lokal tetap dipertahankan.

Pengenalan form Coretax nyata dan kontrol PDF live tetap belum diterima: fixture sintetis membuktikan perilaku form yang didukung, bukan kecocokan semua layout portal. Challenge/field/aksi yang tidak dikenal tetap manual. Kesiapan form awal diperbaiki; jangan mengatribusi perubahan pada loop post-login yang tidak diubah. Tidak ada endpoint PDF yang ditebak atau remote document generation. Capture JSON privat yang diberikan pengguna sebelumnya diperiksa lokal secara baca-saja, tidak diunggah atau dijadikan fixture. Itu berbeda dari eksekusi portal live, yang tidak dilakukan di pekerjaan ini.

Review seluruh delta PR #8 dilakukan independen pada 12 modul produksi (`deleg_7174ba8c`). Satu dugaan masalah dot-segment href diregrade independen (`deleg_ac415334`) sebagai NotBug: `_financial_url` (`coretax_attachments.py:135–143`) memakai URL resolution, memeriksa origin HTTPS, dan tidak memakai href sebagai path lokal. GET tetap same-origin/no-redirect dan respons harus memenuhi pin URL serta validasi PDF; path lokal diturunkan dari hash. Tidak ada bypass origin/filesystem yang dibuktikan, sehingga tidak dibuat perbaikan produksi spekulatif. Ini bukan pembuktian ACL server atau keaslian isi dokumen. Tidak ada temuan Critical/Important terbukti yang tertinggal pada review ini; dokumentasi tidak mengesahkan merge.

Pilot JSON-first SPT Badan **belum diimplementasikan**. Setelah Tugas 5 ditutup, pilot menjadi pilihan alternatif di samping DOM; respons dari aksi View teramati harus diadaptasikan ke model canonical yang ada. Pagination parsial, provenance, checkpoint, pembatalan, raw values dan PDF tetap wajib; fixture pilot harus sintetis.
