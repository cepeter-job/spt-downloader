"""Synthetic regressions for verified, recoverable output publication."""
import json
from pathlib import Path
import subprocess
import sys

import pytest
from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import coretax
from test_split_output import fixture_run


def snapshot(folder):
    return {p.name: p.read_bytes() for p in folder.iterdir() if p.is_file()}


def test_verification_remains_enabled_under_python_optimization(tmp_path):
    run = fixture_run()
    path = coretax.save_output(run, tmp_path)
    wb = load_workbook(path)
    wb['Ringkasan']['B4'] = '0000000000000002'
    wb.save(path)
    wb.close()
    script = (
        'import json,sys,coretax; from pathlib import Path; '
        'folder=Path(sys.argv[1]); '
        'run=json.loads((folder/"run.json").read_text(encoding="utf-8")); '
        'coretax.verify_workbook(folder/"resume.xlsx",run,include_details=False)'
    )
    result = subprocess.run([sys.executable, '-O', '-c', script, str(tmp_path)],
                            cwd=Path(coretax.__file__).parent, capture_output=True, text=True)
    assert result.returncode != 0, 'Optimized Python accepted another taxpayer workbook'
    assert 'NPWP mismatch' in result.stderr


def test_verification_failure_preserves_previous_output(tmp_path, monkeypatch):
    run = fixture_run()
    coretax.save_output(run, tmp_path)
    before = snapshot(tmp_path)
    run['taxpayer_name'] = 'SYNTHETIC REPLACEMENT'
    def fail_verification(*args, **kwargs):
        raise ValueError('Synthetic invalid generated workbook')
    monkeypatch.setattr(coretax, 'verify_workbook', fail_verification)
    with pytest.raises(ValueError, match='Synthetic invalid'):
        coretax.save_output(run, tmp_path)
    assert snapshot(tmp_path) == before


def test_untracked_workbook_cannot_be_overwritten(tmp_path):
    existing = tmp_path / 'resume.xlsx'
    existing.write_bytes(b'SYNTHETIC UNTRACKED DOCUMENT')
    with pytest.raises(FileExistsError, match='scope'):
        coretax.save_output(fixture_run(), tmp_path)
    assert existing.read_bytes() == b'SYNTHETIC UNTRACKED DOCUMENT'


def test_case_insensitive_existing_filename_collision_is_rejected(tmp_path):
    run = fixture_run()
    coretax.save_output(run, tmp_path)
    existing = tmp_path / 'SPT_Badan.xlsx'
    existing.rename(tmp_path / 'spt_badan.XLSX')
    before = snapshot(tmp_path)
    with pytest.raises(FileExistsError, match='collision'):
        coretax.save_output(run, tmp_path)
    assert snapshot(tmp_path) == before


def test_reduced_type_scope_does_not_leave_stale_workbooks(tmp_path):
    run = fixture_run()
    coretax.save_output(run, tmp_path)
    before = snapshot(tmp_path)
    run['records'] = run['records'][:2]
    with pytest.raises(FileExistsError, match='scope'):
        coretax.save_output(run, tmp_path)
    assert snapshot(tmp_path) == before


def test_failed_replacement_rolls_back_completed_replacements(tmp_path, monkeypatch):
    run = fixture_run()
    coretax.save_output(run, tmp_path)
    before = snapshot(tmp_path)
    run['taxpayer_name'] = 'SYNTHETIC NEW NAME'
    real_replace = Path.replace
    failed = False
    def fail_one_replace(source, target):
        nonlocal failed
        target = Path(target)
        if target.parent == tmp_path and target.name == 'SPT_21.xlsx' and not failed:
            failed = True
            raise PermissionError('Synthetic workbook lock')
        return real_replace(source, target)
    monkeypatch.setattr(Path, 'replace', fail_one_replace)
    with pytest.raises(PermissionError, match='Synthetic workbook lock'):
        coretax.save_output(run, tmp_path)
    assert failed
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize('url', [
    'http://user:secret@localhost:9235', 'http://localhost:9235/path',
    'http://localhost:9235?proxy=elsewhere', 'http://localhost:9235#secret',
    'http://localhost:99999', 'http://localhost:0', 'http://localhost:',
    'http://localhost:9235\n', 'http://127.0.0.1.evil.invalid:9235',
])
def test_debugging_endpoint_rejects_ambiguous_or_credential_urls(url):
    validator = getattr(coretax, 'validate_debug_endpoint', None)
    assert callable(validator), 'Explicit debugging endpoint validation is missing'
    with pytest.raises(ValueError):
        validator(url)


