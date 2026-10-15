"""Runner-only synthetic worker, offline and real-Tk mode contracts."""
from contextlib import nullcontext
import gc
import inspect
import io
import json
from pathlib import Path
import threading
from types import SimpleNamespace
import tkinter as tk

import pytest

MODES = ['dom', 'json-first']
CAPTIONS = ('DOM', 'JSON-hybrid (pilot)')


def worker_job():
    from spt_desktop import worker
    parameter = inspect.signature(worker.run_job).parameters.get('detail_source')
    assert parameter is not None, 'Worker detail_source is missing: intentional feature RED'
    assert parameter.default == 'dom'
    return worker


@pytest.mark.parametrize('mode', MODES)
def test_worker_selected_scope_forwards_literal_mode_to_collector(tmp_path, monkeypatch, mode):
    worker = worker_job()
    from test_split_output import fixture_run
    run = fixture_run()
    run.update(inventory_complete=True)
    for record in run['records']:
        record['capture_complete'] = False
    original_ids = [record['record_id'] for record in run['records']]
    expected_ids = original_ids[1:3]
    captured = []
    closed = []
    emitted = []
    monkeypatch.setattr(worker, 'playwright_factory', lambda: nullcontext(object()))
    monkeypatch.setattr(worker, 'authenticate_owned', lambda *args: (
        SimpleNamespace(close=lambda: closed.append(True)), object()))
    monkeypatch.setattr(worker, 'collect_inventory', lambda *args, **kwargs: run)
    def collect(page, selected, folder, **kwargs):
        assert [r['record_id'] for r in selected['records']] == expected_ids
        captured.append(kwargs.get('detail_source', 'dom'))
        for ordinal in range(1, len(selected['records']) + 1):
            selected['records'][ordinal - 1]['capture_complete'] = ordinal == 1
            kwargs['on_progress'](selected, ordinal)
        return selected
    monkeypatch.setattr(worker, 'collect_details', collect)
    monkeypatch.setattr(worker.coretax, 'save_output', lambda *args: None)
    monkeypatch.setattr(worker, 'downloads_folder', lambda: tmp_path / 'Downloads')
    monkeypatch.setattr(worker, 'existing_outputs', lambda *args: None)
    monkeypatch.setattr(worker, 'publish_workbooks', lambda *args, **kwargs: tmp_path / 'published')
    requests = SimpleNamespace(request=lambda kind, payload, percent: {'selected_ids': expected_ids[::-1]})
    result = worker.run_job('0000000000000001', 2025, tmp_path, 'synthetic-mode',
                            'msedge', True, emitted.append, lambda: False,
                            requests=requests, detail_source=mode)
    assert captured == [mode] and closed == [True]
    assert result == 2 and emitted[-1]['status'] == 'PARTIAL'
    assert all(e['percent'] < 100 for e in emitted)
    details = [e for e in emitted if e['stage'] == 'details']
    assert [(e['processed'], e['total'], e['verified']) for e in details] == [
        (0, 2, 0), (1, 2, 1), (2, 2, 1)]
    assert [r['record_id'] for r in run['records']] == original_ids


@pytest.mark.parametrize('mode', ['', 'JSON-FIRST', None, True, 1, {}])
def test_invalid_worker_mode_has_no_workspace_or_browser_side_effect(tmp_path, monkeypatch, mode):
    worker = worker_job()
    folder = tmp_path / 'must-not-exist'
    called = []
    def forbidden():
        called.append(True)
        raise AssertionError('Invalid mode reached Playwright')
    monkeypatch.setattr(worker, 'playwright_factory', forbidden)
    events = []
    assert worker.run_job('0000000000000001', 2025, folder, 'synthetic-invalid',
                           'msedge', True, events.append, lambda: False,
                           detail_source=mode) == 1
    assert called == [] and not folder.exists()
    assert events[-1]['status'] == 'ERROR' and events[-1]['output'] is None


class StartInput:
    def __init__(self, job):
        self.job = job
        self.first = True
        self.release = threading.Event()

    def readline(self, limit):
        if self.first:
            self.first = False
            return json.dumps({'job_id': self.job, 'command': 'start'}) + '\n'
        self.release.wait(10)
        return ''


