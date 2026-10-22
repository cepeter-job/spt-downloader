"""A reusable native shell. Actions and job authority remain in App/controller."""
import tkinter as tk
from tkinter import ttk
from typing import Callable, Mapping
from .ui_copy import copy_text, STAGE_LABELS
from .ui_state import ExportState
from .ui_theme import configure_theme, effective_scale, dip_to_px, layout_policy


_STAGE_INDEX = {'authentication': 0, 'inventory': 1, 'selection': 1,
                'details': 2, 'export': 3, 'publish': 3, 'overwrite': 3}
_TITLES = {
    'preparing': 'Menyiapkan aplikasi', 'authenticating': 'Memeriksa akses ke Coretax',
    'login_required': 'Selesaikan login di browser', 'inventory': 'Membaca daftar SPT',
    'awaiting_selection': 'Pilih SPT yang ingin diunduh', 'selection_submitted': 'Menyiapkan SPT pilihan',
    'capturing': 'Mengambil rincian SPT', 'exported': 'File Excel sudah dibuat',
    'publishing': 'Menyimpan hasil unduhan', 'awaiting_overwrite': 'Periksa file yang akan diganti',
    'cancellation_pending': 'Menunggu proses berhenti', 'stopping': 'Menghentikan unduhan…',
    'complete': 'File Excel sudah siap', 'empty_complete': 'Tidak ada SPT yang ditemukan',
    'partial': 'Hasil unduhan belum lengkap', 'cancelled': 'Unduhan dihentikan',
    'blocked': 'Unduhan belum bisa dilanjutkan', 'error': 'Unduhan belum berhasil',
}


