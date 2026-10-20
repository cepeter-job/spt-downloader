"""Temporary, synthetic Windows evidence; never shipped in the application."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
import math
from pathlib import Path
import statistics
import struct
import subprocess
import sys
import tempfile
import time
import traceback
import zlib


BASELINE = '977b06846554ca1f2e5af512a69fb201f2cbe8d1'
CANDIDATE = '7475d89c85db4730270fefcd41f18291b9ba75b9'


class Rect(C.Structure):
    _fields_ = [('left', W.LONG), ('top', W.LONG), ('right', W.LONG), ('bottom', W.LONG)]


class MonitorInfo(C.Structure):
    _fields_ = [('size', W.DWORD), ('monitor', Rect), ('work', Rect), ('flags', W.DWORD)]


class BitmapHeader(C.Structure):
    _fields_ = [('size', W.DWORD), ('width', W.LONG), ('height', W.LONG),
                ('planes', W.WORD), ('bits', W.WORD), ('compression', W.DWORD),
                ('image_size', W.DWORD), ('xppm', W.LONG), ('yppm', W.LONG),
                ('used', W.DWORD), ('important', W.DWORD)]


class BitmapInfo(C.Structure):
    _fields_ = [('header', BitmapHeader), ('colors', W.DWORD * 1)]


def api():
    u, g, s = (C.WinDLL(name, use_last_error=True) for name in ('user32', 'gdi32', 'shcore'))
    signatures = {
        'GetAncestor': ([W.HWND, W.UINT], W.HWND),
        'GetWindowRect': ([W.HWND, C.POINTER(Rect)], W.BOOL),
        'GetClientRect': ([W.HWND, C.POINTER(Rect)], W.BOOL),
        'GetWindowDC': ([W.HWND], W.HDC),
        'GetDC': ([W.HWND], W.HDC),
        'ReleaseDC': ([W.HWND, W.HDC], C.c_int),
        'PrintWindow': ([W.HWND, W.HDC, W.UINT], W.BOOL),
        'MonitorFromWindow': ([W.HWND, W.DWORD], W.HANDLE),
        'GetMonitorInfoW': ([W.HANDLE, C.POINTER(MonitorInfo)], W.BOOL),
        'GetDpiForWindow': ([W.HWND], W.UINT),
        'GetWindowDpiAwarenessContext': ([W.HWND], W.HANDLE),
        'GetAwarenessFromDpiAwarenessContext': ([W.HANDLE], C.c_int),
        'SetForegroundWindow': ([W.HWND], W.BOOL),
        'GetForegroundWindow': ([], W.HWND),
        'GetThreadDpiAwarenessContext': ([], W.HANDLE),
        'SetWindowPos': ([W.HWND, W.HWND, C.c_int, C.c_int, C.c_int, C.c_int, W.UINT], W.BOOL),
    }
    for name, (args, result) in signatures.items():
        getattr(u, name).argtypes, getattr(u, name).restype = args, result
    for name, args, result in (
        ('CreateCompatibleDC', [W.HDC], W.HDC),
        ('CreateCompatibleBitmap', [W.HDC, C.c_int, C.c_int], W.HBITMAP),
        ('SelectObject', [W.HDC, W.HGDIOBJ], W.HGDIOBJ),
        ('DeleteObject', [W.HGDIOBJ], W.BOOL), ('DeleteDC', [W.HDC], W.BOOL),
        ('GetDIBits', [W.HDC, W.HBITMAP, W.UINT, W.UINT, C.c_void_p, C.POINTER(BitmapInfo), W.UINT], C.c_int),
        ('BitBlt', [W.HDC, C.c_int, C.c_int, C.c_int, C.c_int, W.HDC, C.c_int, C.c_int, W.DWORD], W.BOOL),
    ):
        getattr(g, name).argtypes, getattr(g, name).restype = args, result
    s.GetScaleFactorForMonitor.argtypes = [W.HANDLE, C.POINTER(C.c_int)]
    s.GetScaleFactorForMonitor.restype = C.c_long
    return u, g, s


def rect_values(rect):
    return [rect.left, rect.top, rect.right, rect.bottom]


def native(window):
    u, _, s = api()
    hwnd = u.GetAncestor(window.winfo_id(), 2)
    outer, client, monitor = Rect(), Rect(), MonitorInfo()
    monitor.size = C.sizeof(monitor)
    assert u.GetWindowRect(hwnd, C.byref(outer))
    assert u.GetClientRect(hwnd, C.byref(client))
    hmon = u.MonitorFromWindow(hwnd, 2)
    assert u.GetMonitorInfoW(hmon, C.byref(monitor))
    scale = C.c_int()
    hr = s.GetScaleFactorForMonitor(hmon, C.byref(scale))
    context = u.GetWindowDpiAwarenessContext(hwnd)
    physical = Rect()
    dwm = C.WinDLL('dwmapi')
    dwm.DwmGetWindowAttribute.argtypes = [W.HWND, W.DWORD, C.c_void_p, W.DWORD]
    physical_hr = dwm.DwmGetWindowAttribute(hwnd, 9, C.byref(physical), C.sizeof(physical))
    return {
        'native_dpi': u.GetDpiForWindow(hwnd),
        'awareness': u.GetAwarenessFromDpiAwarenessContext(context),
        'monitor_scale_percent': scale.value if hr == 0 else None,
        'monitor_scale_hresult': hr, 'outer_rect': rect_values(outer),
        'native_client_px': [client.right, client.bottom],
        'client_px': [window.winfo_width(), window.winfo_height()],
        'work_area': rect_values(monitor.work), 'monitor_rect': rect_values(monitor.monitor),
        'physical_frame_rect': rect_values(physical) if physical_hr == 0 else None,
        'tk_scaling': float(window.tk.call('tk', 'scaling')),
        'effective_scale': float(window.winfo_fpixels('1i') / 96),
    }


def capture_desktop(args):
    """Only this standalone helper opts into DPI awareness; it never imports Tk/product code."""
    u = C.WinDLL('user32', use_last_error=True)
    u.SetProcessDpiAwarenessContext.argtypes = [W.HANDLE]
    u.SetProcessDpiAwarenessContext.restype = W.BOOL
    if not u.SetProcessDpiAwarenessContext(C.c_void_p(-4)):
        raise C.WinError(C.get_last_error())
    u, g, _ = api()
    awareness = u.GetAwarenessFromDpiAwarenessContext(u.GetThreadDpiAwarenessContext())
    assert awareness == 2, ('capture helper is not per-monitor aware', awareness)
    hwnd, path = args.capture_desktop, Path(args.out)
    outer, frame, monitor = Rect(), Rect(), MonitorInfo()
    monitor.size = C.sizeof(monitor)
    assert u.GetWindowRect(hwnd, C.byref(outer))
    assert u.GetMonitorInfoW(u.MonitorFromWindow(hwnd, 2), C.byref(monitor))
    dwm = C.WinDLL('dwmapi')
    dwm.DwmGetWindowAttribute.argtypes = [W.HWND, W.DWORD, C.c_void_p, W.DWORD]
    dwm.DwmGetWindowAttribute.restype = C.c_long
    frame_hr = dwm.DwmGetWindowAttribute(hwnd, 9, C.byref(frame), C.sizeof(frame))
    dwm.DwmFlush.restype = C.c_long
    flush_hr = dwm.DwmFlush()
    rect = monitor.monitor
    width, height = rect.right - rect.left, rect.bottom - rect.top
    assert 100 < width <= 8192 and 100 < height <= 4320, (width, height)
    src = u.GetDC(None)
    dc = g.CreateCompatibleDC(src)
    bitmap = g.CreateCompatibleBitmap(src, width, height)
    assert src and dc and bitmap
    old = g.SelectObject(dc, bitmap)
    try:
        assert g.BitBlt(dc, 0, 0, width, height, src, rect.left, rect.top, 0x40CC0020), C.get_last_error()
        # GetDIBits requires the bitmap to be deselected from its DC.
        g.SelectObject(dc, old)
        info = BitmapInfo()
        info.header.size, info.header.width, info.header.height = C.sizeof(BitmapHeader), width, -height
        info.header.planes, info.header.bits = 1, 32
        buffer = C.create_string_buffer(width * height * 4)
        assert g.GetDIBits(dc, bitmap, 0, height, buffer, C.byref(info), 0) == height
        raw = buffer.raw
        colors = len({raw[i:i+3] for i in range(0, len(raw), max(4, len(raw)//28000*4))})
        assert colors > 8, ('blank capture', colors)
        rgba = bytearray(raw)
        rgba[0::4], rgba[2::4], rgba[3::4] = raw[2::4], raw[0::4], bytes([255]) * (width * height)
        stride = width * 4
        rows = b''.join(b'\0' + rgba[y*stride:(y+1)*stride] for y in range(height))
        def chunk(kind, data):
            return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind+data) & 0xffffffff)
        data = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>2I5B', width, height, 8, 6, 0, 0, 0))
                + chunk(b'IDAT', zlib.compress(rows, 6)) + chunk(b'IEND', b''))
        path.write_bytes(data)
        visible = frame if frame_hr == 0 else outer
        def contained(inner, bounds):
            return (inner.left >= bounds.left and inner.top >= bounds.top and
                    inner.right <= bounds.right and inner.bottom <= bounds.bottom)
        result = {'filename': path.name, 'sha256': hashlib.sha256(data).hexdigest(),
                  'image_px': [width, height], 'image_origin_px': [rect.left, rect.top],
                  'colors_sampled': colors, 'method': 'DPI-aware helper desktop BitBlt',
                  'capture_helper_awareness': awareness, 'target_awareness':
                  u.GetAwarenessFromDpiAwarenessContext(u.GetWindowDpiAwarenessContext(hwnd)),
                  'physical_outer_rect': rect_values(outer),
                  'physical_frame_rect': rect_values(frame) if frame_hr == 0 else None,
                  'physical_monitor_rect': rect_values(monitor.monitor),
                  'physical_work_area': rect_values(monitor.work),
                  'window_outside_monitor': not contained(visible, monitor.monitor),
                  'window_outside_work_area': not contained(visible, monitor.work),
                  'target_is_foreground': u.GetForegroundWindow() == hwnd,
                  'dwm_frame_hresult': frame_hr, 'dwm_flush_hresult': flush_hr}
        print(json.dumps(result), flush=True)
    finally:
        g.SelectObject(dc, old)
        g.DeleteObject(bitmap)
        g.DeleteDC(dc)
        u.ReleaseDC(None, src)


def capture(window, path):
    u, _, _ = api()
    hwnd = u.GetAncestor(window.winfo_id(), 2)
    window.lift()
    u.SetForegroundWindow(hwnd)
    window.update_idletasks()
    window.update()
    command = [sys.executable, str(Path(__file__).resolve()), '--capture-desktop', str(hwnd),
               '--out', str(path.resolve())]
    completed = subprocess.run(command, capture_output=True, text=True, encoding='utf-8',
                               errors='replace', timeout=30, check=False)
    if completed.returncode:
        raise RuntimeError(f'Physical capture helper failed: {completed.stderr[-3000:]}')
    return json.loads(completed.stdout)


def fit_to_work_area(window, requested_px):
    """Clamp in the unchanged product process's logical coordinate space."""
    metrics = native(window)
    outer, work, client = metrics['outer_rect'], metrics['work_area'], metrics['native_client_px']
    borders = [outer[2] - outer[0] - client[0], outer[3] - outer[1] - client[1]]
    available = [max(1, work[2] - work[0] - borders[0]), max(1, work[3] - work[1] - borders[1])]
    target = [min(requested_px[i], available[i]) for i in range(2)]
    window.geometry(f'{target[0]}x{target[1]}')
    window.update_idletasks()
    actual = native(window)['outer_rect']
    x = min(max(work[0], actual[0]), work[2] - (actual[2] - actual[0]))
    y = min(max(work[1], actual[1]), work[3] - (actual[3] - actual[1]))
    u, _, _ = api()
    assert u.SetWindowPos(u.GetAncestor(window.winfo_id(), 2), None, x, y, 0, 0, 0x0015)
    return {'requested_client_px': list(requested_px), 'maximum_client_px': available,
            'clamped_client_px': target, 'logical_work_area': work, 'measured_border_px': borders}


