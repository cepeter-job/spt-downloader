"""Simple native Windows interface; settings persist no password/token values."""
from datetime import date, datetime
import json
import os
import queue
import re
import threading
import time
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import ttk,messagebox
from .controller import JobController,validate_job_scope,validate_detail_source
from . import diagnostics
from .credentials import ALLOWED_ORIGINS,LOGIN_ORIGIN,save_login,delete_login
from .ui_copy import copy_text, format_text
from .ui_state import ExportState, begin_export, scope_errors, reduce_export, mark_stopping, record_reply
from .ui_views import MainView
from .ui_theme import configure_dialog, dip_to_px, effective_scale
from .job_pruning import (DEFAULT_KEEP_JOBS, validate_keep_jobs,
                          preview_published_jobs, prune_published_jobs)
from .job_maintenance import inspect_job_storage, delete_incomplete_jobs
from .paths import downloads_folder
from .build_info import read_build_info
from . import update_notice

# Maintainer-approved personal OneDrive within the organizational Microsoft 365
# tenant, intentionally shared with colleagues in the organization. '/personal/'
# identifies its storage location; it does not imply public access or a team site.
# The maintainer confirmed this exact destination. Because the repository
# and binary are public, the path exposes the owner's account identifier;
# this disclosure and its lifecycle implications require explicit review.
# Personnel changes, link revocation, or folder moves require a reviewed URL
# migration; no permissions, credentials, or download links come from Worker JSON.
UPDATE_FOLDER_URL = ('https://kemenkeu-my.sharepoint.com/my?'
    'id=%2Fpersonal%2Fpuntoami%5Fpriyono%5Fkemenkeu%5Fgo%5Fid%2FDocuments%2FSPT%20Downloader'
    '&ga=1')

#punto ami priyono

DEFAULTS={'browser':'msedge','headless':True,'login_origin':LOGIN_ORIGIN,'identifier':'','detail_source':'json-first','keep_jobs':DEFAULT_KEEP_JOBS}
DETAIL_SOURCE_LABELS={'dom':copy_text('main.source.label.dom'),'json-first':copy_text('main.source.label.json.hybrid.pilot')}
_SELECTION_MONTHS = ('Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
                     'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember')


def _selection_period_label(tax, period):
    """Display captions only; source periods still own search, sorting and capture."""
    if tax.casefold() == 'pph badan':
        return copy_text('selection.period.label.tahunan')
    number = re.fullmatch(r'0?[1-9]|1[0-2]', period)
    code = re.fullmatch(r'(0[1-9]|1[0-2])\1(?:19|20|21)[0-9]{2}', period)
    if number or code:
        return _SELECTION_MONTHS[int(period if number else code[1]) - 1]
    caption = re.fullmatch(r'([a-z]+) [0-9]{4}', period.casefold())
    if caption:
        for month in _SELECTION_MONTHS:
            if caption[1] == month.casefold():
                return month
    return period


def _selection_detail_key(period, model):
    months = tuple(month.casefold() for month in _SELECTION_MONTHS)
    monthly = re.fullmatch(r'([a-z]+) ([0-9]{4})', period.casefold())
    annual = re.fullmatch(r'(?:januari - desember )?([0-9]{4})', period.casefold())
    if monthly and monthly[1] in months:
        year, month = int(monthly[2]), months.index(monthly[1]) + 1
    elif annual:
        year, month = int(annual[1]), 13
    else:
        # Unknown periods are incomparable: even their models keep source order.
        return (1,)
    return (0, year, month, _selection_model_key(model))


def _selection_model_key(model):
    if model.casefold() == 'normal':
        return (0,)
    amendment = re.fullmatch(r'(?:pembetulan (?:ke-)?|amendment )([0-9]+)', model.casefold())
    if amendment:
        # Decimal length/text avoids integer limits without altering source values.
        number = amendment[1].lstrip('0') or '0'
        return (1, len(number), number)
    return (2,)


def _selection_latest_period(tax, period, fallback_year):
    """Recognize source syntax only; never group by its shortened display label."""
    key = _selection_detail_key(period, 'Normal')
    annual = tax.casefold() == 'pph badan'
    if key[0] == 0 and key[1] and (key[2] == 13) == annual:
        return (key[1], 1, 12) if annual else (key[1], key[2], key[2])
    code = re.fullmatch(r'(0[1-9]|1[0-2])(0[1-9]|1[0-2])([0-9]{4})', period)
    if code and int(code[3]) and (
            (annual and (code[1], code[2]) == ('01', '12')) or (not annual and code[1] == code[2])):
        return (int(code[3]), int(code[1]), int(code[2]))
    if (not annual and re.fullmatch(r'0?[1-9]|1[0-2]', period)
            and re.fullmatch(r'[0-9]{4}', fallback_year) and int(fallback_year)):
        return (int(fallback_year), int(period), int(period))
    return None


def _selection_latest_iids(records, scope_year=''):
    """Rank recognized source periods, retaining every original value and ID."""
    groups, unresolved = {}, set()
    for ordinal, record in enumerate(records):
        iid, meta = f'record-{ordinal}', record['meta'] if 'meta' in record else {}
        tax, period, model = (meta.get(field, '') for field in ('Jenis Pajak', 'Masa Pajak', 'Model SPT'))
        year = meta.get('Tahun Pajak', '')
        if not all(isinstance(value, str) and value for value in (tax, period)):
            unresolved.add(iid)
            continue
        valid_year = ('Tahun Pajak' not in meta or (
            isinstance(year, str) and re.fullmatch(r'[0-9]{4}', year) and int(year)))
        period_key = _selection_latest_period(tax, period, year if valid_year and year else scope_year)
        if period_key is None:
            unresolved.add(iid)
            continue
        group = (tax.casefold(), *period_key)
        rank = _selection_model_key(model) if isinstance(model, str) else (2,)
        if not valid_year or (year and int(year) != period_key[0]):
            rank = (2,)
            if valid_year and year:
                # Either conflicting year must remain manual, including its aliases.
                groups.setdefault((tax.casefold(), int(year), *period_key[1:]), []).append((iid, rank))
        groups.setdefault(group, []).append((iid, rank))
    latest = set()
    for members in groups.values():
        if any(rank[0] == 2 for _, rank in members):
            unresolved.update(iid for iid, _ in members)
            continue
        highest = max(rank for _, rank in members)
        latest.update(iid for iid, rank in members if rank == highest)
    return latest, unresolved


def load_preferences(root):
    try:data=json.loads((Path(root)/'preferences.json').read_text(encoding='utf-8'))
    except (OSError,ValueError):return dict(DEFAULTS)
    if not isinstance(data,dict):return dict(DEFAULTS)
    result=dict(DEFAULTS)
    if data.get('browser') in ('msedge','chrome'):result['browser']=data['browser']
    if type(data.get('headless')) is bool:result['headless']=data['headless']
    # Legacy origin preferences never migrate or read credentials; Satu owns login.
    result['login_origin']=LOGIN_ORIGIN
    if isinstance(data.get('identifier'),str) and len(data['identifier'])<=256:result['identifier']=data['identifier']
    if type(data.get('detail_source')) is str and data['detail_source'] in DETAIL_SOURCE_LABELS:
        result['detail_source']=data['detail_source']
    if type(data.get('keep_jobs')) is int and 0 <= data['keep_jobs'] <= 100:
        result['keep_jobs']=data['keep_jobs']
    return result


def save_preferences(root,data):
    allowed={key:data.get(key,default) for key,default in DEFAULTS.items()}
    allowed['login_origin']=LOGIN_ORIGIN
    validate_detail_source(allowed['detail_source'])
    if allowed['detail_source'] not in DETAIL_SOURCE_LABELS:
        raise ValueError('Mode sumber detail hanya didukung melalui CLI SPT Badan.')
    validate_keep_jobs(allowed['keep_jobs'])
    if allowed['browser'] not in ('msedge','chrome') or allowed['login_origin'] not in ALLOWED_ORIGINS:
        raise ValueError('Preferensi browser/origin tidak valid.')
    if type(allowed['headless']) is not bool or not isinstance(allowed['identifier'],str):
        raise ValueError('Preferensi tidak valid.')
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    temporary=root/'preferences.tmp'
    temporary.write_text(json.dumps(allowed,ensure_ascii=False,indent=2),encoding='utf-8')
    temporary.replace(root/'preferences.json')


def _record_update_check(outcome, manual, duration_ms=None):
    """Record only fixed update outcomes and duration, never response metadata."""
    fields = {'update_check_result': outcome,
              'update_check_trigger': 'manual' if manual else 'automatic'}
    if duration_ms is not None:
        fields['duration_ms'] = max(0.0, duration_ms)
    diagnostics.record('update.check', **fields)


def _fetch_update_with_logging(installed, manual):
    """Isolate network work from Tk; never log the URL, manifest or exception."""
    began = time.monotonic()
    try:
        notice = update_notice.fetch_notice(update_notice.MANIFEST_URL, installed)
    except Exception:
        # Preserve the original fail-silent contract for network/format failures.
        result = ('unavailable', None)
        outcome = 'unavailable'
    else:
        result = ('ok', notice)
        outcome = 'update_available' if notice is not None else 'up_to_date'
    _record_update_check(outcome, manual, (time.monotonic() - began) * 1000)
    return result


