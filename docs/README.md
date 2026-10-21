# Dokumentasi SPT Downloader

Untuk memakai aplikasi atau memulihkan checkpoint, baca [README utama](../README.md).
Kontributor mulai dari panduan di bawah dan [AGENTS.md](../AGENTS.md). Instruksi akses,
privasi dan lingkungan eksekusi di AGENTS tetap berlaku; dokumentasi tidak memperluas izin.

## Mulai dari kebutuhan Anda

| Kebutuhan | Panduan utama | Isi yang dipelihara di sana |
| --- | --- | --- |
| Setup, tes dan build | [Pengembangan](pengembangan.md) | Alur PR/runner, referensi perintah Windows/Linux, lapisan tes, build dan review. |
| Menemukan fungsi yang perlu diubah | [Peta kode](peta-kode.md) | Alur CLI/desktop, pemilik data, fungsi penting dan tes terkait. |
| Versi dan dependensi | [Kebijakan Python](python-314.md) | Pin produksi, lock, migrasi worker dan batas rollback; bukan salinan setup. |
| Kontrak backend | [Arsitektur](arsitektur.md) | Scope, akses baca, proses, sumber nilai, Excel/PDF dan publikasi. |
| Desain antarmuka | [UI/UX desain B](ui-ux/README.md) | Navigasi ke baseline, bahasa, interaksi dan checklist; bukan kontrak backend kedua. |
| Pipeline dan distribusi | [CI dan rilis](ci-dan-rilis.md) | Routing, cache, gate, artifact, provenance dan branch cleanup. |
| Error yang sedang terjadi | [Pemecahan masalah](pemecahan-masalah.md) | Gejala, tindakan aman, dan arah ke panduan rinci. |
| Mengambil log dan melaporkan bug | [Diagnostik](diagnostik.md) | Cara mengambil bukti, schema, retensi dan batas privasi. |
| Memeriksa portal/Excel nyata | [Penerimaan manual](penerimaan-manual.md) | Checklist operator berizin; bukan hasil acceptance yang sudah dilakukan. |

Urutan kontributor baru: pengembangan → peta kode → arsitektur area yang diubah →
tes yang relevan → CI. Untuk perubahan UI, mulai dari baseline yang ditautkan pada panduan
UI/UX; jangan membangun ulang fitur yang sudah ada. Jangan menggunakan akun nyata
untuk membuat tes otomatis lulus.

## Sumber kebenaran

Periksa kode pada commit yang sedang dikerjakan. Hitungan tes, screenshot dan
artifact hanya membuktikan revisi serta scope yang tertulis pada laporannya.

| Kontrak | Sumber yang diperiksa |
| --- | --- |
| Interpreter, uv dan resource worker | [runtime.py](../spt_desktop/runtime.py) |
| Dependensi langsung dan hash resolusi | [requirements.txt](../requirements.txt), [requirements-test.txt](../requirements-test.txt), [requirements-build.txt](../requirements-build.txt), [requirements-audit.txt](../requirements-audit.txt), dan [locks/](../locks/) |
| Default desktop, pilihan tersimpan dan consent | [app.py](../spt_desktop/app.py), [interaction.py](../spt_desktop/interaction.py) |
| Teks dan status GUI | [ui_copy.py](../spt_desktop/ui_copy.py), [ui_state.py](../spt_desktop/ui_state.py) |
| Workload dan routing CI | [ci_tests.py](../scripts/ci_tests.py), [ci_route.py](../scripts/ci_route.py) |
| Pipeline dan distribusi | [windows-build.yml](../.github/workflows/windows-build.yml), [build_desktop.py](../build_desktop.py), [ci_artifact.py](../scripts/ci_artifact.py) |

Saat satu kontrak berubah, perbarui panduan pemilik topiknya dan tautkan dari
panduan lain. Jangan menyalin seluruh prosedur setup, tabel versi, hasil benchmark,
atau riwayat status PR ke beberapa tempat. Ringkasan keselamatan tetap boleh ada
pada tempat pengguna melakukan tindakan.

## Catatan teknis dan bukti historis

Berkas berikut mempertahankan analisis sumber, keputusan atau hasil pada revisi
tertentu. Status seperti “pending”, “draft”, versi lama dan jumlah tes di dalamnya
adalah catatan saat dibuat, bukan daftar pekerjaan aktif atau jaminan build terbaru.
Gunakan panduan utama untuk tindakan saat ini, lalu baca catatan ini untuk asal-usul
kontrak. URL/path lama dipertahankan; tidak ada penghapusan bukti.

