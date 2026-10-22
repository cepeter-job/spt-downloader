"""Process-death publication drills use generated workbooks and no real records."""
import importlib
import importlib.util
import json
import errno
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from test_desktop_overwrite_safety import previous_and_selected, workbook_bytes


CRASH_CHILD = r'''
import json, os, sys
from pathlib import Path
from spt_desktop import output
source, downloads, final = map(Path, sys.argv[1:4])
boundary = sys.argv[4]
run = json.loads((source / 'run.json').read_text(encoding='utf-8'))
real_move = output._move_no_replace
def move(source_path, target_path):
    source_path, target_path = Path(source_path), Path(target_path)
    result = real_move(source_path, target_path)
    selected = final / 'SPT Masa 21' / 'SPT_21_Januari 2025_Normal.xlsx'
    if ((boundary == 'displaced' and source_path == selected)
            or (boundary == 'installed' and target_path == selected)
            or (boundary == 'index' and target_path == final / 'resume.xlsx')):
        os._exit(73)
    return result
output._move_no_replace = move
output.publish_workbooks(run, source, downloads, 'crash-job', overwrite=True)
raise SystemExit('The requested real publication boundary was not reached')
'''


def crash_publication(tmp_path, boundary):
    _, source, downloads, final = previous_and_selected(tmp_path)
    before = workbook_bytes(final)
    child = subprocess.run([sys.executable, '-c', CRASH_CHILD, str(source),
                            str(downloads), str(final), boundary],
                           capture_output=True, text=True, timeout=90)
    assert child.returncode == 73, child.stderr
    return source, downloads, final, before


def recovery():
    assert importlib.util.find_spec('spt_desktop.publication_recovery'), \
        'Restart-safe publication recovery is missing'
    return importlib.import_module('spt_desktop.publication_recovery')


@pytest.mark.parametrize('boundary', ['displaced', 'installed', 'index'])
def test_hard_exit_has_durable_private_recovery_before_any_output_move(tmp_path, boundary):
    source, downloads, final, _ = crash_publication(tmp_path, boundary)
    notices = list(source.glob('publication-recovery-*.json'))
    assert len(notices) == 1, 'Process death lost the private recovery location'
    notice = json.loads(notices[0].read_text(encoding='utf-8'))
    manifest = Path(notice['manifest'])
    assert manifest.is_file(), 'Recovery journal was not durable before output mutation'
    state = json.loads(manifest.read_text(encoding='utf-8'))
    assert state['state'] == 'pending'
    assert state['target'] == str(final)
    assert state['entries'], 'Recovery must identify each possibly displaced file'
    assert not list(downloads.rglob('*.json')), 'Private manifests must stay out of Downloads'


@pytest.mark.parametrize('boundary', ['displaced', 'installed', 'index'])
def test_restart_restores_exact_old_bytes_and_preserves_unselected_outputs(tmp_path, boundary):
    module = recovery()
    source, downloads, final, before = crash_publication(tmp_path, boundary)
    result = module.recover_publication(source, downloads)
    assert result == final
    assert workbook_bytes(final) == before
    assert not list(final.rglob('*.recovery'))
    assert module.recover_publication(source, downloads) == final, 'Recovery must be repeatable'


def test_restart_refuses_concurrent_output_edit_without_discarding_recovery(tmp_path):
    module = recovery()
    source, downloads, final, _ = crash_publication(tmp_path, 'installed')
    selected = final / 'SPT Masa 21' / 'SPT_21_Januari 2025_Normal.xlsx'
    concurrent = b'SYNTHETIC UNAPPROVED POST-CRASH CHANGE'
    selected.write_bytes(concurrent)
    with pytest.raises((ValueError, RuntimeError), match='changed|unapproved|recovery'):
        module.recover_publication(source, downloads)
    assert selected.read_bytes() == concurrent
    assert list(source.glob('publication-recovery-*.json'))
    assert list(source.parent.glob('.spt-publish-*'))


def test_restart_rejects_target_redirect_without_touching_outside_files(tmp_path):
    module = recovery()
    source, downloads, final, _ = crash_publication(tmp_path, 'displaced')
    original = final.with_name(final.name + '-kept')
    final.rename(original)
    outside = tmp_path / 'outside'
    outside.mkdir()
    marker = outside / 'keep.txt'
    marker.write_bytes(b'SYNTHETIC UNRELATED DATA')
    if sys.platform == 'win32':
        subprocess.run(['cmd', '/d', '/c', 'mklink', '/J', str(final), str(outside)],
                       check=True, capture_output=True, timeout=10)
    else:
        final.symlink_to(outside, target_is_directory=True)
    with pytest.raises((ValueError, RuntimeError), match='path|reparse|changed|recovery'):
        module.recover_publication(source, downloads)
    assert marker.read_bytes() == b'SYNTHETIC UNRELATED DATA'
    assert list(outside.iterdir()) == [marker]


