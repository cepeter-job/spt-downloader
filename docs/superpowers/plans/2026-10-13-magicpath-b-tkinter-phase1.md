# MagicPath B — Tahap 1: State, Copy, dan Shell — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended when delegation is available) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Menghasilkan irisan pertama B-TK-1 yang dapat dijalankan dan diuji: jendela utama Tkinter/ttk dengan bahasa yang disetujui, formulir, ringkasan pekerjaan, penanda tahap, dan progres yang tidak menyesatkan.

**Architecture:** `App` tetap mengoordinasikan controller dan lifecycle; empat modul presentasi kecil memisahkan teks, state murni, tema/layout, dan widget. Pertahankan dialog pemilihan SPT, penggantian file, Pengaturan, jalur login, serta mesin Excel/PDF yang sudah berjalan; jangan menulis ulang backend untuk mencocokkan prototipe. Seluruh eksekusi produk dan tes dilakukan di GitHub runner.

**Tech Stack:** CPython 3.14.8 dengan GIL sesuai baseline; stdlib Tkinter/ttk, dataclasses, typing, unittest.mock, dan pytest dari lock repository. Tidak ada dependensi produk baru.

**Spec:** [B-TK-1](../specs/2026-10-13-magicpath-b-tkinter-design.md), terutama bagian 5–7, 11, dan irisan 1 pada bagian 16.

## Global Constraints

1. Pertahankan `App(root, workspace, controller=None)`, API controller, private consent channel, satu job aktif, Stop, dan verifikasi COMPLETE. Tidak mengubah capture, PDF, layout Excel, origin allowlist, Credential Manager, CLI, `WORKER_FILES`, pin Python, dependensi, atau workflow.
2. Enam teks terkunci pada tabel di bawah wajib literal. NPWP tetap string 16 digit ASCII tanpa normalisasi; tahun empat digit 1900–2100. Pemilihan SPT tetap eksplisit, bukan unduh semua otomatis.
3. Target shell: 1120 × 800 DIP; dua kolom mulai 960 DIP; formulir satu kolom di bawah 560 DIP lebar isi atau ketika teks tidak muat. Penanda compact 2 × 2; gap 24 DIP; ringkasan sekitar 244 DIP; spasi 4/8/12/16/24/32 DIP; kontrol 40–44 DIP. Jangan memperkecil font atau membesarkan minimum melebihi work area.
4. Pertahankan polling 100 ms. Debounce reflow 75 ms dengan satu callback tertunda. Tidak ada Tk pada thread worker, parsing workbook/PDF pada GUI, ETA rekaan, event mentah di log, atau progres 100% sebelum terminal COMPLETE dari controller. Anggaran latency/performa B-TK-1 tetap target yang belum dibuktikan.
5. [AGENTS.md](../../../AGENTS.md): pytest, product import, Tk/browser fixture, source/frozen self-test, build, dan EXE **hanya di GitHub runner**. Lokal boleh pemeriksaan dokumen/source/AST dan hash; itu bukan bukti runtime. Merge, deployment, dan akses Coretax nyata memerlukan keputusan terpisah.

## Review Focus

1. **Fixture event tanpa job ID:** tes GUI/self-test lama mengirim progress langsung ketika controller idle. Perbaiki fixture agar meniru job sah; jangan membuat reducer menerima event asing untuk mempertahankan tes lama. Dimiliki T2, T4, T5.
2. **Counter berpindah makna:** denominator inventaris tidak boleh menjadi jumlah SPT terpilih; counter hilang, boolean, atau tidak konsisten tidak boleh berubah menjadi nol atau hitungan pasti. Dimiliki T2 dan T4.
3. **Stop/consent berdekatan dengan terminal:** membangun shell tidak boleh membuka kembali dialog atau menghentikan job baru melalui callback lama; `respond=False` bukan sukses dan bukan alasan membatalkan job lain. Dimiliki T2 dan T4.
4. **Judul humor panjang pada jendela kecil:** heading nyata dan hint Downloads harus tetap terlihat, bukan hanya benar di caption atau lolos karena jendela diperbesar keluar layar. Dimiliki T3 dan T5.
5. **Cek login setelah ekspor:** pengujian login tidak boleh menghapus output/counter ekspor sebelumnya atau menyatakan unduhan selesai. Dimiliki T4; katalog status login lengkap tetap tahap 3.

---

## 1. Persetujuan, baseline, dan batas tahap

**Revisi rencana:** B-TK-P1 · 13 Oktober 2026. **Status:** siap untuk review rencana; belum dieksekusi.

Pemilik menjawab **“Approved”** setelah menerima spesifikasi B-TK-1. Persetujuan itu dicatat terhadap commit dokumentasi `6f8deb049364e73611fe300dc898a3c77d571f63`, blob spesifikasi `94085b9b069de8b702ef27d84f213a4ca5d8c113`. Status “untuk review” dalam snapshot spesifikasi merupakan status saat ditulis; catatan ini merekam persetujuan sesudahnya, tanpa mengubah isi keputusan yang disetujui. Ini bukan GitHub review approval yang dibuat atas nama pemilik.

Pemeriksaan ulang menemukan `main` masih `be67f5153a07ce100048d67191a02ca1d0fca1db`. PR #11 masih draft, terbuka, belum merged. Sumber visual tetap MagicPath B, komponen `460285747178659840`, revisi `460301118992445440`. Tidak ada perubahan prototipe pada pekerjaan perencanaan ini.

