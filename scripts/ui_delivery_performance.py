"""Synthetic dialog timing evidence for GitHub Windows runners only.

Primary observer, payload, session and benchmark functions are copied verbatim
from scripts/_p2_dialog_evidence.py at 67396564dd12b8a3d9eb8cd08920316cf83ae2d3
(blob 3ed745bd1059c07753cfc1389a0772687645972d). Trace runs are separate processes;
their instrumented timings must never replace the primary settled metric.
No account, worker, browser, screenshot, or live data access is performed.
"""
from __future__ import annotations

import argparse
import ast
from contextlib import contextmanager
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time
import traceback


HISTORICAL_COMMIT = '67396564dd12b8a3d9eb8cd08920316cf83ae2d3'
HISTORICAL_BLOB = '3ed745bd1059c07753cfc1389a0772687645972d'


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


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def git_output(source, *args):
    return subprocess.check_output(['git', '-C', str(source), *args], text=True).strip()


def source_evidence(source, expected):
    revision = git_output(source, 'rev-parse', 'HEAD')
    if revision != expected or len(expected) != 40:
        raise RuntimeError('Source HEAD does not match the full expected revision')
    if git_output(source, 'status', '--porcelain', '--untracked-files=no'):
        raise RuntimeError('Tracked source must be clean before timing')
    tracked = git_output(source, 'ls-files', 'spt_desktop').splitlines()
    files = {name: hashlib.sha256((source / name).read_bytes()).hexdigest()
             for name in tracked if (source / name).is_file()}
    return {'revision': revision, 'tree': git_output(source, 'rev-parse', 'HEAD^{tree}'),
            'desktop_file_sha256': files, 'tracked_source_clean': True}


def observer_evidence():
    source = Path(__file__).read_text(encoding='utf-8')
    names = {'children', 'geometry_signature', 'settle', 'measure', 'payload_for',
             'session', 'operation', 'benchmark'}
    functions = {node.name: hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()
                 for node in ast.parse(source).body
                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names}
    return {'historical_commit': HISTORICAL_COMMIT, 'historical_blob': HISTORICAL_BLOB,
            'harness_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'primary_function_ast_sha256': functions,
            'metric': 'max(handler, last geometry-or-owned-token change minus action start)',
            'quiet_iterations': 3, 'quiet_sleep_seconds': .001,
            'observer_overhead_subtracted': False, 'first_paint_metric': False}


