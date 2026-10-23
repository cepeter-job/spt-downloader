"""Native ttk presentation metrics, without changing process DPI awareness."""
import ctypes.wintypes
from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk


@dataclass(frozen=True)
class LayoutPolicy:
    compact: bool
    form_stacked: bool
    stage_columns: int
    summary_width_dip: int = 244
    gap_dip: int = 24


def layout_policy(client_width_dip: float, content_width_dip: float) -> LayoutPolicy:
    compact = client_width_dip < 960
    return LayoutPolicy(compact, content_width_dip < 560, 2 if compact else 4)


def dip_to_px(value: float, scale: float) -> int:
    return round(value * scale)


def effective_scale(root: tk.Misc) -> float:
    # This is the effective Tk scale, not proof of per-monitor DPI support.
    return root.winfo_fpixels('1i') / 96


def _window_work_metrics(window: tk.Misc, monitor_window: tk.Misc):
    """Measure the modal border independently from its owner's monitor."""
    class MonitorInfo(ctypes.Structure):
        _fields_ = [('size', ctypes.wintypes.DWORD), ('monitor', ctypes.wintypes.RECT),
                    ('work', ctypes.wintypes.RECT), ('flags', ctypes.wintypes.DWORD)]

    api = ctypes.WinDLL('user32', use_last_error=True)
    api.GetAncestor.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.UINT]
    api.GetAncestor.restype = ctypes.wintypes.HWND
    api.MonitorFromWindow.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.DWORD]
    api.MonitorFromWindow.restype = ctypes.wintypes.HANDLE
    api.GetMonitorInfoW.argtypes = [ctypes.wintypes.HANDLE, ctypes.POINTER(MonitorInfo)]
    api.GetMonitorInfoW.restype = ctypes.wintypes.BOOL
    for name in ('GetWindowRect', 'GetClientRect'):
        function = getattr(api, name)
        function.argtypes = [ctypes.wintypes.HWND, ctypes.POINTER(ctypes.wintypes.RECT)]
        function.restype = ctypes.wintypes.BOOL
    hwnd = api.GetAncestor(window.winfo_id(), 2)
    owner = api.GetAncestor(monitor_window.winfo_id(), 2)
    monitor = api.MonitorFromWindow(owner, 2)
    info = MonitorInfo()
    info.size = ctypes.sizeof(info)
    outer, inner, parent = (ctypes.wintypes.RECT() for _ in range(3))
    if (not hwnd or not owner or not monitor or not api.GetMonitorInfoW(monitor, ctypes.byref(info))
            or not api.GetWindowRect(hwnd, ctypes.byref(outer))
            or not api.GetClientRect(hwnd, ctypes.byref(inner))
            or not api.GetWindowRect(owner, ctypes.byref(parent))):
        raise OSError('Windows work area could not be measured')
    border_width = max(0, outer.right - outer.left - (inner.right - inner.left))
    border_height = max(0, outer.bottom - outer.top - (inner.bottom - inner.top))
    work = (info.work.left, info.work.top, info.work.right, info.work.bottom)
    if work[2] - work[0] <= border_width or work[3] - work[1] <= border_height:
        raise OSError('Windows reported an invalid client work area')
    owner_rect = (parent.left, parent.top, parent.right, parent.bottom)
    return api, hwnd, work, owner_rect, border_width, border_height


def client_work_area(window: tk.Tk | tk.Toplevel, *, monitor_window: tk.Misc | None = None) -> tuple[int, int]:
    """Use measured borders; never guess the taskbar or titlebar size."""
    _, _, work, _, border_width, border_height = _window_work_metrics(
        window, window if monitor_window is None else monitor_window)
    return work[2] - work[0] - border_width, work[3] - work[1] - border_height