@pytest.mark.parametrize('url', [
    'http://127.0.0.1:9235', 'http://localhost:9235/',
    'http://[::1]:9235', 'https://localhost:9235',
])
def test_debugging_endpoint_accepts_explicit_loopback_origins(url):
    validator = getattr(coretax, 'validate_debug_endpoint', None)
    assert callable(validator), 'Explicit debugging endpoint validation is missing'
    assert validator(url) == url


def test_checkpoint_manifest_cannot_authorize_overwriting_other_taxpayer(tmp_path):
    run = fixture_run()
    coretax.save_output(run, tmp_path)
    before = {p.name: p.read_bytes() for p in tmp_path.glob('*.xlsx')}
    other = fixture_run()
    other['npwp'] = '0000000000000002'
    # Capture checkpoints update run.json before Excel is regenerated.
    (tmp_path / 'run.json').write_text(json.dumps(other), encoding='utf-8')
    with pytest.raises(FileExistsError, match='scope'):
        coretax.save_output(other, tmp_path)
    assert {p.name: p.read_bytes() for p in tmp_path.glob('*.xlsx')} == before


def test_resume_link_must_identify_exact_amendment_not_just_existing_sheet(tmp_path):
    run = fixture_run()
    coretax.save_output(run, tmp_path)
    path = tmp_path / 'resume.xlsx'
    wb = load_workbook(path)
    wb['Daftar SPT']['A6'].hyperlink.location = wb['Daftar SPT']['A5'].hyperlink.location
    wb.save(path)
    wb.close()
    with pytest.raises(ValueError, match='detail'):
        coretax.verify_outputs(run, tmp_path)


def test_interrupt_immediately_after_replace_rolls_back_that_file(tmp_path, monkeypatch):
    run = fixture_run()
    coretax.save_output(run, tmp_path)
    before = snapshot(tmp_path)
    run['taxpayer_name'] = 'SYNTHETIC UPDATED NAME'
    real_replace = Path.replace
    interrupted = False
    def interrupt_after_replace(source, target):
        nonlocal interrupted
        result = real_replace(source, target)
        target = Path(target)
        if target.parent == tmp_path and target.name == 'SPT_21.xlsx' and not interrupted:
            interrupted = True
            raise KeyboardInterrupt()
        return result
    monkeypatch.setattr(Path, 'replace', interrupt_after_replace)
    with pytest.raises(KeyboardInterrupt):
        coretax.save_output(run, tmp_path)
    assert snapshot(tmp_path) == before


def test_blocked_rollback_keeps_recoverable_original_files(tmp_path, monkeypatch):
    run = fixture_run()
    coretax.save_output(run, tmp_path)
    before = snapshot(tmp_path)
    run['taxpayer_name'] = 'SYNTHETIC UPDATED NAME'
    real_replace = Path.replace
    def fail_publication_and_rollback(source, target):
        target = Path(target)
        if target.parent == tmp_path and (target.name == 'SPT_21.xlsx' or source.parent.name == 'backup'):
            raise PermissionError('Synthetic persistent file lock')
        return real_replace(source, target)
    monkeypatch.setattr(Path, 'replace', fail_publication_and_rollback)
    with pytest.raises(RuntimeError, match='recovery files retained'):
        coretax.save_output(run, tmp_path)
    recovery, = tmp_path.glob('.spt-export-*')
    assert {p.name: p.read_bytes() for p in (recovery / 'backup').iterdir()} == before
