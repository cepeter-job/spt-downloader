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


def client_work_area(root: tk.Tk) -> tuple[int, int]:
    """Use measured window borders; never guess the taskbar or titlebar size."""
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
    hwnd = api.GetAncestor(root.winfo_id(), 2)  # GA_ROOT includes native non-client borders.
    monitor = api.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST.
    info = MonitorInfo()
    info.size = ctypes.sizeof(info)
    outer, inner = ctypes.wintypes.RECT(), ctypes.wintypes.RECT()
    if (not hwnd or not monitor or not api.GetMonitorInfoW(monitor, ctypes.byref(info))
            or not api.GetWindowRect(hwnd, ctypes.byref(outer))
            or not api.GetClientRect(hwnd, ctypes.byref(inner))):
        raise OSError('Windows work area could not be measured')
    border_width = max(0, outer.right - outer.left - (inner.right - inner.left))
    border_height = max(0, outer.bottom - outer.top - (inner.bottom - inner.top))
    width = info.work.right - info.work.left - border_width
    height = info.work.bottom - info.work.top - border_height
    if width <= 0 or height <= 0:
        raise OSError('Windows reported an invalid client work area')
    return width, height


def configure_theme(root: tk.Tk) -> None:
    style = ttk.Style(root)
    if 'vista' in style.theme_names():
        style.theme_use('vista')
    names = set(root.tk.splitlist(root.tk.call('font', 'names')))
    family = root.tk.call('font', 'actual', 'TkDefaultFont', '-family')
    if 'Segoe UI' in root.tk.splitlist(root.tk.call('font', 'families')):
        family = 'Segoe UI'
    for name, size, weight in [('SPTBody', 11, 'normal'), ('SPTLabel', 11, 'bold'),
                                ('SPTCaption', 9, 'normal'), ('SPTHeading', 14, 'bold'),
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