**Yang diselesaikan tahap 1:** AC01–AC05; kerangka layout yang aman untuk jendela utama; state/copy yang siap dipakai tahap selanjutnya; integrasi yang mempertahankan fungsi baseline. Panel hasil masih mempertahankan fungsi status dan buka-folder yang ada, bukan klaim seluruh redesign hasil B08 sudah selesai.

**Yang belum diimplementasikan:** desain ulang dialog B04/B07, penguatan folder wajib pada overwrite, batching daftar besar, konfirmasi Pengaturan dirty, seluruh copy/status login dan hasil baru, rincian PDF, pengujian aksesibilitas lengkap, benchmark 100 siklus, serta penerimaan manual. Semuanya tetap milik irisan 2–5; tidak dihapus dari B-TK-1.

| Irisan B-TK-1 | Pemilik pekerjaan | Status dalam rencana ini |
| --- | --- | --- |
| 1: state/copy/shell | T1–T5; AC01–AC05 | Direncanakan sampai bisa direview sebagai PR produk. |
| 2: pemilihan/penggantian | Rencana berikutnya; AC06–AC14, AC18 | Regresi baseline dipertahankan; visual dan penguatan baru ditunda. |
| 3: hasil/login/Pengaturan | Rencana berikutnya; AC15–AC22 | Fungsi baseline dipertahankan; bukan klaim penerimaan penuh. |
| 4: reflow/a11y/performa | Rencana berikutnya; AC23–AC26 | Shell tidak boleh menambah clipping; matriks menyeluruh belum selesai. |
| 5: regresi/distribusi | Gerbang T5 untuk irisan 1; AC27–AC28 penuh pada konsolidasi | Tetap perlu build dan readback per head; penerimaan manual terpisah. |

## 2. Peta file dan dependensi tugas

Semua file bertanda baru di bawah adalah **target implementasi**, belum ditambahkan oleh PR dokumentasi ini.

| Tugas | File produk | File pengujian | Hasil independen |
| --- | --- | --- | --- |
| T1 | Baru `spt_desktop/ui_copy.py` | Baru `tests/test_desktop_ui_copy.py` | Katalog teks murni dan kontrak template. |
| T2 | Baru `spt_desktop/ui_state.py` | Baru `tests/test_desktop_ui_state.py` | Pemetaan state/progres yang tidak mengakses Tk atau disk. |
| T3 | Baru `spt_desktop/ui_theme.py`, `spt_desktop/ui_views.py` | Baru `tests/test_desktop_ui_theme.py`, `tests/test_desktop_ui_views.py` | Shell nyata dapat dirender dengan callback sintetis. |
| T4 | Ubah `spt_desktop/app.py` dan `spt_gui.py` (self-test UI) | Baru `tests/test_desktop_ui_integration.py`; perbarui fixture/ekspektasi pada tes GUI dan teks | Shell tersambung; self-test berubah pada commit integrasi yang sama. |
| T5 | Tidak menambah perilaku produk; dokumentasi bukti | Gunakan seluruh tes T1–T4 dan build/branding existing | Gerbang source/frozen, readback, serta status irisan yang jujur. |

Dependensi: T1 → T2 → T3 → T4 → T5. T1/T2 tidak mengimpor `app`, `controller`, Tk, Playwright, openpyxl, exporter, atau output. T3 mengimpor T1/T2, bukan sebaliknya. App mempertahankan otoritas controller. Jangan membuat modul placeholder, service locator, event bus, atau framework terjemahan.

Pemeriksaan independen paling berguna saat eksekusi adalah penelusuran fixture/self-test dan review lifecycle consent. Delegasikan hanya jika alat subagen tersedia; jangan menyebut self-review sebagai review independen. Rencana ini disusun melalui inspeksi sumber dan self-review, tanpa klaim hasil subagen.

## 3. Kontrak lintas tugas yang ditetapkan

### 3.1 Teks yang tidak boleh berubah

| ID | Teks literal |
| --- | --- |
| `app.title` | Coretax SPT downloader : kalau bisa ribet, kenapa dibikin gampang |
| `app.subtitle` | Coretax → Excel · for personal use only |
| `app.credit` | for personal use : punto ap |
| `settings.background.label` | jalankan proses sedot di background |
| `results.location_hint` | Hasil Sedot berada di folder Downloads Windows |
| `selection.confirm` | Sedot SPT terpilih |

T1 menyediakan katalog B-TK-1 bagian 11. T4 baru memakai teks yang diperlukan jendela utama: judul, subtitle, kredit, form, tombol Mulai/Hentikan/Buka, dan tahap. Caption Pengaturan `Cek Kredensial`/`Batalkan Cek` tetap baseline sampai tahap 3 agar perubahan ini tidak menyeret validator build dan tes login. Teks tersebut bukan pengecualian permanen terhadap katalog; ini urutan migrasi.

### 3.2 State ekspor murni

Tetapkan `Counters` dan `ExportState` sebagai frozen dataclass. `Counters` memiliki `processed`, `total`, `verified`, `scanned`, masing-masing `int | None`. `ExportState` memiliki `job_id: str | None`, `view_state: str`, `stage: str | None`, `percent: int | None`, `npwp: str`, `year: str`, `inventory: Counters | None`, `details: Counters | None`, `selected_count: int | None`, `terminal_status: str | None`, `output: str | None`, dan `consent: tuple[str, str] | None`. Default adalah idle, identitas kosong, tanpa counters/output/consent, percent 0.