def children(widget):
    for child in widget.winfo_children():
        yield child
        yield from children(child)


def named(dialog, name):
    matches = [w for w in children(dialog) if w.winfo_name() == name]
    assert len(matches) == 1, (name, len(matches))
    return matches[0]


def table(dialog):
    return next(w for w in children(dialog) if w.winfo_class() == 'Treeview')


def search(dialog):
    return next(w for w in children(dialog) if w.winfo_class() == 'TEntry')


def bounds(widget):
    return [widget.winfo_rootx(), widget.winfo_rooty(), widget.winfo_width(), widget.winfo_height()]


def geometry_signature(dialog):
    result = []
    if dialog is not None and dialog.winfo_exists():
        for w in [dialog, *children(dialog)]:
            row = [str(w), w.winfo_x(), w.winfo_y(), w.winfo_width(), w.winfo_height(),
                   w.winfo_reqwidth(), w.winfo_reqheight()]
            if w.winfo_class() == 'Canvas':
                row += [str(w.cget('scrollregion')), str(w.yview())]
            result.append(tuple(row))
    return tuple(result)


def settle(root, app, started=None):
    """Stop at stable modal geometry/owned timer completion, not a fixed sleep."""
    started = time.perf_counter_ns() if started is None else started
    last_change, previous, quiet = started, None, 0
    deadline = time.perf_counter() + 5
    while time.perf_counter() < deadline:
        root.update_idletasks()
        root.update()
        interaction = app._interaction
        dialog = interaction['dialog'] if interaction else None
        pending = interaction.get('layout_after') if interaction else None
        state = (geometry_signature(dialog), pending)
        now = time.perf_counter_ns()
        if state != previous:
            previous, last_change, quiet = state, now, 0
        elif not pending:
            quiet += 1
        if quiet >= 3:
            return (last_change - started) / 1e6
        time.sleep(.001)
    raise RuntimeError('Modal layout did not stabilize within 5 seconds')


