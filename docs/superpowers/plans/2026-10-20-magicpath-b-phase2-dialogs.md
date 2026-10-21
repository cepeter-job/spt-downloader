# MagicPath B — Phase 2 Dialogs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Memperjelas pilihan SPT dan penggantian file pada dua dialog existing, tanpa mengubah identitas, consent, capture atau output bisnis.

**Architecture:** App tetap memiliki modal, job, request/reply dan teardown. Perubahan hanya pada metode selection/overwrite, helper ukuran native yang kecil, katalog copy dan tes. Selection dikerjakan dahulu, lalu overwrite, kemudian verifikasi gabungan; tidak ada subsistem dialog/event bus baru.

**Tech Stack:** CPython **3.14.8/GIL**, stdlib Tkinter/ttk, pytest dari `locks/test.txt`, packaging dari `locks/build.txt`. Tidak ada dependency produk baru. Eksekusi produk/tes hanya pada GitHub runner.

**Spec:** [B-TK-P2-D1](../specs/2026-10-20-magicpath-b-phase2-dialogs-design.md). Pemilik menyatakan **“Approve B-TK-P2-D1”** pada 20 Oktober 2026, terhadap commit `1766e01aa4c27e34794df7a17b406217be633e67`, blob `e7baa072082211239384a2a13baa2dbd254011b4`. Snapshot desain tidak diedit; status draft di dalamnya adalah riwayat sebelum persetujuan.

## Global Constraints

1. Baseline produk `main@977b06846554ca1f2e5af512a69fb201f2cbe8d1`: satu job, private request/reply, payload **16 MiB**, ID unik maksimal **512 karakter**, deadline **600 detik**, polling GUI **100 ms**, reflow modal **75 ms**. Tidak mengubah controller/worker/interaction/ui_state, capture/output, dependency, allowlist, pin Python, LICENSE atau CI produk.
2. Selection reply tepat `{'selected_ids': [...]}` dalam **urutan inventaris asli**. Awal kosong; search menghapus pilihan; sort menjaga query/pilihan/fokus. Overwrite hanya bool; Escape/X selection = Stop, Escape/X overwrite = False, **Alt+S pada keduanya = Stop tanpa reply**. False/stale reply tidak membuat progress atau terminal.
3. Folder overwrite wajib string nonblank, tetapi ditampilkan literal; tidak menebak tujuan, menormalisasi path, menginspeksi filesystem, atau mengubah snapshot. Normal/pembetulan terpisah per Model SPT; source values, rollback, folder resume dan relative PDF links tetap.
4. Client target selection **920×600 DIP**, overwrite **800×520 DIP**; acceptance keduanya **640×560** dan **540×390 DIP**, efektif **100/150/200%** bila area cukup. Work area monitor parent dan border modal harus diukur; tidak mengubah root geometry atau DPI awareness. Font tidak diperkecil; action bar di luar body scroll.
5. Hanya data sintetis; tanpa akun/portal nyata. Pertahankan lima teks pemilik dan bugreport, tanpa `app.credit`; default desktop JSON-hybrid/saved DOM/CLI DOM unchanged. Settings dirty, batching, multijob, dark mode, resume GUI dan merge/deployment di luar scope. [AGENTS.md](../../../AGENTS.md) melarang pytest/product import/Tk/browser/self-test/build/EXE di vm148 atau container lokal.

## Review Focus

1. **Queued empty-selection event sesudah filter:** pesan reset tidak hilang; query dengan hasil normalisasi sama tetap menghapus consent. T1: `test_filter_reset_survives_empty_tree_events`.
2. **Fokus row berubah tanpa selection berubah:** field ID mengikuti `tree.focus()` yang visible, termasuk keyboard navigation. T1: `test_focused_id_tracks_navigation_without_selecting`.
3. **Job berubah sewaktu private request dibaca:** folder invalid request lama tidak menghentikan job baru. T2: `test_stale_malformed_folder_cannot_stop_new_job`.
4. **Close saat reflow pending:** modal lama tidak meninggalkan timer/grab atau mencuri fokus terminal shell. T1/T2: `test_dialog_close_cancels_only_owned_callbacks`, `test_old_reflow_cannot_steal_terminal_focus`.
5. **Work area kecil dan Entry read-only tambahan:** root tidak diubah, ID/folder tidak dikira search, semua teks panjang dapat diinspeksi. T1/T2: `test_dialog_sizes_leave_parent_unchanged`, `test_long_readonly_values_remain_literal_and_reachable`.