| Topik | Catatan yang dipertahankan |
| --- | --- |
| Audit dan optimasi CI | [Audit 12 Oktober](audit-2026-10-12.md); [evaluasi 16 Oktober](audits/2026-10-16-optimization-completion.md); [evaluasi dua shard Windows](audits/2026-10-21-windows-shard-evaluation.md); [pengukuran fixture browser](audits/2026-10-21-browser-fixture-performance.md). |
| Audit panduan kontributor | [Audit dokumentasi dan komentar 21 Oktober](audits/2026-10-21-developer-docs-comments.md). |
| Inventaris dan period-year | [Filter sumber](inventory-year-filter.md); [acceptance filter](inventory-year-filter-acceptance.md); [grid vs auxiliary](inventory-list-binding.md). |
| Metadata periode | [Diagnostik cache](period-cache-diagnostics.md); [readiness terbatas](period-cache-readiness.md); [alias kode/label terverifikasi](period-metadata-conflict.md). |
| PPN | [Tahap DOM](ppn-dom-release.md); [integrasi native PR30](ppn-native-integration.md). |
| PPh21 dan Unifikasi | [PPh21 DOM](pph21-dom-mapping.md); [ledger native PPh21](pph21-json-native.md); [ledger native Unifikasi](unifikasi-json-native.md). |
| Snapshot UI/UX | [20 Oktober sebelum Phase 2](ui-ux/baseline-2026-10-20.md); [21 Oktober setelah Phase 2](ui-ux/baseline-2026-10-21.md), dengan sumber dan batas ukur masing-masing. |

<details>
<summary>Spesifikasi, rencana dan laporan per revisi</summary>

Snapshot yang sudah disetujui tidak ditulis ulang agar terlihat seperti status
hari ini. Rencana lama bukan otorisasi baru untuk akses live, merge atau deployment.

### Spesifikasi

- [SPT Downloader — Windows Desktop Design](superpowers/specs/2026-10-09-windows-desktop-design.md)
- [Desain pemilihan SPT dan workbook per masa](superpowers/specs/2026-10-12-period-selection-layout-design.md)
- [Spesifikasi implementasi MagicPath B → Tkinter/ttk](superpowers/specs/2026-10-13-magicpath-b-tkinter-design.md)
- [Pilot sumber detail JSON-hybrid untuk SPT Badan dan Masa](superpowers/specs/2026-10-13-spt-json-hybrid-design.md)
- [Native JSON PPh Unifikasi](superpowers/specs/2026-10-19-unifikasi-native-json.md)
- [MagicPath B — Tahap 2: dialog pilihan SPT dan penggantian hasil](superpowers/specs/2026-10-20-magicpath-b-phase2-dialogs-design.md)
- [Desain sorting pemilihan SPT: jenis, masa, dan pembetulan](superpowers/specs/spt-selection-sorting-design.md)

### Rencana

- [SPT Downloader Windows Desktop Implementation Plan](superpowers/plans/2026-10-09-windows-desktop.md)
- [Rencana pengembangan, CI, dan persiapan Python 3.14](superpowers/plans/2026-10-12-development-ci-py314.md)
- [Rencana implementasi pemilihan SPT dan workbook per masa](superpowers/plans/2026-10-12-period-selection-layout.md)
- [MagicPath B — Tahap 1: State, Copy, dan Shell — Implementation Plan](superpowers/plans/2026-10-13-magicpath-b-tkinter-phase1.md)
- [PR consolidation implementation plan](superpowers/plans/2026-10-13-pr-consolidation.md)
- [Consolidation of PR18 and PR19 — Implementation Plan](superpowers/plans/2026-10-15-pr18-pr19-consolidation.md)
- [Diagnostik lokal untuk bugfixing — Implementation Plan](superpowers/plans/2026-10-15-safe-diagnostics.md)
- [SPT optimization completion](superpowers/plans/2026-10-16-optimization-completion.md)
- [Corporate observer missing-period repair](superpowers/plans/2026-10-19-corporate-missing-period.md)
- [Inventory/native readiness repair — trace and delivery plan](superpowers/plans/2026-10-19-inventory-native-readiness.md)
- [Masa capture and Unifikasi layout recovery](superpowers/plans/2026-10-19-masa-capture-layout-recovery.md)
- [Pagination, benchmark logging, and JSON-hybrid default implementation plan](superpowers/plans/2026-10-19-pagination-benchmark-json-default.md)
- [MagicPath B — Phase 2 Dialogs Implementation Plan](superpowers/plans/2026-10-20-magicpath-b-phase2-dialogs.md)
- [Phase 2 Dialog Performance Implementation Plan](superpowers/plans/2026-10-21-phase2-performance.md)

### Laporan

- [Penerimaan otomatis sepuluh persyaratan SPT Downloader](superpowers/reports/2026-10-13-feature-acceptance.md)
- [B-TK-P1 — Bukti implementasi tahap 1](superpowers/reports/2026-10-13-ui-b-phase1-evidence.md)
- [Bukti UI B — Phase 2 dialog pemilihan dan penggantian](superpowers/reports/2026-10-20-ui-b-phase2-evidence.md)
- [Phase 2 Performance — evidence and remaining limits](superpowers/reports/2026-10-21-phase2-performance-evidence.md)
- [PR20 retirement — residual scenario disposition](superpowers/reports/2026-10-21-pr20-retirement.md)

</details>