class Controller:
    active = False
    operation = 'export'
    job_id = 'synthetic-job'

    def __init__(self, payload):
        self.payload, self.replies, self.stops = payload, [], []

    def start(self, *args, detail_source='dom'):
        assert not self.active
        self.active = True
        return self.job_id

    def poll(self):
        return self.active

    def read_request(self, event):
        assert event['job_id'] == self.job_id
        return self.payload

    def respond(self, kind, request_id, payload):
        self.replies.append([kind, request_id, payload])
        return True

    def stop(self):
        self.stops.append(time.perf_counter_ns())

    def close(self):
        self.active = False


def event(controller, kind):
    return {'job_id': controller.job_id, 'type': kind + '_required', 'request_id': 'a' * 32,
            'stage': kind, 'percent': 20 if kind == 'selection' else 99,
            'message': 'Synthetic diagnostic consent'}


def payload_for(kind, count):
    if kind == 'overwrite':
        paths = [f'SPT Masa PPN/SYNTHETIC_{i:04d}_' + ('long_literal_Ω_資料_' * 12) + '_Normal.xlsx'
                 for i in range(100)]
        paths.append(paths[0])
        return {'folder': '  C:\\Users\\SYNTHETIC_USER\\Downloads\\' + 'Long literal folder Ω\\' * 12 + 'EXPORT  ',
                'files': paths}
    types = ('PPh Badan', 'PPh Pasal 21/26', 'PPh Unifikasi', 'PPN')
    return {'records': [
        {'record_id': ('SYNTHETIC-' + 'x' * 502) if i == 0 else f'::synthetic {{{i:04d}}}; [literal] / Ω',
         'meta': {'Jenis Pajak': types[i % 4], 'Masa Pajak': f'{i % 12 + 1:02d}/2025',
                  'Model SPT': 'Normal' if i % 3 == 0 else f'Pembetulan {i % 3}'}}
        for i in range(count)]}


@contextmanager
def session(payload):
    import tkinter as tk
    from spt_desktop.app import App
    errors = []
    with tempfile.TemporaryDirectory(prefix='p2-synthetic-') as td:
        root = tk.Tk()
        root.report_callback_exception = lambda *info: errors.append(str(info[1]))
        controller = Controller(payload)
        app = App(root, Path(td), controller=controller)
        try:
            fit_to_work_area(root, (1000, 740))
            root.deiconify()
            app.npwp.set('0000000000000001')
            app.year.set('2025')
            app.start()
            settle(root, app)
            yield root, app, controller
            assert not errors, errors
        finally:
            app._close_interaction()
            app._dispose()
            controller.close()
            for token in root.tk.splitlist(root.tk.call('after', 'info')):
                root.after_cancel(token)
            root.destroy()


def measure(root, app, action):
    start = time.perf_counter_ns()
    action()
    handler = (time.perf_counter_ns() - start) / 1e6
    return max(handler, settle(root, app, start)), handler


