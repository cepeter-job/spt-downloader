# Developer Documentation and Indonesian Comments Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Memutakhirkan panduan pengembangan dan menjelaskan fungsi penting melalui peta kode serta komentar bahasa Indonesia yang sesuai dengan implementasi.

**Architecture:** Pertahankan perilaku aplikasi dan kontrak yang sudah ada. Panduan pemilik topik tetap menjadi rujukan; peta kode baru menghubungkan fungsi, alur data, dan tes tanpa menyalin kontrak arsitektur.

**Tech Stack:** Python, Tkinter/ttk, Playwright, openpyxl, GitHub Actions, Markdown.

**Spec:** Permintaan pemilik proyek pada 21 Oktober 2026 untuk audit/update development docs dan komentar kode bahasa Indonesia; batas implementasi mengikuti [AGENTS.md](../../../AGENTS.md) dan [arsitektur](../../arsitektur.md).

## Global Constraints

- Baseline audit: `main` pada `310ba143b1f3eb9739a29620ce3931e82fa5fd14`; periksa kembali main sebelum publikasi.
- Perubahan Python hanya komentar `#`; jangan mengubah docstring, signature, nilai, impor, kontrol alur, atau dependensi.
- Komentar menjelaskan maksud, syarat kebenaran, dan alasan keputusan; hindari mengulang operasi yang sudah jelas.
- Pytest, import produk, Tk/browser, self-test, build, dan EXE hanya pada GitHub runner sesuai AGENTS.md; lokal hanya pemeriksaan sumber/AST/tautan/metadata.
- Pertahankan bukti historis, fixture, workflow, data pribadi, dan pekerjaan PR lain.

## Review Focus

- Panduan harus membedakan perintah runner, pemeriksaan sumber lokal, dan acceptance operator.
- Nama fungsi, modul, opsi CLI, pin, dan nama artifact harus cocok dengan sumber.
- Komentar tidak boleh menyatakan jaminan COMPLETE, atomisitas, atau privasi yang lebih kuat daripada kode.
- Semua Python yang disentuh harus memiliki AST dan token bermakna yang sama dengan baseline.
- Klaim CI harus mengacu pada revisi/run yang benar; hasil historis bukan bukti kandidat.

## Tasks

### 1. Audit dan rencana koreksi

- [x] Baca AGENTS.md, verifikasi baseline main dan PR terbuka, serta siapkan branch terpisah.
- [x] Bagi audit dokumentasi, capture/export, dan desktop untuk pemeriksaan sumber independen.
- [x] Catat temuan yang dapat dibuktikan dan pemilik dokumen yang perlu diperbarui.

### 2. Perbarui panduan kontributor

**Files:** `README.md`, `docs/README.md`, `docs/pengembangan.md`, `docs/ci-dan-rilis.md`, `docs/python-314.md`, `docs/arsitektur.md`, `docs/peta-kode.md`.

- [x] Perbaiki petunjuk runtime/artifact dan alur verifikasi melalui PR/GitHub runner.
- [x] Tulis peta fungsi dan alur CLI/desktop/capture/publikasi/CI dengan tautan sumber serta tes terkait.
- [x] Tautkan peta kode dari panduan aktif; simpan hasil audit pada laporan bertanggal tanpa menulis ulang bukti lama.

### 3. Tambahkan komentar yang membantu perubahan berikutnya

**Files:** Modul capture/export `coretax*.py`, lifecycle pada `spt_desktop/`, dan helper CI yang dipilih setelah audit.

- [x] Tambahkan komentar bahasa Indonesia pada invariant capture, fallback, kepemilikan proses, pembatalan, publikasi, dan cakupan CI.
- [x] Pertahankan semua token yang bukan komentar; jangan menambah tes baru untuk teks komentar.

### 4. Review dan verifikasi

- [x] Bandingkan AST/token setiap Python yang berubah dengan baseline tanpa mengimpor produk.
- [x] Periksa diff, whitespace, tautan lokal/anchor, dan kecocokan rujukan fungsi/tes.
- [x] Minta review independen atas akurasi dokumen dan komentar, lalu perbaiki temuan.

### 5. Publikasi dan bukti

Status dua langkah berikut dicatat pada PR/run kandidat setelah snapshot sumber
ini dipublikasikan; checklist rencana ini bukan penunjuk hasil CI terbaru.

- [ ] Publikasikan commit dan PR dengan temuan, cakupan, serta batas verifikasi yang konkret.
- [ ] Baca hasil CI pada revisi kandidat dan laporkan status, tanpa mengubah gate atau mengklaim acceptance live.