Jangan menambah salinan records, path daftar overwrite, password, atau exception ke state. `stage` memakai nilai event baseline; `consent` hanya pasangan `(kind, request_id)`. Status login tidak dimasukkan ke state ekspor. Message aman existing tetap ditangani App, dipotong maksimum 500 karakter, bukan diurai untuk menentukan state.

| Fungsi di `ui_state.py` | Kontrak |
| --- | --- |
| `scope_errors(npwp: str, year: str) -> dict[str, str]` | Mengembalikan key `npwp`/`year` dengan copy ID error. Tidak mengubah input. App tetap memanggil `validate_job_scope` sebelum start. |
| `begin_export(job_id: str, npwp: str, year: str) -> ExportState` | Dipanggil sesudah start sah; snapshot baru, state preparing, percent None. Tidak mengakses controller. |
| `reduce_export(state: ExportState, event: Mapping[str, object], *, controller_active: bool) -> ExportState` | ID harus cocok; terminal hanya diterapkan setelah controller idle. Abaikan progres lama sesudah terminal/stopping. Tidak mengesahkan output lewat filesystem. |
| `mark_stopping(state: ExportState) -> ExportState` | State stopping, consent dibuang; bukan terminal CANCELLED. Idempotent; state terminal tidak diubah. |
| `record_reply(state: ExportState, *, job_id: str, kind: str, request_id: str, selected_count: int \| None = None, overwrite: bool \| None = None) -> ExportState` | Dipanggil **hanya setelah** `controller.respond(...)` mengembalikan True. Harus cocok dengan consent aktif; selain itu no-op. Selection menyimpan jumlah saja; overwrite false → cancellation_pending, true → publishing. |

`scope_errors` boleh mengulang dua pemeriksaan literal yang kecil untuk menempatkan error per field; jangan mengekstrak validator backend hanya demi abstraksi. Tes equivalence mengikat hasilnya dengan `validate_job_scope` existing.

Pemetaan state mengikuti bagian 7 spesifikasi. Inventaris dan detail disimpan terpisah. Pada event progress, field counter yang tidak ada menjadi None pada kelompok tahap tersebut; tidak mengambil denominator tahap lain. Hanya integer non-boolean, nonnegatif, serta hubungan `verified <= processed <= total` yang diketahui sah dapat ditampilkan sebagai kelompok detail. Ketika kelompok tidak konsisten, sembunyikan metrik kelompok itu; jangan clamp untuk menyiratkan lengkap. `scanned` hanya label inventaris, bukan jumlah ID unik. Export/publish/terminal mempertahankan detail terakhir yang sah untuk job yang sama. Tampilan jumlah pilihan berasal dari reply sah, bukan panjang daftar inventaris.

Percent tidak dihitung ulang. `setup` memakai None; progress memakai integer 0–99 dari controller; COMPLETE sah memakai 100, status lain tidak boleh 100. Event yang melanggar pasangan status/percent diabaikan oleh reducer sebagai pertahanan presentasi, bukan pengganti validator controller. Output hanya diterima dari terminal COMPLETE/PARTIAL yang sudah dilepas controller; progress dengan key output tidak mengaktifkan tombol hasil.

### 3.3 Shell dan adapter App

`ui_theme.py` menyediakan `LayoutPolicy` (frozen dataclass: `compact`, `form_stacked`, `stage_columns`, `summary_width_dip`, `gap_dip`), `layout_policy(client_width_dip: float, content_width_dip: float) -> LayoutPolicy`, `dip_to_px(value: float, scale: float) -> int`, `effective_scale(root: tk.Misc) -> float`, `client_work_area(root: tk.Tk) -> tuple[int, int]`, dan `configure_theme(root: tk.Tk) -> None`.

`effective_scale` memakai ukuran 1 inci efektif Tk dibagi 96; dokumentasikan hasilnya sebagai skala efektif toolkit, bukan klaim per-monitor sudah benar. Jangan ubah DPI awareness proses. `client_work_area` membaca work area monitor jendela Windows dan mengurangi ukuran non-client yang terukur; helper native tetap di `ui_theme.py`, memakai ctypes stdlib dan API resmi yang diperiksa implementer sebelum menulisnya. Jika pengukuran gagal, pertahankan geometri yang sudah dipilih window manager tanpa menerapkan pembesaran/minimum baru; catat pengujian work-area sebagai belum terverifikasi, bukan menebak margin taskbar. Dukungan multi-monitor menyeluruh tetap tahap 4.

`ui_views.py` menyediakan `MainView(ttk.Frame)` dengan konstruktor `MainView(master, *, year_default: str, on_start: Callable[[], object], on_stop: Callable[[], object], on_settings: Callable[[], object], on_open_result: Callable[[], object])`. Empat callback tidak dipanggil saat konstruksi.

Handle publik yang diteruskan App: `npwp`, `year`, `status`, `percent` (StringVar), `npwp_entry`, `year_entry`, `start_button`, `stop_button`, `settings_button`, `open_button`, `bar`, `results_label`. Handle uji tambahan: `heading`, `stage_labels` (empat Label), `npwp_error`, `year_error`, `scope_npwp`, `scope_year`, `scope_selected` (StringVar).

Metode: `render(state: ExportState, *, active: bool) -> None`, `set_busy(active: bool, *, stopping: bool = False) -> None`, `show_errors(errors: Mapping[str, str]) -> None`, `request_reflow() -> None`, `dispose() -> None`. `render` tidak melakukan start, consent, login, baca file, atau `focus_set`. `show_errors` hanya menampilkan error; App memilih fokus. `dispose` hanya membatalkan callback milik view, bukan semua timer root.