def trace_opening(revision, kind, count, records, checkpoint):
    """Observe a distinct opening; all durations include diagnostic overhead.

    Inclusive function costs overlap and must not be added as a time partition.
    Native event delivery timestamps are observations, not physical paint times.
    The primary benchmark never installs these bindings or a Python profiler.
    """
    import tkinter as tk
    import tkinter.ttk as ttk
    import spt_desktop.app as app_module
    import spt_desktop.ui_theme as theme_module
    import spt_desktop.ui_views as views_module

    payload = payload_for(kind, count)
    result = {'dialog': kind, 'inventory_size': count, 'instrumented': True,
              'acceptance_measurement': False, 'events': [], 'spans': [], 'costs': {},
              'payload_sha256': hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()}
    # Keep partial events/costs in the parent's error checkpoint if a trace fails.
    records.append(result)
    checkpoint()
    with session(payload) as (root, app, controller):
        started = None
        active = {}
        selected_codes = {
            geometry_signature.__code__: 'observer.geometry_signature',
            children.__code__: 'observer.children_generator',
            tk.Misc.update.__code__: 'tk.update',
            tk.Misc.update_idletasks.__code__: 'tk.update_idletasks',
            tk.BaseWidget.__init__.__code__: 'tk.widget_construction',
            ttk.Treeview.insert.__code__: 'tk.tree_insert',
        }
        product_paths = {str(Path(module.__file__).resolve()): Path(module.__file__).stem
                         for module in (app_module, theme_module, views_module)}
        product_names = {'on_event', 'selection_dialog', 'overwrite_dialog', '_new_interaction',
                         'configure_dialog', '_window_work_metrics', 'client_work_area',
                         'reflow', 'request_reflow', 'update_scrollregion', 'filter_records',
                         'render', '_reflow', '_reveal_priority', '_update_scrollregion'}

        def profile(frame, action, arg):
            if action not in ('call', 'return'):
                return
            code = frame.f_code
            label = selected_codes.get(code)
            if label is None and code.co_name in product_names and code.co_filename in product_paths:
                label = 'product.' + product_paths[code.co_filename] + '.' + code.co_name
            if label is None:
                return
            if action == 'call':
                active[id(frame)] = (time.perf_counter_ns(), label)
                return
            entry = active.pop(id(frame), None)
            if entry is None:
                return
            before, label = entry
            after = time.perf_counter_ns()
            duration = (after - before) / 1e6
            cost = result['costs'].setdefault(label, {'calls': 0, 'inclusive_ms': 0, 'max_ms': 0})
            cost['calls'] += 1
            cost['inclusive_ms'] += duration
            cost['max_ms'] = max(cost['max_ms'], duration)
            if label.startswith('product.') and len(result['spans']) < 2000:
                result['spans'].append({'function': label, 'start_ms': (before - started) / 1e6,
                                        'end_ms': (after - started) / 1e6})

        def native_event(received):
            interaction = app._interaction
            if started is None or interaction is None:
                return
            dialog = interaction['dialog']
            widget = received.widget
            if widget is not dialog and getattr(widget, 'winfo_name', lambda: '')() != 'body_viewport':
                return
            if len(result['events']) < 2000:
                result['events'].append({'type': getattr(received.type, 'name', str(received.type)),
                                         'widget': str(widget),
                                         'at_ms': (time.perf_counter_ns() - started) / 1e6,
                                         'width': getattr(received, 'width', None),
                                         'height': getattr(received, 'height', None)})

        for sequence in ('<Map>', '<Expose>', '<Configure>'):
            root.bind_all(sequence, native_event, add='+')
        previous_profile = sys.getprofile()
        started = time.perf_counter_ns()
        try:
            sys.setprofile(profile)
            duration, handler = measure(root, app, operation(root, app, controller, kind, 'open'))
        finally:
            sys.setprofile(previous_profile)
            for sequence in ('<Map>', '<Expose>', '<Configure>'):
                root.unbind_all(sequence)
        dialog = app._interaction['dialog']
        result.update(environment(root, dialog, revision))
        result.update(instrumented_settled_ms=duration, instrumented_handler_ms=handler,
                      widget_count=len(list(children(dialog))) + 1,
                      layout_after=app._interaction.get('layout_after'))
        # Isolate the observer's cost only after settling, outside the primary metric.
        observations = []
        for _ in range(30):
            before = time.perf_counter_ns()
            geometry_signature(dialog)
            observations.append((time.perf_counter_ns() - before) / 1e6)
        result['stable_geometry_observer_only_ms'] = observations
        result['stable_geometry_observer_median_ms'] = statistics.median(observations)
        assert not controller.replies and not controller.stops
    return result


def child(args):
    source = Path(args.source).resolve()
    evidence = source_evidence(source, args.revision)
    sys.path.insert(0, str(source))
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    result = {**evidence, 'observer': observer_evidence(), 'synthetic': True,
              'portal_accessed': False, 'credentials_accessed': False,
              'mode': args.mode, 'timings': [], 'traces': [],
              'github_run_id': os.environ.get('GITHUB_RUN_ID'),
              'github_run_attempt': os.environ.get('GITHUB_RUN_ATTEMPT'),
              'workflow_sha': os.environ.get('GITHUB_SHA')}
    checkpoint = lambda: write_json(out / 'evidence.json', result)
    checkpoint()
    try:
        if args.mode == 'primary':
            benchmark(args.revision, result['timings'], checkpoint)
        else:
            for kind, count in [('selection', 1), ('selection', 100), ('selection', 1000), ('overwrite', 101)]:
                trace_opening(args.revision, kind, count, result['traces'], checkpoint)
                checkpoint()
        if source_evidence(source, args.revision) != evidence:
            raise RuntimeError('Source evidence changed during measurement')
        result['completed'] = True
    except Exception:
        result['completed'] = False
        result['error'] = traceback.format_exc()
        raise
    finally:
        checkpoint()


