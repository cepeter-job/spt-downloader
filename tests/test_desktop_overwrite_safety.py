"""Synthetic consent races and recovery; never access live taxpayer outputs."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

import coretax
from coretax_browser import CaptureCancelled
from spt_desktop import output
from support_runs import fixture_run


def workbook_bytes(folder):
    return {path.relative_to(folder).as_posix(): path.read_bytes()
            for path in folder.rglob('*.xlsx')}


def previous_and_selected(tmp_path):
    assert callable(getattr(output, 'existing_outputs', None)), 'Consent-bound output inspection is missing'
    run = fixture_run()
    source = tmp_path / 'old-source'
    downloads = tmp_path / 'Downloads'
    coretax.save_output(run, source)
    final = output.publish_workbooks(run, source, downloads, 'first-job')
    selected = deepcopy(run)
    selected['records'] = selected['records'][2:3]
    selected['records'][0]['sections'][0]['fields'][0]['value'] = 'SYNTHETIC REPLACEMENT'
    source = tmp_path / 'new-source'
    coretax.save_output(selected, source)
    return selected, source, downloads, final


def test_consent_snapshot_lists_only_workbooks_that_would_be_replaced(tmp_path):
    run, source, downloads, final = previous_and_selected(tmp_path)
    before = workbook_bytes(final)
    snapshot = output.existing_outputs(run, downloads)
    assert set(snapshot['files']) == {'resume.xlsx', 'SPT Masa 21/SPT_21_Januari 2025_Normal.xlsx'}
    assert workbook_bytes(final) == before
    assert not list(downloads.rglob('*.json'))
    assert output.publish_workbooks(run, source, downloads, 'second-job', overwrite=True,
                                    expected_outputs=snapshot) == final
    assert (final / 'SPT Masa 21/SPT_21_Februari 2025_Normal.xlsx').read_bytes() == before[
        'SPT Masa 21/SPT_21_Februari 2025_Normal.xlsx']


def test_workbook_changed_while_consent_is_open_is_not_replaced(tmp_path):
    run, source, downloads, final = previous_and_selected(tmp_path)
    snapshot = output.existing_outputs(run, downloads)
    changed = final / 'resume.xlsx'
    changed.write_bytes(changed.read_bytes() + b'SYNTHETIC CONCURRENT EDIT')
    before = workbook_bytes(final)
    with pytest.raises(ValueError, match='changed|consent|snapshot'):
        output.publish_workbooks(run, source, downloads, 'second-job', overwrite=True,
                                 expected_outputs=snapshot)
    assert workbook_bytes(final) == before


def test_captured_consent_never_switches_to_a_newer_export_folder(tmp_path):
    run, source, downloads, final = previous_and_selected(tmp_path)
    snapshot = output.existing_outputs(run, downloads)
    newer = final.parent / '20991231-235959-999999-newer-job'
    shutil.copytree(final, newer)
    untouched = workbook_bytes(newer)
    assert output.publish_workbooks(run, source, downloads, 'second-job', overwrite=True,
                                    expected_outputs=snapshot) == final
    assert workbook_bytes(newer) == untouched


@pytest.mark.parametrize('alias', ['UNTRACKED.xlsx', 'RESUME.xlsx'])
def test_unknown_or_case_alias_workbook_cannot_be_authorized(tmp_path, alias):
    run, source, downloads, final = previous_and_selected(tmp_path)
    if alias == 'RESUME.xlsx':
        (final / 'resume.xlsx').rename(final / alias)
    else:
        shutil.copy2(final / 'SPT_Badan_Januari - Desember 2025_Normal.xlsx', final / alias)
    before = workbook_bytes(final)
    with pytest.raises(ValueError, match='filename|collision|scope|unknown'):
        output.publish_workbooks(run, source, downloads, 'second-job', overwrite=True)
    assert workbook_bytes(final) == before


def test_sanitized_period_collision_cannot_replace_a_different_literal_period(tmp_path):
    assert callable(getattr(output, 'existing_outputs', None)), 'Consent-bound output inspection is missing'
    run = fixture_run()
    run['records'] = run['records'][2:3]
    run['records'][0]['meta']['Masa Pajak'] = 'Januari/2025'
    coretax.save_output(run, tmp_path / 'old-source')
    final = output.publish_workbooks(run, tmp_path / 'old-source', tmp_path / 'Downloads', 'first-job')
    before = workbook_bytes(final)
    run['records'][0]['meta']['Masa Pajak'] = 'Januari:2025'
    coretax.save_output(run, tmp_path / 'new-source')
    with pytest.raises(ValueError, match='period|collision|scope'):
        output.publish_workbooks(run, tmp_path / 'new-source', tmp_path / 'Downloads', 'second-job',
                                 overwrite=True)
    assert workbook_bytes(final) == before


def test_redirected_destination_after_consent_keeps_original_and_outside_files(tmp_path):
    run, source, downloads, final = previous_and_selected(tmp_path)
    snapshot = output.existing_outputs(run, downloads)
    before = workbook_bytes(final)
    moved = tmp_path / 'original-result'
    final.rename(moved)
    outside = tmp_path / 'outside'
    outside.mkdir()
    if sys.platform == 'win32':
        subprocess.run(['cmd', '/d', '/c', 'mklink', '/J', str(final), str(outside)],
                       check=True, capture_output=True, text=True, timeout=10)
    else:
        final.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match='changed|path|reparse|Downloads'):
        output.publish_workbooks(run, source, downloads, 'second-job', overwrite=True,
                                 expected_outputs=snapshot)
    assert workbook_bytes(moved) == before
    assert list(outside.iterdir()) == []


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows directory sharing and junction regression')
@pytest.mark.parametrize('phase', ['publication', 'rollback'])
def test_junction_at_replace_boundary_cannot_overwrite_unapproved_outside_bytes(tmp_path, monkeypatch, phase):
    run, source, downloads, final = previous_and_selected(tmp_path)
    snapshot = output.existing_outputs(run, downloads)
    before = workbook_bytes(final)
    period = final / 'SPT Masa 21'
    selected_path = period / 'SPT_21_Januari 2025_Normal.xlsx'
    moved = tmp_path / 'original-period'
    outside = tmp_path / 'unapproved-outside'
    outside.mkdir()
    unrelated = outside / selected_path.name
    outside_bytes = b'SYNTHETIC OUTSIDE FILE: THESE UNAPPROVED BYTES MUST NEVER BE REPLACED'
    unrelated.write_bytes(outside_bytes)
    real_move = output._move_no_replace
    selected_replacements = 0
    attempted = False

    def redirect_at_actual_replacement(path, destination):
        nonlocal selected_replacements, attempted
        path = Path(path)
        destination = Path(destination)
        if phase == 'rollback' and path == final / 'resume.xlsx':
            raise PermissionError('Synthetic later file lock requires rollback')
        if path == selected_path:
            selected_replacements += 1
            boundary = 1 if phase == 'publication' else 2
            if selected_replacements == boundary:
                attempted = True
                # All production pathname checks have already happened at this boundary.
                try:
                    period.rename(moved)
                except OSError:
                    if phase == 'publication':
                        raise  # Abort the controlled publication with the original bytes intact.
                    # A denied redirect must still allow the pending rollback to restore its file.
                else:
                    subprocess.run(['cmd', '/d', '/c', 'mklink', '/J', str(period), str(outside)],
                                   check=True, capture_output=True, text=True, timeout=10)
        return real_move(path, destination)

    monkeypatch.setattr(output, '_move_no_replace', redirect_at_actual_replacement)
    with pytest.raises((OSError, ValueError, RuntimeError)):
        output.publish_workbooks(run, source, downloads, 'second-job', overwrite=True,
                                 expected_outputs=snapshot)
    assert attempted, 'The actual publication/rollback replacement boundary was not exercised'
    assert unrelated.read_bytes() == outside_bytes, 'Unapproved outside bytes were overwritten before rejection'
    original_period = moved if moved.exists() else period
    expected_period = {name.split('/', 1)[1]: value for name, value in before.items()
                       if name.startswith('SPT Masa 21/')}
    assert workbook_bytes(original_period) == expected_period
    for name, value in before.items():
        if not name.startswith('SPT Masa 21/'):
            assert (final / name).read_bytes() == value
    # Any directory handles used by the failed transaction must have been released.
    released = tmp_path / 'period-after-transaction'
    original_period.rename(released)
    released.rename(original_period)


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows replacement transaction regression')
@pytest.mark.parametrize('mutation', ['write', 'replace'])
def test_selected_file_changed_at_replace_boundary_is_preserved_and_not_certified(tmp_path, monkeypatch, mutation):
    run, source, downloads, final = previous_and_selected(tmp_path)
    snapshot = output.existing_outputs(run, downloads)
    selected_path = final / 'SPT Masa 21/SPT_21_Januari 2025_Normal.xlsx'
    original_bytes = selected_path.read_bytes()
    raced_bytes = b'SYNTHETIC CONCURRENT VERSION: PRESERVE THESE DISTINCT UNAPPROVED BYTES'
    real_move = output._move_no_replace
    attempted = False
    changed = False

    def change_after_last_check(path, destination):
        nonlocal attempted, changed
        destination = Path(destination)
        if Path(path) == selected_path and not attempted:
            attempted = True
            # The consent fingerprint has already been checked by the caller.
            if mutation == 'write':
                selected_path.write_bytes(raced_bytes)
            else:
                replacement = tmp_path / 'concurrent-version.xlsx'
                replacement.write_bytes(raced_bytes)
                replacement.replace(selected_path)
            changed = True
        return real_move(path, destination)

    monkeypatch.setattr(output, '_move_no_replace', change_after_last_check)
    failure = None
    try:
        output.publish_workbooks(run, source, downloads, 'second-job', overwrite=True,
                                 expected_outputs=snapshot)
    except (OSError, ValueError, RuntimeError) as error:
        failure = error
    assert attempted, 'The actual workbook replacement boundary was not exercised'
    if changed:
        assert any(path.read_bytes() == raced_bytes for path in tmp_path.rglob('*') if path.is_file()), (
            'The concurrent workbook version was overwritten without retaining recoverable bytes')
    else:
        assert selected_path.read_bytes() == original_bytes
    assert failure is not None, 'Publication certified a result after a concurrent workbook mutation'


def test_stop_after_replacement_rolls_back_every_old_workbook(tmp_path, monkeypatch):
    run, source, downloads, final = previous_and_selected(tmp_path)
    before = workbook_bytes(final)
    real_move = output._move_no_replace
    stopped = False

    def replace_then_stop(path, target):
        nonlocal stopped
        result = real_move(path, target)
        if Path(target).is_relative_to(final) and Path(target).suffix == '.xlsx':
            stopped = True
        return result

    def check_cancel():
        if stopped:
            raise CaptureCancelled('Synthetic Stop after publication begins')

    monkeypatch.setattr(output, '_move_no_replace', replace_then_stop)
    with pytest.raises(CaptureCancelled):
        output.publish_workbooks(run, source, downloads, 'second-job', check_cancel,
                                 overwrite=True)
    assert stopped
    assert workbook_bytes(final) == before
    assert (source / 'run.json').is_file()


def test_exception_immediately_after_replace_restores_that_workbook(tmp_path, monkeypatch):
    run, source, downloads, final = previous_and_selected(tmp_path)
    before = workbook_bytes(final)
    real_move = output._move_no_replace
    interrupted = False

    def replace_then_fail(path, target):
        nonlocal interrupted
        result = real_move(path, target)
        if Path(target) == final / 'resume.xlsx' and not interrupted:
            interrupted = True
            raise PermissionError('Synthetic post-replacement interruption')
        return result

    monkeypatch.setattr(output, '_move_no_replace', replace_then_fail)
    with pytest.raises(PermissionError, match='Synthetic post-replacement'):
        output.publish_workbooks(run, source, downloads, 'second-job', overwrite=True)
    assert interrupted
    assert workbook_bytes(final) == before


def test_blocked_rollback_retains_private_originals_for_recovery(tmp_path, monkeypatch):
    run, source, downloads, final = previous_and_selected(tmp_path)
    before = workbook_bytes(final)
    real_move = output._move_no_replace
    replaced = False

    def fail_after_first_replacement(path, target):
        nonlocal replaced
        if Path(target).is_relative_to(final) and Path(target).suffix == '.xlsx':
            if replaced:
                raise PermissionError('Synthetic persistent workbook lock')
            replaced = True
        return real_move(path, target)

    monkeypatch.setattr(output, '_move_no_replace', fail_after_first_replacement)
    with pytest.raises(RuntimeError, match='recovery files retained') as failure:
        output.publish_workbooks(run, source, downloads, 'second-job', overwrite=True)
    assert replaced
    recovery = Path(str(failure.value).split('recovery files retained at ', 1)[1])
    assert recovery.is_dir() and not recovery.is_relative_to(downloads)
    for name in ('resume.xlsx', 'SPT Masa 21/SPT_21_Januari 2025_Normal.xlsx'):
        assert any(path.read_bytes() == before[name] for path in recovery.rglob(Path(name).name))


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows no-clobber publication regression')
def test_a_workbook_appearing_in_the_empty_destination_gap_is_kept(tmp_path, monkeypatch):
    run, source, downloads, final = previous_and_selected(tmp_path)
    selected_path = final / 'SPT Masa 21/SPT_21_Januari 2025_Normal.xlsx'
    original_bytes = selected_path.read_bytes()
    newcomer = b'SYNTHETIC GAP ARRIVAL: THIS DIFFERENT FILE MUST NOT BE OVERWRITTEN'
    real_move = output._move_no_replace
    attempted = False

    def create_after_original_moves(path, destination):
        nonlocal attempted
        result = real_move(path, destination)
        if Path(path) == selected_path and not attempted:
            attempted = True
            assert not selected_path.exists()
            selected_path.write_bytes(newcomer)
        return result

    monkeypatch.setattr(output, '_move_no_replace', create_after_original_moves)
    with pytest.raises(RuntimeError, match='recovery files retained') as failure:
        output.publish_workbooks(run, source, downloads, 'second-job', overwrite=True)
    assert attempted, 'The empty public destination interval was not exercised'
    assert selected_path.read_bytes() == newcomer
    recovery = Path(str(failure.value).split('recovery files retained at ', 1)[1])
    assert any(path.read_bytes() == original_bytes for path in recovery.rglob(selected_path.name))


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows move journal regression')
def test_exception_immediately_after_moving_original_aside_preserves_it(tmp_path, monkeypatch):
    run, source, downloads, final = previous_and_selected(tmp_path)
    before = workbook_bytes(final)
    selected_path = final / 'SPT Masa 21/SPT_21_Januari 2025_Normal.xlsx'
    real_move = output._move_no_replace
    attempted = False

    def fail_after_actual_move(path, destination):
        nonlocal attempted
        result = real_move(path, destination)
        if Path(path) == selected_path and not attempted:
            attempted = True
            raise PermissionError('Synthetic interruption after original moved aside')
        return result

    monkeypatch.setattr(output, '_move_no_replace', fail_after_actual_move)
    with pytest.raises(PermissionError, match='after original moved aside'):
        output.publish_workbooks(run, source, downloads, 'second-job', overwrite=True)
    assert attempted, 'The completed original-file move was not exercised'
    assert workbook_bytes(final) == before


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows same-volume recovery regression')
def test_failed_private_recovery_copy_keeps_and_records_the_raced_version(tmp_path, monkeypatch):
    run, source, downloads, final = previous_and_selected(tmp_path)
    selected_path = final / 'SPT Masa 21/SPT_21_Januari 2025_Normal.xlsx'
    raced_bytes = b'SYNTHETIC RECOVERY COPY FAILURE: THIS ACTUAL DISPLACED VERSION MUST SURVIVE'
    real_move = output._move_no_replace
    real_copy = output.shutil.copy2
    captured = None
    attempted = False
    copy_attempted = False

    def mutate_at_capture(path, destination):
        nonlocal captured, attempted
        if Path(path) == selected_path and not attempted:
            attempted = True
            selected_path.write_bytes(raced_bytes)
            captured = Path(destination)
        return real_move(path, destination)

    def fail_private_copy(path, destination, *args, **kwargs):
        nonlocal copy_attempted
        if captured is not None and Path(path) == captured and not Path(destination).is_relative_to(downloads):
            copy_attempted = True
            raise OSError('Synthetic private recovery disk is full')
        return real_copy(path, destination, *args, **kwargs)

    monkeypatch.setattr(output, '_move_no_replace', mutate_at_capture)
    monkeypatch.setattr(output.shutil, 'copy2', fail_private_copy)
    with pytest.raises(RuntimeError, match='same-volume recovery'):
        output.publish_workbooks(run, source, downloads, 'second-job', overwrite=True)
    assert attempted and copy_attempted, 'Both the actual capture and failed private copy must be exercised'
    assert captured.is_file() and captured.read_bytes() == raced_bytes
    notices = list(source.glob('publication-recovery-*.json'))
    assert len(notices) == 1
    locations = [Path(path) for path in json.loads(notices[0].read_text(encoding='utf-8'))['recovery_files']]
    assert any(captured.is_relative_to(path) for path in locations)
    assert all(path.exists() for path in locations)
    assert not list(downloads.rglob('*.json'))