App mempertahankan semua metode publik dan handle baseline. `self._ui_state` menampung ExportState. Controller tetap menentukan operasi aktif. Login check memakai cabang existing sebelum reducer; ekspor terakhir tidak dihapus. Hook `_reply_interaction` boleh merekam jumlah/keputusan sesudah True; tidak mengubah payload, `_interaction_current`, atau tindakan pada False. Jangan memanggil pembatalan baru hanya karena respons stale ditolak.

## 4. Cara menjalankan TDD tanpa melanggar kebijakan runner

Perintah pytest dalam tugas berikut adalah perintah **untuk GitHub runner yang sudah diprovisi workflow**, bukan terminal lokal. Jangan menjalankannya di container ChatGPT atau komputer pengguna.

Sebelum tugas pertama, baca ulang AGENTS dan diff `main` terhadap baseline. Buat isolated branch/worktree sesuai skill eksekusi. Bila PR #11 belum merged, branch implementasi dapat berasal dari head dokumennya dan tetap menargetkan `main` agar workflow PR yang ada berjalan; jelaskan commit dokumentasi yang ikut terbawa. Jangan menggabungkan PR #11 atau mengubah base workflow hanya sebagai jalan pintas. Nama branch yang direncanakan: `feat/ui-b-phase1`.

Tes baru diimpor di dalam fungsi uji ketika perlu, bukan mengimpor modul yang belum ada saat collection. Tes yang membangun Tk tetap di fungsi/fixture runtime, bukan saat collection. Semua modul tes baru dijalankan full suite Windows; **tidak perlu mengubah** `PORTABLE_FILES` untuk tahap ini. Linux tetap mengumpulkan inventaris yang sama dan menjalankan subset yang ditinjau.

Siklus runner untuk setiap tugas:

1. Tambahkan tes kontrak gagal; buat commit checkpoint `test: ...` dan push ke branch PR produk. Identifikasi kegagalan yang diharapkan sebelum menyebut RED.
2. Gunakan run PR otomatis, atau dispatch workflow existing `Build Windows app` pada ref yang sama; catat run/attempt, head SHA, checkout/merge SHA, dan node ID gagal. Tunggu bukti RED sebelum kode solusi.
3. Implementasikan minimum yang diputuskan tugas; commit checkpoint `feat:`/`refactor:` dan push. Jangan melakukan squash/rebase saat run pembuktian masih berlangsung.
4. Periksa full Windows run baru untuk head yang benar; bukti GREEN harus mencakup tes tugas dan seluruh regresi wajib. Dispatch existing tidak mendukung input arbitrary pytest-filter; perintah terfokus di bawah adalah resep reproduksi runner, bukan parameter workflow baru.
5. Catat bukti TDD dan hasil review pada laporan tahap. Jika ada catatan commit baru, bedakan commit dokumentasi dari tree produk yang diuji. Jangan menghapus tes atau melemahkan CI agar tampak hijau.

`workflow_dispatch` tersedia pada baseline. Push feature branch sendiri tidak memicu workflow push-main; gunakan PR ke main atau dispatch. Run baru dapat membatalkan run lama karena concurrency existing, sehingga jangan kehilangan bukti RED saat mendorong GREEN terlalu cepat.

## 5. Tugas implementasi

### T1 — Katalog teks yang natural dan tetap menjaga teks pemilik

**Files:** Create `spt_desktop/ui_copy.py`, `tests/test_desktop_ui_copy.py`. Belum mengubah widget.

**Interfaces:** Consumes katalog B-TK-1 bagian 11. Produces `COPY: Mapping[str, str]`, `STAGE_LABELS: tuple[str, str, str, str]`, `copy_text(key: str, **values: str | int) -> str`.

- [ ] **Step 1 — Tulis tes kontrak berikut, termasuk parametrization enam teks terkunci.**

```python
def test_main_copy_is_exact_and_selection_is_not_automatic():
    from spt_desktop.ui_copy import copy_text, STAGE_LABELS
    assert copy_text('action.start') == 'Mulai unduh'
    assert copy_text('form.help') == 'Setelah daftar muncul, pilih SPT yang ingin diunduh.'
    assert copy_text('selection.confirm') == 'Sedot SPT terpilih'
    assert STAGE_LABELS == ('Masuk ke Coretax', 'Daftar SPT',
                            'Mengambil rincian', 'Hasil unduhan')


def test_selection_summary_requires_named_integer_counts():
    import pytest
    from spt_desktop.ui_copy import copy_text
    assert copy_text('selection.summary', selected=2, visible=3, inventory=8) == (
        '2 SPT dipilih · 3 dari 8 SPT ditampilkan.')
    with pytest.raises(TypeError):
        copy_text('selection.summary', selected=True, visible=3, inventory=8)
    with pytest.raises(ValueError):
        copy_text('selection.summary', selected=2, visible=3)
    with pytest.raises(KeyError):
        copy_text('key.yang.tidak.ada')
```

Tambahkan `test_locked_owner_copy_is_literal` untuk seluruh tabel 3.1 dan `test_template_rejects_extra_or_negative_counts`: parameter berlebih/kurang → ValueError, counter negatif → ValueError, tipe salah termasuk bool → TypeError. Enam teks dibandingkan literal independen, bukan mengambil expected dari COPY yang sedang diuji.