---

## 1. Status dan baseline eksekusi

**Revisi rencana B-TK-P2-P1 — siap ditinjau, belum dieksekusi.** Approval desain mengizinkan rencana ini, bukan kode atau merge. Tambahkan rencana ke PR #52; PR #50 dan PR lain tidak digabung. Rekomendasi eksekusi **inline T1→T2→T3** dengan satu review independen akhir, setelah review rencana dan instruksi eksekusi. Metode fase pertama tidak dianggap otorisasi otomatis untuk fase kedua.

Saat eksekusi, periksa `main`/AGENTS/source kembali; rekonsiliasi bila kontrak berubah. Gunakan branch terisolasi `feat/ui-b-phase2-dialogs`, bukan main/branch dokumen. Jika #52 belum merged, branch produk boleh berasal dari head dokumen yang disetujui dan tetap menargetkan main agar workflow existing berjalan; jelaskan commit docs yang ikut terbawa. Jangan merge #50/#52 sebagai jalan pintas.

## 2. Peta file dan antarmuka

| Pemilik | Berkas | Deliverable mandiri |
| --- | --- | --- |
| T1 selection | `spt_desktop/app.py`, `spt_desktop/ui_theme.py`, `spt_desktop/ui_copy.py`; `tests/test_desktop_selection_gui.py`, `tests/test_desktop_selection_sorting.py`, `tests/test_desktop_ui_copy.py`, `tests/test_desktop_ui_theme.py`; baru `tests/test_desktop_dialog_layout.py`; `tests/support_gui.py` hanya observasi/teardown | Selection baru dan modal ownership, sementara overwrite existing tetap berjalan |
| T2 overwrite | `spt_desktop/app.py`, `spt_desktop/ui_copy.py`; `tests/test_desktop_selection_gui.py`, `tests/test_desktop_ui_copy.py`, `tests/test_desktop_dialog_layout.py` | Folder wajib, path read-only, hitungan dan keputusan exact; fixture sah/malformed eksplisit |
| T3 evidence | Existing full suite/source/frozen; setelah bukti tersedia baru `docs/superpowers/reports/2026-10-20-ui-b-phase2-evidence.md` dan status `docs/ui-ux/README.md` | Matriks acceptance, screenshot/timing/DPI dan exact artifact; tidak menambah fitur produk |

Tidak ada modul produk baru atau pemisahan besar App. `spt_gui.py`/`build_desktop.py` dipertahankan; self-test existing mengamati selection/sorting. Jika selector actual perlu diubah, sertakan bukti dan ubah selector sempit beserta tesnya pada tugas terkait, bukan schema/validator atau capture machinery di EXE.

### Interface T1 untuk T2

- `client_work_area(window: tk.Tk | tk.Toplevel, *, monitor_window: tk.Misc | None = None) -> tuple[int, int]` di `ui_theme.py`: panggilan lama tetap sama; monitor boleh berasal dari parent, border/client dari modal sendiri. Tuple adalah ukuran, bukan bukti posisi layar atau per-monitor awareness.
- `configure_dialog(dialog: tk.Toplevel, parent: tk.Tk, *, size_dip: tuple[int, int]) -> float`: pakai `effective_scale(parent)`, named fonts existing, style **SPT.Dialog.Treeview** dan **SPT.Dialog.Treeview.Heading**; rowheight = measured body linespace + 8 DIP. Initial target/minimum 540×390 di-clamp ke work area monitor parent. Pengukuran gagal → biarkan window manager, bukan ukuran/minimum tekaan. Jangan panggil `configure_theme(parent)` lagi; return skala efektif, tidak mengubah global scaling. Gunakan native work-rectangle monitor parent untuk menempatkan modal di dalam area tersebut (pusat parent bila muat, clamp tepi termasuk border); ukuran tuple saja bukan bukti penempatan benar.
- `App._new_interaction(self, key, title)` menambah registry `layout_after: str | None = None`, `bindings: list[tuple[tk.Misc, str, str]] = []` ke dictionary existing; `traces` tetap. Timer dijadwalkan/dibatalkan pada owner **dialog**, bindings menyimpan widget/sequence/id, bukan `unbind_all`.
- `App._close_interaction(self, interaction=None) -> None`: invalidasi dahulu, cancel timer, buang trace/binding milik modal, release grab/destroy lalu restore focus. Idempotent dan tidak membatalkan timer root/Settings/view lain. `_reply_interaction`, `_interaction_current` dan `_interaction_error` tetap otoritas existing.
- Masing-masing metode dialog punya closure `request_reflow(event=None) -> None`, `reflow() -> None`: satu token pending 75 ms, guard current interaction, measured wrap/rowheight. Resize tidak menginsert ulang data atau menghapus selection. Tidak membuat base-class dialog universal.