def test_changed_recovery_manifest_cannot_redirect_restoration(tmp_path):
    module = recovery()
    source, downloads, final, _ = crash_publication(tmp_path, 'installed')
    before = workbook_bytes(final)
    notice, = source.glob('publication-recovery-*.json')
    manifest = Path(json.loads(notice.read_text(encoding='utf-8'))['manifest'])
    data = json.loads(manifest.read_text(encoding='utf-8'))
    outside = tmp_path / 'outside'
    outside.mkdir()
    marker = outside / 'keep.xlsx'
    marker.write_bytes(b'SYNTHETIC UNRELATED FILE')
    data['target'] = str(outside)
    manifest.write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises((ValueError, RuntimeError), match='scope|target|recovery|path'):
        module.recover_publication(source, downloads)
    assert workbook_bytes(final) == before
    assert marker.read_bytes() == b'SYNTHETIC UNRELATED FILE'


def test_journal_write_failure_prevents_any_original_output_move(tmp_path, monkeypatch):
    module = recovery()
    from spt_desktop import output
    run, source, downloads, final = previous_and_selected(tmp_path)
    before = workbook_bytes(final)
    real_write = module._write
    def fail_journal(path, value):
        if Path(path).name == 'manifest.json' and value.get('entries'):
            raise OSError('Synthetic recovery volume full before first replacement')
        return real_write(path, value)
    monkeypatch.setattr(module, '_write', fail_journal)
    with pytest.raises(OSError, match='Synthetic recovery volume full'):
        output.publish_workbooks(run, source, downloads, 'journal-full', overwrite=True)
    assert workbook_bytes(final) == before
    assert not list(final.rglob('*.recovery'))


def test_changed_private_backup_refuses_recovery_before_modifying_public_files(tmp_path):
    module = recovery()
    source, downloads, final, _ = crash_publication(tmp_path, 'installed')
    before = workbook_bytes(final)
    notice, = source.glob('publication-recovery-*.json')
    manifest = Path(json.loads(notice.read_text(encoding='utf-8'))['manifest'])
    backup = manifest.parent / 'backup' / 'SPT Masa 21' / 'SPT_21_Januari 2025_Normal.xlsx'
    backup.write_bytes(b'SYNTHETIC CHANGED PRIVATE BACKUP')
    with pytest.raises(ValueError, match='backup changed'):
        module.recover_publication(source, downloads)
    assert workbook_bytes(final) == before


def test_second_process_death_during_backup_copy_can_be_retried(tmp_path):
    module = recovery()
    source, downloads, final, before = crash_publication(tmp_path, 'installed')
    notice, = source.glob('publication-recovery-*.json')
    manifest = Path(json.loads(notice.read_text(encoding='utf-8'))['manifest'])
    data = json.loads(manifest.read_text(encoding='utf-8'))
    # A prior blocked rollback may have retained the verified private backup
    # while cleaning its same-volume original. Exercise that actual fallback.
    for entry in data['entries']:
        if entry['original']:
            (final / entry['original']).unlink(missing_ok=True)
    child_code = r'''
import os, sys
from pathlib import Path
from spt_desktop import publication_recovery as recovery
def interrupted_copy(source, destination, *args):
    destination.write(source.read(128))
    destination.flush()
    os._exit(79)
recovery.shutil.copyfileobj = interrupted_copy
recovery.recover_publication(Path(sys.argv[1]), Path(sys.argv[2]))
'''
    child = subprocess.run([sys.executable, '-c', child_code, str(source), str(downloads)],
                           capture_output=True, text=True, timeout=90)
    assert child.returncode == 79, child.stderr
    assert module.recover_publication(source, downloads) == final
    assert workbook_bytes(final) == before
    assert not list(final.rglob('*.recovery'))


def test_recovery_requires_native_custody_before_any_output_change(tmp_path, monkeypatch):
    module = recovery()
    source, downloads, final, _ = crash_publication(tmp_path, 'installed')
    before = workbook_bytes(final)
    monkeypatch.setattr(module, 'sys', SimpleNamespace(platform='unsupported'), raising=False)
    with pytest.raises(OSError) as failure:
        module.recover_publication(source, downloads)
    assert failure.value.errno == errno.ENOTSUP
    assert workbook_bytes(final) == before


def test_changed_displaced_file_at_final_cleanup_is_retained(tmp_path, monkeypatch):
    module = recovery()
    from spt_desktop import output_windows
    remove = getattr(output_windows, 'delete_verified', None)
    assert callable(remove), 'Recovery cleanup needs held native file custody'
    source, downloads, final, before = crash_publication(tmp_path, 'installed')
    raced = []
    changed = b'SYNTHETIC UNAPPROVED CHANGE AT RECOVERY CLEANUP'
    def change_before_delete(path, expected):
        path.write_bytes(changed)
        raced.append(path)
        return remove(path, expected)
    monkeypatch.setattr(module, 'delete_verified', change_before_delete, raising=False)
    with pytest.raises(ValueError, match='changed|state|fingerprint|bytes'):
        module.recover_publication(source, downloads)
    assert raced and all(path.read_bytes() == changed for path in raced)
    assert workbook_bytes(final) == before
    assert list(source.glob('publication-recovery-*.json'))