def configure_dialog(dialog: tk.Toplevel, parent: tk.Tk, *, size_dip: tuple[int, int]) -> float:
    """Apply native modal metrics without reconfiguring its owner's shell."""
    scale = effective_scale(parent)
    style = ttk.Style(dialog)
    linespace = int(parent.tk.call('font', 'metrics', 'SPTBody', '-linespace'))
    style.configure('SPT.Dialog.Treeview', font='SPTBody', rowheight=linespace + dip_to_px(8, scale))
    style.configure('SPT.Dialog.Treeview.Heading', font='SPTLabel')
    dialog.update_idletasks()
    try:
        available_width, available_height = client_work_area(dialog, monitor_window=parent)
        api, hwnd, work, owner, border_width, border_height = _window_work_metrics(dialog, parent)
    except (OSError, AttributeError):
        # Keep the window manager's geometry when native measurement is unavailable.
        return scale
    width = min(dip_to_px(size_dip[0], scale), available_width)
    height = min(dip_to_px(size_dip[1], scale), available_height)
    dialog.minsize(min(dip_to_px(540, scale), available_width),
                   min(dip_to_px(390, scale), available_height))
    dialog.geometry(f'{width}x{height}')
    dialog.update_idletasks()
    outer_width, outer_height = width + border_width, height + border_height
    x = min(max(work[0], (owner[0] + owner[2] - outer_width) // 2), work[2] - outer_width)
    y = min(max(work[1], (owner[1] + owner[3] - outer_height) // 2), work[3] - outer_height)
    # Tk's negative geometry offsets mean right/bottom anchoring, not virtual
    # screen coordinates. Native positioning supports monitors left of primary.
    api.SetWindowPos.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.HWND,
        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.wintypes.UINT]
    api.SetWindowPos.restype = ctypes.wintypes.BOOL
    api.SetWindowPos(hwnd, None, x, y, 0, 0, 0x0001 | 0x0004 | 0x0010)
    return scale


def configure_theme(root: tk.Tk) -> None:
    style = ttk.Style(root)
    if 'vista' in style.theme_names():
        style.theme_use('vista')
    names = set(root.tk.splitlist(root.tk.call('font', 'names')))
    family = root.tk.call('font', 'actual', 'TkDefaultFont', '-family')
    if 'Segoe UI' in root.tk.splitlist(root.tk.call('font', 'families')):
        family = 'Segoe UI'
    for name, size, weight in [('SPTBody', 11, 'normal'), ('SPTLabel', 11, 'bold'),
                                ('SPTCaption', 9, 'normal'), ('SPTContact', 12, 'normal'),
                                ('SPTHeading', 14, 'bold'),
                                ('SPTTitle', 18, 'bold')]:
        # Tcl-owned named fonts survive this function without Python Font GC.
        root.tk.call('font', 'configure' if name in names else 'create', name,
                     '-family', family, '-size', size, '-weight', weight)
    scale = effective_scale(root)
    style.configure('SPT.Shell.TFrame', background='SystemButtonFace')
    style.configure('SPT.Card.TFrame', background='SystemWindow')
    for name, font in [('SPT.TLabel', 'SPTBody'), ('SPT.Label.TLabel', 'SPTLabel'),
                       ('SPT.Caption.TLabel', 'SPTCaption'), ('SPT.Heading.TLabel', 'SPTHeading'),
                       ('SPT.Error.TLabel', 'SPTBody')]:
        style.configure(name, font=font, background='SystemWindow', foreground='SystemWindowText')
    style.configure('Title.TLabel', font='SPTTitle', background='SystemButtonFace', foreground='SystemWindowText')
    style.configure('SPT.Stage.TLabel', font='SPTCaption', background='SystemButtonFace', foreground='SystemWindowText')
    style.configure('SPT.Contact.TLabel', font='SPTContact', background='SystemButtonFace', foreground='SystemWindowText')
    style.configure('SPT.ActiveStage.TLabel', font='SPTLabel', background='SystemButtonFace', foreground='SystemHighlight')
    style.configure('SPT.TButton', font='SPTBody', padding=(dip_to_px(12, scale), dip_to_px(8, scale)))
    style.configure('SPT.Primary.TButton', font='SPTLabel', padding=(dip_to_px(12, scale), dip_to_px(8, scale)))
    style.configure('SPT.TEntry', font='SPTBody', padding=dip_to_px(8, scale))
    root.update_idletasks()
    try:
        available_width, available_height = client_work_area(root)
    except (OSError, AttributeError):
        # Keep window-manager geometry if native measurement is unavailable.
        return
    width, height = root.winfo_width(), root.winfo_height()
    if width <= 200 and height <= 200:
        width, height = dip_to_px(1120, scale), dip_to_px(800, scale)
    root.minsize(min(dip_to_px(540, scale), available_width),
                 min(dip_to_px(390, scale), available_height))
    root.geometry(f'{min(width, available_width)}x{min(height, available_height)}')