Nama widget internal stabil: selection `search`, `records`, `focused_id`, `scope`, `summary`, `notice`, `confirm`, `stop`; overwrite `folder`, `files`, `file_count`, `confirm`, `decline`; kedua dialog `body_viewport` dan `actions`. Nama tidak berasal dari raw ID/path. Tambahkan helper tes `named_widget(dialog, name)` di `tests/support_gui.py`, yang mencari tepat satu nama dalam descendants. Migrasikan selector search yang sebelumnya mengandalkan Entry pertama agar menggunakan nama `search`; pengamatan perilakunya tetap.

Fixture baru **`active_app`** di `tests/test_desktop_dialog_layout.py`: real App/visible Tk root, `ConsentController({})`, NPWP sintetis `0000000000000001`, tahun `2025`, start sintetis; yield `(root, app, controller)` **sebelum consent event**. Helper **`settle(root)`** menunggu sentinel 250 ms dalam tes. Tidak ada nested loop produk. Teardown `_close_interaction()` dahulu, `_dispose()` kemudian, lalu timer fixture. Assertion timer/trace/grab dilakukan **sebelum** finalizer membersihkan root agar leak tidak tertutup cleanup. Default `window(tmp_path, payload, kind='selection')` tetap menuntut satu modal; jangan menambahkan folder otomatis.

## 3. TDD pada runner

Semua perintah pytest di rencana ini berlaku **hanya untuk GitHub Windows runner yang sudah disiapkan dengan lock repository**, bukan terminal vm148. Full suite existing:

```powershell
.venv/Scripts/python.exe -m pytest tests -p scripts.ci_tests --ci-workload windows -q --basetemp "$env:RUNNER_TEMP/spt-pytest-windows" --ci-manifest "$env:RUNNER_TEMP/test-inventory.json" --durations=10
```

Pada T1/T2, commit/push tes `test:` lebih dahulu; baca node RED dan ikat head/merge SHA/run sebelum implementasi. Kemudian commit/push solusi dan baca full GREEN. Jangan kehilangan run RED karena concurrency membatalkannya. Recipe terfokus di tiap tugas bukan parameter filter arbitrary pada workflow_dispatch. Kegagalan collection akibat fixture salah bukan RED perilaku: perbaiki fixture dahulu; helper baru diimpor dalam fungsi tes. Jangan mengganti aturan CI atau menjalankan produk lokal saat runner unavailable.

## 4. Tugas implementasi

### T1 — Selection: konteks, keyboard dan layout native

**Files:** berkas T1 pada tabel bagian 2. **Interfaces:** consumes `_read_interaction`, `_selection_detail_key`, `_ui_state`, `_reply_interaction` dan `copy_text`; produces `App.selection_dialog(self, event) -> None` dengan kontrak publik yang sama dan interface native/ownership bagian 2 untuk T2. Overwrite belum berubah perilakunya.

- [ ] **Step 1 — Tambahkan tes kontrak gagal berikut.** Gunakan `active_app` sebelum request untuk kasus snapshot; fixture `window` untuk kasus selection biasa. Tests names/assertions merupakan kontrak yang harus diwujudkan, bukan hasil eksekusi saat ini.