def environment(root, dialog, revision):
    return {'revision': revision, 'python': sys.version, 'tcl': root.tk.call('info', 'patchlevel'),
            'tk': root.tk.call('package', 'provide', 'Tk'), **native(dialog),
            'synthetic': True, 'portal_accessed': False, 'credentials_accessed': False}


def operation(root, app, controller, kind, name):
    if name == 'open':
        return lambda: app.on_event(event(controller, kind))
    dialog = app._interaction['dialog']
    if name == 'filter':
        return lambda: root.setvar(str(search(dialog).cget('textvariable')), 'PPN')
    return lambda: root.tk.call(table(dialog).heading('type', 'command'))


def benchmark(revision, results, checkpoint):
    for kind, count in [('selection', 1), ('selection', 100), ('selection', 1000), ('overwrite', 101)]:
        payload = payload_for(kind, count)
        names = ['open', 'filter', 'sort'] if kind == 'selection' else ['open']
        for name in names:
            samples, handlers, cancel_samples, cancel_late = [], [], [], []
            for repeat in range(11):
                with session(payload) as (root, app, controller):
                    if name != 'open':
                        app.on_event(event(controller, kind))
                        settle(root, app)
                    duration, handler = measure(root, app, operation(root, app, controller, kind, name))
                    meta = environment(root, app._interaction['dialog'], revision)
                    if repeat:
                        samples.append(duration)
                        handlers.append(handler)
                # A separate cancellation trial must not truncate the layout sample.
                with session(payload) as (root, app, controller):
                    if name != 'open':
                        app.on_event(event(controller, kind))
                        settle(root, app)
                    start = time.perf_counter_ns()
                    root.after(1, app.stop)
                    operation(root, app, controller, kind, name)()
                    deadline = time.perf_counter() + 5
                    while not controller.stops and time.perf_counter() < deadline:
                        root.update()
                    assert controller.stops and not controller.replies
                    assert app._interaction is None
                    delay = (controller.stops[0] - start) / 1e6
                    if repeat:
                        cancel_samples.append(delay)
                        cancel_late.append(max(0, delay - 1))
            record = {**meta, 'dialog': kind, 'inventory_size': count,
                      'payload_bytes': len(json.dumps(payload, ensure_ascii=False).encode()),
                      'payload_sha256': hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest(),
                      'operation': name, 'warmup_excluded': 1, 'samples_ms': samples,
                      'handler_ms': handlers, 'median_ms': statistics.median(samples),
                      'p95_ms': sorted(samples)[math.ceil(.95 * len(samples)) - 1], 'max_ms': max(samples),
                      'cancel_service_ms': cancel_samples, 'cancel_lateness_ms': cancel_late,
                      'repeated_over_100ms': sum(value > 100 for value in samples) >= 2,
                      'cancel_repeated_over_100ms': sum(value > 100 for value in cancel_samples) >= 2}
            results.append(record)
            checkpoint()
            print(json.dumps({k: record[k] for k in ('revision', 'dialog', 'inventory_size', 'operation', 'median_ms', 'max_ms')}), flush=True)
    return results


def key(root, app, sequence, **kwargs):
    focused = root.focus_get()
    assert focused is not None
    focused.event_generate(sequence, **kwargs)
    settle(root, app)


def focus(root, app, widget):
    u, _, _ = api()
    u.SetForegroundWindow(u.GetAncestor(widget.winfo_id(), 2))
    widget.focus_force()
    settle(root, app)


def traversal(root, app, dialog, start):
    seen = {'forward': [], 'reverse': []}
    for direction, sequence in [('forward', '<Tab>'), ('reverse', '<Shift-Tab>')]:
        focus(root, app, start)
        for _ in range(16):
            current = root.focus_get()
            seen[direction].append(current.winfo_name() if current else None)
            key(root, app, sequence)
    return seen


def inside(widget, container):
    x, y, width, height = bounds(widget)
    cx, cy, cw, ch = bounds(container)
    return x >= cx and y >= cy and x + width <= cx + cw and y + height <= cy + ch


def focus_identity(root):
    widget = root.focus_get()
    if widget is None:
        return None
    return {'path': str(widget), 'name': widget.winfo_name(), 'class': widget.winfo_class(),
            'exists': bool(widget.winfo_exists()),
            'disabled': bool(widget.instate(['disabled'])) if hasattr(widget, 'instate') else False}


