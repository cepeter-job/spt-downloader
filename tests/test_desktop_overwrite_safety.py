"""Synthetic consent races and recovery; never access live taxpayer outputs."""
from copy import deepcopy
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

import coretax
from coretax_browser import CaptureCancelled
from spt_desktop import output
from test_split_output import fixture_run


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
    assert set(snapshot['files']) == {'resume.xlsx', 'SPT Masa 21/SPT_21_Januari 2025.xlsx'}
    assert workbook_bytes(final) == before
    assert not list(downloads.rglob('*.json'))
    assert output.publish_workbooks(run, source, downloads, 'second-job', overwrite=True,
                                    expected_outputs=snapshot) == final
    assert (final / 'SPT Masa 21/SPT_21_Februari 2025.xlsx').read_bytes() == before[
        'SPT Masa 21/SPT_21_Februari 2025.xlsx']


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
        shutil.copy2(final / 'SPT_Badan.xlsx', final / alias)
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


def test_stop_after_replacement_rolls_back_every_old_workbook(tmp_path, monkeypatch):
    run, source, downloads, final = previous_and_selected(tmp_path)
    before = workbook_bytes(final)
    real_replace = Path.replace
    stopped = False

    def replace_then_stop(path, target):
        nonlocal stopped
        result = real_replace(path, target)
        if Path(target).is_relative_to(final):
            stopped = True
        return result

    def check_cancel():
        if stopped:
            raise CaptureCancelled('Synthetic Stop after publication begins')

    monkeypatch.setattr(Path, 'replace', replace_then_stop)
    with pytest.raises(CaptureCancelled):
        output.publish_workbooks(run, source, downloads, 'second-job', check_cancel,
                                 overwrite=True)
    assert stopped
    assert workbook_bytes(final) == before
    assert (source / 'run.json').is_file()


def test_exception_immediately_after_replace_restores_that_workbook(tmp_path, monkeypatch):
    run, source, downloads, final = previous_and_selected(tmp_path)
    before = workbook_bytes(final)
    real_replace = Path.replace
    interrupted = False

    def replace_then_fail(path, target):
        nonlocal interrupted
        result = real_replace(path, target)
        if Path(target) == final / 'resume.xlsx' and not interrupted:
            interrupted = True
            raise PermissionError('Synthetic post-replacement interruption')
        return result

    monkeypatch.setattr(Path, 'replace', replace_then_fail)
    with pytest.raises(PermissionError, match='Synthetic post-replacement'):
        output.publish_workbooks(run, source, downloads, 'second-job', overwrite=True)
    assert interrupted
    assert workbook_bytes(final) == before


def test_blocked_rollback_retains_private_originals_for_recovery(tmp_path, monkeypatch):
    run, source, downloads, final = previous_and_selected(tmp_path)
    before = workbook_bytes(final)
    real_replace = Path.replace
    replaced = False

    def fail_after_first_replacement(path, target):
        nonlocal replaced
        if Path(target).is_relative_to(final):
            if replaced:
                raise PermissionError('Synthetic persistent workbook lock')
            replaced = True
        return real_replace(path, target)

    monkeypatch.setattr(Path, 'replace', fail_after_first_replacement)
    with pytest.raises(RuntimeError, match='recovery files retained') as failure:
        output.publish_workbooks(run, source, downloads, 'second-job', overwrite=True)
    assert replaced
    recovery = Path(str(failure.value).split('recovery files retained at ', 1)[1])
    assert recovery.is_dir() and not recovery.is_relative_to(downloads)
    for name in ('resume.xlsx', 'SPT Masa 21/SPT_21_Januari 2025.xlsx'):
        assert any(path.read_bytes() == before[name] for path in recovery.rglob(Path(name).name))