| Tes | Assertion wajib |
| --- | --- |
| `test_selection_context_uses_matching_job_snapshot` | StringVar formulir berubah setelah start → konteks tetap NPWP/tahun snapshot job. Missing/mismatched snapshot → `Konteks permintaan tidak tersedia`, tanpa fallback. |
| `test_filter_reset_survives_empty_tree_events` | Pilih → edit query → selection kosong, submit disabled, reset hint tetap setelah queued empty event. Query dengan `.strip().casefold()` sama juga reset. Pilihan visible baru membersihkan hint. |
| `test_selection_empty_and_no_match_keep_exact_counts` | Inventaris [] → 0/0/0 + empty message; tiga record/no match → 0/0/3 + no-match message. Tidak ada reply/default-all. |
| `test_focused_id_tracks_navigation_without_selecting` | Mouse/arrow/Ctrl-navigation memperbarui readonly ID tanpa mengubah selection. ID `::synthetic {return}; [literal] / Ω` dan ID 512 karakter tetap literal; focus tak-visible → kosong; copy bukan consent. |
| `test_alt_j_and_header_preserve_filtered_selection_and_reply_order` | A–Z/Z–A existing tetap, query/raw values/selection/focus terjaga, focused row dapat dilihat; reply urutan inventaris. Semua oracle kronologi/leading-zero/unknown/source-ties existing tetap. |
| `test_only_focused_submit_activation_sends_selection_once` | Enter search/tree dan double-click tree → nol reply. Click/Enter/Space tombol aktif → satu reply; callback kedua tidak Stop atau mengirim ulang. |
| `test_dialog_sizes_leave_parent_unchanged` | Target 920×600/minimum ter-clamp, monitor parent dengan border modal; root geometry/font/scale unchanged. Native probe gagal tidak memaksakan ukuran baru. |
| `test_selection_layout_keeps_actions_visible_and_body_reachable` | Parameter 920×600, 640×560, 540×390: actions utuh dalam client; label tidak tertimpa tombol; Tab/Shift+Tab mencapai search/tree/ID/buttons dan body scroll memperlihatkan kontrol fokus tanpa mengubah selection. |
| `test_selection_reflow_preserves_data_and_owned_resources` | 20 requests resize → satu timer; query/selection/ID tidak berubah. 25 open/close cycles tanpa net live modal/timer/trace/grab atau Tcl error; sentinel root tetap. |
| `test_old_reflow_cannot_steal_terminal_focus` | Pending reflow → terminal → fokus hasil/Mulai → tunggu timer; fokus/job berikutnya tetap benar, Alt+J tidak tertinggal pada root. |

Tambahkan lima key selection persis spec §5 pada oracle independen `test_catalog_matches_approved_copy`; tambahkan `test_phase2_selection_copy_is_exact` yang berisi pasangan literal approved. Semua 44 key/value lama tetap; target setelah T1 **49 ID**. Jangan menghasilkan expected dengan membaca runtime COPY.

Contoh inti tes baru (helper `named_widget` berasal dari bagian 2; Tk dan fixture diimpor dalam modul tes sebagaimana baseline):

```python
def test_selection_context_uses_matching_job_snapshot(active_app):
    root, app, controller = active_app
    controller.payload = {'records': []}
    app.npwp.set('0000000000000002')
    app.year.set('2024')
    app.on_event(consent_event(controller))
    settle(root)
    dialog = app._interaction['dialog']
    scope = named_widget(dialog, 'scope').cget('text')
    assert '0000000000000001' in scope and '2025' in scope
    assert '0000000000000002' not in scope and '2024' not in scope
    assert controller.replies == []
```

Tambahkan kasus snapshot None/job ID berbeda dengan assertion fallback exact melalui public builder `app.selection_dialog(event)` pada controller aktif. Jangan melemahkan penolakan job/state mismatch pada `App.on_event` demi memaksa modal muncul. Konteks pada named Label `scope` memakai dua baris `NPWP permintaan: <literal>` dan `Tahun pajak permintaan: <literal>`; jangan memasukkan datanya ke count-template.

- [ ] **Step 2 — Buktikan RED pada runner.**

```powershell
.venv/Scripts/python.exe -m pytest tests/test_desktop_selection_gui.py tests/test_desktop_selection_sorting.py tests/test_desktop_ui_copy.py tests/test_desktop_ui_theme.py tests/test_desktop_dialog_layout.py -q --basetemp "$env:RUNNER_TEMP/spt-p2-t1"
```

