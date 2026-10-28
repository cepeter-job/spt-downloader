"""CLI terminal outcomes survive failed checkpoints and owned resource cleanup."""
import errno
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_mpn import scope_run


PRIVATE = 'SYNTHETIC-PRIVATE-EXCEPTION-CONTENT'


@pytest.fixture
def cli(tmp_path, monkeypatch):
    import coretax
    state = SimpleNamespace(run=scope_run(), closed=[], failures={}, exports=0)
    folder = tmp_path / 'output'
    folder.mkdir()
    old = json.dumps(state.run).encode()
    (folder / 'run.json').write_bytes(old)
    (folder / 'resume.xlsx').write_bytes(b'SYNTHETIC EXISTING WORKBOOK BYTES')

    def close(kind):
        state.closed.append(kind)
        if kind in state.failures:
            raise state.failures[kind]

    page = SimpleNamespace(set_viewport_size=lambda _: None, is_closed=lambda: False,
                           close=lambda: close('page'))
    context = SimpleNamespace(new_page=lambda: page, close=lambda: close('context'))
    class Driver:
        def __enter__(self):
            if 'startup' in state.failures:
                raise state.failures['startup']
            return SimpleNamespace(chromium=SimpleNamespace(
                launch_persistent_context=lambda *a, **k: context,
                connect_over_cdp=lambda *a, **k: SimpleNamespace(contexts=[context])))

        def __exit__(self, *args):
            close('driver')

    def inventory(*args, **kwargs):
        if 'inventory' in state.failures:
            raise state.failures['inventory']
        return state.run

    def details(*args, **kwargs):
        raise state.failures.get('capture', RuntimeError(PRIVATE))

    def export(run, output, **kwargs):
        state.exports += 1
        if 'export' in state.failures:
            raise state.failures['export']
        run['output_files'] = ['resume.xlsx']
        return output / 'resume.xlsx'

    monkeypatch.setattr(coretax, 'sync_playwright', Driver)
    monkeypatch.setattr(coretax, 'authenticate', lambda *a: None)
    monkeypatch.setattr(coretax, 'collect_inventory', inventory)
    monkeypatch.setattr(coretax, 'collect_details', details)
    monkeypatch.setattr(coretax, 'save_output', export)
    args = ['--npwp', state.run['npwp'], '--year', '2025', '--output', str(folder),
            '--non-interactive']
    def invoke(*extra):
        try:
            return coretax._main([*args, *extra])
        except KeyboardInterrupt:
            pytest.fail('CLI leaked interruption instead of returning exit 130')
    state.invoke = invoke
    state.folder, state.old, state.page = folder, old, page
    return state


@pytest.mark.parametrize('stop', [False, True])
def test_capture_failure_checkpoints_partial_without_retrying_export(cli, stop, capsys):
    from coretax_browser import CaptureCancelled
    if stop:
        cli.failures['capture'] = CaptureCancelled(PRIVATE)
    assert cli.invoke() == (130 if stop else 1)
    saved = json.loads((cli.folder / 'run.json').read_bytes())
    assert saved['complete'] is False and saved['errors']
    assert saved['npwp'] == '0000000000000001' and saved['year'] == 2025
    assert cli.exports == 0
    assert cli.closed == ['page', 'context', 'driver']
    assert (cli.folder / 'resume.xlsx').read_bytes() == b'SYNTHETIC EXISTING WORKBOOK BYTES'
    assert PRIVATE not in json.dumps(saved['errors']) + capsys.readouterr().err


@pytest.mark.parametrize('kind', ['space', 'permission', 'replace'])
@pytest.mark.parametrize('stop', [False, True])
def test_failed_atomic_checkpoint_keeps_old_bytes_and_original_exit(cli, monkeypatch, kind, stop):
    import os
    from coretax_browser import CaptureCancelled
    if stop:
        cli.failures['capture'] = CaptureCancelled(PRIVATE)
    original_open, original_replace = Path.open, os.replace

    def opening(path, mode='r', *args, **kwargs):
        if path.name.startswith('run.json.') and mode == 'xb' and kind != 'replace':
            raise OSError(errno.ENOSPC if kind == 'space' else errno.EACCES, PRIVATE)
        return original_open(path, mode, *args, **kwargs)

    def replacing(source, target):
        if Path(target) == cli.folder / 'run.json' and kind == 'replace':
            raise PermissionError(PRIVATE)
        return original_replace(source, target)

    monkeypatch.setattr(Path, 'open', opening)
    monkeypatch.setattr(os, 'replace', replacing)
    assert cli.invoke() == (130 if stop else 1)
    assert (cli.folder / 'run.json').read_bytes() == cli.old
    assert not list(cli.folder.glob('*.tmp'))
    assert cli.exports == 0
    assert cli.closed == ['page', 'context', 'driver']