def visuals(out, revision, frames, checks, checkpoint):
    for kind in ('selection', 'overwrite'):
        sizes = [(920, 600) if kind == 'selection' else (800, 520), (640, 560), (540, 390)]
        for case_index, size in enumerate(sizes):
            with session(payload_for(kind, 100)) as (root, app, controller):
                app.on_event(event(controller, kind))
                settle(root, app)
                dialog = app._interaction['dialog']
                root_before = root.geometry()
                scale = dialog.winfo_fpixels('1i') / 96
                requested = [round(value * scale) for value in size]
                geometry_plan = {'geometry_policy': 'product-default', 'requested_client_px': requested}
                if case_index:
                    geometry_plan = {'geometry_policy': 'requested-size-clamped-to-work-area',
                                     **fit_to_work_area(dialog, requested)}
                settle(root, app)
                def snap(state):
                    name = f'{kind}-{size[0]}x{size[1]}-{state}.png'
                    shot = capture(dialog, out/name)
                    viewport = named(dialog, 'body_viewport')
                    messages = {}
                    for widget in children(dialog):
                        if widget.winfo_name() in ('summary', 'notice'):
                            variable = str(widget.cget('textvariable'))
                            messages[widget.winfo_name()] = {
                                'text': str(widget.getvar(variable)) if variable else str(widget.cget('text')),
                                'bounds': bounds(widget), 'inside_body_viewport': inside(widget, viewport)}
                    frames.append({'state': state, 'dialog': kind, 'requested_dip': size,
                                   **geometry_plan, 'actual_client_px': [dialog.winfo_width(), dialog.winfo_height()],
                                   **environment(root, dialog, revision), **shot,
                                   'body_yview': list(viewport.yview()), 'messages': messages,
                                   'focus': focus_identity(root),
                                   'widgets': {w.winfo_name(): bounds(w) for w in children(dialog)
                                               if w.winfo_name() in ('actions', 'body_viewport', 'search', 'records',
                                                                    'focused_id', 'folder', 'files', 'confirm', 'stop',
                                                                    'decline', 'summary', 'notice')}})
                    checkpoint()
                def snap_bottom(state):
                    viewport = named(dialog, 'body_viewport')
                    previous = viewport.yview()[0]
                    viewport.yview_moveto(1)
                    settle(root, app)
                    snap(state + '-body-bottom')
                    viewport.yview_moveto(previous)
                    settle(root, app)
                row = {'dialog': kind, 'requested_dip': size, **geometry_plan,
                       'actual_client_px': [dialog.winfo_width(), dialog.winfo_height()],
                       'root_unchanged': root.geometry() == root_before}
                row['actions_inside_client'] = all(inside(named(dialog, name), dialog)
                                                  for name in (('confirm', 'stop') if kind == 'selection' else ('confirm', 'decline')))
                if kind == 'selection':
                    tree = named(dialog, 'records')
                    entry = named(dialog, 'search')
                    snap('initial')
                    focus(root, app, tree)
                    ids = tree.get_children()
                    # Pointer/class bindings perform actual extended selection, not selection_set.
                    for index, state in [(0, 0), (2, 4)]:
                        tree.see(ids[index])
                        settle(root, app)
                        x, y, w, h = tree.bbox(ids[index])
                        tree.event_generate('<ButtonPress-1>', x=x+15, y=y+h//2, state=state)
                        tree.event_generate('<ButtonRelease-1>', x=x+15, y=y+h//2, state=state)
                        settle(root, app)
                    chosen = set(tree.selection())
                    row['ctrl_click_multi_select'] = len(chosen) == 2
                    snap('multi-select')
                    before = tree.focus()
                    key(root, app, '<KeyPress-Down>')
                    key(root, app, '<KeyRelease-Down>')
                    row['native_navigation_updates_id'] = (tree.focus() != before and
                        named(dialog, 'focused_id').get() == tree.set(tree.focus(), 'identifier'))
                    row['selection_after_native_down'] = list(tree.selection())
                    row['traversal'] = traversal(root, app, dialog, entry)
                    required = {'search', 'records', 'focused_id', 'stop', 'confirm'}
                    row['all_enabled_actions_in_tab_cycle'] = all(required <= set(v) for v in row['traversal'].values())
                    focus(root, app, entry)
                    sort_before = tree.heading('type', 'text')
                    chosen = set(tree.selection())
                    key(root, app, '<Alt-j>')
                    row['alt_j_preserves_selection'] = tree.heading('type', 'text') != sort_before and set(tree.selection()) == chosen
                    root.setvar(str(entry.cget('textvariable')), 'PPN')
                    settle(root, app)
                    row['search_clears_selection'] = not tree.selection() and named(dialog, 'confirm').instate(['disabled'])
                    snap('search-reset')
                    snap_bottom('search-reset')
                    root.setvar(str(entry.cget('textvariable')), 'no-synthetic-match-zzzz')
                    settle(root, app)
                    snap('no-match')
                    snap_bottom('no-match')
                    root.setvar(str(entry.cget('textvariable')), '')
                    settle(root, app)
                    tree.focus('record-0')
                    tree.see('record-0')
                    focus(root, app, tree)
                    tree.event_generate('<KeyRelease>')
                    settle(root, app)
                    field = named(dialog, 'focused_id')
                    focus(root, app, field)
                    field.xview_moveto(1)
                    settle(root, app)
                    row['long_id_literal'] = field.get() == controller.payload['records'][0]['record_id']
                    snap('long-id-suffix')
                    key(root, app, '<Escape>')
                    row['escape_stops_without_reply'] = bool(controller.stops) and not controller.replies and app._interaction is None
                else:
                    row['initial_focus_decline'] = root.focus_get() == named(dialog, 'decline')
                    snap('long-folder-paths')
                    field, tree = named(dialog, 'folder'), named(dialog, 'files')
                    row['folder_literal'] = field.get() == controller.payload['folder']
                    row['all_paths_literal'] = [tree.set(iid, 'file') for iid in tree.get_children()] == controller.payload['files']
                    row['traversal'] = traversal(root, app, dialog, field)
                    row['all_enabled_actions_in_tab_cycle'] = all({'folder', 'files', 'decline', 'confirm'} <= set(v)
                                                                for v in row['traversal'].values())
                    focus(root, app, field)
                    field.xview_moveto(1)
                    tree.xview_moveto(1)
                    tree.yview_moveto(1)
                    settle(root, app)
                    row['suffix_scrolling_reaches_end'] = tree.xview()[1] >= .999 and tree.yview()[1] >= .999
                    snap('long-path-suffix')
                    focus(root, app, named(dialog, 'decline'))
                    snap('decline-focused')
                    key(root, app, '<Return>')
                    row['decline_false_once'] = (len(controller.replies) == 1 and controller.replies[0][2] == {'overwrite': False}
                                                 and not controller.stops and app._interaction is None)
                row['no_grab_after_close'] = root.grab_current() is None
                checks.append(row)
                checkpoint()
    return frames, checks


def close_checks(checks, checkpoint):
    import _tkinter
    for kind in ('selection', 'overwrite'):
        for action in ('window-close', 'alt-s', 'terminal-pending-reflow'):
            with session(payload_for(kind, 20)) as (root, app, controller):
                app.on_event(event(controller, kind))
                settle(root, app)
                dialog = app._interaction['dialog']
                focus(root, app, dialog)
                width, height = dialog.winfo_width(), dialog.winfo_height()
                minimum = dialog.minsize()[0]
                dialog.geometry(f'{width - 1 if width > minimum else width + 1}x{height}')
                # Process real Configure/geometry work, excluding all timer events.
                # Close as soon as the product schedules its own reflow callback.
                deadline = time.perf_counter() + 2
                flags = _tkinter.WINDOW_EVENTS | _tkinter.IDLE_EVENTS | _tkinter.DONT_WAIT
                while not app._interaction.get('layout_after') and time.perf_counter() < deadline:
                    if not root.tk.dooneevent(flags):
                        time.sleep(.001)
                pending = app._interaction.get('layout_after')
                assert pending, 'Native Configure did not schedule an owned reflow timer'
                pending_info = tuple(root.tk.call('after', 'info', pending))
                pending_observed_ns = time.perf_counter_ns()
                close_focus = focus_identity(root)
                if action == 'window-close':
                    root.tk.call(dialog.protocol('WM_DELETE_WINDOW'))
                elif action == 'alt-s':
                    dialog.event_generate('<Alt-s>')
                else:
                    controller.active = False
                    app.on_event({'job_id': controller.job_id, 'type': 'terminal', 'status': 'CANCELLED',
                                  'percent': 20, 'message': 'Synthetic cancellation complete'})
                close_delay_ms = (time.perf_counter_ns() - pending_observed_ns) / 1e6
                pending_cancelled = pending not in root.tk.splitlist(root.tk.call('after', 'info'))
                settle(root, app)
                focus_before = focus_identity(root)
                expired = []
                root.after(200, lambda: expired.append(True))
                while not expired:
                    root.update()
                    time.sleep(.001)
                closed = app._interaction is None
                correct = (len(controller.replies) == 1 and controller.replies[0][2] == {'overwrite': False}) if (
                    kind == 'overwrite' and action == 'window-close') else not controller.replies
                checks.append({'dialog': kind, 'action': action, 'pending_timer_before': bool(pending),
                               'pending_timer_id': pending, 'pending_timer_info': pending_info,
                               'timer_events_excluded_until_close': True,
                               'close_after_pending_observed_ms': close_delay_ms,
                               'pending_timer_cancelled': pending_cancelled,
                               'focus_before_close': close_focus, 'focus_after_close': focus_before,
                               'focus_after_expiry': focus_identity(root), 'late_expiry_wait_ms': 200,
                               'closed': closed, 'correct_reply': correct,
                               'stop_called': bool(controller.stops), 'no_grab': root.grab_current() is None,
                               'focus_unchanged_after_expiry': focus_identity(root) == focus_before})
                checkpoint()
    return checks


def fresh_keyboard_checks(checks, checkpoint):
    for kind in ('selection', 'overwrite'):
        with session(payload_for(kind, 20)) as (root, app, controller):
            app.on_event(event(controller, kind))
            settle(root, app)
            dialog = app._interaction['dialog']
            tree = table(dialog)
            first = named(dialog, 'search' if kind == 'selection' else 'folder')
            focus(root, app, first)
            traversed = []
            for _ in range(20):
                if root.focus_get() == tree:
                    break
                traversed.append(str(root.focus_get()))
                key(root, app, '<Tab>')
            before = tree.focus()
            key(root, app, '<KeyPress-Down>')
            key(root, app, '<KeyRelease-Down>')
            after = tree.focus()
            row = {'dialog': kind, 'probe': 'fresh-keyboard-entry', 'tree_focused': root.focus_get() == tree,
                   'item_focus_before_down': before, 'item_focus_after_down': after,
                   'row_navigation_available': bool(after), 'replies': controller.replies}
            if kind == 'selection':
                row['id_matches_focus'] = bool(after) and named(dialog, 'focused_id').get() == tree.set(after, 'identifier')
            else:
                initial_x = list(tree.xview())
                for sequence in ('<Right>', '<Shift-Right>', '<Control-Right>', '<End>'):
                    for _ in range(3):
                        key(root, app, sequence)
                row['xview_before_keys'], row['xview_after_keys'] = initial_x, list(tree.xview())
                scrollbars = [w for w in children(dialog) if w.winfo_class() == 'TScrollbar']
                row['scrollbar_takefocus'] = [str(w.cget('takefocus')) for w in scrollbars]
                row['horizontal_keyboard_route_observed'] = list(tree.xview()) != initial_x
            checks.append(row)
            checkpoint()


class Luid(C.Structure):
    _fields_ = [('low', W.DWORD), ('high', W.LONG)]


class SourceInfo(C.Structure):
    _fields_ = [('adapter', Luid), ('id', W.UINT), ('mode', W.UINT), ('flags', W.UINT)]


class TargetInfo(C.Structure):
    _fields_ = [('adapter', Luid), ('id', W.UINT), ('mode', W.UINT), ('technology', W.UINT),
                ('rotation', W.UINT), ('scaling', W.UINT), ('numerator', W.UINT), ('denominator', W.UINT),
                ('scanline', W.UINT), ('available', W.BOOL), ('flags', W.UINT)]


class DisplayPath(C.Structure):
    _fields_ = [('source', SourceInfo), ('target', TargetInfo), ('flags', W.UINT)]


class DeviceHeader(C.Structure):
    _fields_ = [('type', W.UINT), ('size', W.UINT), ('adapter', Luid), ('id', W.UINT)]


class SourceName(C.Structure):
    _fields_ = [('header', DeviceHeader), ('name', W.WCHAR * 32)]


class DpiGet(C.Structure):
    _fields_ = [('header', DeviceHeader), ('minimum', C.c_int32), ('current', C.c_int32), ('maximum', C.c_int32)]


class DpiSet(C.Structure):
    _fields_ = [('header', DeviceHeader), ('relative', C.c_int32)]


class MonitorEx(C.Structure):
    _fields_ = [('info', MonitorInfo), ('device', W.WCHAR * 32)]


def monitor_scale():
    u, _, s = api()
    monitor = u.MonitorFromWindow(None, 2)
    scale = C.c_int()
    hr = s.GetScaleFactorForMonitor(monitor, C.byref(scale))
    info = MonitorEx()
    info.info.size = C.sizeof(info)
    assert u.GetMonitorInfoW(monitor, C.cast(C.byref(info), C.POINTER(MonitorInfo)))
    return {'percent': scale.value if hr == 0 else None, 'hresult': hr,
            'device': info.device, 'work_area': rect_values(info.info.work),
            'monitor_rect': rect_values(info.info.monitor)}


def dpi_source():
    """Diagnostic-only undocumented source DPI packets; native readback is authoritative."""
    u, _, _ = api()
    assert C.sizeof(DeviceHeader) == 20 and C.sizeof(DpiGet) == 32 and C.sizeof(DpiSet) == 24
    assert C.sizeof(DisplayPath) == 72
    npath, nmode = W.UINT(), W.UINT()
    rc = u.GetDisplayConfigBufferSizes(2, C.byref(npath), C.byref(nmode))
    if rc:
        raise RuntimeError(f'GetDisplayConfigBufferSizes returned {rc}')
    paths, modes = (DisplayPath * npath.value)(), C.create_string_buffer(64 * nmode.value)
    rc = u.QueryDisplayConfig(2, C.byref(npath), paths, C.byref(nmode), modes, None)
    if rc:
        raise RuntimeError(f'QueryDisplayConfig returned {rc}')
    device = monitor_scale()['device']
    for path in paths[:npath.value]:
        source = path.source
        name = SourceName(DeviceHeader(1, C.sizeof(SourceName), source.adapter, source.id))
        rc = u.DisplayConfigGetDeviceInfo(C.byref(name))
        if rc == 0 and name.name == device:
            packet = DpiGet(DeviceHeader(0xfffffffd, C.sizeof(DpiGet), source.adapter, source.id))
            rc = u.DisplayConfigGetDeviceInfo(C.byref(packet))
            if rc:
                raise RuntimeError(f'DisplayConfigGetDeviceInfo source DPI returned {rc}')
            return packet
    raise RuntimeError('No active display source matched the measured monitor')


def set_dpi(packet, relative):
    assert packet.minimum <= relative <= packet.maximum
    u, _, _ = api()
    request = DpiSet(DeviceHeader(0xfffffffc, C.sizeof(DpiSet), packet.header.adapter, packet.header.id), relative)
    return u.DisplayConfigSetDeviceInfo(C.byref(request))


def enlarge_display():
    """Use only an enumerated OS display mode, without changing DPI awareness."""
    u, _, _ = api()
    u.EnumDisplaySettingsW.argtypes = [W.LPCWSTR, W.DWORD, C.c_void_p]
    u.ChangeDisplaySettingsW.argtypes = [C.c_void_p, W.DWORD]
    def mode(index):
        value = C.create_string_buffer(220)
        struct.pack_into('<H', value, 68, 220)
        return value if u.EnumDisplaySettingsW(None, index, value) else None
    original = mode(0xffffffff)
    choices = []
    for i in range(1000):
        item = mode(i)
        if item is None:
            break
        width, height = struct.unpack_from('<II', item, 172)
        if 1920 <= width <= 3840 and 1440 <= height <= 2160:
            choices.append((width * height, item, width, height))
    if not choices:
        attempts = []
        # Virtual displays may enumerate only their current mode. Let Windows
        # validate larger modes with CDS_TEST before applying any of them.
        for width, height in ((2560, 1600), (1920, 1440), (1440, 900)):
            selected = C.create_string_buffer(original.raw, 220)
            struct.pack_into('<I', selected, 72, 0x00180000)
            struct.pack_into('<II', selected, 172, width, height)
            test_rc = u.ChangeDisplaySettingsW(selected, 2)
            attempt = {'requested_px': [width, height], 'test_return_code': test_rc}
            attempts.append(attempt)
            if test_rc == 0:
                attempt['apply_return_code'] = u.ChangeDisplaySettingsW(selected, 0)
                attempt['observed'] = monitor_scale()
                if attempt['apply_return_code'] == 0:
                    return original, {'status': 'changed_after_CDS_TEST', 'attempts': attempts}
        return original, {'status': 'unavailable', 'initial': monitor_scale(), 'attempts': attempts}
    _, selected, width, height = min(choices, key=lambda entry: entry[0])
    rc = u.ChangeDisplaySettingsW(selected, 0)
    return original, {'status': 'changed' if rc == 0 else 'failed', 'return_code': rc,
                      'selected_px': [width, height], 'observed': monitor_scale()}


def orchestrate(args):
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    report = {'synthetic': True, 'portal_accessed': False, 'runs': [], 'scales': [],
              'scale_method': 'undocumented DisplayConfig source DPI packets; observed native monitor scale required',
              'no_product_awareness_changes': True}
    original_mode, packet = None, None
    paired_benchmark_done = False
    try:
        try:
            original_mode, report['display'] = enlarge_display()
        except Exception as error:
            report['display_error'] = str(error)
        try:
            packet = dpi_source()
            report['source_dpi_relative'] = {'minimum': packet.minimum, 'current': packet.current, 'maximum': packet.maximum}
        except Exception as error:
            report['scale_capability_error'] = str(error)
        for requested in (100, 150, 200):
            attempt = {'requested_percent': requested, 'before': monitor_scale()}
            if attempt['before']['percent'] != requested and packet is not None:
                relative = (100, 125, 150, 175, 200, 225, 250, 300, 350, 400, 450, 500).index(requested) + packet.minimum
                attempt['requested_relative'] = relative
                if packet.minimum <= relative <= packet.maximum:
                    attempt['set_return_code'] = set_dpi(packet, relative)
                    until = time.perf_counter() + 3
                    while time.perf_counter() < until:
                        if monitor_scale()['percent'] == requested:
                            break
                        time.sleep(.05)
                else:
                    attempt['unsupported_relative'] = True
            attempt['after'] = monitor_scale()
            attempt['verified_monitor_scale'] = attempt['after']['percent'] == requested and attempt['after']['hresult'] == 0
            report['scales'].append(attempt)
            write_json(out/'runner.json', report)
            if not attempt['verified_monitor_scale']:
                print(f'SCALE {requested}: NOT VERIFIED {attempt}', flush=True)
                continue
            for label, source, revision in [('baseline', args.baseline, BASELINE), ('candidate', args.candidate, CANDIDATE)]:
                if paired_benchmark_done and label == 'baseline':
                    continue
                destination = out / f'{label}-{requested}'
                command = [sys.executable, str(Path(__file__).resolve()), '--source', str(Path(source).resolve()),
                           '--revision', revision, '--out', str(destination)]
                if label == 'candidate':
                    command.append('--visual')
                if paired_benchmark_done:
                    command.append('--skip-benchmark')
                # Separate processes preserve independent module/Tk state for both exact checkouts.
                record = {'label': label, 'requested_percent': requested, 'revision': revision, 'directory': destination.name}
                try:
                    completed = subprocess.run(command, cwd=source, timeout=480, check=False)
                    record['return_code'] = completed.returncode
                except Exception as error:
                    record.update(return_code=-1, process_error=str(error))
                report['runs'].append(record)
                write_json(out/'runner.json', report)
            paired_benchmark_done = True
        report['paired_benchmark_attempted'] = paired_benchmark_done
    finally:
        if packet is not None:
            try:
                report['restore_dpi_return_code'] = set_dpi(packet, packet.current)
            except Exception as error:
                report['restore_dpi_error'] = str(error)
        if original_mode is not None:
            try:
                report['restore_resolution_return_code'] = api()[0].ChangeDisplaySettingsW(original_mode, 0)
            except Exception as error:
                report['restore_resolution_error'] = str(error)
        write_json(out/'runner.json', report)
    assert report['runs'], 'No supported native scaling mode could be exercised'
    assert all(run['return_code'] == 0 for run in report['runs']), 'At least one evidence process failed; inspect JSON'


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def child(args):
    source = Path(args.source).resolve()
    revision = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    assert revision == args.revision, (revision, args.revision)
    sys.path.insert(0, str(source))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    result = {'revision': revision, 'synthetic': True, 'portal_accessed': False, 'frames': [], 'checks': [], 'timings': []}
    checkpoint = lambda: write_json(out/'evidence.json', result)
    if args.visual:
        try:
            visuals(out, revision, result['frames'], result['checks'], checkpoint)
            result['close_checks'] = []
            close_checks(result['close_checks'], checkpoint)
            result['fresh_keyboard_checks'] = []
            fresh_keyboard_checks(result['fresh_keyboard_checks'], checkpoint)
        except Exception:
            result['visual_error'] = traceback.format_exc()
            checkpoint()
    if not args.skip_benchmark:
        try:
            benchmark(revision, result['timings'], checkpoint)
        except Exception:
            result['benchmark_error'] = traceback.format_exc()
    checkpoint()
    assert 'visual_error' not in result and 'benchmark_error' not in result, result.get('visual_error', result.get('benchmark_error'))


def keyboard_regressions(args):
    source = Path(args.candidate).resolve()
    revision = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    assert revision == CANDIDATE
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, '-m', 'pytest', '-q',
               'tests/test_desktop_dialog_layout.py::test_fresh_selection_keyboard_navigation_can_authorize_only_at_button',
               'tests/test_desktop_dialog_layout.py::test_overwrite_path_suffix_is_reachable_by_keyboard_without_consent',
               'tests/test_desktop_dialog_layout.py::test_overwrite_keyboard_navigation_reaches_last_file_without_consent',
               '--basetemp', str(out.parent / 'p2-keyboard-pytest')]
    completed = subprocess.run(command, cwd=source, text=True, encoding='utf-8',
                               errors='replace', capture_output=True, timeout=180)
    write_json(out / 'keyboard-regressions.json', {
        'revision': revision, 'synthetic': True, 'portal_accessed': False,
        'command': command, 'return_code': completed.returncode,
        'stdout': completed.stdout, 'stderr': completed.stderr})
    print(completed.stdout, flush=True)
    print(completed.stderr, flush=True)
    return completed.returncode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source')
    parser.add_argument('--revision')
    parser.add_argument('--out', required=True)
    parser.add_argument('--visual', action='store_true')
    parser.add_argument('--skip-benchmark', action='store_true')
    parser.add_argument('--baseline')
    parser.add_argument('--candidate')
    parser.add_argument('--regression-only', action='store_true')
    parser.add_argument('--capture-desktop', type=int, metavar='HWND')
    args = parser.parse_args()
    assert sys.platform == 'win32', 'Execution is authorized on the GitHub Windows runner only'
    if args.capture_desktop is not None:
        capture_desktop(args)
        return
    if args.regression_only:
        raise SystemExit(keyboard_regressions(args))
    if args.baseline and args.candidate:
        orchestrate(args)
    else:
        child(args)


if __name__ == '__main__':
    main()