Expected: helper/copy/control belum ada atau assertion perilaku baru gagal; bukan collection error atau pelemahan baseline. Catat node/run sebelum solusi.

- [ ] **Step 3 — Implementasikan selection dan interface bagian 2.** Urutan body: instruksi/konteks → search → tabel → readonly ID → counts/notice; action bar terpisah. Lima key baru dipakai pada widget, bukan hanya ada di katalog. Sorting helper dan urutan reply tetap.

Counts selalu memakai `selection.summary`; notice terpisah untuk no-match/empty/reset. Latch `reset_pending` sebelum delete row; queued empty selection tidak membersihkannya, hanya pilihan visible valid. `sync_focused_id(event=None) -> None` membaca focus setelah class event melalui `<KeyRelease>`, `<ButtonRelease-1>`, `<FocusIn>` dan selection callback. Setelah sort, `tree.see(focus_iid)` jika masih visible, tanpa mengambil keyboard focus ke kontrol lain.

Alt+J wrapper memanggil handler `sort_type()` existing dan mengembalikan `'break'`. Enter/Space pada tombol submit sendiri melakukan satu invoke lalu `'break'` agar tidak diulang class binding; tidak ada approve binding pada root/dialog/tree. Body scroll memunculkan kontrol yang mendapat focus. Wheel pada tabel hanya menggerakkan tabel, bukan sekaligus body. Cancel/close tetap ke `_cancel_interaction`; tidak ada implicit selection.

- [ ] **Step 4 — Buktikan GREEN recipe T1 dan full suite Windows.** Existing selection/sorting/consent, locked copy, lifecycle, source/frozen self-test tetap lulus. Fixture root withdrawn bukan bukti screenshot; pengujian visual ada di T3. Tidak ada perubahan worker/IPC.
- [ ] **Step 5 — Commit solusi dan rekam checkpoint.** Pesan `feat: refine selection dialog context and native keyboard layout`. Ledger memuat RED/GREEN head/merge/run, node, fixture delta dan bukti yang belum tersedia. Jangan masuk T2 saat suite masih merah.

### T2 — Overwrite: folder wajib dan keputusan exact

**Files:** berkas T2 bagian 2. **Interfaces:** consumes sizing/style/ownership T1, `_read_interaction` dan `_reply_interaction`; produces `App.overwrite_dialog(self, event) -> None` dengan validation sebelum modal, folder readonly, file count dan safe focus. Reply schema unchanged.

- [ ] **Step 1 — Tulis tests berikut dan oracle lima copy overwrite.** Kasus invalid menggunakan `active_app`, bukan helper yang sudah menuntut satu modal.

```python
@pytest.mark.parametrize('folder', [None, '', ' \t\n', 7, False, [], {}])
def test_blank_or_nonstring_folder_never_opens_confirmation(active_app, folder):
    root, app, controller = active_app
    controller.payload = {'files': ['SPT_Badan_2025_Normal.xlsx'], 'folder': folder}
    app.on_event(consent_event(controller, 'overwrite'))
    settle(root)
    assert controller.stopped and controller.replies == []
    assert app._interaction is None
    assert not any(isinstance(child, tk.Toplevel) for child in root.winfo_children())
    assert app._ui_state.terminal_status is None
    assert 'Folder hasil sebelumnya belum tersedia.' in app.status.get()
```

