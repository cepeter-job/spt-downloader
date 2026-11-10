"""Only sealed, byte-verified COMPLETE jobs are eligible for automatic pruning."""
import json
import os

import pytest

from spt_desktop import job_pruning as prune


def _job(root, number, *, complete, sealed=False, final=None):
    job_id = f'{number:032x}'
    folder = root / 'jobs' / job_id
    folder.mkdir(parents=True)
    saved = {'complete': complete, 'npwp': 'SYNTHETIC', 'year': 2025,
             'year_basis': 'period', 'records': []}
    (folder / 'run.json').write_text(json.dumps(saved), encoding='utf-8')
    (folder / 'source.txt').write_bytes(b'SYNTHETIC PRIVATE SOURCE')
    if sealed:
        assert final is not None
        size, digest = prune._hash_file(final / 'resume.xlsx')
        count, tree = prune._tree_digest(folder, deadline=float('inf'))
        claim = {'schema': 1, 'job_id': job_id,
                 'run_sha256': prune._hash_file(folder / 'run.json')[1],
                 'tree_entries': count, 'tree_sha256': tree,
                 'output': str(final),
                 'files': {'resume.xlsx': [size, digest]}}
        (folder / prune.SEAL).write_text(json.dumps(claim), encoding='utf-8')
    return folder


def _root(tmp_path, monkeypatch):
    root = tmp_path / 'workspace'
    downloads = tmp_path / 'Downloads'
    (root / 'jobs').mkdir(parents=True)
    (downloads / 'synthetic-run').mkdir(parents=True)
    (downloads / 'synthetic-run' / 'resume.xlsx').write_bytes(b'SYNTHETIC PUBLISHED WORKBOOK')
    monkeypatch.setattr(prune, '_windows', lambda: True)
    monkeypatch.setattr('spt_desktop.paths.downloads_folder', lambda: downloads)
    return root, downloads, downloads / 'synthetic-run'


@pytest.mark.parametrize('count', [0, 1, 10, 100])
def test_retention_limit_is_explicit_and_bounded(count):
    assert prune.validate_keep_jobs(count) == count


@pytest.mark.parametrize('count', [-1, 101, True, False, '10', 1.5, None])
def test_invalid_retention_limit_never_authorizes_deletion(count):
    with pytest.raises(ValueError):
        prune.validate_keep_jobs(count)


def test_keep_recent_including_partial_and_prune_only_older_sealed_complete(tmp_path, monkeypatch):
    root, downloads, published = _root(tmp_path, monkeypatch)
    oldest = _job(root, 1, complete=True, sealed=True, final=published)
    unsealed = _job(root, 2, complete=True)
    incomplete = _job(root, 3, complete=False)
    latest = _job(root, 4, complete=True, sealed=True, final=published)
    for ordinal, path in enumerate((oldest, unsealed, incomplete, latest), 1):
        stamp = 1_700_000_000 + ordinal
        os.utime(path, (stamp, stamp))
    assert prune.prune_published_jobs(root, downloads, 1, exclude=latest.name) == 1
    assert not oldest.exists()
    assert unsealed.is_dir() and incomplete.is_dir() and latest.is_dir()
    assert (published / 'resume.xlsx').is_file()
    assert prune.prune_published_jobs(root, downloads, 0) == 0


@pytest.mark.parametrize('defect', ['changed-run', 'changed-output', 'extra-source', 'symlink', 'recovery-notice'])
def test_changed_source_or_publication_is_never_pruned(tmp_path, monkeypatch, defect):
    root, downloads, published = _root(tmp_path, monkeypatch)
    old = _job(root, 1, complete=True, sealed=True, final=published)
    newest = _job(root, 2, complete=False)
    if defect == 'changed-run':
        (old / 'run.json').write_text('{"complete": false}')
    elif defect == 'changed-output':
        (published / 'resume.xlsx').write_bytes(b'SYNTHETIC MODIFICATION')
    elif defect == 'extra-source':
        (old / 'new.txt').write_bytes(b'NEW SOURCE')
    elif defect == 'symlink':
        try:
            (old / 'external.txt').symlink_to(published / 'resume.xlsx')
        except (OSError, NotImplementedError):
            pytest.skip('Symlink privileges unavailable')
    else:
        (old / 'publication-recovery-test.json').write_text('{}')
    assert prune.prune_published_jobs(root, downloads, 1) == 0
    assert old.exists() and newest.exists()