class MainView(ttk.Frame):
    def __init__(self, master, *, year_default: str, on_start: Callable[[], object],
                 on_stop: Callable[[], object], on_settings: Callable[[], object],
                 on_open_result: Callable[[], object]):
        super().__init__(master, style='SPT.Shell.TFrame')
        self.window = master.winfo_toplevel()
        configure_theme(self.window)
        self.scale = effective_scale(self.window)
        self._disposed = False
        self._reflow_after = None
        self._reveal_after = None
        self._pending_reveal = 'form'
        self._last_geometry = None
        self._last_compact = None
        self._indeterminate = False
        self._state = ExportState()
        self._root_bindings = []
        self.npwp = tk.StringVar(self)
        self.year = tk.StringVar(self, value=year_default)
        self.status = tk.StringVar(self, value='Masukkan NPWP dan tahun pajak, lalu klik Mulai unduh.')
        self.percent = tk.StringVar(self, value='0%')
        self.npwp_error, self.year_error = tk.StringVar(self), tk.StringVar(self)
        self.scope_npwp, self.scope_year, self.scope_selected = (tk.StringVar(self, value='—') for _ in range(3))
        self.process_title, self.process_help = tk.StringVar(self), tk.StringVar(self)
        self.metric_text = tk.StringVar(self)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self.header = ttk.Frame(self, style='SPT.Shell.TFrame')
        self.header.grid(row=0, column=0, sticky='ew', pady=(0, self.px(12)))
        self.header.columnconfigure(0, weight=1)
        self.heading = ttk.Label(self.header, text=copy_text('app.title'), style='Title.TLabel', wraplength=self.px(500))
        self.heading.grid(row=0, column=0, sticky='ew', padx=(0, self.px(12)))
        self.settings_button = ttk.Button(self.header, text='Pengaturan', command=on_settings, underline=0, style='SPT.TButton')
        self.settings_button.grid(row=0, column=1, sticky='ne')
        self.subtitle = ttk.Label(self.header, text=copy_text('app.subtitle'), style='SPT.Stage.TLabel', wraplength=self.px(500))
        self.subtitle.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(self.px(4), 0))
        self.stage_strip = ttk.Frame(self, style='SPT.Shell.TFrame')
        self.stage_strip.grid(row=1, column=0, sticky='ew', pady=(0, self.px(12)))
        self.stage_labels = tuple(ttk.Label(self.stage_strip, text=f'{index + 1} · {label}',
            style='SPT.Stage.TLabel', takefocus=False, padding=(0, self.px(4)))
            for index, label in enumerate(STAGE_LABELS))
        self.viewport = ttk.Frame(self, style='SPT.Shell.TFrame')
        self.viewport.grid(row=2, column=0, sticky='nsew')
        self.viewport.columnconfigure(0, weight=1)
        self.viewport.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(self.viewport, borderwidth=0, highlightthickness=0,
                                background='SystemButtonFace', takefocus=False)
        self.canvas.grid(row=0, column=0, sticky='nsew')
        scrollbar = ttk.Scrollbar(self.viewport, orient='vertical', command=self.canvas.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.workspace = ttk.Frame(self.canvas, style='SPT.Shell.TFrame')
        self._canvas_window = self.canvas.create_window(0, 0, window=self.workspace, anchor='nw')
        self.content_slot = ttk.Frame(self.workspace, style='SPT.Shell.TFrame')
        self.content_slot.columnconfigure(0, weight=1)
        self.scope_panel = ttk.Frame(self.workspace, style='SPT.Card.TFrame', padding=self.px(16))
        self.scope_panel.columnconfigure(0, weight=1)
        self.scope_title = ttk.Label(self.scope_panel, text='Ringkasan unduhan', style='SPT.Heading.TLabel')
        self.scope_title.grid(row=0, column=0, columnspan=3, sticky='w', pady=(0, self.px(12)))
        self._scope_labels = []
        self._scope_holders = []
        for row, (caption, value) in enumerate((('NPWP', self.scope_npwp), ('Tahun pajak', self.scope_year),
                                                ('SPT dipilih', self.scope_selected)), start=1):
            holder = ttk.Frame(self.scope_panel, style='SPT.Card.TFrame')
            holder.grid(row=row, sticky='ew', pady=(0, self.px(8)))
            holder.columnconfigure(0, weight=1)
            ttk.Label(holder, text=caption, style='SPT.Caption.TLabel').grid(row=0, sticky='w')
            label = ttk.Label(holder, textvariable=value, style='SPT.Label.TLabel', wraplength=self.px(200))
            label.grid(row=1, sticky='ew')
            self._scope_labels.append(label)
            self._scope_holders.append(holder)
        self._build_form()
        self._build_status()
        self.action_bar = ttk.Frame(self, style='SPT.Shell.TFrame')
        self.action_bar.grid(row=3, column=0, sticky='ew', pady=(self.px(12), self.px(8)))
        self.start_button = ttk.Button(self.action_bar, text=copy_text('action.start'), command=on_start, underline=0, style='SPT.Primary.TButton')
        self.stop_button = ttk.Button(self.action_bar, text=copy_text('action.stop'), command=on_stop, state='disabled', style='SPT.TButton')
        self.open_button = ttk.Button(self.action_bar, text=copy_text('action.open_result'), command=on_open_result, state='disabled', style='SPT.TButton')
        self._actions = (self.start_button, self.stop_button, self.open_button)
        self.footer = ttk.Frame(self, style='SPT.Shell.TFrame')
        self.footer.grid(row=4, column=0, sticky='ew')
        self.footer.columnconfigure(0, weight=1)
        self.results_label = ttk.Label(self.footer, text=copy_text('results.location_hint'), style='SPT.Stage.TLabel', wraplength=self.px(500))
        self.results_label.grid(row=0, column=0, sticky='ew')
        self.bugreport_label = ttk.Label(self.footer, text=copy_text('app.bugreport'),
            style='SPT.Stage.TLabel', justify='right', wraplength=self.px(500))
        self.bugreport_label.grid(row=1, column=0, sticky='e', pady=(self.px(4), 0))
        self.canvas.bind('<Configure>', lambda event: self.request_reflow())
        self.workspace.bind('<Configure>', self._update_scrollregion)
        self.bind('<Configure>', lambda event: self.request_reflow())
        self.bind('<Destroy>', self._on_destroy, add='+')
        for sequence, handler in (('<MouseWheel>', self._wheel), ('<FocusIn>', self._reveal_focus)):
            self._root_bindings.append((sequence, self.window.bind(sequence, handler, add='+')))
        self.render(self._state, active=False)

    def px(self, value: float) -> int:
        return dip_to_px(value, self.scale)

    def _build_form(self):
        self.form = ttk.Frame(self.content_slot, style='SPT.Card.TFrame', padding=self.px(16))
        self.form.columnconfigure(0, weight=1)
        self.form_title = ttk.Label(self.form, text=copy_text('form.title'), style='SPT.Heading.TLabel', wraplength=self.px(500))
        self.form_title.grid(row=0, column=0, sticky='ew')
        self.form_help = ttk.Label(self.form, text=copy_text('form.help'), style='SPT.TLabel', wraplength=self.px(500))
        self.form_help.grid(row=1, column=0, sticky='ew', pady=(self.px(8), self.px(16)))
        self.fields = ttk.Frame(self.form, style='SPT.Card.TFrame')
        self.fields.grid(row=2, column=0, sticky='ew')
        self.npwp_field = ttk.Frame(self.fields, style='SPT.Card.TFrame')
        self.year_field = ttk.Frame(self.fields, style='SPT.Card.TFrame')
        for holder in (self.npwp_field, self.year_field):
            holder.columnconfigure(0, weight=1)
        self.npwp_label = ttk.Label(self.npwp_field, text=copy_text('form.npwp.label'), style='SPT.Label.TLabel')
        self.npwp_label.grid(row=0, sticky='w')
        ttk.Label(self.year_field, text='Tahun pajak', style='SPT.Label.TLabel').grid(row=0, sticky='w')
        self.npwp_entry = ttk.Entry(self.npwp_field, textvariable=self.npwp, width=24, style='SPT.TEntry')
        self.year_entry = ttk.Entry(self.year_field, textvariable=self.year, width=10, style='SPT.TEntry')
        self._field_wrappers = []
        for holder, entry, error, name in ((self.npwp_field, self.npwp_entry, self.npwp_error, 'npwp'),
                                           (self.year_field, self.year_entry, self.year_error, 'year')):
            entry.grid(row=1, sticky='ew', pady=(self.px(4), self.px(8)))
            helper = ttk.Label(holder, text=copy_text(f'form.{name}.help'), style='SPT.Caption.TLabel', wraplength=self.px(260))
            helper.grid(row=2, sticky='ew')
            error_label = ttk.Label(holder, textvariable=error, style='SPT.Error.TLabel', wraplength=self.px(260))
            error_label.grid(row=3, sticky='ew', pady=(self.px(4), 0))
            self._field_wrappers.append((holder, helper, error_label))
        self.show_errors({})

    def _build_status(self):
        self.progress_panel = ttk.Frame(self.content_slot, style='SPT.Card.TFrame', padding=self.px(16))
        self.progress_panel.columnconfigure(0, weight=1)
        self.progress_title_label = ttk.Label(self.progress_panel, textvariable=self.process_title, style='SPT.Heading.TLabel', wraplength=self.px(500))
        self.progress_title_label.grid(row=0, column=0, sticky='ew')
        ttk.Label(self.progress_panel, textvariable=self.percent, style='SPT.Label.TLabel').grid(row=1, column=0, sticky='e', pady=(self.px(16), 0))
        self.bar = ttk.Progressbar(self.progress_panel, mode='determinate', maximum=100)
        self.bar.grid(row=2, column=0, sticky='ew', pady=(self.px(8), self.px(16)))
        self.progress_help_label = ttk.Label(self.progress_panel, textvariable=self.process_help, style='SPT.TLabel', wraplength=self.px(500))
        self.progress_help_label.grid(row=3, column=0, sticky='ew')
        self.metrics_label = ttk.Label(self.progress_panel, textvariable=self.metric_text, style='SPT.Label.TLabel', wraplength=self.px(500))
        self.metrics_label.grid(row=4, column=0, sticky='ew', pady=self.px(12))
        self.status_label = ttk.Label(self.progress_panel, textvariable=self.status, style='SPT.Caption.TLabel', wraplength=self.px(500))
        self.status_label.grid(row=5, column=0, sticky='ew')
        self.setup_hint = ttk.Label(self.progress_panel,
            text='Setup Python/uv otomatis saat Mulai. Password hanya di Windows Credential Manager.',
            style='SPT.Caption.TLabel', wraplength=self.px(500))
        self.setup_hint.grid(row=6, column=0, sticky='ew', pady=(self.px(16), 0))
        self.result_panel = ttk.Frame(self.content_slot, style='SPT.Card.TFrame', padding=self.px(16))
        self.result_panel.columnconfigure(0, weight=1)
        self.result_title_label = ttk.Label(self.result_panel, textvariable=self.process_title, style='SPT.Heading.TLabel', wraplength=self.px(500))
        self.result_title_label.grid(row=0, sticky='ew')
        self.result_status_label = ttk.Label(self.result_panel, textvariable=self.status, style='SPT.TLabel', wraplength=self.px(500))
        self.result_status_label.grid(row=1, sticky='ew', pady=(self.px(8), 0))

    def render(self, state: ExportState, *, active: bool) -> None:
        if self._disposed:
            return
        if (state.view_state != self._state.view_state
                or state.terminal_status != self._state.terminal_status):
            self._pending_reveal = self._priority_area(state)
        self._state = state
        self.scope_npwp.set(state.npwp or '—')
        self.scope_year.set(state.year or '—')
        self.scope_selected.set(str(state.selected_count) if state.selected_count is not None else 'Belum dipilih')
        self.process_title.set(_TITLES.get(state.view_state, ''))
        help_text = 'Persentase menunjukkan progres seluruh proses.'
        if state.view_state == 'preparing':
            help_text = 'Saat pertama kali digunakan, aplikasi perlu mengunduh paket pendukung. Pastikan koneksi internet tersedia.'
        elif state.view_state == 'login_required':
            help_text = 'Selesaikan login, CAPTCHA, atau MFA di browser aplikasi. Unduhan berlanjut setelah akses siap.'
        elif state.view_state in ('stopping', 'cancellation_pending'):
            help_text = 'Tunggu sampai proses berhenti. Data sementara yang sudah dibuat tetap disimpan.'
        self.process_help.set(help_text)
        counts = state.inventory if state.view_state == 'inventory' else state.details
        metrics = []
        if counts is not None:
            if counts.processed is not None and counts.total is not None:
                caption = 'Bagian daftar dibaca' if state.view_state == 'inventory' else 'SPT diproses'
                metrics.append(f'{caption}: {counts.processed} / {counts.total}')
            if state.view_state == 'inventory' and counts.scanned is not None:
                metrics.append(f'Baris terbaca: {counts.scanned}')
            elif state.view_state != 'inventory' and counts.verified is not None:
                metrics.append(f'Lengkap: {counts.verified}')
                if counts.processed is not None:
                    metrics.append(f'Belum pasti lengkap: {counts.processed - counts.verified}')
        self.metric_text.set('\n'.join(metrics))
        is_form = state.view_state in ('idle', 'form_invalid') or state.terminal_status is not None
        if is_form:
            self.form.grid(row=0, column=0, sticky='ew')
            self.progress_panel.grid_remove()
        else:
            self.form.grid_remove()
            self.progress_panel.grid(row=0, column=0, sticky='ew')
        if state.terminal_status:
            self.result_panel.grid(row=1, column=0, sticky='ew', pady=(self.px(12), 0))
        else:
            self.result_panel.grid_remove()
        self.percent.set('—' if state.percent is None else f'{state.percent}%')
        if state.percent is None:
            if not self._indeterminate:
                self.bar.configure(mode='indeterminate')
                self.bar.start(20)
                self._indeterminate = True
        else:
            if self._indeterminate:
                self.bar.stop()
                self._indeterminate = False
            self.bar.configure(mode='determinate', value=state.percent)
        index = _STAGE_INDEX.get(state.stage, 0)
        if state.view_state in ('awaiting_selection', 'selection_submitted'):
            index = 1
        elif state.view_state in ('awaiting_overwrite', 'complete', 'empty_complete', 'partial'):
            index = 3
        for ordinal, label in enumerate(self.stage_labels):
            label.configure(style='SPT.ActiveStage.TLabel' if active and ordinal == index else 'SPT.Stage.TLabel')
        self.set_busy(active, stopping=state.view_state in ('stopping', 'cancellation_pending'))
        self.open_button.configure(text=copy_text('action.open_partial' if state.terminal_status == 'PARTIAL' else 'action.open_result'))
        can_open = bool(not active and state.output and state.terminal_status in ('COMPLETE', 'PARTIAL'))
        self.open_button.state(['!disabled' if can_open else 'disabled'])
        self.request_reflow()

    def set_busy(self, active: bool, *, stopping: bool = False) -> None:
        for widget in (self.start_button, self.settings_button, self.npwp_entry, self.year_entry):
            widget.state(['disabled' if active else '!disabled'])
        self.stop_button.state(['!disabled' if active and not stopping else 'disabled'])

    def show_errors(self, errors: Mapping[str, str]) -> None:
        for name, value, entry, (_, _, label) in zip(('npwp', 'year'),
                (self.npwp_error, self.year_error), (self.npwp_entry, self.year_entry), self._field_wrappers):
            value.set(copy_text(errors[name]) if name in errors else '')
            entry.state(['invalid' if name in errors else '!invalid'])
            if name in errors:
                label.grid()
            else:
                label.grid_remove()
        self.request_reflow()

    def request_reflow(self) -> None:
        if not self._disposed and self._reflow_after is None:
            self._reflow_after = self.after(75, self._reflow)

    @staticmethod
    def _wrap(label, width):
        width = max(80, int(width))
        if int(label.cget('wraplength') or 0) != width:
            label.configure(wraplength=width)

    @staticmethod
    def _priority_area(state: ExportState) -> str:
        if state.terminal_status is not None:
            return 'result'
        return 'form' if state.view_state in ('idle', 'form_invalid') else 'progress'

    def _reveal_priority(self):
        """Show the actual input, progress, or outcome when a compact viewport is short."""
        self._reveal_after = None
        priority, self._pending_reveal = self._pending_reveal, None
        if self._disposed or priority is None or self.canvas.winfo_height() <= 1:
            return
        if priority == 'result':
            start, end = self.result_title_label, self.result_status_label
        elif priority == 'progress':
            start, end = self.progress_title_label, self.bar
        else:
            start, end = self.npwp_label, self.npwp_entry
        if not start.winfo_ismapped() or not end.winfo_ismapped():
            return
        # Reflowed children have now settled; use the final scroll region.
        self._update_scrollregion()
        above = self.canvas.winfo_rooty()
        below = above + self.canvas.winfo_height()
        first, last = start.winfo_rooty(), end.winfo_rooty() + end.winfo_height()
        offset = self.canvas.canvasy(0)
        # If the compact summary title and the primary action fit together
        # at scroll position zero, keep both visible instead of clipping
        # the summary heading merely to add unnecessary bottom whitespace.
        if (priority in ('form', 'progress') and self.scope_title.winfo_ismapped()
                and self.window.winfo_width() / self.scale < 960
                and self.scope_title.winfo_rooty() + offset >= above
                and last + offset <= below):
            if offset > 0:
                self.canvas.yview_moveto(0)
            return
        if first >= above and last <= below:
            return
        height = max(0, last - first)
        margin = min(self.px(6), max(0, (self.canvas.winfo_height() - height) // 2))
        if last > below:
            shift = last - below + margin
        else:
            shift = first - above - margin
        extent = max(1, self.workspace.winfo_height())
        limit = max(0, extent - self.canvas.winfo_height())
        self.canvas.yview_moveto(min(limit, max(0, self.canvas.canvasy(0) + shift)) / extent)

    def _reflow(self):
        self._reflow_after = None
        if self._disposed or self.winfo_width() <= 1 or self.canvas.winfo_width() <= 1:
            return
        policy = layout_policy(self.window.winfo_width() / self.scale, 0)
        # Keep the usable viewport large enough for a field label and entry
        # even when Windows restores the minimum-size application window.
        tiny = policy.compact and self.window.winfo_height() / self.scale < 480
        padding = self.px(8 if tiny else (16 if policy.compact else 24))
        self.configure(padding=padding)
        available = self.canvas.winfo_width()
        self.canvas.itemconfigure(self._canvas_window, width=available)
        gap, summary_width = self.px(10 if policy.compact else policy.gap_dip), self.px(policy.summary_width_dip)
        main_width = available if policy.compact else max(1, available - summary_width - gap)
        content_width = max(self.px(160), main_width - self.px(24 if policy.compact else 32))
        policy = layout_policy(self.window.winfo_width() / self.scale, content_width / self.scale)
        geometry = (self.winfo_width(), self.winfo_height())
        if (self._last_geometry is not None
                and (self._last_compact != policy.compact
                     or geometry[1] < self._last_geometry[1] - self.px(12))):
            self._pending_reveal = self._priority_area(self._state)
        self._last_compact, self._last_geometry = policy.compact, geometry
        self.form.configure(padding=self.px(12 if policy.compact else 16))
        self.progress_panel.configure(padding=self.px(12 if policy.compact else 16))
        # Grid updates move mapped panels directly. Hiding them first remaps
        # every native child during otherwise unchanged status/layout updates.
        self.workspace.columnconfigure(0, weight=1)
        self.workspace.columnconfigure(1, weight=0, minsize=0 if policy.compact else summary_width)
        self.scope_panel.grid_propagate(policy.compact)
        self.scope_panel.configure(padding=self.px(8 if policy.compact else 16))
        self.scope_title.grid_configure(pady=(0, self.px(4 if policy.compact else 12)))
        for entry in (self.npwp_entry, self.year_entry):
            entry.grid_configure(pady=(0, self.px(4)) if policy.compact
                                 else (self.px(4), self.px(8)))
        for column in range(3):
            self.scope_panel.columnconfigure(column, weight=1 if policy.compact else (1 if column == 0 else 0))
        for ordinal, holder in enumerate(self._scope_holders):
            holder.grid(row=1 if policy.compact else ordinal + 1,
                        column=ordinal if policy.compact else 0, sticky='ew',
                        padx=(0, self.px(8)) if policy.compact and ordinal < 2 else (0, 0),
                        pady=(0, 0) if policy.compact else (0, self.px(8)))
        if policy.compact:
            self.scope_panel.grid(row=0, column=0, sticky='ew', pady=(0, gap))
            self.content_slot.grid(row=1, column=0, sticky='ew')
        else:
            self.scope_panel.configure(width=summary_width, height=1)
            self.content_slot.grid(row=0, column=0, sticky='ew', padx=(0, gap))
            self.scope_panel.grid(row=0, column=1, sticky='nsew')
        for column in range(4):
            self.stage_strip.columnconfigure(column, weight=1 if column < policy.stage_columns else 0)
        stage_width = max(80, (self.winfo_width() - 2 * padding) // policy.stage_columns - self.px(8))
        for ordinal, label in enumerate(self.stage_labels):
            label.grid(row=ordinal // policy.stage_columns, column=ordinal % policy.stage_columns, sticky='ew', padx=(0, self.px(8)))
            self._wrap(label, stage_width)
        self.fields.columnconfigure(0, weight=3)
        self.fields.columnconfigure(1, weight=0 if policy.form_stacked else 1)
        self.npwp_field.grid(row=0, column=0, sticky='ew', padx=(0, 0 if policy.form_stacked else self.px(16)))
        self.year_field.grid(row=1 if policy.form_stacked else 0, column=0 if policy.form_stacked else 1,
                             sticky='ew', pady=(self.px(12) if policy.form_stacked else 0, 0))
        for holder, helper, error in self._field_wrappers:
            width = holder.winfo_width() if holder.winfo_width() > 1 else content_width
            self._wrap(helper, width)
            self._wrap(error, width)
        for label in (self.form_title, self.form_help, self.progress_title_label, self.progress_help_label,
                       self.metrics_label, self.status_label, self.setup_hint, self.result_title_label, self.result_status_label):
            self._wrap(label, content_width)
        for label in self._scope_labels:
            width = ((available - self.px(20) - self.px(16)) // 3 if policy.compact
                     else summary_width - self.px(32))
            self._wrap(label, width)
        outer = self.winfo_width() - 2 * padding
        self._wrap(self.heading, outer - self.settings_button.winfo_reqwidth() - self.px(12))
        self._wrap(self.subtitle, outer)
        self._wrap(self.results_label, outer)
        self._wrap(self.bugreport_label, outer)
        action_width = sum(button.winfo_reqwidth() for button in self._actions) + self.px(16)
        for ordinal, button in enumerate(self._actions):
            wrap = action_width > outer and ordinal == 2
            button.grid(row=1 if wrap else 0, column=0 if wrap else ordinal, sticky='w',
                        padx=(0, self.px(8)), pady=(self.px(4) if wrap else 0, 0))
        self._update_scrollregion()
        if self._pending_reveal is not None and self._reveal_after is None:
            # Tk may still be arranging the newly re-gridded compact summary
            # during the next idle; reveal against its settled measurements.
            self._reveal_after = self.after(60, self._reveal_priority)

    def _update_scrollregion(self, event=None):
        if not self._disposed:
            self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def _wheel(self, event) -> str | None:
        if not self._disposed and (event.widget is self.canvas or str(event.widget).startswith(str(self.workspace))):
            self.canvas.yview_scroll(-int(event.delta / 120), 'units')
            return 'break'
        return None

    def _reveal_focus(self, event):
        if self._disposed or not str(event.widget).startswith(str(self.workspace)):
            return
        top = event.widget.winfo_rooty() - self.canvas.winfo_rooty()
        height = self.canvas.winfo_height()
        if top < 0 or top + event.widget.winfo_height() > height:
            total = max(1, self.workspace.winfo_height())
            target = self.canvas.canvasy(0) + top - self.px(8)
            self.canvas.yview_moveto(max(0, target / total))

    def _on_destroy(self, event):
        if event.widget is self:
            self.dispose()

    def dispose(self) -> None:
        if self._disposed:
            return
        self._disposed = True
        for callback in (self._reflow_after, self._reveal_after):
            if callback is not None:
                try:
                    self.after_cancel(callback)
                except tk.TclError:
                    # Widget destruction may already have removed this Tcl timer.
                    pass
        self._reflow_after = None
        self._reveal_after = None
        try:
            self.bar.stop()
            for sequence, identifier in self._root_bindings:
                self.window.unbind(sequence, identifier)
        except (tk.TclError, AttributeError):
            # The root may already be disposing its Tcl commands.
            pass
        self._root_bindings.clear()