def test_invalid_scope_never_replaces_last_checkpoint_or_publishes(cli):
    cli.run['npwp'] = 'invalid-synthetic-scope'
    assert cli.invoke() == 1
    assert (cli.folder / 'run.json').read_bytes() == cli.old
    assert cli.exports == 0


@pytest.mark.parametrize('stop', [False, True])
@pytest.mark.parametrize('failure', ['page', 'context', 'driver', 'all', 'closed-probe'])
def test_original_failure_survives_cleanup_errors_and_all_resources_are_attempted(cli, stop, failure):
    from coretax_browser import CaptureCancelled
    if stop:
        cli.failures['capture'] = CaptureCancelled(PRIVATE)
    if failure == 'closed-probe':
        def broken():
            raise RuntimeError(PRIVATE)
        cli.page.is_closed = broken
    else:
        for kind in (['page', 'context', 'driver'] if failure == 'all' else [failure]):
            cli.failures[kind] = RuntimeError(PRIVATE)
    assert cli.invoke() == (130 if stop else 1)
    assert cli.closed == (['context', 'driver'] if failure == 'closed-probe'
                          else ['page', 'context', 'driver'])
    assert json.loads((cli.folder / 'run.json').read_bytes())['complete'] is False
    assert cli.exports == 0


def test_interrupt_during_cleanup_takes_precedence_over_capture_error(cli):
    cli.failures['page'] = KeyboardInterrupt(PRIVATE)
    assert cli.invoke() == 130
    assert cli.closed == ['page', 'context', 'driver']
    assert cli.exports == 0


def test_cleanup_interrupt_is_not_hidden_by_later_cleanup_failure(cli):
    cli.failures.update(page=KeyboardInterrupt(PRIVATE), context=PermissionError(PRIVATE),
                        driver=RuntimeError(PRIVATE))
    assert cli.invoke() == 130
    assert cli.closed == ['page', 'context', 'driver']
    assert cli.exports == 0


def test_interrupt_during_checkpoint_returns_stop_and_keeps_old_bytes(cli, monkeypatch):
    original = Path.open
    def opening(path, mode='r', *args, **kwargs):
        if path.name.startswith('run.json.') and mode == 'xb':
            raise KeyboardInterrupt(PRIVATE)
        return original(path, mode, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', opening)
    assert cli.invoke() == 130
    assert (cli.folder / 'run.json').read_bytes() == cli.old
    assert cli.exports == 0


def test_already_closed_page_is_not_closed_again(cli):
    cli.page.is_closed = lambda: True
    assert cli.invoke() == 1
    assert cli.closed == ['context', 'driver']
    assert cli.exports == 0


@pytest.mark.parametrize('failure', ['startup', 'inventory'])
def test_failure_before_inventory_does_not_overwrite_old_checkpoint(cli, failure):
    cli.failures[failure] = RuntimeError(PRIVATE)
    assert cli.invoke() == 1
    assert (cli.folder / 'run.json').read_bytes() == cli.old
    assert cli.closed == ([] if failure == 'startup' else ['page', 'context', 'driver'])
    assert cli.exports == 0


def test_reused_browser_context_is_not_closed_by_cli(cli):
    assert cli.invoke('--reuse-browser', 'http://127.0.0.1:9235') == 1
    assert cli.closed == ['page', 'driver']
    assert cli.exports == 0


def test_export_failure_is_not_retried_in_error_handler(cli, monkeypatch):
    import coretax
    cli.failures['export'] = OSError(errno.ENOSPC, PRIVATE)
    monkeypatch.setattr(coretax, 'collect_details', lambda *a, **k: None)
    monkeypatch.setattr(coretax, 'collect_mpn', lambda *a, **k: None)
    assert cli.invoke() == 1
    assert cli.exports == 1
    assert json.loads((cli.folder / 'run.json').read_bytes())['complete'] is False


def test_successful_body_with_cleanup_failure_is_not_reported_as_success(cli, monkeypatch):
    import coretax
    cli.failures['context'] = RuntimeError(PRIVATE)
    monkeypatch.setattr(coretax, 'collect_details', lambda *a, **k: None)
    monkeypatch.setattr(coretax, 'collect_mpn', lambda *a, **k: None)
    assert cli.invoke() == 1
    assert cli.exports == 1
    assert cli.closed == ['page', 'context', 'driver']
    assert json.loads((cli.folder / 'run.json').read_bytes())['complete'] is False


def test_safe_diagnostics_keep_original_failure_type_without_exception_content(cli, tmp_path, capsys):
    from spt_desktop import diagnostics
    cli.failures['context'] = PermissionError(PRIVATE)
    logs = tmp_path / 'logs'
    with diagnostics.session(logs, 'cli'):
        assert cli.invoke() == 1
    raw = ''.join(path.read_text(encoding='utf-8') for path in logs.rglob('*.jsonl'))
    assert 'RuntimeError' in raw and 'PermissionError' in raw
    assert PRIVATE not in raw + capsys.readouterr().err
