"""Finite candidate fixture host. No reader observer, worker, browser, or vault access."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

SCENARIOS = ('main', 'settings', 'selection', 'overwrite', 'progress', 'result', 'regression')


class SnapshotPublisher:
    """Publish at most 128 immutable, complete snapshots in the owned directory."""
    def __init__(self, directory):
        self.directory = directory
        self.count = 0

    def publish(self, data):
        if self.count >= 128:
            raise ValueError('fixture snapshot limit reached')
        target = self.directory / f'ready-{self.count:03d}.json'
        pending = self.directory / 'ready.pending'
        if target.exists():
            raise ValueError('published fixture snapshot already exists')
        encoded = json.dumps(data).encode('utf-8')
        if len(encoded) > 1048576:
            raise ValueError('fixture snapshot size limit reached')
        with pending.open('xb') as stream:
            stream.write(encoded)
        pending.rename(target)
        self.count += 1
        return target


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
        if scenario == 'regression':
            return _regression(directory)
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
    publisher = SnapshotPublisher(directory)
    last_snapshot_state = None

    def snapshot():
        nonlocal last_snapshot_state
        root.update_idletasks()
        # Read installed callback state; never install, reload, or patch accessibility.
        installed = bool(root.tk.call('info', 'commands', '::tk::accessible::_getentrytext'))
        current_state = (sequence, installed)
        if current_state == last_snapshot_state:
            return
        data = {'pid': os.getpid(), 'hwnd': int(api.GetAncestor(target.winfo_id(), 2)),
                'password_hwnd': int(password.winfo_id()) if password is not None else None,
                'candidate': candidate, 'frozen': bool(getattr(sys, 'frozen', False)), 'scenario': scenario,
                'tk_initialized': installed, 'sequence': sequence, 'callback_errors': errors,
                'credentials_accessed': False, 'live_scrape': False, 'stopped': controller.stopped}
        publisher.publish(data)
        last_snapshot_state = current_state

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



def _regression(directory):
    """Finite behavioral checks of real App handlers; no reader acceptance claim."""
    from contextlib import contextmanager
    import subprocess
    import tkinter as tk
    from spt_desktop import app as gui
    from spt_desktop.windows import ProcessJob
    from scripts.launcher_candidate.probe import application_probe

    checks = dict.fromkeys(('settings_return_discard_save_clear', 'selection_explicit_consent',
        'overwrite_preserve_and_explicit_consent', 'stale_and_stop_precedence',
        'complete_partial_eligibility', 'owned_cleanup'), False)
    report = {'checks': checks, 'frozen': bool(getattr(sys, 'frozen', False)),
              'credentials_accessed': False, 'live_scrape': False,
              'accessibility_acceptance': False,
              'eligibility_scope': 'App terminal UI gate; full controller/output eligibility covered by candidate Windows suite'}

    def checkpoint():
        (directory / 'regression.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

    def children(widget):
        for child in widget.winfo_children():
            yield child
            yield from children(child)

    def button(widget, text):
        return next(w for w in children(widget) if w.winfo_class() == 'TButton' and w.cget('text') == text)

    @contextmanager
    def window(label):
        root = tk.Tk()
        errors = []
        root.report_callback_exception = lambda kind, *_: errors.append(kind.__name__)
        controller = SyntheticController()
        workspace = directory / label
        workspace.mkdir()
        gui.save_preferences(workspace, dict(gui.DEFAULTS, identifier='SYNTHETIC_ACCOUNT'))
        app = gui.App(root, workspace, controller)
        try:
            root.update()
            root.focus_force()
            root.update()
            if 'candidate' not in report:
                report['candidate'] = application_probe(root)
            yield root, app, controller
            assert not errors, 'Tk callback failure in finite regression'
        finally:
            controller.close()
            app._dispose()
            for token in root.tk.splitlist(root.tk.call('after', 'info')):
                root.after_cancel(token)
            root.destroy()

    def start(app):
        app.npwp.set('0000000000000001')
        app.year.set('2025')
        app.start()
        assert app.controller.active

    def event(controller, kind, **values):
        return dict(job_id=controller.job_id, type=kind, percent=20,
                    stage='details', message='Synthetic regression', **values)

    original = gui.save_login, gui.delete_login
    vault_writes = []
    gui.save_login = lambda *args, **kwargs: vault_writes.append(True)
    gui.delete_login = lambda *args, **kwargs: None
    checkpoint()
    try:
        with window('settings') as (root, app, controller):
            def password(dialog):
                return next(w for w in children(dialog) if w.winfo_class() == 'TEntry' and w.cget('show'))
            def decision():
                app._settings_close()
                root.update()
                return next(w for w in children(root) if isinstance(w, tk.Toplevel) and w.title() == 'Perubahan belum disimpan')
            dialog = app.settings()
            password(dialog).insert(0, 'SYNTHETIC_REGRESSION_SECRET')
            prompt = decision()
            button(prompt, 'Kembali').invoke()
            root.update()
            assert password(dialog).get() and app._settings_dialog is dialog and not vault_writes
            button(decision(), 'Abaikan').invoke()
            root.update()
            assert app._settings_dialog is None and not vault_writes
            dialog = app.settings()
            assert password(dialog).get() == ''
            password(dialog).insert(0, 'SYNTHETIC_REGRESSION_SECRET')
            button(decision(), 'Simpan').invoke()
            root.update()
            assert vault_writes == [True] and app._settings_dialog is None
            dialog = app.settings()
            assert password(dialog).get() == ''
            app._settings_close()
            assert app._settings_dialog is None
        checks['settings_return_discard_save_clear'] = True
        checkpoint()

        with window('selection') as (root, app, controller):
            start(app)
            literal = '::synthetic {return}; [literal] / id'
            controller.payload = {'records': [{'record_id': literal, 'meta': {'Jenis Pajak': 'PPN', 'Model SPT': 'Pembetulan 001'}}]}
            app.on_event(event(controller, 'selection_required', request_id='a'*32))
            dialog = app._interaction['dialog']
            tree = next(w for w in children(dialog) if w.winfo_class() == 'Treeview')
            confirm = button(dialog, 'Sedot SPT terpilih')
            assert not tree.selection() and confirm.instate(['disabled']) and not controller.replies
            tree.selection_set(tree.get_children()[0])
            tree.event_generate('<<TreeviewSelect>>')
            root.update()
            assert not controller.replies
            confirm.invoke()
            assert controller.replies == [{'kind': 'selection', 'request_id': 'a'*32, 'payload': {'selected_ids': [literal]}}]
            assert app._interaction is None
        checks['selection_explicit_consent'] = True
        checkpoint()

        for allow in (False, True):
            with window('overwrite-' + str(allow)) as (root, app, controller):
                start(app)
                controller.payload = {'folder': str(directory / 'SYNTHETIC_EXPORT'), 'files': ['resume.xlsx']}
                app.on_event(event(controller, 'overwrite_required', request_id='b'*32))
                dialog = app._interaction['dialog']
                assert not controller.replies
                button(dialog, 'Ganti file tersebut' if allow else 'Jangan ganti').invoke()
                assert controller.replies == [{'kind': 'overwrite', 'request_id': 'b'*32, 'payload': {'overwrite': allow}}]
                assert app._interaction is None
        checks['overwrite_preserve_and_explicit_consent'] = True
        checkpoint()

        with window('stale-stop') as (root, app, controller):
            start(app)
            before = app._ui_state
            app.on_event(dict(event(controller, 'progress'), job_id='stale-job'))
            assert app._ui_state is before
            app.stop()
            assert controller.stopped and app._ui_state.view_state == 'stopping'
            stopped = app._ui_state
            app.on_event(event(controller, 'progress'))
            app.on_event(dict(event(controller, 'terminal', status='COMPLETE', output=str(directory)), percent=100))
            assert app._ui_state is stopped and app._result is None
            app.on_event(event(controller, 'terminal', status='CANCELLED', output=None))
            assert app._ui_state.terminal_status == 'CANCELLED'
        checks['stale_and_stop_precedence'] = True
        checkpoint()

        for terminal in ('PARTIAL', 'COMPLETE'):
            with window('terminal-' + terminal) as (root, app, controller):
                start(app)
                complete = dict(event(controller, 'terminal', status='COMPLETE', output=str(directory)), percent=100)
                before = app._ui_state
                app.on_event(complete)
                assert app._ui_state is before, 'Active cleanup must withhold terminal completion'
                controller.active = False
                app.on_event(dict(complete, output=None))
                assert app._ui_state is before, 'COMPLETE requires output'
                app.on_event(dict(complete, percent=20))
                assert app._ui_state is before, 'COMPLETE requires exactly 100 percent'
                app.on_event(complete if terminal == 'COMPLETE' else event(controller, 'terminal', status='PARTIAL', output=None))
                assert app._ui_state.terminal_status == terminal
                assert (app._ui_state.percent == 100) == (terminal == 'COMPLETE')
                assert app.open_button.instate(['!disabled' if terminal == 'COMPLETE' else 'disabled'])
        checks['complete_partial_eligibility'] = True
        checkpoint()

        # Exercise native owned-tree termination with a fixed synthetic child.
        # No command or path is accepted from the fixture caller.
        with ProcessJob() as owned:
            process = owned.spawn(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
                                   'Start-Sleep -Seconds 60'], stdin=subprocess.DEVNULL,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                assert process.poll() is None
            finally:
                owned.close()
                process.wait(timeout=10)
            assert process.poll() is not None
        checks['owned_cleanup'] = True
        checkpoint()
        return 0
    finally:
        gui.save_login, gui.delete_login = original
        checkpoint()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', choices=SCENARIOS, required=True)
    parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    return run(args.scenario, args.directory)


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    raise SystemExit(main())
