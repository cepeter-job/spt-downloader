"""Synthetic cross-PR contracts; all product execution belongs to runners."""
import gc
import importlib
import importlib.util
import json
import threading

import pytest

import support_mode_gui as transport

window = transport.window


def diagnostics():
    assert importlib.util.find_spec('spt_desktop.diagnostics') is not None, (
        'PR19 diagnostics are not yet integrated with PR18')
    return importlib.import_module('spt_desktop.diagnostics')


def log_rows(root):
    return [json.loads(line) for path in sorted((root / 'logs').glob('diag-*.jsonl'))
            for line in path.read_text(encoding='utf-8').splitlines()]


@pytest.mark.parametrize('mode', ['dom', 'json-first'])
@pytest.mark.parametrize('level', ['INFO', 'OFF'])
def test_authorized_worker_preserves_mode_protocol_and_logging(tmp_path, monkeypatch, capsys, mode, level):
    d = diagnostics()
    from spt_desktop import worker
    job = 'synthetic-combined-job'
    commands = transport.StartInput(job)
    seen = []
    listeners = []
    real_thread = threading.Thread
    monkeypatch.setenv('SPT_LOG_LEVEL', level)
    monkeypatch.setenv('SPT_LOG_ROOT', str(tmp_path))

    def thread(*args, **kwargs):
        result = real_thread(*args, **kwargs)
        listeners.append(result)
        return result

    def run(npwp, year, root, job_id, browser, headless, emit, cancelled, *, requests, account, detail_source='dom'):
        assert account == ''
        assert not cancelled() and requests is not None
        seen.append(detail_source)
        d.record('operation.started', operation='export')
        print('SYNTHETIC PRIVATE STDERR ONLY')
        emit({'job_id': job_id, 'type': 'terminal', 'status': 'PARTIAL', 'percent': 0, 'output': None})
        return 2

    monkeypatch.setattr(worker.threading, 'Thread', thread)
    monkeypatch.setattr(worker.sys, 'stdin', commands)
    monkeypatch.setattr(worker, 'run_job', run)
    try:
        code = worker.main(['--npwp', '0000000000000001', '--year', '2025',
            '--root', str(tmp_path), '--job-id', job, '--detail-source', mode])
    finally:
        commands.release.set()
        for listener in listeners:
            listener.join(timeout=2)
            assert not listener.is_alive()
    captured = capsys.readouterr()
    assert code == 2 and seen == [mode]
    assert [json.loads(line) for line in captured.out.splitlines()] == [
        {'job_id': job, 'type': 'terminal', 'status': 'PARTIAL', 'percent': 0, 'output': None}]
    assert captured.err == 'SYNTHETIC PRIVATE STDERR ONLY\n'
    rows = log_rows(tmp_path)
    if level == 'INFO':
        assert {'session.started', 'operation.started', 'session.closed'} <= {r['event'] for r in rows}
        assert all(r['job_ref'] == d.job_reference(job) for r in rows)
    else:
        assert rows == [] and not (tmp_path / 'logs').exists()
    assert 'SYNTHETIC PRIVATE' not in json.dumps(rows)
    assert '0000000000000001' not in json.dumps(rows)


def test_settings_keep_mode_status_and_log_action_separate(window):
    diagnostics()
    root, app, controller, path = window
    root.deiconify()
    dialog = app.settings()
    root.update_idletasks()
    widgets = list(transport.descendants(dialog))
    controls = [w for w in widgets if w.winfo_class() == 'TButton' and w.cget('text') == 'Buka folder log']
    assert len(controls) == 1
    status = next(w for w in widgets if w.winfo_class() == 'TLabel'
                  and str(w.cget('textvariable')) == str(app._credential_status))
    log_button = controls[0]
    mode = transport.mode_control(dialog)
    assert mode.get() == 'JSON-hybrid (pilot)' and mode.instate(['readonly'])
    assert mode.master == status.master == log_button.master
    assert int(mode.grid_info()['row']) < int(status.grid_info()['row']) < int(log_button.grid_info()['row'])
    assert log_button.winfo_y() >= status.winfo_y() + status.winfo_height()
    mode.current(1)
    transport.button(dialog, 'Simpan').invoke()
    from spt_desktop.app import load_preferences
    assert load_preferences(path)['detail_source'] == 'json-first'
    app._settings_close()


def test_unsafe_hybrid_remains_rejected_and_diagnostics_stay_private(tmp_path, monkeypatch):
    d = diagnostics()
    import coretax_json as native
    from support_json_hybrid import Scenario
    case = Scenario(tmp_path / 'capture', monkeypatch, status=401)
    root = tmp_path / 'diagnostics'
    with d.session(root, 'worker', job_id='synthetic-unsafe', level='DEBUG') as log:
        with pytest.raises(native.JsonSafetyError):
            case.collect()
        assert log.flush()
    case.assert_closed()
    assert case.dom_calls == [] and case.pdf_calls == []
    assert not case.run['complete'] and not case.record['capture_complete']
    assert case.record['sections'] == [] and case.record.get('attachments', []) == []
    rows = log_rows(root)
    errors = [r for r in rows if r['event'] == 'phase.failed']
    assert any(r['error']['type'] == 'JsonSafetyError' for r in errors)
    assert not any(r.get('status') == 'COMPLETE' for r in rows)
    text = json.dumps(rows)
    for private in [case.run['npwp'], case.record['record_id'], case.record['list_url'], str(case.folder)]:
        assert private not in text
    assert all('message' not in r.get('error', {}) for r in rows)


def test_source_selftest_exercises_hybrid_sorting_and_diagnostics_together(tmp_path):
    diagnostics()
    from spt_gui import self_test
    report = tmp_path / 'combined-selftest.json'
    try:
        assert self_test(report) == 0
        data = json.loads(report.read_text(encoding='utf-8'))
        assert data['diagnostics'] == {'schema': 1, 'safe_logging': True}
        assert data['detail_source_control'] == {
            'labels': ['DOM', 'JSON-hybrid (pilot)'], 'default': 'json-first',
            'saved': 'json-first', 'started': 'json-first'}
        assert data['selection_sorting_control']['selection_preserved'] is True
        assert len(data['selection_sorting_control']['directions']) == 2
        assert {'spt_desktop/diagnostics.py', 'spt_desktop/diagnostic_store.py',
                'coretax_json.py', 'coretax_json_capture.py', 'coretax_corporate.py'} <= set(data['worker_resources'])
        assert data['credentials_accessed'] is False and data['live_scrape'] is False
    finally:
        gc.collect()