def orchestrate(args):
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    report = {'synthetic': True, 'portal_accessed': False, 'credentials_accessed': False,
              'runs': [], 'observer': observer_evidence(),
              'display_changed_by_harness': False, 'instrumentation_in_primary': False}
    write_json(out / 'runner.json', report)
    for mode in (['primary', 'trace'] if args.trace else ['primary']):
        for label, path, expected in [('baseline', args.baseline, args.baseline_revision),
                                      ('candidate', args.candidate, args.candidate_revision)]:
            source = Path(path).resolve()
            source_evidence(source, expected)
            destination = out / (label + '-' + mode)
            command = [sys.executable, str(Path(__file__).resolve()), '--source', str(source),
                       '--revision', expected, '--mode', mode, '--out', str(destination)]
            run = {'label': label, 'mode': mode, 'revision': expected, 'directory': destination.name}
            report['runs'].append(run)
            try:
                completed = subprocess.run(command, cwd=source, timeout=600, check=False)
                run['return_code'] = completed.returncode
            except Exception:
                run['return_code'] = -1
                run['error'] = traceback.format_exc()
            write_json(out / 'runner.json', report)
    successful = all(run['return_code'] == 0 for run in report['runs'])
    if successful:
        baseline = json.loads((out / 'baseline-primary' / 'evidence.json').read_text(encoding='utf-8'))
        candidate = json.loads((out / 'candidate-primary' / 'evidence.json').read_text(encoding='utf-8'))
        compared = []
        for before, after in zip(baseline['timings'], candidate['timings'], strict=True):
            keys = ('dialog', 'inventory_size', 'operation', 'payload_sha256', 'payload_bytes',
                    'python', 'tcl', 'tk', 'native_dpi', 'awareness', 'monitor_scale_percent',
                    'client_px', 'work_area', 'monitor_rect', 'tk_scaling', 'effective_scale')
            mismatches = [key for key in keys if before[key] != after[key]]
            compared.append({'dialog': after['dialog'], 'inventory_size': after['inventory_size'],
                             'operation': after['operation'], 'comparable': not mismatches,
                             'mismatches': mismatches, 'baseline_median_ms': before['median_ms'],
                             'candidate_median_ms': after['median_ms'],
                             'candidate_p95_ms': after['p95_ms'],
                             'candidate_max_ms': after['max_ms'],
                             'candidate_cancel_max_ms': max(after['cancel_service_ms'])})
        report['comparisons'] = compared
        report['comparable'] = all(row['comparable'] for row in compared)
        report['opening_target_met'] = report['comparable'] and all(
            row['candidate_median_ms'] < 100 for row in compared if row['operation'] == 'open')
        report['candidate_cancel_samples_under_100ms'] = all(
            row['candidate_cancel_max_ms'] < 100 for row in compared)
        successful = report['comparable']
    report['completed'] = successful
    write_json(out / 'runner.json', report)
    if not successful:
        raise RuntimeError('Incomplete or noncomparable evidence; inspect preserved JSON')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', help='Clean baseline checkout path')
    parser.add_argument('--baseline-revision', help='Full expected baseline commit SHA')
    parser.add_argument('--candidate', help='Clean candidate checkout path')
    parser.add_argument('--candidate-revision', help='Full expected candidate commit SHA')
    parser.add_argument('--trace', action='store_true', help='Run separate instrumented child processes')
    parser.add_argument('--source', help=argparse.SUPPRESS)
    parser.add_argument('--revision', help=argparse.SUPPRESS)
    parser.add_argument('--mode', choices=('primary', 'trace'), default='primary', help=argparse.SUPPRESS)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    if sys.platform != 'win32' or os.environ.get('GITHUB_ACTIONS') != 'true':
        parser.error('Execution is authorized on GitHub Windows runners only')
    if args.source:
        if not args.revision:
            parser.error('--source requires --revision')
        child(args)
    else:
        if not all((args.baseline, args.candidate, args.baseline_revision, args.candidate_revision)):
            parser.error('Both checkout paths and full expected revisions are required')
        orchestrate(args)


if __name__ == '__main__':
    main()