- [ ] **Step 2 — Buktikan RED di runner:** `.venv\Scripts\python.exe -m pytest tests/test_desktop_ui_copy.py -q --basetemp "$env:RUNNER_TEMP/spt-b-t1"`. Expected: tes baru gagal karena modul belum ada; collection tetap bisa selesai.
- [ ] **Step 3 — Implementasikan tiga interface T1.** Kamus sederhana, template bernama, validasi parameter eksplisit; tanpa i18n framework. Masukkan katalog yang disetujui, tetapi jangan ubah caption dialog existing pada tugas ini. Tidak ada import Tk atau modul produk lain.
- [ ] **Step 4 — Buktikan GREEN untuk perintah T1 dan full Windows suite.** Tambahkan pemeriksaan AST import murni dalam tes; jangan menyebut pemeriksaan AST lokal sebagai bukti tes.
- [ ] **Step 5 — Review dan catat checkpoint T1.** Periksa diff enam teks terkunci dan isi form.help, catat RED/GREEN SHA serta node ID. Tidak melanjutkan jika teks hilang atau template diam-diam menerima parameter salah.

### T2 — State dan counter terpisah dari widget

**Files:** Create `spt_desktop/ui_state.py`, `tests/test_desktop_ui_state.py`.

**Interfaces:** Consumes copy ID T1. Produces seluruh dataclass/fungsi tabel 3.2. Tidak ada akses ke filesystem, controller, atau Tk.

- [ ] **Step 1 — Tambahkan tes murni dengan event sintetis ber-ID.**

```python
def test_inventory_counts_do_not_become_selected_detail_counts():
    from spt_desktop.ui_state import begin_export, reduce_export
    state = begin_export('job-a', '0000000000000001', '2025')
    state = reduce_export(state, {'job_id': 'job-a', 'type': 'progress',
        'stage': 'inventory', 'percent': 20, 'processed': 4, 'total': 4,
        'scanned': 90}, controller_active=True)
    state = reduce_export(state, {'job_id': 'job-a', 'type': 'progress',
        'stage': 'details', 'percent': 43, 'processed': 1, 'total': 3},
        controller_active=True)
    assert state.details.total == 3
    assert state.details.verified is None
    assert state.selected_count is None
    assert state.percent == 43


def test_publish_is_not_complete_and_late_progress_does_not_clear_stop():
    from spt_desktop.ui_state import begin_export, reduce_export, mark_stopping
    state = begin_export('job-a', '0000000000000001', '2025')
    event = {'job_id': 'job-a', 'type': 'progress', 'stage': 'publish', 'percent': 99}
    state = reduce_export(state, event, controller_active=True)
    assert state.terminal_status is None and state.output is None
    state = mark_stopping(state)
    assert reduce_export(state, event, controller_active=True) == state
    assert state.view_state == 'stopping'
```

Tambahkan tes berikut dengan assertions tepat: `test_foreign_or_missing_job_id_is_ignored` (state identik); `test_new_job_clears_scope_counts_output_and_consent` (semua konteks lama dibuang); `test_details_reject_bool_negative_and_inconsistent_counts` (metrik tidak ditampilkan); `test_complete_requires_idle_controller_and_matching_terminal` (100/progress/active terminal tidak membuka output); `test_partial_cannot_use_100_percent`; `test_terminal_retains_last_valid_detail_counts`; `test_reply_requires_matching_job_kind_and_request` (stale no-op); `test_overwrite_decline_is_pending_not_terminal` (cancellation_pending); dan parametrization `test_scope_errors_matches_controller_validation` untuk ASCII/Unicode, whitespace, pemisah, nol awal, serta tahun 1899/1900/2100/2101. Equivalence test boleh mengimpor controller di tes, bukan di modul state.

- [ ] **Step 2 — Buktikan RED:** `.venv\Scripts\python.exe -m pytest tests/test_desktop_ui_state.py -q --basetemp "$env:RUNNER_TEMP/spt-b-t2"`. Kegagalan di kontrak baru, bukan syntax/collection.
- [ ] **Step 3 — Implementasikan interface 3.2 dengan pemetaan eksplisit.** Tetap pakai persen event. Stop/terminal mengalahkan progress/consent baru. Validasi input tidak menebak jenis error dari kalimat exception. Jangan membuat terminal atau file output dari persen.
- [ ] **Step 4 — Buktikan GREEN T1/T2 dan full Windows suite.** Pastikan tes memeriksa state/value, bukan urutan helper internal. Tambahkan tes import boundary sehingga Tk/exporter/output tidak masuk transitif.
- [ ] **Step 5 — Catat checkpoint T2 dan review tabel state terhadap B-TK-1 bagian 7.** Output pemeriksaan tidak memuat NPWP/record/path nyata; semua fixture sintetis.

### T3 — Bangun shell ttk yang dapat diuji tanpa worker

**Files:** Create `spt_desktop/ui_theme.py`, `spt_desktop/ui_views.py`, `tests/test_desktop_ui_theme.py`, `tests/test_desktop_ui_views.py`.

**Interfaces:** Consumes COPY/STAGE_LABELS dan ExportState. Produces `LayoutPolicy`, helper tema, dan `MainView` sesuai 3.3. Shell dapat dibuat dengan empat callback no-op; belum mengganti App.

- [ ] **Step 1 — Tulis tes kebijakan layout dan widget nyata.**

```python
def test_layout_thresholds_do_not_shrink_typography():
    from spt_desktop.ui_theme import layout_policy
    assert layout_policy(959, 600).compact is True
    assert layout_policy(960, 600).compact is False
    assert layout_policy(960, 559).form_stacked is True
    assert layout_policy(960, 560).form_stacked is False
    assert layout_policy(640, 540).stage_columns == 2
    assert layout_policy(1120, 700).stage_columns == 4


def test_dip_conversion_is_applied_once():
    from spt_desktop.ui_theme import dip_to_px
    assert dip_to_px(24, 1.0) == 24
    assert dip_to_px(24, 1.5) == 36
    assert dip_to_px(24, 2.0) == 48
```