def test_recovery_sibling_disables_pruning_for_all_jobs(tmp_path, monkeypatch):
    root, downloads, published = _root(tmp_path, monkeypatch)
    old = _job(root, 1, complete=True, sealed=True, final=published)
    _job(root, 2, complete=False)
    (root / 'jobs' / '.spt-publish-test').mkdir()
    assert prune.prune_published_jobs(root, downloads, 1) == 0
    assert old.exists()


def test_no_prune_while_ten_runs_fit_retention(tmp_path, monkeypatch):
    root, downloads, published = _root(tmp_path, monkeypatch)
    created = [_job(root, i, complete=True, sealed=True, final=published) for i in range(1, 11)]
    assert prune.prune_published_jobs(root, downloads) == 0
    assert all(folder.exists() for folder in created)


def test_legacy_unsealed_job_stays_even_if_empty_or_old(tmp_path, monkeypatch):
    root, downloads, published = _root(tmp_path, monkeypatch)
    old = _job(root, 1, complete=True)
    _job(root, 2, complete=True, sealed=True, final=published)
    assert prune.prune_published_jobs(root, downloads, 1) == 0
    assert old.exists()


def test_seal_requires_verified_complete_job_and_published_outputs(tmp_path, monkeypatch):
    root, downloads, published = _root(tmp_path, monkeypatch)
    folder = _job(root, 1, complete=True)
    run = json.loads((folder / 'run.json').read_text())
    monkeypatch.setattr('spt_desktop.paths.downloads_folder', lambda: downloads)
    monkeypatch.setattr(prune, '_windows', lambda: True)
    monkeypatch.setattr('spt_desktop.output._selected', lambda value: (['resume.xlsx'], {}))
    assert prune.seal_completed_job(root, folder.name, run, published, downloads)
    assert (folder / prune.SEAL).is_file()
    assert not prune.seal_completed_job(root, folder.name, {**run, 'complete': False}, published, downloads)
    assert not prune.seal_completed_job(root, 'bad-id', run, published, downloads)


def test_foreign_output_or_traversing_receipt_cannot_authorize_cleanup(tmp_path, monkeypatch):
    root, downloads, published = _root(tmp_path, monkeypatch)
    old = _job(root, 1, complete=True, sealed=True, final=published)
    _job(root, 2, complete=False)
    receipt = old / prune.SEAL
    data = json.loads(receipt.read_text())
    data['files'] = {'../resume.xlsx': data['files']['resume.xlsx']}
    receipt.write_text(json.dumps(data))
    assert prune.prune_published_jobs(root, downloads, 1) == 0
    assert old.is_dir()
    data['files'] = {'resume.xlsx': [len(b'foreign'), 'b'*64]}
    data['output'] = str(tmp_path / 'foreign')
    receipt.write_text(json.dumps(data))
    assert prune.prune_published_jobs(root, downloads, 1) == 0
    assert old.is_dir()


def test_saved_preference_defaults_and_rejects_invalid_retention(tmp_path):
    from spt_desktop.app import load_preferences, save_preferences
    assert load_preferences(tmp_path)['keep_jobs'] == 10
    for count in (0, 5, 100):
        save_preferences(tmp_path, {'keep_jobs': count})
        assert load_preferences(tmp_path)['keep_jobs'] == count
    for invalid in (-1, 101, '10', True):
        with pytest.raises(ValueError):
            save_preferences(tmp_path, {'keep_jobs': invalid})
    assert load_preferences(tmp_path)['keep_jobs'] == 100
