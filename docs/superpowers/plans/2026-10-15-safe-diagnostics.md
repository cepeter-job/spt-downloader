# Diagnostik lokal untuk bugfixing — Implementation Plan

**Goal:** PR terpisah dari main b8c0389 menambahkan logging lokal yang membantu mencari sumber kegagalan tanpa merekam data pajak, rahasia, atau mengubah hasil pekerjaan.
**Architecture:** Satu sink JSONL per proses/session dengan antrian terbatas. Instrumentasi memakai event/field allowlist, bukan menyalin stdout/stderr atau objek aplikasi. GUI, worker dan CLI berbagi modul stdlib; korelasi job memakai digest dari ID pekerjaan, bukan NPWP/record ID.
**Tech Stack:** CPython 3.14.8/GIL; stdlib; DirectoryGuard Windows yang sudah ada. Tidak ada dependency/CI/PR18 change, telemetry, browser tracing atau upload otomatis.
**Spec:** kontrak di bawah adalah lingkup implementasi yang diminta pengguna; bukan klaim acceptance sampai gate runner lulus.

## Kontrak dan batas

- Path desktop: `%LOCALAPPDATA%\SPTDownloader\logs`; CLI menggunakan workspace diagnostik yang sama pada Windows, state lokal pada Linux. `SPT_LOG_ROOT` boleh menunjuk direktori absolut khusus diagnostik; tidak digunakan untuk mengarahkan hasil pajak. Tidak membuat log saat import. Root relatif ditolak.
- Level `SPT_LOG_LEVEL=INFO|DEBUG|OFF`; INFO lifecycle, fase, hasil/error; DEBUG progress dan detail penolakan protokol. Tidak ada mode unsafe/HTTP bodies. OFF tidak mematikan validasi produk, audit workbook atau checkpoint.
- JSONL schema 1: UTC, severity, fixed event, role, session UUID, job reference digest, sequence, elapsed/duration, fixed phase/status/operation, counters, exit/error codes. Error hanya tipe allowlist serta maksimal delapan frame file/function/line allowlist. Tidak ada message exception, chain, locals, source line, full path, URL, NPWP/tahun/nama WP, akun/sandi/cookie/token, request/reply payload, nama/hash PDF, environment, raw stdout/stderr.
- Maksimal record 4 KiB, antrian 256 record; overflow dicatat sebagai hitungan dropped. I/O hanya pada thread sink. Flush/close menunggu maksimal dua detik, tidak mengubah exception/exit/protokol bisnis.
- File unik per session/segmen, maksimal 1 MiB per file dan tiga segmen per session. Retensi tujuh hari dan anggaran 32 file per folder; cleanup hanya nama format milik logger dan file regular satu hardlink yang tidak aktif. File aktif tidak dihapus; jika kapasitas tidak bisa direklamasi, logging boleh berhenti tanpa menggagalkan aplikasi. Dokumen menyebut batas konkurensi/kerusakan storage, bukan jaminan forensik.
- Windows lexical directory guards, exclusive file creation, no-follow checks, inode validation; path redirect/reparse ditolak. Tidak menghapus checkpoint, profil, output atau file asing. Tidak ada janji perlindungan terhadap administrator/proses malicious yang menguasai akun atau filesystem.
- Fase: startup/setup, authentication, inventory/details, consent, PDF, export/verify/publish/rollback, Stop/forced cleanup, reconciliation terminal, GUI callback/poll. Logger tidak menetapkan COMPLETE dan tidak membaca data sumber untuk diagnostik.
- Akses pengguna: tombol `Buka folder log` pada Pengaturan, tanpa mengubah teks terkunci. Kegagalan membuka log memakai pesan aman. CLI normal dan worker protocol stdout tidak diduplikasi ke file.

## Review focus

1. Injection melalui exception/field/frame tidak boleh tersimpan, bahkan ketika level DEBUG.
2. Disk full/permission/rotation/thread failure tidak boleh mengganti outcome produk.
3. GUI/worker tidak berbagi handler atau file aktif; queue dan retensi tetap terbatas.
4. Stop/stale IPC/exit mismatch tidak boleh menjadi COMPLETE atau consent ulang.
5. Frozen build benar-benar memuat modul diagnostik; self-test menulis/membaca log sintetis di scratch, bukan profil pengguna.

## Eksekusi

- [x] T1: Tambah kontrak sintetis backend dan integrasi; publish test-only PR; baca RED GitHub runner sebelum source.
- [x] T2: Implementasi diagnostic_store.py dan diagnostics.py, instrumentasi entry/controller/worker/runtime/capture/PDF/export/publish/GUI. Pertahankan API bisnis.
- [ ] T3: Review independen source + privacy/path/concurrency; perbaiki blocker; jalankan full Windows/portable/source/frozen/build via workflow yang ada.
- [ ] T4: Baca artefak exact ID/digest/report; dokumentasikan cara mereproduksi bug dan batas logging. PR tetap terpisah dan tidak merged.

## Referensi desain

Python Logging Cookbook: file handler multi-proses tidak boleh memakai file bersama tanpa serialisasi; OWASP Logging Cheat Sheet: allowlist, minimisasi data, pengujian kegagalan logging, batas penyimpanan. Tidak ada sertifikasi kepatuhan hukum atau security audit menyeluruh yang diklaim.

## Bukti antara dan penutupan

T1 test-only `cb170751e4155be9857166daf36656b8d28e6af7` pada run `38682575566` membuktikan 40 kegagalan kontrak baru dengan 748 tes lama lulus. Integrasi `f4b37ae39d6c748d7fddaaf0ba1642e3528965a7`, run `38683897790`, mengungkap sembilan kegagalan Windows (786 lulus) dan satu portable; root discovery, concurrent mkdir, metadata retensi Windows, orphan lease, dan Stop sebelum izin kemudian diperbaiki setelah bukti itu.

Commit `66cf0ad98b538c9a2e554af193a5e5a578359f44`, run `38686052589`, lulus 794 tes Windows dan seluruh 369 portable, tetapi satu race test masih gagal bersama peringatan finalizer Tk di luar thread GUI. Fixture self-test baru belum melakukan `gc.collect()` pada thread GUI seperti fixture native lainnya. Cleanup itu ditambahkan tanpa mengubah batas waktu/semua assertion race; dua thread yang benar-benar mencapai mkdir kini juga dipastikan. Tidak ada pelonggaran protokol, default logger, CI, atau skip tes.

Review sumber/integrasi privasi dan perbaikan dilakukan secara independen. T3/T4 hanya ditutup setelah run final dan artefak commit yang sama berhasil; koordinat immutable dan hasil terbarunya dicatat di [PR #19](https://github.com/cepeter-job/spt-downloader/pull/19), agar bukti historis di dokumen ini tidak dianggap sebagai hasil commit setelahnya. Penerimaan portal nyata, integrasi PR #18, dan merge tidak termasuk pekerjaan logging ini.