`test_shell_has_one_real_heading_and_downloads_hint` membangun `MainView` pada Tk root dengan callback spy, memeriksa satu Title.TLabel dengan teks terkunci, satu results_label, empat tahap nonfocusable, npwp/year Entry nyata, callback belum dipanggil. `test_compact_reorders_summary_without_hiding_it` memeriksa summary di atas main dan nilai masih sama. `test_render_reuses_widgets_and_does_not_steal_focus` merender 100 progress sintetis dan membandingkan identitas/jumlah widget serta fokus sebelum/sesudah. `test_reflow_has_one_pending_callback_and_dispose_cancels_only_its_own` memeriksa timer unrelated tetap ada. `test_window_geometry_never_exceeds_measured_client_work_area` memakai work area sintetis dan native runner; kegagalan native probe tidak diberi hasil lolos palsu. `test_error_labels_wrap_without_overlapping_action_bar` memakai kedua error form dan judul panjang.

- [ ] **Step 2 — Buktikan RED T3 di runner:** `.venv\Scripts\python.exe -m pytest tests/test_desktop_ui_theme.py tests/test_desktop_ui_views.py -q --basetemp "$env:RUNNER_TEMP/spt-b-t3"`.
- [ ] **Step 3 — Implementasikan interface 3.3.** Pakai tema Windows yang tersedia, named fonts, grid antarkelompok, action bar di luar viewport isi, dan header/footer yang wrap. Skala ukuran berbasis DIP hanya sekali; ukuran font point mengikuti Tk. Buat panel sekali dan ubah visibility/properti, bukan bangun ulang tiap event. Terapkan ukuran awal terukur bila tersedia; jangan membuat satu minimum tetap yang melampaui layar. Jangan menggambar kontrol interaktif di SVG/Canvas.
- [ ] **Step 4 — Buktikan GREEN T1–T3/full suite.** Ambil screenshot sintetis shell regular dan compact dari runner. Pemeriksaan state/fokus/teks dilakukan di samping screenshot; bukan disimpulkan dari screenshot saja. High Contrast tidak diklaim lulus sebelum diuji di Windows.
- [ ] **Step 5 — Review visual dan catat checkpoint T3.** Pastikan judul panjang benar-benar terlihat, ringkasan tidak hilang, tombol masih terjangkau. Bukan review Figma/Penpot; keduanya tidak diperlukan untuk menjalankan produk.

### T4 — Sambungkan shell ke App tanpa mengubah consent atau backend

**Files:** Modify `spt_desktop/app.py`: `__init__`, `_running`, `start`, `stop`, `on_event`, `_poll`, `request_close`, dan hook sukses `_reply_interaction`; `spt_gui.py:self_test`; `tests/test_desktop_gui.py`; `tests/test_desktop_requested_text.py`. Create `tests/test_desktop_ui_integration.py`. Migrasikan stub/label self-test dalam tugas yang sama agar full suite tidak sengaja merah sampai T5. Tidak mengubah ekspektasi consent.

**Interfaces:** Consumes T1–T3. Produces App dengan API/handle existing yang sama. Dialog/persistence tetap di App; `read_request` dan `respond` tidak berubah.

- [ ] **Step 1 — Tambahkan fixture controller jujur dan tes publik App.** Fake memiliki `active`, `operation`, `job_id`; `start` mencatat argumen, menetapkan ID baru, dan mengembalikan ID seperti controller nyata. Fake tidak membuka worker atau membaca kredensial.

| Tes baru | Assertions wajib |
| --- | --- |
| `test_invalid_fields_do_not_start_and_focus_first_error` | NPWP penuh lebar/spasi/pemisah/tahun salah: starts kosong, nilai tidak diubah, error per field, fokus NPWP jika keduanya salah. Tidak bergantung pada terjemahan exception. |
| `test_click_enter_and_alt_m_share_one_start_guard` | Semua jalur masuk start yang sama; setelah pertama aktif hanya satu start, NPWP/tahun/settings disabled, Stop enabled. |
| `test_scope_snapshot_does_not_follow_later_stringvar_changes` | State memakai NPWP/tahun yang diterima; perubahan StringVar sintetis tidak mengubah summary job. |
| `test_setup_login_required_and_counts_use_correct_presentation` | Setup indeterminate tanpa ETA; login manual punya instruksi browser tanpa tombol konfirmasi sesi; metrik detail tidak memakai denominator inventory. |
| `test_99_percent_cannot_open_a_result` | Progress publish99 dengan/ tanpa path tidak mengaktifkan open_button; controller active tetap true. |

Tambahkan `test_duplicate_stop_and_late_progress_do_not_reenable_actions` (satu stop per job, Mulai tetap disabled); `test_old_dialog_callback_cannot_stop_new_job`; `test_respond_false_does_not_record_selection_or_cancel_new_job`; `test_login_check_preserves_export_snapshot_and_result`; serta `test_closing_root_disposes_view_and_poll_callbacks`. Gunakan fixture/kontrak existing `test_desktop_selection_gui.py` dan `test_desktop_consent_lifecycle.py`, bukan versi simulasi yang menghindari controller.

