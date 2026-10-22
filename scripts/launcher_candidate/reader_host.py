"""Finite candidate fixture host. No reader observer, worker, browser, or vault access."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

SCENARIOS = ('main', 'settings', 'selection', 'overwrite', 'progress', 'result')


def replace_snapshot(pending, target, *, sleep=time.sleep):
    """Windows readers can briefly deny delete-sharing of the ready snapshot."""
    for attempt in range(5):
        try:
            pending.replace(target)
            return
        except PermissionError as error:
            if getattr(error, 'winerror', None) not in (32, 33) or attempt == 4:
                raise
            sleep(0.02)


def prepare_directory(directory):
    directory = Path(directory).absolute()
    if directory.exists() or directory.is_symlink() or directory.is_junction():
        raise ValueError('candidate fixture requires a new directory')
    if directory.parent.is_symlink() or directory.parent.is_junction():
        raise ValueError('linked fixture parent')
    directory.mkdir()
    return directory


class SyntheticController:
    active = False
    operation = 'export'
    job_id = 'synthetic-reader-job'

    def __init__(self):
        self.payload = {}
        self.replies = []
        self.stopped = False

    def start(self, *args, **kwargs):
        self.active = True
        return self.job_id

    def poll(self):
        return self.active

    def read_request(self, event):
        return self.payload

    def respond(self, kind, request_id, payload):
        self.replies.append({'kind': kind, 'request_id': request_id, 'payload': payload})
        return True

    def stop(self):
        self.stopped = True
        self.active = False

    def close(self):
        self.active = False

    def check_credentials(self, *args, **kwargs):
        raise RuntimeError('candidate fixture never checks credentials')


def run(scenario, directory):
    if scenario not in SCENARIOS:
        raise ValueError('unknown finite candidate scenario')
    if sys.platform != 'win32' or os.environ.get('GITHUB_ACTIONS') != 'true':
        raise RuntimeError('candidate fixture requires a GitHub Windows runner')
    directory = prepare_directory(directory)
    try:
        return _host(scenario, directory)
    except Exception as error:
        import traceback
        safe = {'exception': type(error).__name__, 'frames': [
            {'file': Path(frame.filename).name, 'line': frame.lineno, 'function': frame.name}
            for frame in traceback.extract_tb(error.__traceback__)]}
        (directory / 'host-error.json').write_text(json.dumps(safe), encoding='utf-8')
        raise RuntimeError('candidate host failed; inspect sanitized host-error.json') from None


def _host(scenario, directory):
    def phase(name):
        (directory / 'host-phase.json').write_text(json.dumps({'phase': name, 'pid': os.getpid(),
            'frozen': bool(getattr(sys, 'frozen', False)), 'scenario': scenario}), encoding='utf-8')
    phase('before_imports')
    import ctypes
    from ctypes import wintypes
    import tkinter as tk
    from spt_desktop import app as app_module
    from scripts.launcher_candidate.probe import application_probe
    # Injection prevents even accidental Save/Delete from reaching Credential Manager.
    original = app_module.save_login, app_module.delete_login
    app_module.save_login = lambda *args, **kwargs: None
    app_module.delete_login = lambda *args, **kwargs: None
    api = ctypes.WinDLL('user32', use_last_error=True)
    api.GetAncestor.argtypes = (wintypes.HWND, wintypes.UINT)
    api.GetAncestor.restype = wintypes.HWND
    phase('before_tk')
    root = tk.Tk()
    phase('after_tk_before_app')
    controller = SyntheticController()
    app = app_module.App(root, directory, controller=controller)
    phase('after_app')
    errors = []
    def callback_error(kind, error, trace):
        import traceback
        errors.append(kind.__name__)
        safe = {'exception': kind.__name__, 'frames': [
            {'file': Path(frame.filename).name, 'line': frame.lineno, 'function': frame.name}
            for frame in traceback.extract_tb(trace)]}
        (directory / 'host-error.json').write_text(json.dumps(safe), encoding='utf-8')
    root.report_callback_exception = callback_error
    app.open_logs = lambda: None
    app.open_result = lambda: None
    app.open_button.configure(command=app.open_result)
    app.npwp.set('0000000000000001')
    app.year.set('2025')
    target = root
    password = None

    def children(widget):
        for child in widget.winfo_children():
            yield child
            yield from children(child)

    def settings():
        nonlocal target, password
        app.settings()
        target = app._settings_dialog
        password = next(w for w in children(target) if w.winfo_class() == 'TEntry' and w.cget('show'))
        password.focus_set()

    if scenario == 'settings':
        phase('before_settings')
        settings()
        phase('after_settings')
    elif scenario in ('selection', 'overwrite', 'progress', 'result'):
        app.start()
        if scenario in ('selection', 'overwrite'):
            controller.payload = ({'records': [{'record_id': '::synthetic {return}; [literal] / id', 'meta': {
                'Jenis Pajak': 'PPN', 'Masa Pajak': 'Januari 2025', 'Model SPT': 'Pembetulan 10'}}]}
                if scenario == 'selection' else {'folder': str(directory / 'SYNTHETIC_EXPORT'), 'files': ['resume.xlsx', 'SPT_Badan_2025_Normal.xlsx']})
            app.on_event({'job_id': controller.job_id, 'type': scenario + '_required', 'request_id': 'a'*32,
                          'stage': scenario, 'percent': 20, 'message': 'Synthetic consent request'})
            target = app._interaction['dialog']
        else:
            app.on_event({'job_id': controller.job_id, 'type': 'progress', 'stage': 'details', 'percent': 40,
                          'message': 'Synthetic progress; no worker'})
            if scenario == 'result':
                controller.active = False
                app.on_event({'job_id': controller.job_id, 'type': 'terminal', 'status': 'PARTIAL',
                              'percent': 40, 'output': None, 'message': 'Synthetic partial result; no files'})
    root.geometry('1000x740')
    target.deiconify()
    target.lift()
    target.focus_force()
    if password is not None: password.focus_set()
    candidate = application_probe(root)
    phase('after_identity')
    began = time.monotonic()
    sequence = 0

    def snapshot():
        root.update_idletasks()
        # Read installed callback state; never install, reload, or patch accessibility.
        installed = bool(root.tk.call('info', 'commands', '::tk::accessible::_getentrytext'))
        data = {'pid': os.getpid(), 'hwnd': int(api.GetAncestor(target.winfo_id(), 2)),
                'password_hwnd': int(password.winfo_id()) if password is not None else None,
                'candidate': candidate, 'frozen': bool(getattr(sys, 'frozen', False)), 'scenario': scenario,
                'tk_initialized': installed, 'sequence': sequence, 'callback_errors': errors,
                'credentials_accessed': False, 'live_scrape': False, 'stopped': controller.stopped}
        temp = directory / 'ready.pending'
        temp.write_text(json.dumps(data), encoding='utf-8')
        replace_snapshot(temp, directory / 'ready.json')

    def poll():
        nonlocal sequence
        command = directory / 'command.txt'
        if command.exists():
            action = command.read_text(encoding='utf-8-sig').strip()
            command.unlink()
            if action == 'close': root.quit(); return
            if action == 'remap' and password is not None:
                target.withdraw(); target.deiconify(); target.lift(); password.focus_force()
            elif action == 'reopen' and password is not None:
                password.delete(0, 'end')
                app._settings_close()
                settings()
            elif action == 'focus_password' and password is not None:
                password.focus_force()
            elif action != 'snapshot':
                raise ValueError('unsupported finite fixture action')
            sequence += 1
        snapshot()
        if time.monotonic() - began > 120: root.quit(); return
        root.after(100, poll)

    try:
        root.after(200, poll)
        root.mainloop()
        return 0
    finally:
        if password is not None and password.winfo_exists(): password.delete(0, 'end')
        controller.close()
        app._dispose()
        root.destroy()
        app_module.save_login, app_module.delete_login = original


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', choices=SCENARIOS, required=True)
    parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    return run(args.scenario, args.directory)


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    raise SystemExit(main())