class App:
    def __init__(self,root,workspace,controller=None):
        self.root=root;self.workspace=Path(workspace)
        self._previous_callback = root.report_callback_exception
        root.report_callback_exception = self._report_callback
        self.preferences=load_preferences(self.workspace)
        # Only the controller created by this App owns its retention policy.
        # Self-test deliberately injects a synthetic controller and may replace
        # the JobController factory with a non-type sentinel.
        self._owns_controller=controller is None
        self.controller=JobController(self.workspace,self.on_event) if controller is None else controller
        if self._owns_controller:
            self.controller.keep_jobs=self.preferences['keep_jobs']
        self._closing=False;self._result=None
        self._settings_dialog=None
        self._credential_status=None
        self._settings_close=None
        self._settings_refresh=None
        self._manual_prune_busy=False
        self._storage_snapshot=None
        self._storage_vars=None
        self._storage_pending=False
        self._storage_rerun=False
        self._storage_results=queue.Queue(maxsize=1)
        self._storage_after=None
        self._interaction=None
        self._interaction_seen=set()
        self._interaction_stopped_job=None
        self._ui_state = ExportState()
        self._poll_after = None
        self._poll_failed = False
        self._disposed = False
        self._update_after = None
        self._update_pending = False
        self._update_results = queue.Queue(maxsize=1)
        self._update_seen = set()
        self._update_dialog = None
        self._update_deferred_logged = False
        self._update_notice_deferred_logged = False
        root.title(copy_text('app.title'))
        self.view = MainView(root, year_default=str(date.today().year),
                            on_start=self.start, on_stop=self.stop,
                            on_settings=self.settings, on_open_result=self.open_result)
        self.view.pack(fill='both', expand=True)
        for name in ('npwp', 'year', 'status', 'percent', 'npwp_entry', 'year_entry',
                     'start_button', 'stop_button', 'settings_button', 'open_button',
                     'bar', 'results_label'):
            setattr(self, name, getattr(self.view, name))
        root.protocol('WM_DELETE_WINDOW', self.request_close)
        root.bind('<Alt-m>', lambda event: self.start())
        root.bind('<Alt-s>', lambda event: self.stop())
        root.bind('<Alt-p>', lambda event: self.settings())
        self.npwp_entry.bind('<Return>', lambda event: self.start())
        self.year_entry.bind('<Return>', lambda event: self.start())
        root.bind('<Destroy>', self._on_destroy, add='+')
        self.npwp_entry.focus_set()
        self._poll_after = root.after(100, self._poll)
        # Start the automatic check on the first Tk event-loop turn after the
        # window is built; the fetch itself remains on the background thread.
        # Synthetic GUI self-tests inject a controller and must stay offline.
        if self._owns_controller:
            self._update_after = root.after(0, self.check_updates)
            # Read-only private job inventory; never delete PARTIAL/failed on startup.
            self._storage_after = root.after(0, self._refresh_storage)

    def check_updates(self, manual=False):
        """Fetch public release metadata off Tk's thread, never touching Coretax."""
        self._update_after = None
        if self._disposed or self._closing:
            return
        if self._update_pending:
            _record_update_check('already_pending', manual)
            return
        if self.controller.active:
            # Automatic retries run every 15s; emit only one deferral per job.
            if manual or not self._update_deferred_logged:
                _record_update_check('deferred_active', manual)
            self._update_deferred_logged = True
            if manual:
                messagebox.showinfo(copy_text('update.dialog.title.pekerjaan.sedang.berjalan'),
                    copy_text('update.dialog.body.pemeriksaan.pembaruan.tersedia.setelah.pekerjaan'),
                    parent=self._settings_dialog or self.root)
            else:
                self._update_after = self.root.after(15000, self.check_updates)
            return
        self._update_deferred_logged = False
        installed = read_build_info()
        if installed is None:
            _record_update_check('invalid_build', manual)
            if manual:
                messagebox.showinfo(copy_text('update.dialog.title.identitas.build.tidak.tersedia'),
                    copy_text('update.dialog.body.versi.aplikasi.tidak.dapat.diverifikasi'), parent=self._settings_dialog or self.root)
            return
        self._update_pending = True
        _record_update_check('started', manual)

        def worker():
            self._update_results.put(_fetch_update_with_logging(installed, manual))

        threading.Thread(target=worker, daemon=True, name='spt-update-check').start()
        self._update_after = self.root.after(200, lambda: self._receive_update(manual))

    def _receive_update(self, manual=False):
        self._update_after = None
        if self._disposed:
            return
        try:
            state, notice = self._update_results.get_nowait()
        except queue.Empty:
            self._update_after = self.root.after(200, lambda: self._receive_update(manual))
            return
        self._update_pending = False
        if notice is not None and (self.controller.active or self._interaction is not None
                                   or self._settings_dialog is not None and not manual
                                   or not manual and self.root.state() == 'iconic'):
            # Automatic checks also wait for a restored main window; a manual
            # Settings check must not disappear into an invisible retry loop.
            if not self._update_notice_deferred_logged:
                _record_update_check('notice_deferred', manual)
            self._update_notice_deferred_logged = True
            self._update_results.put((state, notice))
            self._update_pending = True
            self._update_after = self.root.after(2000, lambda: self._receive_update(manual))
            return
        self._update_notice_deferred_logged = False
        if state != 'ok':
            if manual:
                messagebox.showinfo(copy_text('update.dialog.title.pemeriksaan.tidak.tersedia'),
                    copy_text('update.dialog.body.pembaruan.belum.dapat.diperiksa.coba'),
                    parent=self._settings_dialog or self.root)
        elif notice is None:
            if manual:
                messagebox.showinfo(copy_text('update.dialog.title.pembaruan'),
                    copy_text('update.dialog.body.tidak.ada.pembaruan.yang.lebih'),
                    parent=self._settings_dialog or self.root)
        elif notice.run_id not in self._update_seen:
            self._update_seen.add(notice.run_id)
            self._show_update_notice(notice)
        if not manual and self._owns_controller:
            self._update_after = self.root.after(24 * 60 * 60 * 1000, self.check_updates)

    def _show_update_notice(self, notice):
        """Show one short, dismissible notice; browser navigation is user-initiated."""
        if self._disposed or self._closing or self._update_dialog is not None:
            return
        parent = self._settings_dialog or self.root
        dialog = tk.Toplevel(parent)
        # Avoid flashing the new window at Tk's default screen origin.
        dialog.withdraw()
        self._update_dialog = dialog
        dialog.title(copy_text('update.window.title.pembaruan'))
        dialog.transient(parent)
        frame = ttk.Frame(dialog, padding=18)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text=copy_text('update.widget.update.tersedia'),
                  style='SPT.Heading.TLabel').pack(anchor='w', pady=(0, 12))
        actions = ttk.Frame(frame)
        actions.pack(anchor='e')
        prior_grab = self.root.grab_current()

        def dismiss():
            self._update_dialog = None
            if self.root.grab_current() is dialog:
                dialog.grab_release()
            dialog.destroy()
            if (prior_grab is not None and prior_grab.winfo_exists()
                    and not self._disposed):
                prior_grab.grab_set()

        def open_folder():
            # Fixed approved SharePoint folder; never follow a URL from the manifest.
            try:
                opened = webbrowser.open(UPDATE_FOLDER_URL, new=2)
            except (OSError, webbrowser.Error):
                opened = False
            if opened:
                dismiss()
            else:
                messagebox.showerror(copy_text('update.dialog.title.browser.tidak.tersedia'),
                    copy_text('update.dialog.body.folder.pembaruan.tidak.dapat.dibuka'), parent=dialog)

        ttk.Button(actions, text=copy_text('update.widget.update'), command=open_folder).pack(side='left', padx=(0, 8))
        ttk.Button(actions, text=copy_text('update.widget.close'), command=dismiss).pack(side='left')
        dialog.protocol('WM_DELETE_WINDOW', dismiss)

        # Position after Tk has measured the controls, relative to the window
        # that owns the notice (Settings for a manual check, otherwise the app).
        # Use screen coordinates so this also works on secondary monitors.
        parent.update_idletasks()
        dialog.update_idletasks()
        width, height = dialog.winfo_reqwidth(), dialog.winfo_reqheight()
        parent_width = (parent.winfo_width() if parent.winfo_width() > 1
                        else parent.winfo_reqwidth())
        parent_height = (parent.winfo_height() if parent.winfo_height() > 1
                         else parent.winfo_reqheight())
        # Tk's wm.geometry coordinates reference the decorated window frame,
        # while winfo_root* reports the content origin. Correct for the same
        # frame offset observed on the already mapped parent; otherwise Windows
        # shifts the visible notice down by its 31px title bar.
        frame_dx = parent.winfo_rootx() - parent.winfo_x()
        frame_dy = parent.winfo_rooty() - parent.winfo_y()
        x = parent.winfo_rootx() + (parent_width - width) // 2 - frame_dx
        y = parent.winfo_rooty() + (parent_height - height) // 2 - frame_dy
        dialog.geometry(f'+{x}+{y}')
        dialog.deiconify()
        if prior_grab is not None:
            dialog.grab_set()

    def _report_callback(self, kind, error, trace):
        diagnostics.record('gui.callback_failed', error=error, level='ERROR')
        self._previous_callback(kind, error, trace)

    def open_logs(self):
        try:
            os.startfile(str(diagnostics.log_folder(self.workspace)))  # nosec B606 - Open an inspected existing output/log folder, not a generated command.
        except (OSError, ValueError):
            messagebox.showerror(copy_text('main.dialog.title.log.tidak.tersedia'),
                copy_text('main.dialog.body.folder.log.belum.tersedia.atau'),
                parent=self._settings_dialog or self.root)

    def _refresh_storage(self):
        """Inspect private job storage off Tk, without starting any cleanup."""
        self._storage_after = None
        if self._disposed:
            return
        if self._storage_pending:
            self._storage_rerun = True
            return
        self._storage_pending = True
        self._paint_storage()
        workspace = self.workspace
        keep = self.preferences['keep_jobs']
        active_id = (getattr(self.controller, 'job_id', None)
                     if self.controller.active else None)

        def inspect():
            try:
                snapshot = inspect_job_storage(workspace, keep, active_id=active_id)
            except (OSError, ValueError, TypeError, RuntimeError):
                snapshot = None
            self._storage_results.put(snapshot)

        threading.Thread(target=inspect, name='spt-storage-inventory',
                         daemon=True).start()
        self._storage_after = self.root.after(150, self._receive_storage)

    def _receive_storage(self):
        self._storage_after = None
        if self._disposed:
            return
        try:
            self._storage_snapshot = self._storage_results.get_nowait()
        except queue.Empty:
            self._storage_after = self.root.after(150, self._receive_storage)
            return
        self._storage_pending = False
        self._paint_storage()
        if self._storage_rerun:
            self._storage_rerun = False
            self._refresh_storage()

    def _paint_storage(self):
        """Show only aggregates; do not display tax data or job identifiers."""
        if self._storage_vars is None:
            return
        fields = self._storage_vars
        if self._storage_pending or self._storage_snapshot is None:
            for name in ('total', 'complete', 'partial', 'failed', 'protected', 'size'):
                fields[name].set(copy_text('settings.storage.checking' if self._storage_pending else 'settings.storage.unavailable'))
            return
        snapshot = self._storage_snapshot
        for name in ('total', 'complete', 'partial', 'failed', 'protected'):
            fields[name].set(str(snapshot[name]))
        size = snapshot['estimated_bytes'] / (1024 * 1024)
        prefix = copy_text('settings.storage.lower_bound' if not snapshot['scan_complete'] else 'settings.storage.approximate')
        fields['size'].set(format_text('settings.storage.size_display', prefix=prefix, size=f'{size:.1f}'))

    def _prune_old_jobs(self, dialog, dirty):
        """Dry-run, confirm, then revalidate in an idle worker before deleting."""
        if self._manual_prune_busy or self.controller.active or self._disposed:
            return
        if dirty():
            messagebox.showinfo(copy_text('settings.dialog.title.simpan.pengaturan'),
                copy_text('settings.dialog.body.simpan.atau.abaikan.perubahan.pengaturan'),
                parent=dialog)
            return
        keep = self.preferences['keep_jobs']
        if keep == 0:
            messagebox.showinfo(copy_text('settings.dialog.title.pemangkasan.nonaktif'),
                copy_text('settings.dialog.body.ubah.jumlah.cache.job.ke'),
                parent=dialog)
            return
        try:
            downloads = downloads_folder()
        except (OSError, ValueError):
            messagebox.showerror(copy_text('settings.dialog.title.pemangkasan.tidak.tersedia'),
                copy_text('settings.dialog.body.folder.downloads.windows.tidak.dapat'), parent=dialog)
            return
        excluded = getattr(self.controller, 'job_id', None)
        work = queue.Queue(maxsize=1)
        approved_ids = ()  # Never written to UI or diagnostics.
        self._manual_prune_busy = True
        if self._settings_refresh is not None:
            self._settings_refresh(preserve_status=True)
        self._credential_status.set(copy_text('settings.status.memeriksa.job.lama.yang.aman'))

        def inspect():
            try:
                result = preview_published_jobs(self.workspace, downloads, keep,
                                                exclude=excluded)
                work.put(('preview', result))
            except (OSError, ValueError, TypeError, RuntimeError):
                work.put(('preview_error', None))

        def delete():
            try:
                outcome = prune_published_jobs(self.workspace, downloads, keep,
                                               exclude=excluded, allowed_ids=approved_ids,
                                               report=True)
                work.put(('deleted', outcome))
            except (OSError, ValueError, TypeError, RuntimeError):
                work.put(('delete_error', None))

        def receive():
            nonlocal approved_ids
            if self._disposed:
                return
            try:
                kind, result = work.get_nowait()
            except queue.Empty:
                self.root.after(100, receive)
                return
            if kind == 'preview':
                total = result['eligible_jobs']
                size = result['estimated_bytes']
                if not result['scan_complete']:
                    self._manual_prune_busy = False
                    messagebox.showinfo(copy_text('settings.dialog.title.pratinjau.belum.lengkap'),
                        copy_text('settings.dialog.body.sebagian.job.belum.dapat.diverifikasi'), parent=dialog)
                elif not total:
                    self._manual_prune_busy = False
                    messagebox.showinfo(copy_text('settings.dialog.title.tidak.ada.job.yang.memenuhi'),
                        copy_text('settings.dialog.body.tidak.ada.job.lama.bersegel'),
                        parent=dialog)
                elif self.controller.active:
                    self._manual_prune_busy = False
                    messagebox.showinfo(copy_text('settings.dialog.title.job.sedang.berjalan'),
                        copy_text('settings.dialog.body.pemangkasan.dibatalkan.karena.ada.pekerjaan'), parent=dialog)
                else:
                    approved_ids = tuple(result['candidate_ids'])
                    if len(approved_ids) != total:
                        self._manual_prune_busy = False
                        messagebox.showerror(copy_text('settings.dialog.title.pratinjau.tidak.konsisten'),
                            copy_text('settings.dialog.body.kandidat.job.tidak.cocok.dengan'), parent=dialog)
                        if self._settings_dialog is dialog and dialog.winfo_exists():
                            self._settings_refresh(preserve_status=True)
                        return
                    diagnostics.record('jobs.prune_preview', count=total, estimated_bytes=size)
                    confirmed = messagebox.askyesno(copy_text('settings.dialog.title.konfirmasi.pemangkasan.job'),
                        format_text('settings.dialog.body.total.job.lama.memenuhi.syarat', total=total, value2=f'{size / (1024 * 1024):.1f}'),
                        parent=dialog, default='no')
                    if confirmed and not self.controller.active:
                        self._credential_status.set(copy_text('settings.status.memangkas.hanya.job.lama.yang'))
                        threading.Thread(target=delete, name='spt-manual-prune',
                                         daemon=True).start()
                        self.root.after(100, receive)
                        return
                    self._manual_prune_busy = False
            else:
                self._manual_prune_busy = False
                if kind in ('preview_error', 'delete_error'):
                    message = ((copy_text('settings.message.pratinjau.gagal.dan.tidak.ada') if kind == 'preview_error' else copy_text('settings.message.pemangkasan.mengalami.gangguan.sebagian.job')))
                    messagebox.showerror(copy_text('settings.dialog.title.pemangkasan.tidak.tersedia'), message, parent=dialog)
                else:
                    removed = result['removed']
                    diagnostics.record('jobs.manual_pruned', count=removed)
                    if result['incomplete']:
                        messagebox.showwarning(copy_text('settings.dialog.title.pemangkasan.belum.tuntas'),
                            format_text('settings.dialog.body.removed.job.selesai.dipangkas.tetapi', removed=removed), parent=dialog)
                    else:
                        messagebox.showinfo(copy_text('settings.dialog.title.pemangkasan.selesai'),
                            format_text('settings.dialog.body.removed.job.lama.berhasil.dipangkas', removed=removed),
                            parent=dialog)
            if self._settings_dialog is dialog and dialog.winfo_exists():
                if self._settings_refresh is not None:
                    self._settings_refresh(preserve_status=True)
                self._credential_status.set(
                    copy_text('settings.status.pemangkasan.selesai.atau.dibatalkan.nilai'))
                self._refresh_storage()

        threading.Thread(target=inspect, name='spt-prune-preview', daemon=True).start()
        self.root.after(100, receive)

    def _remove_incomplete_jobs(self, dialog, dirty):
        """Explicit selection and two-stage confirmation for incomplete jobs."""
        if self._manual_prune_busy or self.controller.active or self._disposed:
            return
        if dirty():
            messagebox.showinfo(copy_text('settings.dialog.title.simpan.pengaturan'),
                copy_text('settings.dialog.body.simpan.atau.abaikan.perubahan.sebelum'), parent=dialog)
            return
        self._manual_prune_busy = True
        if self._settings_refresh is not None:
            self._settings_refresh(preserve_status=True)
        self._credential_status.set(copy_text('settings.status.memeriksa.job.partial.gagal.secara'))
        work = queue.Queue(maxsize=1)
        # A finished PARTIAL job must be selectable. Exclude only an active ID.
        excluded = (getattr(self.controller, 'job_id', None)
                    if self.controller.active else None)
        candidates = {}
        approvals = ()

        def inspect():
            try:
                snapshot = inspect_job_storage(
                    self.workspace, self.preferences['keep_jobs'], active_id=excluded)
                work.put(('preview', snapshot))
            except (OSError, ValueError, TypeError, RuntimeError):
                work.put(('preview_error', None))

        def delete():
            try:
                result = delete_incomplete_jobs(
                    self.workspace, approvals, active_id=excluded)
                work.put(('deleted', result))
            except (OSError, ValueError, TypeError, RuntimeError):
                work.put(('delete_error', None))

        def finish():
            self._manual_prune_busy = False
            if self._settings_refresh is not None:
                self._settings_refresh(preserve_status=True)

        def choose(items):
            nonlocal approvals
            picker = tk.Toplevel(dialog)
            picker.title(copy_text('settings.window.title.pilih.job.partial.gagal'))
            picker.transient(dialog)
            frame = ttk.Frame(picker, padding=16)
            frame.pack(fill='both', expand=True)
            ttk.Label(frame, text=copy_text('settings.widget.pilih.job.yang.akan.dihapus'),
                      wraplength=560).pack(anchor='w', pady=(0, 12))
            table = ttk.Treeview(frame, columns=('number', 'status', 'modified', 'size'),
                                 show='headings', selectmode='extended', height=10)
            columns = (('number', copy_text('settings.table.heading.no'), 55), ('status', copy_text('settings.table.heading.status'), 95),
                       ('modified', copy_text('settings.table.heading.terakhir.berubah'), 155), ('size', copy_text('settings.table.heading.ukuran.mib'), 110))
            for key, label, width in columns:
                table.heading(key, text=label)
                table.column(key, width=width, anchor='center', stretch=(key == 'modified'))
            for number, item in enumerate(items, 1):
                try:
                    changed = datetime.fromtimestamp(
                        item['modified_ns'] / 1_000_000_000).strftime('%Y-%m-%d %H:%M')
                except (OSError, ValueError, OverflowError):
                    changed = copy_text('settings.message.tidak.tersedia')
                table.insert('', 'end', iid=item['id'],
                             values=(number, item['status'], changed,
                                     f"{item['bytes'] / (1024 * 1024):.1f}"))
            table.pack(fill='both', expand=True)
            # This only changes the visible selection. The separate default-No
            # confirmation and backend snapshot revalidation remain mandatory.
            row_ids = tuple(table.get_children(''))
            all_selected = tk.BooleanVar(master=picker, value=False)

            def toggle_all():
                if all_selected.get():
                    table.selection_set(*row_ids)
                elif table.selection():
                    table.selection_remove(*table.selection())

            def sync_all(_event=None):
                all_selected.set(bool(row_ids) and set(table.selection()) == set(row_ids))

            ttk.Checkbutton(frame, text=copy_text('settings.widget.select.all'), name='select_all_incomplete',
                            variable=all_selected, command=toggle_all).pack(
                                anchor='w', pady=(8, 0))
            table.bind('<<TreeviewSelect>>', sync_all, add='+')
            ttk.Label(frame, text=copy_text('settings.widget.gunakan.ctrl.shift.untuk.memilih'), wraplength=560).pack(
                          anchor='w', pady=(10, 8))
            actions = ttk.Frame(frame)
            actions.pack(anchor='e')

            def cancel():
                picker.grab_release()
                picker.destroy()
                if dialog.winfo_exists():
                    dialog.grab_set()
                finish()
                self._credential_status.set(copy_text('settings.status.pembersihan.job.dibatalkan'))

            def confirm():
                nonlocal approvals
                chosen = tuple(table.selection())
                if not chosen:
                    messagebox.showinfo(copy_text('settings.dialog.title.pilih.job'),
                        copy_text('settings.dialog.body.pilih.sekurangnya.satu.job.partial'), parent=picker)
                    return
                bytes_total = sum(candidates[i]['bytes'] for i in chosen)
                accepted = messagebox.askyesno(
                    copy_text('settings.dialog.title.konfirmasi.penghapusan.permanen'),
                    format_text('settings.dialog.body.value1.job.partial.gagal.dipilih', value1=len(chosen), value2=f'{bytes_total / (1024 * 1024):.1f}'),
                    parent=picker, default='no')
                if not accepted:
                    return
                approvals = tuple((i, candidates[i]['digest']) for i in chosen)
                picker.grab_release()
                picker.destroy()
                if dialog.winfo_exists():
                    dialog.grab_set()
                self._credential_status.set(copy_text('settings.status.menghapus.job.terpilih.setelah.verifikasi'))
                threading.Thread(target=delete, name='spt-remove-incomplete',
                                 daemon=True).start()
                self.root.after(100, receive)

            ttk.Button(actions, text=copy_text('settings.widget.batal'), command=cancel).pack(side='left', padx=(0, 8))
            ttk.Button(actions, text=copy_text('settings.widget.hapus.terpilih'), command=confirm).pack(side='left')
            picker.protocol('WM_DELETE_WINDOW', cancel)
            picker.bind('<Escape>', lambda event: cancel())
            dialog.grab_release()
            picker.grab_set()
            picker.focus_set()

        def receive():
            if self._disposed:
                return
            try:
                kind, result = work.get_nowait()
            except queue.Empty:
                self.root.after(100, receive)
                return
            if kind == 'preview' and result is not None:
                self._storage_snapshot = result
                self._paint_storage()
                if not result['scan_complete']:
                    finish()
                    messagebox.showinfo(copy_text('settings.dialog.title.inventaris.belum.lengkap'),
                        copy_text('settings.dialog.body.ada.file.job.yang.tidak'),
                        parent=dialog)
                elif not result['removable']:
                    finish()
                    messagebox.showinfo(copy_text('settings.dialog.title.tidak.ada.job.partial.gagal'),
                        copy_text('settings.dialog.body.tidak.ada.job.partial.gagal'),
                        parent=dialog)
                elif self.controller.active:
                    finish()
                    messagebox.showinfo(copy_text('settings.dialog.title.job.masih.aktif'),
                        copy_text('settings.dialog.body.pembersihan.dibatalkan.selama.scraping.berjalan'), parent=dialog)
                else:
                    candidates.update({item['id']: item for item in result['removable']})
                    choose(result['removable'])
                return
            finish()
            if kind in ('preview_error', 'delete_error'):
                messagebox.showerror(copy_text('settings.dialog.title.pembersihan.gagal'),
                    copy_text('settings.dialog.body.pemeriksaan.atau.penghapusan.tidak.tuntas'), parent=dialog)
            elif kind == 'deleted':
                if result['incomplete']:
                    messagebox.showwarning(copy_text('settings.dialog.title.pembersihan.tidak.tuntas'),
                        format_text('settings.dialog.body.value1.job.dihapus.sepenuhnya.ada', value1=result['removed']), parent=dialog)
                else:
                    messagebox.showinfo(copy_text('settings.dialog.title.pembersihan.selesai'),
                        format_text('settings.dialog.body.value1.job.partial.gagal.berhasil', value1=result['removed']), parent=dialog)
            self._credential_status.set(copy_text('settings.status.pembersihan.selesai.atau.dibatalkan'))
            self._refresh_storage()

        threading.Thread(target=inspect, name='spt-incomplete-preview',
                         daemon=True).start()
        self.root.after(100, receive)

    def start(self):
        if self.controller.active or self._closing or self._disposed or self._manual_prune_busy:
            return
        errors = scope_errors(self.npwp.get(), self.year.get())
        self.view.show_errors(errors)
        if errors:
            self.status.set(copy_text('main.status.periksa.kembali.npwp.dan.tahun'))
            (self.npwp_entry if 'npwp' in errors else self.year_entry).focus_set()
            return
        self._close_interaction()
        try:
            npwp, year = validate_job_scope(self.npwp.get(), self.year.get())
            options = {} if self.preferences['detail_source']=='dom' else {'detail_source':self.preferences['detail_source']}
            if self.preferences['identifier']:
                options['account']=self.preferences['identifier']
            job_id = self.controller.start(npwp, str(year), self.preferences['browser'], self.preferences['headless'], **options)
            self._ui_state = begin_export(job_id, npwp, str(year))
        except (ValueError, RuntimeError) as error:
            messagebox.showerror(copy_text('main.dialog.title.tidak.dapat.mulai'), str(error), parent=self.root)
            return
        self._interaction_seen.clear()
        self._interaction_stopped_job = None
        self._poll_failed = False
        self._result = None
        self.status.set(copy_text('main.status.menyiapkan.aplikasi.untuk.mengunduh.spt'))
        self.view.render(self._ui_state, active=True)
        self.stop_button.focus_set()

    def stop(self):
        job_id = getattr(self.controller, 'job_id', None)
        if not self.controller.active:
            self._close_interaction()
            return
        if self._interaction_stopped_job == job_id:
            return
        self._interaction_stopped_job = job_id
        self._close_interaction()
        self.controller.stop()
        self._ui_state = mark_stopping(self._ui_state)
        self.status.set(copy_text('main.status.menghentikan.unduhan.data.sementara.tetap'))
        self.view.render(self._ui_state, active=True)
        self.stop_button.state(['disabled'])

    def on_event(self, event):
        if self._disposed:
            return
        job_id = getattr(self.controller, 'job_id', None)
        if not job_id or event.get('job_id') != job_id:
            return
        kind = event['type']
        if kind == 'terminal' and self.controller.active:
            return
        if kind in ('selection_required', 'overwrite_required'):
            if (not self._export_job_active(job_id)
                    or (job_id, event.get('request_id')) in self._interaction_seen):
                return
        state = reduce_export(self._ui_state, event, controller_active=self.controller.active)
        if state is self._ui_state:
            return
        self._ui_state = state
        self.status.set(event.get('message', '')[:500])
        if kind == 'terminal':
            self._interaction_stopped_job = job_id
            self._close_interaction()
            self.status.set(format_text('main.status.value1.value2', value1=state.terminal_status, value2=event.get('message', '')[:450]))
            self._result = Path(state.output) if state.output else None
        self.view.render(state, active=self.controller.active)
        if kind == 'selection_required':
            self.selection_dialog(event)
        elif kind == 'overwrite_required':
            self.overwrite_dialog(event)
        elif kind == 'terminal':
            # The result pane may have scrolled the form out of view.
            # Keep keyboard focus on a visible action rather than the hidden input.
            target = self.open_button if self.open_button.instate(['!disabled']) else self.start_button
            target.focus_set()

    def _poll(self):
        self._poll_after = None
        if self._disposed:
            return
        try:
            # Pengurasan antrean dan callback UI tetap di thread Tk; thread latar
            # menyerahkan event lewat antrean tanpa menyentuh widget.
            self.controller.poll()
        except Exception as error:
            diagnostics.record('gui.poll_failed', error=error, level='ERROR')
            # A monitoring error is not proof that the owned process has exited.
            # Request cleanup once, but leave the UI busy until the controller is idle.
            if not self._poll_failed:
                self._poll_failed = True
                self._interaction_stopped_job = getattr(self.controller, 'job_id', None)
                self._close_interaction()
                self.controller.close()
                self._ui_state = mark_stopping(self._ui_state)
                self.view.render(self._ui_state, active=self.controller.active)
            self.status.set(copy_text('main.status.proses.belum.bisa.dipantau.menunggu'))
            if not self.controller.active and self._ui_state.job_id == getattr(self.controller, 'job_id', None):
                self.on_event({'job_id': self._ui_state.job_id, 'type': 'terminal', 'status': 'ERROR',
                    'percent': min(99, self._ui_state.percent or 0), 'output': None,
                    'message': copy_text('main.poll.error')})
        if self._interaction is not None and not self._interaction_current(self._interaction):
            self._close_interaction()
        if self._closing and not self.controller.active:
            self.controller.close()
            self._dispose()
            self.root.destroy()
            return
        self._poll_after = self.root.after(100, self._poll)

    def _on_destroy(self, event):
        if event.widget is self.root:
            self._dispose()

    def _dispose(self):
        if self._disposed:
            return
        self._disposed = True
        self.root.report_callback_exception = self._previous_callback
        if self._poll_after is not None:
            try:
                self.root.after_cancel(self._poll_after)
            except tk.TclError:
                # Root teardown may already have removed the pending poll command.
                pass
            self._poll_after = None
        if self._storage_after is not None:
            try:
                self.root.after_cancel(self._storage_after)
            except tk.TclError:
                # Tk may already have retired the pending callback during root
                # teardown. Disposal is terminal; no retry is safe or needed.
                pass
            self._storage_after = None
        if self._update_after is not None:
            try:
                self.root.after_cancel(self._update_after)
            except tk.TclError:
                # Root teardown may already have removed the pending callback.
                pass
            self._update_after = None
        if self._update_dialog is not None:
            try:
                self._update_dialog.destroy()
            except tk.TclError:
                # Root teardown may already have destroyed this widget.
                pass
            self._update_dialog = None
        self.view.dispose()

    def request_close(self):
        if self._disposed or self._manual_prune_busy:
            return  # Keep the window and its worker alive until cleanup finishes.
        if self._settings_close is not None and not self.controller.active:
            self._settings_close(on_closed=self.request_close)
            return
        if self.controller.active:
            if not messagebox.askyesno(copy_text('main.dialog.title.hentikan.pekerjaan'), copy_text('main.dialog.body.hentikan.worker.milik.aplikasi.dan'),
                                       parent=self.root, default='no'):
                return
            self._closing = True
            self.stop()
        else:
            self._close_interaction()
            self.controller.close()
            self._dispose()
            self.root.destroy()

    def open_result(self):
        if self._result and self._result.is_dir():os.startfile(str(self._result))  # nosec B606 - Open an inspected existing output/log folder, not a generated command.
        else:messagebox.showerror(copy_text('main.dialog.title.hasil.tidak.ditemukan'),copy_text('main.dialog.body.folder.hasil.tidak.lagi.tersedia'),parent=self.root)

    def _export_job_active(self,job_id):
        return (isinstance(job_id,str) and bool(job_id) and not self._closing
                and self.controller.active and getattr(self.controller,'operation','export')=='export'
                and job_id==getattr(self.controller,'job_id',None) and job_id!=self._interaction_stopped_job)

    def _read_interaction(self,event,kind):
        job_id=event.get('job_id');request_id=event.get('request_id')
        if (not self._export_job_active(job_id) or event.get('type')!=kind+'_required'
                or not isinstance(request_id,str) or len(request_id)!=32
                or any(character not in '0123456789abcdef' for character in request_id)):
            return None
        if (job_id,request_id) in self._interaction_seen:return None
        if self._interaction is not None:
            if self._interaction['key'][0]==job_id:return None
            self._close_interaction()
        self._interaction_seen.add((job_id,request_id))
        try:
            payload=self.controller.read_request(event)
            if not isinstance(payload,dict):raise ValueError('Invalid confirmation data')
        except (OSError,ValueError,RuntimeError):
            self._interaction_error(job_id,'Daftar konfirmasi belum bisa dibuka.');return None
        return (job_id,kind,request_id),payload

    def _new_interaction(self,key,title):
        previous_focus=self.root.focus_get()
        # A transient can stay hidden with its minimized owner while holding
        # the input grab. Restore the owner before creating the modal.
        if self.root.state() in ('iconic', 'withdrawn'):
            self.root.deiconify()
        dialog=tk.Toplevel(self.root);dialog.title(title)
        dialog.transient(self.root)
        interaction={'key':key,'dialog':dialog,'focus':previous_focus,'traces':[],
                     'layout_after':None,'bindings':[]}
        self._interaction=interaction
        dialog.grab_set()
        dialog.bind('<Alt-s>',lambda event:self._cancel_interaction(interaction))
        return interaction

    def _interaction_current(self,interaction):
        return (self._interaction is interaction and self._export_job_active(interaction['key'][0])
                and interaction['dialog'].winfo_exists())

    def _close_interaction(self,interaction=None):
        current=self._interaction
        if current is None or (interaction is not None and current is not interaction):return
        # Invalidate callbacks before destroying their widgets or releasing the grab.
        self._interaction=None
        dialog=current['dialog']
        if current['layout_after'] is not None:
            try:dialog.after_cancel(current['layout_after'])
            except tk.TclError:
                # Parent teardown may already have retired this modal's timer.
                pass
            current['layout_after']=None
        for widget,sequence,token in current['bindings']:
            try:widget.unbind(sequence,token)
            except tk.TclError:
                # The binding belongs to the modal or its already-destroyed children.
                pass
        current['bindings'].clear()
        for variable,token in current['traces']:
            try:variable.trace_remove('write',token)
            except tk.TclError:
                # Window shutdown may already have removed this Tcl variable or trace.
                pass
        current['traces'].clear()
        dialog=current['dialog']
        try:
            if dialog.grab_current() is dialog:dialog.grab_release()
            dialog.destroy()
        except tk.TclError:
            # Parent shutdown may already have destroyed the dialog and released its grab.
            pass
        focus=current['focus']
        try:
            if (focus is None or not focus.winfo_exists()
                    or (isinstance(focus,ttk.Widget) and focus.instate(['disabled']))):
                focus=self.stop_button if self.controller.active else self.npwp_entry
            focus.focus_set()
        except tk.TclError:
            # Focus cannot be restored after its widget or Tcl interpreter is destroyed.
            pass

    def _cancel_interaction(self,interaction):
        active=self._interaction_current(interaction)
        self._close_interaction(interaction)
        if active:self.stop()
        return 'break'

    def _interaction_error(self,job_id,message):
        if self._export_job_active(job_id):
            self.stop()
            self.status.set(format_text('main.status.value1.menghentikan.unduhan', value1=message))

    def _reply_interaction(self,interaction,payload):
        if not self._interaction_current(interaction):
            self._close_interaction(interaction);return 'break'
        job_id,kind,request_id=interaction['key']
        self._close_interaction(interaction)
        try:
            # A stale response may arrive during terminal cleanup. Do not turn
            # that dismissal into a new cancellation of the worker's result.
            if not self.controller.respond(kind,request_id,payload):return 'break'
            if self._export_job_active(job_id):
                self._ui_state = record_reply(self._ui_state, job_id=job_id, kind=kind,
                    request_id=request_id,
                    selected_count=len(payload['selected_ids']) if kind == 'selection' else None,
                    overwrite=payload.get('overwrite'))
                if kind == 'selection':
                    total = self._ui_state.selected_count
                    self.status.set(format_text('main.status.spt.diproses.0.total.terverifikasi', total=total))
                self.view.render(self._ui_state, active=True)
        except (OSError,ValueError,RuntimeError):
            self._interaction_error(job_id,'Keputusan belum bisa diproses.')
        return 'break'

    def selection_dialog(self, event):
        request = self._read_interaction(event, 'selection')
        if request is None:
            return
        key, payload = request
        rows, identifiers = {}, set()
        try:
            records = payload.get('records')
            if not isinstance(records, list):
                raise ValueError('Invalid inventory')
            for ordinal, record in enumerate(records):
                if not isinstance(record, dict):
                    raise ValueError('Invalid inventory record')
                identifier, meta = record.get('record_id'), record.get('meta', {})
                if (not isinstance(identifier, str) or not identifier or len(identifier) > 512
                        or identifier in identifiers or not isinstance(meta, dict)):
                    raise ValueError('Invalid inventory identifier or metadata')
                identifiers.add(identifier)
                tax, period, model = (str(meta.get(field, '')) for field in ('Jenis Pajak', 'Masa Pajak', 'Model SPT'))
                values = (tax, _selection_period_label(tax, period), model, identifier)
                # Source identifiers remain data, never Tcl widget paths or item names.
                rows[f'record-{ordinal}'] = (identifier, values, ' '.join((tax, period, model, identifier, values[1])).casefold(),
                                           _selection_detail_key(period, model))
        except (TypeError, ValueError):
            self._interaction_error(key[0], 'Daftar SPT belum bisa ditampilkan.')
            return
        if not self._export_job_active(key[0]):
            return
        interaction = self._new_interaction(key, copy_text('selection.title'))
        dialog = interaction['dialog']
        # Resolve native size before mapping the full child tree at a temporary
        # geometry, which otherwise makes Windows arrange every child twice.
        configure_dialog(dialog, self.root, size_dip=(920, 600))
        scale = effective_scale(self.root)
        px = lambda value: dip_to_px(value, scale)
        frame = ttk.Frame(dialog, padding=px(12))
        frame.pack(fill='both', expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        canvas = tk.Canvas(frame, name='body_viewport', borderwidth=0, highlightthickness=0,
                           background='SystemWindow', takefocus=False)
        canvas.grid(row=0, column=0, sticky='nsew')
        body_scroll = ttk.Scrollbar(frame, orient='vertical', command=canvas.yview, takefocus=False)
        body_scroll.grid(row=0, column=1, sticky='ns')
        canvas.configure(yscrollcommand=body_scroll.set)
        body = ttk.Frame(canvas, padding=px(4), style='SPT.Card.TFrame')
        body.columnconfigure(0, weight=1)
        body.rowconfigure(3, weight=1)
        body_window = canvas.create_window(0, 0, window=body, anchor='nw')
        intro = ttk.Label(body, text=copy_text('selection.help'), style='SPT.TLabel', wraplength=px(700))
        intro.grid(row=0, column=0, sticky='ew', pady=(0, px(8)))
        snapshot = self._ui_state
        context = copy_text('selection.message.konteks.permintaan.tidak.tersedia')
        if snapshot is not None and snapshot.job_id == key[0]:
            context = format_text('selection.message.npwp.permintaan.npwp.tahun.pajak', npwp=snapshot.npwp, year=snapshot.year)
        scope = ttk.Label(body, name='scope', text=context, style='SPT.Caption.TLabel', wraplength=px(700))
        scope.grid(row=1, column=0, sticky='ew', pady=(0, px(8)))
        search_group = ttk.Frame(body, style='SPT.Card.TFrame')
        search_group.columnconfigure(0, weight=1)
        search_group.grid(row=2, column=0, sticky='ew', pady=(0, px(8)))
        search_label = ttk.Label(search_group, text=copy_text('selection.search.label'),
                                 style='SPT.Label.TLabel', wraplength=px(700))
        search_label.grid(row=0, column=0, sticky='ew')
        search = tk.StringVar(dialog)
        entry = ttk.Entry(search_group, name='search', textvariable=search, style='SPT.TEntry')
        entry.grid(row=1, column=0, sticky='ew', pady=(px(4), 0))
        shortcuts = ttk.Frame(search_group, name='selection_shortcuts', style='SPT.Card.TFrame')
        shortcuts.grid(row=0, column=0, sticky='ew', pady=(0, px(4)))
        shortcut_vars = {name: tk.BooleanVar(dialog, False) for name in ('all', 'latest', 'potput', 'ppn')}
        shortcut_controls = {}
        shortcut_help = ttk.Label(search_group, text=copy_text('selection.shortcuts.help'),
                                  style='SPT.Caption.TLabel', wraplength=px(700))
        shortcut_help.grid(row=1, column=0, sticky='ew', pady=(0, px(4)))
        search_label.grid_configure(row=2)
        entry.grid_configure(row=3)
        table = ttk.Frame(body, style='SPT.Card.TFrame')
        table.grid(row=3, column=0, sticky='nsew')
        table.columnconfigure(0, weight=1)
        table.rowconfigure(0, weight=1)
        tree = ttk.Treeview(table, name='records', columns=('type', 'period', 'model', 'identifier'),
                            show='headings', selectmode='extended', height=8, style='SPT.Dialog.Treeview')
        for column, label, width in zip(('type', 'period', 'model', 'identifier'),
                tuple(copy_text(key) for key in ('selection.table.type', 'selection.table.period', 'selection.table.model', 'selection.table.id')), (160, 180, 160, 220)):
            tree.heading(column, text=label)
            heading_width = int(dialog.tk.call('font', 'measure', 'SPTLabel', label)) + px(24)
            tree.column(column, width=px(width), minwidth=max(px(100), heading_width), stretch=True)
        tree.grid(row=0, column=0, sticky='nsew')
        vertical = ttk.Scrollbar(table, orient='vertical', command=tree.yview, takefocus=False)
        vertical.grid(row=0, column=1, sticky='ns')
        horizontal = ttk.Scrollbar(table, orient='horizontal', command=tree.xview, takefocus=False)
        horizontal.grid(row=1, column=0, sticky='ew')
        tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        focused = tk.StringVar(dialog)
        id_label = ttk.Label(body, text=copy_text('selection.focused_id'), style='SPT.Label.TLabel')
        id_label.grid(row=4, column=0, sticky='ew', pady=(px(8), px(4)))
        focused_field = ttk.Entry(body, name='focused_id', textvariable=focused, state='readonly', style='SPT.TEntry')
        focused_field.grid(row=5, column=0, sticky='ew')
        summary, notice = tk.StringVar(dialog), tk.StringVar(dialog)
        summary_label = ttk.Label(body, name='summary', textvariable=summary, style='SPT.TLabel', wraplength=px(700))
        summary_label.grid(row=6, column=0, sticky='ew', pady=(px(8), 0))
        notice_label = ttk.Label(body, name='notice', textvariable=notice, style='SPT.TLabel', wraplength=px(700))
        notice_label.grid(row=7, column=0, sticky='ew', pady=(px(4), 0))
        keyboard_hint = ttk.Label(body, text=copy_text('selection.keyboard_hint'),
                                   style='SPT.Caption.TLabel', wraplength=px(700))
        keyboard_hint.grid(row=8, column=0, sticky='ew', pady=(px(4), 0))
        actions = ttk.Frame(frame, name='actions')
        actions.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(px(10), 0))
        actions.columnconfigure(0, weight=1)
        mpn_var = tk.BooleanVar(dialog, False)
        mpn_choice = ttk.Checkbutton(actions, name='mpn', text=copy_text('selection.mpn'),
                                     variable=mpn_var)
        mpn_choice.grid(row=0, column=0, sticky='w')
        stop = ttk.Button(actions, name='stop', text=copy_text('action.stop'), style='SPT.TButton',
                          command=lambda: self._cancel_interaction(interaction))
        stop.grid(row=0, column=1, padx=(0, px(8)), sticky='e')
        type_priority = {'pph badan': 0, 'pph pasal 21/26': 1, 'pph unifikasi': 2, 'ppn': 3}
        ordered_iids = sorted(rows, key=lambda iid: (
            type_priority.get(rows[iid][1][0].casefold(), len(type_priority)), rows[iid][1][0].casefold(),
            rows[iid][3]))
        descending, reset_pending = None, False
        scope_year = str(snapshot.year) if snapshot is not None and snapshot.job_id == key[0] else ''
        latest_iids, unresolved_latest = _selection_latest_iids(records, scope_year)
        category_iids = {
            'potput': {iid for iid, row in rows.items()
                       if row[1][0].casefold() in ('pph pasal 21/26', 'pph unifikasi')},
            'ppn': {iid for iid, row in rows.items() if row[1][0].casefold() == 'ppn'}}
        preset_selection = None

        def clear_shortcuts():
            nonlocal preset_selection
            preset_selection = None
            for variable in shortcut_vars.values():
                variable.set(False)

        def apply_shortcut(name):
            nonlocal preset_selection
            if not self._interaction_current(interaction):
                return
            if name == 'all':
                for other in ('latest', 'potput', 'ppn'):
                    shortcut_vars[other].set(False)
                scope_all = shortcut_vars['all'].get()
            else:
                shortcut_vars['all'].set(False)
                scope_all = name == 'latest' and shortcut_vars['latest'].get() and not any(
                    shortcut_vars[category].get() for category in ('potput', 'ppn'))
            visible = tree.get_children()
            scope = set(visible) if scope_all else set().union(*(
                category_iids[category] for category in ('potput', 'ppn') if shortcut_vars[category].get()))
            chosen = set(visible) & scope
            if shortcut_vars['latest'].get():
                chosen &= latest_iids
            preset_selection = set(chosen)
            tree.selection_set(tuple(iid for iid in visible if iid in chosen))
            update_selection()
            request_reflow()

        for name in shortcut_vars:
            control = ttk.Checkbutton(shortcuts, name='select_' + name,
                text=copy_text('selection.shortcuts.' + name), variable=shortcut_vars[name],
                command=lambda name=name: apply_shortcut(name))
            shortcut_controls[name] = control
            control.grid(row=0, column=len(shortcut_controls) - 1, sticky='w', padx=(0, px(12)))

        def selected_ids():
            chosen = set(tree.selection()) & set(tree.get_children())
            return [row[0] for iid, row in rows.items() if iid in chosen]

        def sync_focused_id(event=None):
            if not self._interaction_current(interaction):
                return
            iid = tree.focus()
            focused.set(rows[iid][0] if iid in rows and iid in tree.get_children() else '')

        def update_selection(event=None):
            nonlocal reset_pending
            if not self._interaction_current(interaction):
                return
            if preset_selection is not None and set(tree.selection()) != preset_selection:
                clear_shortcuts()
            count, visible = len(selected_ids()), len(tree.get_children())
            visible_iids = set(tree.get_children())
            for name, control in shortcut_controls.items():
                available = visible_iids & category_iids[name] if name in category_iids else visible_iids
                control.state(['!disabled' if available else 'disabled'])
            submit.state(['!disabled' if count else 'disabled'])
            summary.set(copy_text('selection.summary', selected=count, visible=visible, inventory=len(rows)))
            if count:
                reset_pending = False
            messages = []
            if not rows:
                messages.append(copy_text('selection.empty'))
            elif not visible:
                messages.append(copy_text('selection.no_match'))
            if reset_pending:
                messages.append(copy_text('selection.filter_reset'))
            if shortcut_vars['latest'].get() and unresolved_latest & visible_iids:
                messages.append(copy_text('selection.shortcuts.manual'))
            notice.set('\n'.join(messages))
            sync_focused_id()

        def begin_keyboard_navigation(event):
            if not self._interaction_current(interaction):
                return 'break'
            # Preserve native Ctrl-navigation, which moves focus without selecting.
            if tree.focus() or event.state & 0x0004:
                return None
            visible = tree.get_children()
            if visible:
                first = visible[0]
                tree.focus(first)
                tree.selection_set(first)
                tree.see(first)
                update_selection()
            return 'break'

        def filter_records(*args):
            nonlocal reset_pending
            if not self._interaction_current(interaction):
                return
            # Latch before deleting: Tk may deliver the empty selection event later.
            if selected_ids():
                reset_pending = True
            clear_shortcuts()
            children = tree.get_children()
            if children:
                tree.delete(*children)
            query = search.get().strip().casefold()
            for iid in ordered_iids:
                _, values, text, _ = rows[iid]
                if query in text:
                    tree.insert('', 'end', iid=iid, values=values)
            update_selection()
            request_reflow()

        def sort_type():
            nonlocal ordered_iids, descending
            if not self._interaction_current(interaction):
                return
            descending = False if descending is None else not descending
            # Reverse only the type grouping; chronology and source ties stay ascending.
            ordered_iids = sorted(rows, key=lambda iid: rows[iid][3])
            ordered_iids.sort(key=lambda iid: rows[iid][1][0].casefold(), reverse=descending)
            visible = set(tree.get_children())
            for position, iid in enumerate(iid for iid in ordered_iids if iid in visible):
                tree.move(iid, '', position)
            tree.heading('type', text=format_text('selection.table.heading.jenis.pajak.value2', value2='▼' if descending else '▲'))
            if tree.focus() in visible:
                tree.see(tree.focus())
            update_selection()

        def sort_key(event):
            sort_type()
            return 'break'

        def confirm():
            if not self._interaction_current(interaction):
                self._close_interaction(interaction)
                return
            chosen = selected_ids()
            if chosen:
                self._reply_interaction(interaction, {'selected_ids': chosen, 'mpn': mpn_var.get()})

        def confirm_key(event):
            if self._interaction_current(interaction) and submit.instate(['!disabled']):
                confirm()
            return 'break'

        submit = ttk.Button(actions, name='confirm', text=copy_text('selection.confirm'),
                             style='SPT.Primary.TButton', state='disabled', command=confirm)
        submit.grid(row=0, column=2, sticky='e')

        layout_size = None

        def update_scrollregion(event=None):
            if self._interaction_current(interaction):
                # Wrapping finishes in idle geometry work after reflow returns.
                # Match the measured body so its final lines remain reachable.
                height = max(body.winfo_reqheight(), canvas.winfo_height())
                if int(canvas.itemcget(body_window, 'height') or 0) != height:
                    canvas.itemconfigure(body_window, height=height)
                canvas.configure(scrollregion=canvas.bbox('all'))

        def reflow():
            nonlocal layout_size
            interaction['layout_after'] = None
            if not self._interaction_current(interaction):
                return
            width = canvas.winfo_width()
            if width <= 1:
                # Native Map/Configure supplies the first usable viewport.
                # Do not spin idle callbacks while the modal is not mapped.
                return
            layout_size = (width, canvas.winfo_height())
            canvas.itemconfigure(body_window, width=width)
            text_width = max(px(80), width - px(8))
            for label in (intro, scope, shortcut_help, search_label, id_label, summary_label, notice_label, keyboard_hint):
                if int(label.cget('wraplength') or 0) != text_width:
                    label.configure(wraplength=text_width)
            shortcut_width = sum(control.winfo_reqwidth() + px(12) for control in shortcut_controls.values())
            columns = 4 if shortcut_width <= text_width else 2
            if max(control.winfo_reqwidth() + px(12) for control in shortcut_controls.values()) * 2 > text_width:
                columns = 1
            for position, control in enumerate(shortcut_controls.values()):
                control.grid_configure(row=position // columns, column=position % columns)
            # The body can scroll on short displays; the fixed actions remain outside it.
            canvas.itemconfigure(body_window, height=max(body.winfo_reqheight(), canvas.winfo_height()))
            update_scrollregion()

        def request_reflow(event=None):
            if (not self._interaction_current(interaction)
                    or (event is not None and event.widget not in (dialog, canvas))):
                return
            if event is not None and (canvas.winfo_width(), canvas.winfo_height()) == layout_size:
                # Windows can deliver obsolete/duplicate Configure messages
                # after the viewport is already arranged at its actual size.
                return
            if event is None or layout_size is None:
                # Initial and content layout must not wait for resize debounce.
                # Reuse the modal's owned token so Stop retires either kind.
                if interaction['layout_after'] is not None:
                    dialog.after_cancel(interaction['layout_after'])
                interaction['layout_after'] = dialog.after_idle(reflow)
            elif interaction['layout_after'] is None:
                interaction['layout_after'] = dialog.after(75, reflow)

        def reveal_focus(event):
            if not self._interaction_current(interaction) or not str(event.widget).startswith(str(body) + '.'):
                return
            top = event.widget.winfo_rooty() - canvas.winfo_rooty()
            height = canvas.winfo_height()
            if top < 0 or top + event.widget.winfo_height() > height:
                extent = max(1, body.winfo_height())
                if event.widget.winfo_height() > height:
                    target = canvas.canvasy(0) + top
                elif top < 0:
                    target = canvas.canvasy(0) + top - px(4)
                else:
                    target = canvas.canvasy(0) + top + event.widget.winfo_height() - height + px(4)
                canvas.yview_moveto(max(0, target) / extent)

        def wheel(event):
            if not self._interaction_current(interaction) or event.widget is tree:
                return None
            if event.widget is canvas or str(event.widget).startswith(str(body) + '.'):
                canvas.yview_scroll(-int(event.delta / 120), 'units')
                return 'break'
            return None

        for widget, sequence, handler in (
                (tree, '<Down>', begin_keyboard_navigation),
                (tree, '<<TreeviewSelect>>', update_selection), (tree, '<KeyRelease>', sync_focused_id),
                (tree, '<ButtonRelease-1>', sync_focused_id), (tree, '<FocusIn>', sync_focused_id),
                (dialog, '<Alt-j>', sort_key), (submit, '<Return>', confirm_key), (submit, '<space>', confirm_key),
                (canvas, '<Configure>', request_reflow), (dialog, '<Configure>', request_reflow),
                (body, '<Configure>', update_scrollregion), (dialog, '<FocusIn>', reveal_focus),
                (dialog, '<MouseWheel>', wheel)):
            token = widget.bind(sequence, handler, add='+')
            interaction['bindings'].append((widget, sequence, token))
        tree.heading('type', command=sort_type)
        interaction['traces'].append((search, search.trace_add('write', filter_records)))
        dialog.protocol('WM_DELETE_WINDOW', lambda: self._cancel_interaction(interaction))
        dialog.bind('<Escape>', lambda event: self._cancel_interaction(interaction))
        filter_records()
        entry.focus_set()

    def overwrite_dialog(self, event):
        request = self._read_interaction(event, 'overwrite')
        if request is None:
            return
        key, payload = request
        files, folder = payload.get('files'), payload.get('folder')
        if (not isinstance(files, list) or not files
                or any(not isinstance(path, str) or not path for path in files)):
            self._interaction_error(key[0], 'Daftar file yang akan diganti belum bisa ditampilkan.')
            return
        if not isinstance(folder, str) or not folder.strip():
            self._interaction_error(key[0], copy_text('overwrite.context_missing'))
            return
        # The active job can change while the private request is being read.
        if not self._export_job_active(key[0]):
            return
        interaction = self._new_interaction(key, copy_text('overwrite.title'))
        dialog = interaction['dialog']
        configure_dialog(dialog, self.root, size_dip=(800, 520))
        scale = effective_scale(self.root)
        px = lambda value: dip_to_px(value, scale)
        frame = ttk.Frame(dialog, padding=px(12))
        frame.pack(fill='both', expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        canvas = tk.Canvas(frame, name='body_viewport', borderwidth=0, highlightthickness=0,
                           background='SystemWindow', takefocus=False)
        canvas.grid(row=0, column=0, sticky='nsew')
        body_scroll = ttk.Scrollbar(frame, orient='vertical', command=canvas.yview, takefocus=False)
        body_scroll.grid(row=0, column=1, sticky='ns')
        canvas.configure(yscrollcommand=body_scroll.set)
        body = ttk.Frame(canvas, padding=px(4), style='SPT.Card.TFrame')
        body.columnconfigure(0, weight=1)
        body.rowconfigure(3, weight=1)
        body_window = canvas.create_window(0, 0, window=body, anchor='nw')
        intro = ttk.Label(body, text=copy_text('overwrite.help'), style='SPT.TLabel', wraplength=px(700))
        intro.grid(row=0, column=0, sticky='ew', pady=(0, px(10)))
        folder_label = ttk.Label(body, text=copy_text('overwrite.folder.label'),
                                 style='SPT.Label.TLabel', wraplength=px(700))
        folder_label.grid(row=1, column=0, sticky='ew', pady=(0, px(4)))
        # Validation tests nonblank context; the actual path remains untouched.
        folder_field = ttk.Entry(body, name='folder', style='SPT.TEntry')
        # This immutable value needs no StringVar whose lifetime could end
        # before the modal; retain it in the native entry until destruction.
        folder_field.insert(0, folder)
        folder_field.state(['readonly'])
        folder_field.grid(row=2, column=0, sticky='ew', pady=(0, px(10)))
        table = ttk.Frame(body, style='SPT.Card.TFrame')
        table.grid(row=3, column=0, sticky='nsew')
        table.columnconfigure(0, weight=1)
        table.rowconfigure(0, weight=1)
        tree = ttk.Treeview(table, name='files', columns=('file',), show='headings',
                            selectmode='none', height=min(8, len(files)), style='SPT.Dialog.Treeview')
        tree.heading('file', text=copy_text('overwrite.table.heading.file.yang.akan.diganti'), anchor='w')
        path_width = max(int(dialog.tk.call('font', 'measure', 'SPTBody', path)) for path in files) + px(24)
        tree.column('file', width=max(px(300), path_width), minwidth=px(100), stretch=False)
        tree.grid(row=0, column=0, sticky='nsew')
        vertical = ttk.Scrollbar(table, orient='vertical', command=tree.yview, takefocus=False)
        vertical.grid(row=0, column=1, sticky='ns')
        horizontal = ttk.Scrollbar(table, orient='horizontal', command=tree.xview, takefocus=False)
        horizontal.grid(row=1, column=0, sticky='ew')
        tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        for ordinal, path in enumerate(files):
            tree.insert('', 'end', iid=f'file-{ordinal}', values=(path,))
        # Item focus enables native arrow navigation without selecting a file
        # or taking keyboard focus away from the safe decision button.
        tree.focus('file-0')
        file_count = ttk.Label(body, name='file_count', text=copy_text('overwrite.files_count', count=len(files)),
                               style='SPT.Label.TLabel', wraplength=px(700))
        file_count.grid(row=4, column=0, sticky='ew', pady=(px(10), px(6)))
        keep_hint = ttk.Label(body, text=copy_text('overwrite.keep_hint'), style='SPT.TLabel', wraplength=px(700))
        keep_hint.grid(row=5, column=0, sticky='ew')
        actions = ttk.Frame(frame, name='actions')
        actions.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(px(10), 0))
        actions.columnconfigure(0, weight=1)

        def decline():
            return self._reply_interaction(interaction, {'overwrite': False})

        def confirm():
            return self._reply_interaction(interaction, {'overwrite': True})

        safe_button = ttk.Button(actions, name='decline', text=copy_text('overwrite.decline'),
                                  style='SPT.TButton', command=decline)
        safe_button.grid(row=0, column=1, padx=(0, px(8)), sticky='e')
        approve_button = ttk.Button(actions, name='confirm', text=copy_text('overwrite.confirm'),
                                     style='SPT.Primary.TButton', command=confirm)
        approve_button.grid(row=0, column=2, sticky='e')

        def decline_key(event):
            decline()
            return 'break'

        def confirm_key(event):
            confirm()
            return 'break'

        def scroll_paths_key(event):
            if not self._interaction_current(interaction):
                return 'break'
            if event.keysym == 'Home':
                tree.xview_moveto(0)
            elif event.keysym == 'End':
                tree.xview_moveto(1)
            elif event.keysym == 'Left':
                tree.xview_scroll(-1, 'units')
            elif event.keysym == 'Right':
                tree.xview_scroll(1, 'units')
            return 'break'

        layout_size = None

        def update_scrollregion(event=None):
            if self._interaction_current(interaction):
                # Wrapping finishes in idle geometry work after reflow returns.
                # Match the measured body so its final lines remain reachable.
                height = max(body.winfo_reqheight(), canvas.winfo_height())
                if int(canvas.itemcget(body_window, 'height') or 0) != height:
                    canvas.itemconfigure(body_window, height=height)
                canvas.configure(scrollregion=canvas.bbox('all'))

        def reflow():
            nonlocal layout_size
            interaction['layout_after'] = None
            if not self._interaction_current(interaction):
                return
            width = canvas.winfo_width()
            if width <= 1:
                # Native Map/Configure supplies the first usable viewport.
                # Do not spin idle callbacks while the modal is not mapped.
                return
            layout_size = (width, canvas.winfo_height())
            canvas.itemconfigure(body_window, width=width)
            text_width = max(px(80), width - px(8))
            for label in (intro, folder_label, file_count, keep_hint):
                if int(label.cget('wraplength') or 0) != text_width:
                    label.configure(wraplength=text_width)
            canvas.itemconfigure(body_window, height=max(body.winfo_reqheight(), canvas.winfo_height()))
            update_scrollregion()

        def request_reflow(event=None):
            if (not self._interaction_current(interaction)
                    or (event is not None and event.widget not in (dialog, canvas))):
                return
            if event is not None and (canvas.winfo_width(), canvas.winfo_height()) == layout_size:
                # Windows can deliver obsolete/duplicate Configure messages
                # after the viewport is already arranged at its actual size.
                return
            if event is None or layout_size is None:
                # Initial and content layout must not wait for resize debounce.
                # Reuse the modal's owned token so Stop retires either kind.
                if interaction['layout_after'] is not None:
                    dialog.after_cancel(interaction['layout_after'])
                interaction['layout_after'] = dialog.after_idle(reflow)
            elif interaction['layout_after'] is None:
                interaction['layout_after'] = dialog.after(75, reflow)

        def reveal_focus(event):
            if not self._interaction_current(interaction) or not str(event.widget).startswith(str(body) + '.'):
                return
            top = event.widget.winfo_rooty() - canvas.winfo_rooty()
            height = canvas.winfo_height()
            if top < 0 or top + event.widget.winfo_height() > height:
                extent = max(1, body.winfo_height())
                if event.widget.winfo_height() > height:
                    target = canvas.canvasy(0) + top
                elif top < 0:
                    target = canvas.canvasy(0) + top - px(4)
                else:
                    target = canvas.canvasy(0) + top + event.widget.winfo_height() - height + px(4)
                canvas.yview_moveto(max(0, target) / extent)

        def wheel(event):
            if not self._interaction_current(interaction) or event.widget is tree:
                return None
            if event.widget is canvas or str(event.widget).startswith(str(body) + '.'):
                canvas.yview_scroll(-int(event.delta / 120), 'units')
                return 'break'
            return None

        for widget, sequence, handler in (
                (safe_button, '<Return>', decline_key), (safe_button, '<space>', decline_key),
                (approve_button, '<Return>', confirm_key), (approve_button, '<space>', confirm_key),
                (tree, '<Control-Left>', scroll_paths_key), (tree, '<Control-Right>', scroll_paths_key),
                (tree, '<Control-Home>', scroll_paths_key), (tree, '<Control-End>', scroll_paths_key),
                (canvas, '<Configure>', request_reflow), (dialog, '<Configure>', request_reflow),
                (body, '<Configure>', update_scrollregion), (dialog, '<FocusIn>', reveal_focus),
                (dialog, '<MouseWheel>', wheel)):
            token = widget.bind(sequence, handler, add='+')
            interaction['bindings'].append((widget, sequence, token))
        dialog.protocol('WM_DELETE_WINDOW', decline)
        dialog.bind('<Escape>', decline_key)

        def record_presented(event):
            if (event.widget is not dialog or not self._interaction_current(interaction)
                    or interaction.get('presented') or not dialog.winfo_viewable()):
                return
            interaction['presented'] = True
            # A mapped modal is not proof the user acted. No names/paths/IDs.
            diagnostics.record('consent.dialog_presented', kind='overwrite', count=len(files))
        token = dialog.bind('<Map>', record_presented, add='+')
        interaction['bindings'].append((dialog, '<Map>', token))
        request_reflow()
        dialog.lift()
        safe_button.focus_set()

    def settings(self):
        if self._settings_dialog is not None:
            self._settings_dialog.focus_set();return
        if self.controller.active:return
        dialog=tk.Toplevel(self.root);dialog.title(copy_text('settings.window.title.pengaturan.spt.downloader'))
        self._settings_dialog=dialog
        dialog.transient(self.root);dialog.grab_set()
        frame=ttk.Frame(dialog,padding=20);frame.pack(fill='both',expand=True);frame.columnconfigure(1,weight=1)
        identifier=tk.StringVar(dialog,value=self.preferences['identifier']);password=tk.StringVar(dialog)
        browser=tk.StringVar(dialog,value=self.preferences['browser']);hidden=tk.BooleanVar(dialog,value=self.preferences['headless'])
        detail_source=tk.StringVar(dialog,value=DETAIL_SOURCE_LABELS[self.preferences['detail_source']])
        keep_jobs=tk.StringVar(dialog,value=str(self.preferences['keep_jobs']))
        self._credential_status=tk.StringVar(dialog,value=copy_text('settings.status.akun.tersimpan.dipakai.saat.mulai'))
        controls=[(copy_text('settings.field.label.akun.username'),ttk.Entry(frame,textvariable=identifier,width=40)),
                  (copy_text('settings.field.label.password.baru'),ttk.Entry(frame,textvariable=password,show='●',width=40)),
                  (copy_text('settings.field.label.browser'),ttk.Combobox(frame,textvariable=browser,values=('msedge','chrome'),state='readonly',width=20)),
                  (copy_text('settings.field.label.sumber.detail.spt'),ttk.Combobox(frame,textvariable=detail_source,
                    values=tuple(DETAIL_SOURCE_LABELS.values()),state='readonly',width=25)),
                  (copy_text('settings.field.label.jumlah.cache.job.0.nonaktif'),ttk.Spinbox(frame,from_=0,to=100,
                    textvariable=keep_jobs,width=8))]
        for row,(label,widget) in enumerate(controls):
            ttk.Label(frame,text=label).grid(row=row,column=0,sticky='w',padx=(0,12),pady=7)
            widget.grid(row=row,column=1,sticky='ew',pady=7)
        hidden_button=ttk.Checkbutton(frame,text=copy_text('settings.background.label'),variable=hidden)
        hidden_button.grid(row=5,column=0,columnspan=2,sticky='w',pady=8)
        ttk.Label(frame,text=copy_text('settings.widget.login.otomatis.melalui.satu.kemenkeu'),wraplength=520).grid(row=6,column=0,columnspan=2,sticky='w',pady=8)
        buttons=ttk.Frame(frame);buttons.grid(row=7,column=0,columnspan=2,sticky='w',pady=8)
        ttk.Label(frame,textvariable=self._credential_status,wraplength=520).grid(row=8,column=0,columnspan=2,sticky='w',pady=8)
        ttk.Button(frame, text=copy_text('settings.widget.buka.folder.log'), command=self.open_logs).grid(row=9,column=0,columnspan=2,sticky='w',pady=(4,0))
        ttk.Button(frame, text=copy_text('settings.widget.cek.pembaruan'), command=lambda:self.check_updates(manual=True)).grid(
            row=10,column=0,columnspan=2,sticky='w',pady=(4,0))
        storage_frame=ttk.LabelFrame(frame, text=copy_text('settings.widget.dashboard.penyimpanan.job'), padding=10)
        storage_frame.grid(row=11,column=0,columnspan=2,sticky='ew',pady=(12,4))
        self._storage_vars={
            name:tk.StringVar(dialog, value=copy_text('settings.storage.unavailable'))
            for name in ('total','complete','partial','failed','protected','size')}
        for index,(key,caption) in enumerate((
                ('total',copy_text('settings.storage.label.total.job')),('complete',copy_text('settings.storage.label.complete')),
                ('partial',copy_text('settings.storage.label.partial')),('failed',copy_text('settings.storage.label.gagal.dibatalkan')),
                ('protected',copy_text('settings.storage.label.protected.auto.clean')),('size',copy_text('settings.storage.label.ruang.data.privat')))):
            cell=ttk.Frame(storage_frame, padding=(8,4))
            cell.grid(row=index // 3,column=index % 3,sticky='w',padx=(0,12))
            ttk.Label(cell,text=caption).pack(anchor='w')
            ttk.Label(cell,textvariable=self._storage_vars[key]).pack(anchor='w')
        ttk.Label(storage_frame,text=copy_text('settings.widget.protected.dapat.termasuk.complete.partial'),
                  wraplength=540).grid(row=2,column=0,columnspan=3,sticky='w',pady=(6,4))
        storage_refresh_button=ttk.Button(storage_frame,text=copy_text('settings.widget.perbarui.penggunaan.storage'),
                                          command=self._refresh_storage)
        storage_refresh_button.grid(row=3,column=0,columnspan=3,sticky='w')
        self._paint_storage()
        traces=[]
        decision_dialog = None
        pending_preferences = False
        credential_account = self.preferences['identifier']
        credential_changed = False
        credential_action = None
        shutdown_request = None
        def selected():
            mode=next(key for key,label in DETAIL_SOURCE_LABELS.items() if label==detail_source.get())
            count=keep_jobs.get()
            parsed=int(count) if re.fullmatch(r'[0-9]{1,3}',count) else count
            return {'browser':browser.get(),'headless':hidden.get(),'login_origin':LOGIN_ORIGIN,
                    'identifier':identifier.get(),'detail_source':mode,'keep_jobs':parsed}
        def dirty():
            return pending_preferences or bool(password.get()) or selected()!=self.preferences
        def refresh(*args,preserve_status=False):
            active=self.controller.active
            for widget in [w for _,w in controls]+[hidden_button,save_button,remove_button,
                    prune_button,incomplete_button,storage_refresh_button]:
                widget.state(['disabled' if active or self._manual_prune_busy else '!disabled'])
            if not active and not preserve_status:
                self._credential_status.set((copy_text('settings.status.perubahan.belum.disimpan.pilih.simpan') if dirty() else copy_text('settings.status.akun.tersimpan.dipakai.saat.mulai')))
        def finish_close():
            for variable,token in traces:variable.trace_remove('write',token)
            password.set('');dialog.grab_release();dialog.destroy()
            self._settings_dialog=None;self._credential_status=None
            self._storage_vars=None
            self._settings_close=None
            self._settings_refresh=None
            self.settings_button.focus_set()
            if shutdown_request is not None:
                shutdown_request()
        def close(*, on_closed=None):
            nonlocal decision_dialog, shutdown_request
            if self._manual_prune_busy:
                return
            if on_closed is not None:
                shutdown_request = on_closed
            if self.controller.active:
                return
            if decision_dialog is not None:
                decision_dialog.lift()
                return
            if not dirty():
                finish_close()
                return
            previous_focus = dialog.focus_get()
            prompt = tk.Toplevel(dialog)
            decision_dialog = prompt
            prompt.title(copy_text('settings.dirty.title'))
            prompt.transient(dialog)
            body = ttk.Frame(prompt, padding=20)
            body.pack(fill='both', expand=True)
            explanation = copy_text('settings.message.simpan.perubahan.sebelum.menutup.pengaturan')
            if credential_changed:
                explanation += (copy_text('settings.message.login.yang.sudah.disimpan.atau'))
            ttk.Label(body, text=explanation, wraplength=420).pack(fill='x', pady=(0, 16))
            actions = ttk.Frame(body)
            actions.pack(fill='x')
            def dismiss(event=None, *, cancel_shutdown=True):
                nonlocal decision_dialog, shutdown_request
                if cancel_shutdown:
                    shutdown_request = None
                prompt.grab_release()
                prompt.destroy()
                decision_dialog = None
                dialog.grab_set()
                if previous_focus is not None and previous_focus.winfo_exists():
                    previous_focus.focus_set()
                else:
                    controls[0][1].focus_set()
                return 'break'
            def save_and_close():
                nonlocal shutdown_request
                dismiss(cancel_shutdown=False)
                if save():
                    finish_close()
                else:
                    shutdown_request = None
            def discard():
                dismiss(cancel_shutdown=False)
                finish_close()
            ttk.Button(actions, text=copy_text('settings.widget.simpan'), command=save_and_close).pack(side='left', padx=(0, 8))
            ttk.Button(actions, text=copy_text('settings.widget.abaikan'), command=discard).pack(side='left', padx=(0, 8))
            return_button = ttk.Button(actions, text=copy_text('settings.widget.kembali'), command=dismiss)
            return_button.pack(side='left')
            prompt.protocol('WM_DELETE_WINDOW', dismiss)
            prompt.bind('<Escape>', dismiss)
            prompt.grab_set()
            return_button.focus_set()
        def save():
            nonlocal pending_preferences, credential_account, credential_changed, credential_action
            if self.controller.active or self._manual_prune_busy:return False
            try:
                if password.get():
                    if not identifier.get().strip():raise ValueError('Masukkan akun sebelum menyimpan password.')
                    save_login(LOGIN_ORIGIN,identifier.get(),password.get())
                    # Vault and preferences are separate stores. A retry must not
                    # repeat the successful secret write or pretend it rolled back.
                    credential_account = identifier.get()
                    credential_changed = pending_preferences = True
                    credential_action = 'saved'
                    password.set('')
                elif identifier.get() and identifier.get()!=credential_account:
                    raise ValueError('Isi password baru ketika mengganti akun; atau pertahankan akun kosong untuk login manual.')
                preferences=selected()
                save_preferences(self.workspace,preferences);self.preferences=preferences
                if self._owns_controller:
                    self.controller.keep_jobs=preferences['keep_jobs']
            except ValueError:
                messagebox.showerror(copy_text('settings.dialog.title.pengaturan.belum.disimpan'),
                    copy_text('settings.dialog.body.periksa.akun.password.dan.jumlah'),parent=dialog)
                return False
            except OSError as error:
                diagnostics.record('settings.failed', error=error, level='ERROR')
                change = (copy_text('settings.message.login.sudah.dihapus') if credential_action == 'deleted' else copy_text('settings.message.password.sudah.disimpan'))
                message = ((format_text('settings.message.value1.tetapi.pengaturan.belum.tersimpan', value1=change) if pending_preferences else copy_text('settings.message.pengaturan.belum.disimpan.windows.menolak')))
                self._credential_status.set(message)
                refresh(preserve_status=True)
                messagebox.showerror(copy_text('settings.dialog.title.pengaturan.belum.disimpan'),message,parent=dialog)
                return False
            pending_preferences = False
            password.set('');refresh()
            self._credential_status.set(copy_text('settings.status.pengaturan.disimpan.akun.tersimpan.akan'))
            self.status.set(copy_text('settings.status.pengaturan.disimpan.password.tidak.ditulis'))
            if self._owns_controller:
                self._refresh_storage()
            return True
        def remove():
            nonlocal pending_preferences, credential_account, credential_changed, credential_action
            if self.controller.active or self._manual_prune_busy:return
            if not messagebox.askyesno(copy_text('settings.dialog.title.hapus.login.yang.disimpan'),copy_text('settings.dialog.body.hapus.login.satu.yang.disimpan'),parent=dialog,default='no'):return
            try:delete_login(LOGIN_ORIGIN)
            except OSError:messagebox.showerror(copy_text('settings.dialog.title.tidak.dapat.menghapus'),copy_text('settings.dialog.body.windows.menolak.penghapusan.kredensial.aplikasi'),parent=dialog);return
            credential_account = ''
            credential_changed = pending_preferences = True
            credential_action = 'deleted'
            password.set('');identifier.set('')
            preferences = dict(self.preferences, identifier='')
            try:
                save_preferences(self.workspace,preferences)
            except OSError as error:
                diagnostics.record('settings.failed', error=error, level='ERROR')
                message = copy_text('settings.message.login.sudah.dihapus.tetapi.pengaturan')
                self._credential_status.set(message)
                refresh(preserve_status=True)
                messagebox.showerror(copy_text('settings.dialog.title.pengaturan.belum.disimpan'),message,parent=dialog)
                return
            self.preferences = preferences
            if self._owns_controller:
                self.controller.keep_jobs=preferences['keep_jobs']
            pending_preferences = False
            refresh()
            self._credential_status.set(copy_text('settings.status.login.satu.yang.disimpan.sudah'))
        save_button=ttk.Button(buttons,text=copy_text('settings.widget.simpan'),command=save);save_button.pack(side='left',padx=(0,8))
        remove_button=ttk.Button(buttons,text=copy_text('settings.delete'),command=remove);remove_button.pack(side='left',padx=(0,8))
        prune_button=ttk.Button(buttons,text=copy_text('settings.widget.bersihkan.cache.job'),
            command=lambda: self._prune_old_jobs(dialog,dirty))
        prune_button.pack(side='left',padx=(0,8))
        incomplete_button=ttk.Button(storage_frame,text=copy_text('settings.widget.hapus.job.partial.gagal'),
            command=lambda: self._remove_incomplete_jobs(dialog,dirty))
        incomplete_button.grid(row=4,column=0,columnspan=3,sticky='w',pady=(6,0))
        ttk.Button(buttons,text=copy_text('settings.widget.tutup'),command=close).pack(side='left')
        self._settings_close=close
        self._settings_refresh=refresh
        for variable in (identifier,password,browser,hidden,detail_source,keep_jobs):traces.append((variable,variable.trace_add('write',refresh)))
        dialog.protocol('WM_DELETE_WINDOW',close);dialog.bind('<Escape>',lambda e:close())
        refresh()
        controls[0][1].focus_set()
        if self._owns_controller:
            self._refresh_storage()
        return dialog