Tambahkan `test_self_test_reports_main_view_labels_from_real_widgets` (label baru dibaca dari widget; `ui_text`/`personal_use_labels` exact tetap), `test_self_test_uses_job_bound_synthetic_progress_without_runtime_setup` (ensure_runtime/spawn/read credentials gagal jika terpanggil; progress42 ber-ID sah), dan geometry 640×560/1120×800 tanpa menghapus 540×390/900×700. Pertahankan tes mismatched heading serta report salah yang sudah ditolak build.

- [ ] **Step 2 — Buktikan RED tes T4 pada App baseline, sebelum memasang view.** Perintah runner: `.venv\Scripts\python.exe -m pytest tests/test_desktop_ui_integration.py -q --basetemp "$env:RUNNER_TEMP/spt-b-t4"`.
- [ ] **Step 3 — Integrasikan MainView dan reducer.** Alias handle existing ke handle view. `start`: guard active/closing → error inline → validator existing → controller.start → begin_export → render. Jangan menyalakan setup ketika konstruksi. `stop`: guard sekali per job → invalidasi dialog → mark_stopping → controller.stop → render terkunci. Operasi login tetap cabang terpisah; jangan mengirim login event ke reducer ekspor.

`on_event` menolak job asing; state baru tidak dibuat dari event progres lama. Semua event tes normal diberi ID job. Untuk fallback error internal `_poll`, buat event ERROR dengan ID controller saat ini; bila tidak ada job aktif, tampilkan error aplikasi tanpa menandainya sebagai terminal job baru. `_reply_interaction` hanya memanggil record_reply setelah True dengan key yang masih cocok. Semantik False existing tetap: tutup dismissal stale, tidak mengarang jawaban sukses atau stop baru.

`_running` tetap tersedia sebagai adapter set_busy agar Pengaturan existing tetap bekerja. Simpan hasil ekspor sebelum login check dan jangan menghapusnya pada terminal login. Jangan rename `Cek Kredensial`/`Batalkan Cek`, mengubah write preferences, memperketat payload folder, atau memindahkan/menulis ulang isi `selection_dialog`/`overwrite_dialog` pada tahap ini. Dialog hanya tetap terpanggil melalui jalur controller sah. Tangani disposal view/poll sebelum root.destroy tanpa membatalkan timer milik komponen lain.

Pada `spt_gui.self_test`, gunakan stub controller privat khusus self-test, hanya operasi sintetis yang diperlukan, melalui parameter controller App. Periksa form kosong, kemudian lakukan start sintetis melalui App dan kirim progress dengan job ID yang sama; tidak memanggil real start/setup. Baca caption kontrol aktual, bukan array label hardcoded. Tetap `credentials_accessed=False`, `live_scrape=False`, dan pertahankan pemeriksaan resource/Tcl/Tk/Python/frozen/uv. Stub tidak dimasukkan ke controller produksi. Caption login existing dan field yang diharuskan `build_desktop.validate_report` tidak diubah. Perbarui tes yang mencari label Mulai dalam commit integrasi yang sama; jangan menghapus tes atau melonggarkan validator.

- [ ] **Step 4 — Buktikan GREEN T4 dan regresi GUI/consent, lalu full Windows suite.** Regresi terfokus di runner: `.venv\Scripts\python.exe -m pytest tests/test_desktop_ui_integration.py tests/test_desktop_selection_gui.py tests/test_desktop_consent_lifecycle.py tests/test_desktop_requested_text.py -q --basetemp "$env:RUNNER_TEMP/spt-b-integration"`. Jalankan tanpa browser/account nyata.
- [ ] **Step 5 — Review checkpoint T4 terhadap batas file.** Diff controller/interaction/worker/output/capture/runtime harus kosong. Bila kebutuhan nyata mengharuskan perubahan backend, hentikan irisan dan revisi rencana; jangan menyelipkannya sebagai perapian UI.

### T5 — Gerbang runner, artifact, dan serah-terima irisan pertama

**Files:** Tidak ada perubahan kode produk yang direncanakan. Update `docs/ui-ux/README.md` hanya untuk status parsial implementasi setelah bukti ada. Create `docs/superpowers/reports/2026-10-13-ui-b-phase1-evidence.md` ketika eksekusi dilakukan. Gunakan tes GUI/build/branding dan semua tes baru T1–T4.

**Interfaces:** Consumes head produk T4, schema `spt_gui.self_test`/`build_desktop.validate_report`, manifest tes, dan artifact workflow existing. Produces laporan bukti yang dapat ditelusuri. T5 adalah verifikasi, bukan fitur: tidak membuat kegagalan RED buatan untuk pemeriksaan yang sudah lulus.

