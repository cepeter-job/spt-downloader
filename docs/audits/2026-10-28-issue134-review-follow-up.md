# Tindak lanjut review audit desain dan hygiene (#134)

[Kembali ke dokumentasi](../README.md) · [Issue #134](https://github.com/cepeter-job/spt-downloader/issues/134)

Audit terlampir memakai baseline `b11a41c1`; tindak lanjut implementasi pertama
berbasis `main` `54ab897b`, setelah PR132–137. Catatan ini mengoreksi rekomendasi
untuk pekerjaan berikutnya. Dokumen historis dan lampiran audit asal tidak
ditulis ulang. Pemeriksaan sumber/AST bukan bukti eksekusi, keamanan menyeluruh,
percepatan startup, acceptance Coretax atau penerimaan Excel interaktif.

## Koreksi yang digunakan dalam rencana kerja

1. **D1: eager, lazy, dan paket adalah tiga hal berbeda.** Controller mengimpor
   `coretax_json` di tingkat modul. Impor `coretax_corporate_projection` ada di
   fungsi adapter, sedangkan `scripts.ci_runtime` hanya dipanggil lewat
   `--runtime-self-test`. Grafik AST yang memasukkan semua impor dalam fungsi
   menunjukkan kemungkinan dependensi, bukan modul yang otomatis dimuat saat
   GUI dibuka. PyInstaller tetap dapat memasukkan impor tersebut dalam paket.
   Pengukuran startup/memori dan isi artefak diperlukan sebelum klaim dampak.
2. **D2: helper filesystem bukan satu-satunya jalur recovery.**
   `publication_recovery._recover_one` memakai `coretax` dan `output` untuk
   pemeriksaan/pemulihan file. Memindahkan `_atomic_checkpoint`, `_directories`
   dan `_safe_path` saja tidak menghapus seluruh dependensi backend. Worker
   memang memerlukan browser. Sasaran pertama adalah kepemilikan helper yang
   jelas; pemisahan recovery penuh memerlukan pemetaan dan pengujian terpisah.
3. **H1: metadata versi perlu keputusan, bukan diagnosis build yang dipastikan.**
   Tidak ada sumber versi eksplisit di pyproject. Namun
   [setuptools84.2.1](https://github.com/pypa/setuptools/blob/v84.2.1/setuptools/config/pyprojecttoml.py#L286-L293)
   melewati pengambilan versi tanpa konfigurasi dynamic, dan
   [metadata versi](https://github.com/pypa/setuptools/blob/v84.2.1/setuptools/_distutils/dist.py#L1182-L1183)
   mempunyai fallback0.0.0. Ini tidak membuktikan keseluruhan build PEP517
   berhasil atau gagal. Build EXE saat ini memakai PyInstaller; perubahan versi
   harus mengikuti kebijakan yang disengaja dan mempertahankan build-info.
4. **Re-export tidak menjamin kompatibilitas monkeypatch.** Periksa nama yang
   dicari tiap pemanggil. Tes `test_selected_resume_recovery` mem-patch
   `coretax_resume._atomic_checkpoint`; perubahan import/call site harus tetap
   membuktikan race tersebut terpicu. Alias di pemilik lama saja tidak cukup.
5. **Metrik dan durasi harus terikat bukti.** Nyatakan commit, daftar file,
   aturan hitung AST/kompleksitas/siklus dan perintah reproduksi. Tidak ada janji
   portable<60detik sebelum suite baru diukur pada runner. Semua tes tetap
   dijalankan di Windows; penambahan portable menambah feedback Linux.

Sumber yang diperiksa: `coretax_json.adapt_corporate_detail`, `spt_gui.main`,
`publication_recovery._write/_recover_one`, import `spt_desktop.output`,
`build_desktop.build_command`, dan tes pemulihan pilihan. Detail baseline asal
dan tautan sumber terpin tersedia di issue134; source terbaru tetap otoritas
untuk setiap PR berikutnya.

## Urutan dan batas implementasi

Pertama perbaiki handler CLI: error/Stop menyimpan checkpoint PARTIAL tervalidasi
secara atomik, tanpa memanggil ulang exporter dari handler. Tutup resource milik
CLI tanpa menutupi kegagalan awal; interupsi tetap exit130 dan error exit1.
Lihat [desain](../superpowers/specs/2026-10-28-cli-failure-recovery.md) dan
[rencana pengujian](../superpowers/plans/2026-10-28-cli-failure-recovery.md).

Sesudahnya, issue134 masih melacak policy versi, duplikasi coverage/import mati,
navigasi AGENTS, ekstraksi helper, perluasan portable/lint dan TypedDict.
Keputusan pemisahan domain pajak, allowlist worker, literal identitas, Stop dan
gate COMPLETE/PARTIAL dipertahankan. Pembaca hash mempunyai kebijakan provider
script yang berbeda selain batas4/5MiB; penyatuan tidak boleh menerima bukti
fetch/preload pada cabang yang memerlukan script-initiator.

PR137 memperbaiki biaya verifikasi MPN dengan iterator berurutan. Perubahan itu
dipertahankan; refactor CLI tidak memberi izin capture atau publikasi baru.
