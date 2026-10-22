"""Synthetic native UI host for ui_delivery_accessibility.ps1; GitHub Windows only.

The controller supplies synthetic records and cannot launch a worker. Commands
only traverse focus or close the fixture. No credentials or real output is read.
"""
import argparse
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import sys
import tempfile


def main():
    if sys.platform != 'win32' or os.environ.get('GITHUB_ACTIONS') != 'true':
        raise SystemExit('This native diagnostic is restricted to GitHub Windows runners.')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--scenario', choices=('main', 'selection', 'overwrite'), required=True)
    parser.add_argument('--layout', choices=('normal', 'compact'), required=True)
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
    import tkinter as tk
    from support_gui import ConsentController, consent_event
    from spt_desktop.app import App
    from spt_desktop.ui_theme import client_work_area, effective_scale

    api = ctypes.WinDLL('user32', use_last_error=True)
    api.GetAncestor.argtypes = (wintypes.HWND, wintypes.UINT)
    api.GetAncestor.restype = wintypes.HWND
    api.GetDpiForWindow.argtypes = (wintypes.HWND,)
    api.GetDpiForWindow.restype = wintypes.UINT
    api.GetWindowDpiAwarenessContext.argtypes = (wintypes.HWND,)
    api.GetWindowDpiAwarenessContext.restype = wintypes.HANDLE
    api.GetAwarenessFromDpiAwarenessContext.argtypes = (wintypes.HANDLE,)
    api.GetAwarenessFromDpiAwarenessContext.restype = ctypes.c_int
    root = tk.Tk()
    errors = []
    root.report_callback_exception = lambda *error: errors.append(error[0].__name__)
    root.title('SPT synthetic accessibility diagnostic')
    with tempfile.TemporaryDirectory(prefix='spt-synthetic-accessibility-') as workspace:
        controller = ConsentController({})
        app = App(root, Path(workspace), controller=controller)
        app.npwp.set('0000000000000001')
        app.year.set('2025')
        target = root
        if args.scenario != 'main':
            app.start()
            controller.payload = ({'records': [
                {'record_id': 'synthetic-21-january', 'meta': {'Jenis Pajak': 'PPh Pasal 21/26',
                    'Masa Pajak': 'Januari 2025', 'Model SPT': 'Normal'}},
                {'record_id': 'synthetic-badan', 'meta': {'Jenis Pajak': 'PPh Badan',
                    'Masa Pajak': 'Januari - Desember 2025', 'Model SPT': 'Normal'}}]}
                if args.scenario == 'selection' else {'files': ['resume.xlsx',
                    'SPT_Badan_2025_Normal.xlsx'],
                    'folder': r'C:\Users\SYNTHETIC_USER\Downloads\SYNTHETIC_EXPORT'})
            app.on_event(consent_event(controller, args.scenario))
            target = app._interaction['dialog']
        sizes = {'main': (1120, 800), 'selection': (920, 600), 'overwrite': (800, 520)}
        desired = sizes[args.scenario] if args.layout == 'normal' else (640, 560)
        scale = effective_scale(root)
        root.update_idletasks()
        available = client_work_area(target, monitor_window=root)
        target.geometry(f'{min(round(desired[0] * scale), available[0])}x'
                        f'{min(round(desired[1] * scale), available[1])}')
        target.deiconify()
        target.lift()
        target.focus_force()
        if args.scenario == 'main':
            app.npwp_entry.focus_set()

        def write_snapshot(sequence):
            target.update_idletasks()
            hwnd = api.GetAncestor(target.winfo_id(), 2)
            focus = root.focus_get()
            payload = {'pid': os.getpid(), 'hwnd': int(hwnd), 'sequence': sequence,
                'scenario': args.scenario, 'layout': args.layout,
                'tk_version': str(root.tk.call('package', 'require', 'Tk')),
                'tcl_version': str(root.tk.call('info', 'patchlevel')),
                'effective_tk_scale': effective_scale(root),
                'native_window_dpi': api.GetDpiForWindow(hwnd),
                'native_awareness': api.GetAwarenessFromDpiAwarenessContext(
                    api.GetWindowDpiAwarenessContext(hwnd)),
                'desired_client_dip': desired, 'available_client_tk_pixels': available,
                'actual_client_tk_pixels': [target.winfo_width(), target.winfo_height()],
                'nominal_geometry_attained': (abs(target.winfo_width() - desired[0]*scale) <= 2
                    and abs(target.winfo_height() - desired[1]*scale) <= 2),
                'tk_focus_path': str(focus) if focus else None,
                'tk_focus_class': focus.winfo_class() if focus else None,
                'focus_input': 'Tk generated Tab binding; not physical keyboard evidence',
                'callback_errors': errors, 'synthetic': True,
                'credentials_accessed': False, 'live_scrape': False,
                'consent_replies': len(controller.replies)}
            temporary = args.directory / 'ready.pending'
            temporary.write_text(json.dumps(payload, indent=2), encoding='utf-8')
            temporary.replace(args.directory / 'ready.json')

        sequence = 0

        def poll():
            nonlocal sequence
            command_path = args.directory / 'command.json'
            if command_path.exists():
                try:
                    command = json.loads(command_path.read_text(encoding='utf-8-sig'))
                except (ValueError, OSError):
                    root.after(50, poll)
                    return
                if command['sequence'] > sequence:
                    sequence = command['sequence']
                    if command['action'] == 'close':
                        root.quit()
                        return
                    if command['action'] != 'tab':
                        raise ValueError('Unsupported diagnostic action')
                    focus = root.focus_get()
                    (focus or target).event_generate('<Tab>')
                    root.after(250, lambda current=sequence: write_snapshot(current))
            root.after(50, poll)

        try:
            root.after(700, lambda: write_snapshot(0))
            root.after(750, poll)
            root.after(120000, root.quit)
            root.mainloop()
        finally:
            app._close_interaction()
            app._dispose()
            controller.active = False
            for token in root.tk.splitlist(root.tk.call('after', 'info')):
                root.after_cancel(token)
            root.destroy()
        if errors or controller.replies:
            raise SystemExit('Synthetic diagnostic encountered callback errors or consent.')


if __name__ == '__main__':
    main()