- [ ] **Step 1 — Bekukan head kandidat untuk pembuktian.** Catat SHA head, run/attempt, serta checkout/merge SHA yang benar; periksa perubahan base main sejak T4. Bila tree produk berubah, ulangi gerbang pada tree baru. Jangan memakai hasil run yang dibatalkan oleh concurrency sebagai bukti selesai.
- [ ] **Step 2 — Verifikasi seluruh tes runner.** Windows full suite serial, subset portable, audit locks, dan worker fresh/reuse tetap berjalan. Pastikan semua node T1–T4 ada pada manifest Windows; subset Linux tidak dimanipulasi untuk melewatkan tes. Perintah full Windows yang dibaca dari workflow menjadi acuan; `scripts/ci_tests.py` dan workflow tidak diedit.
- [ ] **Step 3 — Baca ulang artifact source/frozen yang tepat.** Catat artifact ID konkret, baca manifest/hash/self-test report aktual, cocokkan Python/Tcl/Tk, tiga teks khusus, `personal_use_labels`, GUI controls, resource allowlist, `credentials_accessed=False`, dan `live_scrape=False`. Periksa source dan frozen, bukan hanya teks dokumen atau hasil source. Jangan mengubah validator untuk menerima report yang salah.
- [ ] **Step 4 — Review hasil irisan dan keterbatasannya.** Periksa screenshot sintetis shell regular/compact, AC01–AC05, dan regresi consent/output/PDF existing. Tidak ada klaim seluruh a11y/DPI/performa atau AC06–AC28 selesai. Jika ada cacat, kembalikan ke T1–T4 yang memilikinya, tambahkan regresi yang benar-benar gagal di runner, lalu jalankan ulang gerbang dengan SHA baru.
- [ ] **Step 5 — Terbitkan laporan dan hentikan sebelum irisan 2.** Laporan memetakan AC01–AC05 ke test node/run, serta mencatat bukti visual dan gap. Status panduan adalah “irisan 1”, bukan “desain B selesai”. Commit laporan terpisah dari tree produk yang diuji dicatat sebagai docs-only. PR produk siap direview, bukan otomatis di-merge/deploy; penerimaan Coretax/Excel/UI manual tetap menunggu konsolidasi dan persetujuan terpisah.

## 6. Verifikasi, bukti, dan kondisi berhenti

Laporan eksekusi memiliki tabel `Task | RED head/run/node | GREEN head/run/node | Review | Remaining`. Jangan mengisi ID dengan contoh rekaan. Bila tidak ada runner atau izin dispatch, berhenti pada tes yang ditulis dan laporkan belum ada bukti; jangan mengganti dengan eksekusi lokal.

| Pemeriksaan | Lulus jika | Tidak cukup |
| --- | --- | --- |
| Kontrak AC01–05 | Node baru lulus pada Windows untuk head/merge tree yang dicatat. | Screenshot, docs-green, atau hasil baseline lama. |
| Integrasi baseline | Pemilihan, consent, overwrite, Stop, login, output/PDF tetap lulus full suite. | Hanya tes murni reducer. |
| GUI tipis | Tidak ada import transitif browser/exporter/output ke GUI dan allowlist worker tidak berubah. | File UI terlihat kecil tanpa memeriksa import. |
| Distribusi | Source/frozen report nyata, artifact ID exact, isi/hash diperiksa kembali. | Run hijau tanpa membaca artifact yang benar. |
| Scope | Hanya irisan 1; perilaku baru dialog/hasil/login/performa ditandai belum dilakukan. | Klaim “desain B selesai” berdasarkan shell saja. |

Rencana ini telah diperiksa sebagai dokumen: interface T1–T5 konsisten, lima Review Focus punya tes pemilik, dan seluruh AC dipetakan ke irisan yang jelas. Itu bukan bukti implementasi atau tes produk. Tidak ada pytest, import produk, Tk, browser, build, atau akses live dijalankan saat menulis rencana.

## 7. Referensi sumber yang diperiksa

| Sumber | Konteks yang dipakai |
| --- | --- |
| [App baseline](https://github.com/cepeter-job/spt-downloader/blob/be67f5153a07ce100048d67191a02ca1d0fca1db/spt_desktop/app.py) | Constructor, handle view, start/stop, branch login, `_reply_interaction`, dialog existing. |
| [Tes GUI](https://github.com/cepeter-job/spt-downloader/blob/be67f5153a07ce100048d67191a02ca1d0fca1db/tests/test_desktop_gui.py) dan [teks pemilik](https://github.com/cepeter-job/spt-downloader/blob/be67f5153a07ce100048d67191a02ca1d0fca1db/tests/test_desktop_requested_text.py) | Event sintetis lama tanpa job ID, widget nyata, geometry, expected text independen. |
| [Lifecycle consent](https://github.com/cepeter-job/spt-downloader/blob/be67f5153a07ce100048d67191a02ca1d0fca1db/tests/test_desktop_consent_lifecycle.py) | Stop/terminal/worker exit dan sinyal persetujuan privat. |
| [Self-test](https://github.com/cepeter-job/spt-downloader/blob/be67f5153a07ce100048d67191a02ca1d0fca1db/spt_gui.py) dan [build](https://github.com/cepeter-job/spt-downloader/blob/be67f5153a07ce100048d67191a02ca1d0fca1db/build_desktop.py) | Report aktual dan pemeriksaan frozen yang harus dipertahankan. |
| [Routing tes](https://github.com/cepeter-job/spt-downloader/blob/be67f5153a07ce100048d67191a02ca1d0fca1db/scripts/ci_tests.py) dan [workflow](https://github.com/cepeter-job/spt-downloader/blob/be67f5153a07ce100048d67191a02ca1d0fca1db/.github/workflows/windows-build.yml) | Full suite Windows, allowlist portable, trigger PR/main/dispatch, concurrency. |

## 8. Serah-terima rencana

Persetujuan spesifikasi sudah dicatat; rencana B-TK-P1 ini adalah artefak baru untuk ditinjau sebelum eksekusi. Rekomendasi pelaksanaan: **inline/native**, urut T1–T5, dengan review perubahan per tugas dan tes GitHub runner. Tugas saling bergantung melalui interface kecil; paralelisasi implementasi pada App yang sama tidak diperlukan.

Bila tersedia alat subagen pada sesi eksekusi, gunakan untuk investigasi fixture atau review independen, bukan berbagi edit App secara bersamaan. Pilihan metode dan persetujuan menjalankan rencana belum diasumsikan. Tidak ada merge atau deployment yang disetujui secara tersirat.