| Tes tambahan | Assertion wajib |
| --- | --- |
| `test_missing_folder_is_not_defaulted` | Key folder sengaja dihilangkan → nol modal/reply, Stop hanya current job; payload tidak dimutasi. |
| `test_stale_malformed_folder_cannot_stop_new_job` | Fake read_request mengubah controller.job_id sebelum mengembalikan folder invalid → nol Stop/reply/modal untuk job baru. Foreign event yang ditolak awal juga tidak membaca payload. |
| `test_long_readonly_values_remain_literal_and_reachable` | Folder dengan leading/trailing spaces nonblank tetap exact via Entry.get(); insert/delete tidak mengubah. Long paths/Unicode/duplikat dipertahankan, count=len(files); tidak menambah/menghapus resume. |
| `test_overwrite_keyboard_decisions_preserve_protocol` | Escape/X → False, Alt+S → Stop tanpa reply, approve → True; safe focus awal dan Enter/Space decline → False; duplicate callback sekali. |
| `test_overwrite_response_false_and_exception_do_not_fabricate_results` | False tidak mengubah status/count/terminal atau Stop tambahan. I/O exception memakai existing error path hanya current job, bukan terminal sukses. |
| `test_overwrite_layout_keeps_actions_visible_and_paths_reachable` | Parameter 800×520, 640×560, 540×390: safe/approve tetap utuh, readonly folder bisa dipilih/digulir, kedua scrollbar menjangkau semua path; keyboard tidak memicu True dari field/table. |
| `test_dialog_close_cancels_only_owned_callbacks` | Close/cancel/terminal saat timer pending membuang milik modal, sentinel root masih hidup; 25 cycles tanpa net handles/trace/grab/Tcl error. |

Lima key overwrite persis spec §5 menjadikan total **54 ID**. `_COUNT_PARAMETERS['overwrite.files_count'] = frozenset({'count'})`. Tes `test_overwrite_count_template_is_strict`: 0 → `0 file akan diganti.`, 2 → `2 file akan diganti.`; bool/string/float → TypeError; negatif/missing/extra → ValueError. Ubah oracle literal secara sengaja, tidak menyalin runtime COPY; selection/detail formatter unchanged.

Migrasikan tiap fixture overwrite yang dimaksud sah di `tests/test_desktop_selection_gui.py` dengan folder sintetis eksplisit `C:\Users\SYNTHETIC_USER\Downloads\SYNTHETIC_EXPORT`. Kasus missing-folder dibuat terpisah. Sebagian fixture memiliki `resume.xlsx`: pertahankan sebagai pengujian UI tidak mengedit snapshot, meskipun worker nyata mengecualikannya. Transport/lifecycle tests yang tidak membangun GUI tidak diberi folder tanpa alasan. `test_overwrite_displays_the_exact_prior_export_folder` membaca named readonly Entry `folder` dan membandingkan keseluruhan `.get()` dengan folder, bukan substring/exists. Assertion positif satu modal tetap.

- [ ] **Step 2 — Buktikan RED.**

```powershell
.venv/Scripts/python.exe -m pytest tests/test_desktop_selection_gui.py tests/test_desktop_ui_copy.py tests/test_desktop_dialog_layout.py -q --basetemp "$env:RUNNER_TEMP/spt-p2-t2"
```

Expected: baseline menerima missing/whitespace folder atau tidak mempunyai widget/template baru. Kegagalan harus karena kontrak tersebut, bukan fixture yang memperbaiki input.

- [ ] **Step 3 — Implementasikan minimum.** Setelah private read, validasi files persis baseline; folder harus `isinstance(folder, str) and bool(folder.strip())`, tanpa memutasi raw value. Invalid memakai `overwrite.context_missing` ke `_interaction_error(key[0], ...)` sebelum modal; tanpa False buatan. Valid memakai size 800×520 via T1; folder readonly, daftar nonselectable, file count, whole-file explanation. Ukur lebar string file terpanjang agar horizontal scroll mencapai suffix. Tidak ada filesystem call/choose-folder/per-file checkbox.

Escape/X/decline → `_reply_interaction(..., {'overwrite': False})`; explicit approve True; Alt+S → `_cancel_interaction`. Semua callback memakai current-interaction guard. Jangan mengubah close-before-response atau memindah otoritas ke view. Reducer/worker existing menentukan progress/terminal/output.