@pytest.mark.parametrize('mode', MODES)
def test_worker_cli_mode_reaches_export_and_keeps_stdout_json_only(tmp_path, monkeypatch, capsys, mode):
    worker = worker_job()
    job = 'synthetic-cli-mode'
    incoming = StartInput(job)
    calls = []
    def run(npwp, year, root, job_id, browser, headless, emit, cancelled, **kwargs):
        calls.append((npwp, year, root, job_id, browser, headless, kwargs.get('detail_source', 'dom')))
        print('SYNTHETIC DIAGNOSTIC')
        emit({'job_id': job_id, 'type': 'terminal', 'status': 'PARTIAL', 'percent': 0, 'output': None})
        return 2
    monkeypatch.setattr(worker.sys, 'stdin', incoming)
    real_thread = threading.Thread
    listeners = []
    def thread(*args, **kwargs):
        result = real_thread(*args, **kwargs)
        listeners.append(result)
        return result
    monkeypatch.setattr(worker.threading, 'Thread', thread)
    monkeypatch.setattr(worker, 'run_job', run)
    try:
        code = worker.main(['--npwp', '0000000000000001', '--year', '2025',
            '--root', str(tmp_path), '--job-id', job, '--browser', 'chrome', '--visible',
            '--detail-source', mode])
    finally:
        incoming.release.set()
        for listener in listeners:
            listener.join(timeout=2)
            assert not listener.is_alive()
    assert listeners
    output = capsys.readouterr()
    assert code == 2
    assert calls == [('0000000000000001', '2025', tmp_path, job, 'chrome', False, mode)]
    assert [json.loads(line)['status'] for line in output.out.splitlines()] == ['PARTIAL']
    assert 'SYNTHETIC DIAGNOSTIC' in output.err and 'SYNTHETIC DIAGNOSTIC' not in output.out


def test_login_check_launch_does_not_acquire_export_mode_or_scope(tmp_path, monkeypatch):
    from spt_desktop.controller import JobController
    # This is a regression contract; it may pass before the new feature.
    controller = JobController(tmp_path, lambda event: None)
    captured = []
    monkeypatch.setattr(controller, '_start_worker', lambda *args: captured.append(args) or 'check-only')
    assert controller.start_login_check('https://satu.intranet.pajak.go.id',
                                       'SYNTHETIC ACCOUNT', 'chrome', False) == 'check-only'
    arguments, browser, headless, operation = captured[0]
    assert arguments == ['--check-login', '--origin', 'https://satu.intranet.pajak.go.id',
                         '--account', 'SYNTHETIC ACCOUNT']
    assert (browser, headless, operation) == ('chrome', False, 'login_check')
    assert '--npwp' not in arguments and '--year' not in arguments and '--detail-source' not in arguments


@pytest.mark.parametrize('mode', MODES)
def test_offline_canonical_json_exports_real_workbooks_without_browser_or_native_decode(tmp_path, monkeypatch, mode):
    import coretax
    from test_split_output import fixture_run
    parsed = coretax.parser().parse_args(['--detail-source', mode])
    assert parsed.detail_source == mode
    original = fixture_run()
    source = tmp_path / 'canonical.json'
    source.write_text(json.dumps(original), encoding='utf-8')
    def forbidden(*args, **kwargs):
        raise AssertionError('Offline canonical export reached browser/native capture')
    monkeypatch.setattr(coretax, 'sync_playwright', forbidden)
    monkeypatch.setattr(coretax, 'collect_inventory', forbidden)
    monkeypatch.setattr(coretax, 'collect_details', forbidden)
    output = tmp_path / 'result'
    assert coretax.main(['--from-json', str(source), '--output', str(output), '--detail-source', mode]) == 2
    saved = json.loads((output / 'run.json').read_text(encoding='utf-8'))
    coretax.verify_outputs(saved, output)
    assert saved['records'] == original['records']
    assert {p.relative_to(output).as_posix() for p in output.rglob('*.xlsx')} == {
        'resume.xlsx', 'SPT_Badan.xlsx', 'SPT Masa 21/SPT_21_Januari 2025.xlsx',
        'SPT Masa 21/SPT_21_Februari 2025.xlsx', 'SPT Masa Unifikasi/SPT_Unifikasi_Januari 2025.xlsx'}
    assert not (output / 'returns').exists()


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