- [ ] **Step 4 — Buktikan GREEN full Windows dan regresi safety.** Recipe diagnosis tambahan pada runner:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_desktop_selection.py tests/test_desktop_selection_transport.py tests/test_desktop_consent_lifecycle.py tests/test_desktop_overwrite.py tests/test_desktop_overwrite_safety.py tests/test_model_workbook_publication.py -q --basetemp "$env:RUNNER_TEMP/spt-p2-safety"
```

Expected: snapshot-changed/newer-folder/deadline/Stop/rollback tests tetap lulus, tidak ada data akun nyata.
- [ ] **Step 5 — Commit solusi dan rekam checkpoint.** Pesan `feat: require exact folder context for overwrite confirmation`. Ikat head/merge/run; backend/output/CI diff harus kosong. Jangan menyatakan Phase 2 selesai sebelum T3.

### T3 — Verifikasi gabungan, bukan penambahan fitur

**Files:** laporan/status pada tabel bagian 2. **Interfaces:** consumes head produk T2, baseline `977b068`, payload sintetis identik dan artifact pipeline existing; produces matriks P2-01–P2-18 dengan bukti per-SHA. Tidak ada RED buatan untuk gerbang yang sudah lulus; defect baru dikembalikan ke T1/T2 untuk regresi terlebih dahulu.

- [ ] **Step 1 — Bekukan kandidat dan verifikasi pipeline existing.** Catat head, checkout merge tree, run/attempt; full Windows, portable inventory, audit, source/frozen self-test wajib pass. Semua node tes baru harus ada di inventory Windows. Hasil docs-only commit berikutnya dibedakan dari product tree yang diuji.
- [ ] **Step 2 — Verifikasi visual, keyboard dan skala pada runner yang diizinkan.** Selection 920×600, overwrite 800×520, keduanya 640×560/540×390; states selection initial/multi-select/search-reset/no-match/long-ID dan overwrite long-folder/long-path/decline. Minimal native screenshots kedua modal pada normal/compact/minimum; catat actual client/work-area supaya permintaan 920×600 yang di-clamp tidak diklaim ukuran penuh. Periksa action bar, semua teks lewat scroll, focus traversal, Alt+J, Escape/X, resize dan terminal focus setelah timer.

Pipeline existing **tidak** menyediakan screenshot/DPI/dialog-timing khusus. Jangan memasukkan PNG ke EXE/five-file payload/test-inventory schema atau mengubah user-owned CI untuk memperolehnya. Jika belum tersedia jalur diagnostic runner yang diizinkan, minta izin **satu branch/draft PR diagnostik terpisah yang tidak di-merge** sebelum membuatnya. Hanya di branch tersebut: `scripts/_p2_dialog_evidence.py` dan `.github/workflows/p2-dialog-evidence.yml`, baseline/candidate checkout exact, production pin/lock/action SHA yang sama, tanpa secrets/portal; upload JSON/PNG sintetis saja. Tutup diagnostic PR tanpa merge sesudah evidence tersimpan; cleanup branch mengikuti otorisasi. Jika jalur itu tidak tersedia, P2-13/14/16 tetap NOT VERIFIED, bukan dijalankan lokal. Approval rencana bukan izin menyisipkan workflow baru pada PR produk.

Untuk P2-14, ubah scaling aktual sebelum membuat proses App dan laporkan native `GetDpiForWindow`, `tk scaling`, `effective_scale`, pixel/DIP/client/work area; ulangi 100/150/200% pada display cukup besar. Screenshot diperbesar atau monkeypatch skala bukan bukti. Hasil Tk-only diberi label toolkit-scaling, tidak dianggap per-monitor Windows DPI. Ketika OS-scaling tidak dapat diuji, tandai bukti itu terbuka, bukan menganggap tes geometry sebagai penggantinya. High Contrast/pembaca layar menyeluruh tetap di luar cakupan ini.

- [ ] **Step 3 — Ukur sebelum batching.** Baseline dan kandidat dijalankan pada job Windows yang sama dalam subprocess/checkout terpisah, payload identik: 1/100/1.000 record dan overwrite dengan path panjang. Satu warm-up dikecualikan, **10 pengulangan** per ukuran/aksi; `perf_counter_ns` mengukur handler dan layout sampai stabil. Catat open/filter/sort dan jeda layanan timer pembatalan; jangan memasukkan fixed sleep fixture sebagai waktu render. Bila harness menunggu settle, berhentikan pencatatan ketika geometry/event pekerjaan terkait stabil, bukan setelah batas tunggu maksimum.

Simpan samples ms, median, p95 nearest-rank (untuk 10 sampel sama dengan maksimum), maksimum, payload bytes, Python/Tcl/Tk, scale/window dan revision. Target feedback ≤100 ms adalah evaluasi, bukan assertion wall-clock flaky. Lebih dari 100 ms pada ≥2 pengulangan → laporkan gap dan usulkan delta batching terpisah; jangan mengurangi dataset/daftar atau menambah thread diam-diam. No optimization claim tanpa bukti.

Schema JSON per aksi: `revision`, `python`, `tcl`, `tk`, `effective_scale`, `native_dpi`, `client_px`, `inventory_size`, `payload_bytes`, `operation`, `samples_ms`, `median_ms`, `p95_ms`, `max_ms`, `cancel_service_ms`, `synthetic=true`, `portal_accessed=false`. Manifest screenshot menyimpan state, filename relatif, client dimensions dan SHA-256. Gunakan data sintetis saja dan jangan menyertakan log/capture akun.

- [ ] **Step 4 — Review final dan exact artifact readback.** Satu fresh-context review seluruh rentang produk, spec/plan/Review Focus sebagai acuan. Critical/Important → tambah regresi RED, perbaiki di tugas pemilik, full GREEN, refresh evidence terdampak; Minor dicatat. Unduh exact-ID package/inventories; cocokkan API ZIP digest, lima file, seluruh SHA256SUMS, Python/GIL/resource allowlist, report frozen dan `credentials_accessed=false`/`live_scrape=false`. Source self-test dibuktikan melalui langkah runner/assertion, bukan diklaim report source diunduh bila pipeline tidak mengekspornya. Head yang berubah perlu gate terkait ulang.
- [ ] **Step 5 — Terbitkan laporan, bukan auto-merge.** Simpan `docs/superpowers/reports/2026-10-20-ui-b-phase2-evidence.md`, link dari panduan aktif, dengan PASS/FAIL/NOT VERIFIED per acceptance. Jangan menandai fase selesai jika P2-14/16 atau gerbang wajib lain belum terbukti. Simpan snapshot/timing berhash ke tujuan yang diizinkan sebelum retensi artifact habis. Pertahankan arsip P1 dan spec yang disetujui. Stop sebelum merge/deployment/Settings dirty atau fase lain.

## 5. Peta acceptance dan self-review rencana

| Acceptance | Pemilik | Bukti minimum |
| --- | --- | --- |
| P2-01–P2-06 | T1 | Snapshot, empty/reset/search, sort/original IDs, focused ID dan keyboard approval |
| P2-07–P2-09 | T2 | Folder missing/type/raw, daftar/count literal, safe decision/Stop/X |
| P2-10–P2-12 | T1 + T2 | False/exception, stale/deadline dan callback/grab/trace lifetime, 25 cycles |
| P2-13–P2-16 | T1/T2 implementasi; T3 bukti | Geometry, native screenshot, actual scaling/focus dan paired timing; bukti yang hilang eksplisit |
| P2-17–P2-18 | T3 | Source/frozen/output regresi, exact artifacts, locked copy/defaults dan scope diff |

Self-review penulis: seluruh section spec memiliki task pemilik; lima Review Focus mempunyai tes. Nama/signature bersama didefinisikan sebelum T2 menggunakannya; helper tidak mengambil otoritas controller. Setup/copy/fixture berada di task yang memakainya, bukan task scaffolding terpisah. Tidak ada implementasi produk atau runtime evidence ketika menulis dokumen ini. Investigasi source/fixture memakai agen read-only independen; **review konsistensi rencana dilakukan penulis**, bukan diklaim sebagai review independen.

## 6. Handoff

Rencana **B-TK-P2-P1** baru siap ditinjau; desain **B-TK-P2-D1** sudah disetujui, tidak meminta persetujuannya ulang. Belum ada pytest, import produk, Tk/browser, build/EXE, DPI experiment, benchmark, screenshot atau revisi MagicPath baru. Perubahan saat ini hanya penambahan dokumen rencana dan pencatatan approval; spec approved beserta PR lain tidak diubah.

Review terutama bagian 1–3 dan jalur evidence T3, lalu pilih/konfirmasi eksekusi. Rekomendasi **inline T1→T2→T3**, karena kedua dialog berbagi lifecycle App; jangan edit App paralel. Ledger harus menyimpan run/node/head per-task dan semua keputusan yang mengubah rencana. Keputusan merge, rilis/deployment dan akses akun tetap terpisah dari persetujuan eksekusi.