def mode_control(dialog):
    matches = [w for w in descendants(dialog) if w.winfo_class() == 'TCombobox'
               and tuple(w.cget('values')) == CAPTIONS]
    assert len(matches) == 1, 'Real DOM / JSON-hybrid mode widget is missing: intentional feature RED'
    return matches[0]


def button(dialog, caption):
    return next(w for w in descendants(dialog) if w.winfo_class() == 'TButton' and w.cget('text') == caption)


@pytest.fixture
def window(tmp_path, monkeypatch):
    from spt_desktop import app as gui
    from test_desktop_login_check_gui import Controller
    class ModeController(Controller):
        def start(self, npwp, year, browser, headless, *, detail_source='dom'):
            self.exports.append((npwp, year, browser, headless, detail_source))
            self.active = True
            self.job_id = 'synthetic-mode-window'
            return self.job_id
    def forbidden(*args):
        raise AssertionError('Mode control must not access credentials')
    monkeypatch.setattr(gui, 'save_login', forbidden)
    monkeypatch.setattr(gui, 'delete_login', forbidden)
    root = tk.Tk()
    controller = ModeController()
    app = None
    try:
        root.withdraw()
        app = gui.App(root, tmp_path, controller)
        yield root, app, controller, tmp_path
    finally:
        controller.active = False
        if app is not None:
            app._dispose()
        for callback in root.tk.splitlist(root.tk.call('after', 'info')):
            root.after_cancel(callback)
        root.destroy()
        del app
        gc.collect()


@pytest.mark.parametrize('mode,index', [('dom', 0), ('json-first', 1)])
def test_real_mode_widget_saves_reloads_and_launches_selected_mode(window, mode, index):
    root, app, controller, path = window
    from spt_desktop.app import load_preferences
    app.settings()
    root.update_idletasks()
    widget = mode_control(app._settings_dialog)
    assert widget.get() == 'DOM' and widget.instate(['readonly'])
    widget.current(index)
    widget.event_generate('<<ComboboxSelected>>')
    root.update_idletasks()
    button(app._settings_dialog, 'Simpan').invoke()
    assert app.preferences['detail_source'] == mode
    assert load_preferences(path)['detail_source'] == mode
    assert json.loads((path / 'preferences.json').read_text())['detail_source'] == mode
    button(app._settings_dialog, 'Tutup').invoke()
    app.settings()
    root.update_idletasks()
    assert mode_control(app._settings_dialog).get() == CAPTIONS[index]
    button(app._settings_dialog, 'Tutup').invoke()
    app.npwp.set('0000000000000001')
    app.year.set('2025')
    app.start_button.invoke()
    assert controller.exports == [('0000000000000001', '2025', 'msedge', True, mode)]
    assert controller.checks == [] and app.settings_button.instate(['disabled'])


def test_saved_mode_does_not_become_a_credential_check_argument(window):
    root, app, controller, path = window
    app.preferences['identifier'] = 'SYNTHETIC ACCOUNT'
    app.settings()
    root.update_idletasks()
    widget = mode_control(app._settings_dialog)
    widget.current(1)
    root.update_idletasks()
    button(app._settings_dialog, 'Simpan').invoke()
    button(app._settings_dialog, 'Cek Kredensial').invoke()
    assert controller.checks == [(app.preferences['login_origin'], 'SYNTHETIC ACCOUNT', 'msedge', True)]
    assert widget.instate(['disabled']) and controller.exports == []
    assert not (path / 'jobs').exists()


def test_source_selftest_observes_real_mode_control_save_and_start(tmp_path):
    import spt_gui
    report = tmp_path / 'mode-selftest.json'
    assert spt_gui.self_test(report) == 0
    data = json.loads(report.read_text())
    assert data.get('detail_source_control') == {
        'labels': list(CAPTIONS), 'default': 'dom', 'saved': 'json-first', 'started': 'json-first'}
    assert not data['credentials_accessed'] and not data['live_scrape']
