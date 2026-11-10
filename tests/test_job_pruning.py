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


@pytest.mark.skipif(os.name != 'nt', reason='Native Windows share-denial regression')
def test_native_windows_keeps_all_published_handles_through_private_deletion(tmp_path, monkeypatch):
    """A replacement/write at the precise deletion boundary must be denied."""
    from spt_desktop import profile_lifecycle

    root, downloads, published = _root(tmp_path, monkeypatch)
    second = published / 'attachment.pdf'
    second.write_bytes(b'SYNTHETIC SECOND PUBLISHED SOURCE')
    old = _job(root, 1, complete=True, sealed=True, final=published)
    receipt_file = old / prune.SEAL
    receipt = json.loads(receipt_file.read_text())
    receipt['files']['attachment.pdf'] = list(prune._hash_file(second))
    receipt_file.write_text(json.dumps(receipt))
    newest = _job(root, 2, complete=False)
    old_time = 1_700_000_000
    os.utime(old, (old_time, old_time))
    os.utime(newest, (old_time + 1, old_time + 1))

    original_remove = profile_lifecycle._remove_tree
    observed = []

    def attempt_concurrent_mutations(*args):
        # This runs AFTER _eligible has verified every output and immediately
        # BEFORE the first irreversible private-job deletion.
        assert old.is_dir()
        for target in (published / 'resume.xlsx', second):
            with pytest.raises(OSError):
                with target.open('r+b') as writer:
                    writer.write(b'MODIFIED')
            replacement = target.parent / ('replacement-' + target.name)
            replacement.write_bytes(b'REPLACEMENT MUST REMAIN SEPARATE')
            with pytest.raises(OSError):
                os.replace(replacement, target)
            assert replacement.is_file()
            observed.append(target.name)
        return original_remove(*args)

    monkeypatch.setattr(profile_lifecycle, '_remove_tree', attempt_concurrent_mutations)
    assert prune.prune_published_jobs(root, downloads, keep=1) == 1
    assert set(observed) == {'resume.xlsx', 'attachment.pdf'}
    assert not old.exists()
    assert (published / 'resume.xlsx').read_bytes() == b'SYNTHETIC PUBLISHED WORKBOOK'
    assert second.read_bytes() == b'SYNTHETIC SECOND PUBLISHED SOURCE'


@pytest.mark.skipif(os.name != 'nt', reason='Native Windows share-denial regression')
def test_native_windows_active_writer_blocks_prune_and_preserves_source(tmp_path, monkeypatch):
    """A pre-existing writer must prevent exclusive output custody."""
    root, downloads, published = _root(tmp_path, monkeypatch)
    old = _job(root, 1, complete=True, sealed=True, final=published)
    newest = _job(root, 2, complete=False)
    old_time = 1_700_000_000
    os.utime(old, (old_time, old_time))
    os.utime(newest, (old_time + 1, old_time + 1))
    with (published / 'resume.xlsx').open('r+b'):
        assert prune.prune_published_jobs(root, downloads, keep=1) == 0
        assert old.exists()
    # After the real writer closes, the original sealed COMPLETE job is
    # eligible again. The failed first attempt performed no destructive step.
    assert prune.prune_published_jobs(root, downloads, keep=1) == 1
    assert not old.exists()


def test_manual_preview_is_read_only_and_retains_ten_of_twelve(tmp_path, monkeypatch):
    root, downloads, published = _root(tmp_path, monkeypatch)
    jobs = [_job(root, i, complete=True, sealed=True, final=published)
            for i in range(1, 13)]
    for index, job in enumerate(jobs):
        os.utime(job, (1_700_000_000 + index, 1_700_000_000 + index))
    original = (published / 'resume.xlsx').read_bytes()
    estimate = prune.preview_published_jobs(root, downloads, keep=10)
    assert estimate['eligible_jobs'] == 2
    assert estimate['estimated_bytes'] >= 2 * len(b'SYNTHETIC PRIVATE SOURCE')
    assert all(job.is_dir() for job in jobs)  # Preview cannot remove anything.
    assert prune.prune_published_jobs(root, downloads, keep=10) == 2
    assert all(not job.exists() for job in jobs[:2])
    assert all(job.is_dir() for job in jobs[2:])
    assert (published / 'resume.xlsx').read_bytes() == original


def test_manual_preview_respects_saved_count_and_excluded_job(tmp_path, monkeypatch):
    root, downloads, published = _root(tmp_path, monkeypatch)
    old = _job(root, 1, complete=True, sealed=True, final=published)
    middle = _job(root, 2, complete=True, sealed=True, final=published)
    newest = _job(root, 3, complete=False)
    for index, job in enumerate((old, middle, newest)):
        os.utime(job, (1_700_000_000 + index, 1_700_000_000 + index))
    assert prune.preview_published_jobs(root, downloads, keep=1)['eligible_jobs'] == 2
    assert prune.preview_published_jobs(
        root, downloads, keep=1, exclude=old.name)['eligible_jobs'] == 1
    assert prune.preview_published_jobs(root, downloads, keep=10)['eligible_jobs'] == 0
    assert prune.preview_published_jobs(root, downloads, keep=0)['eligible_jobs'] == 0
    assert old.is_dir() and middle.is_dir() and newest.is_dir()


def test_manual_preview_does_not_authorize_deletion_after_evidence_change(
        tmp_path, monkeypatch):
    root, downloads, published = _root(tmp_path, monkeypatch)
    old = _job(root, 1, complete=True, sealed=True, final=published)
    _job(root, 2, complete=False)
    assert prune.preview_published_jobs(root, downloads, keep=1)['eligible_jobs'] == 1
    (old / 'source.txt').write_bytes(b'CHANGED AFTER PREVIEW')
    assert prune.prune_published_jobs(root, downloads, keep=1) == 0
    assert old.is_dir()
    assert (published / 'resume.xlsx').read_bytes() == b'SYNTHETIC PUBLISHED WORKBOOK'


def test_manual_preview_fail_closed_on_recovery_and_links(tmp_path, monkeypatch):
    root, downloads, published = _root(tmp_path, monkeypatch)
    old = _job(root, 1, complete=True, sealed=True, final=published)
    _job(root, 2, complete=False)
    (root / 'jobs' / '.spt-publish-recovery').mkdir()
    with pytest.raises(ValueError, match='recovery'):
        prune.preview_published_jobs(root, downloads, keep=1)
    (root / 'jobs' / '.spt-publish-recovery').rmdir()
    try:
        (old / 'source-link').symlink_to(published / 'resume.xlsx')
    except (OSError, NotImplementedError):
        pytest.skip('Symlink unavailable')
    assert prune.preview_published_jobs(root, downloads, keep=1)['eligible_jobs'] == 0


def test_manual_preview_and_background_prune_are_serialized(tmp_path, monkeypatch):
    import threading

    root, downloads, published = _root(tmp_path, monkeypatch)
    old = _job(root, 1, complete=True, sealed=True, final=published)
    newest = _job(root, 2, complete=False)
    os.utime(old, (1_700_000_000, 1_700_000_000))
    os.utime(newest, (1_700_000_001, 1_700_000_001))
    entered = threading.Event()
    released = threading.Event()
    original = prune._eligible

    def stalled(*args, **kwargs):
        entered.set()
        assert released.wait(10), 'Synthetic preview must be released'
        return original(*args, **kwargs)

    monkeypatch.setattr(prune, '_eligible', stalled)
    observed = {}
    preview = threading.Thread(target=lambda: observed.setdefault(
        'preview', prune.preview_published_jobs(root, downloads, keep=1)))
    delete = threading.Thread(target=lambda: observed.setdefault(
        'deleted', prune.prune_published_jobs(root, downloads, keep=1)))
    preview.start()
    try:
        assert entered.wait(10)
        delete.start()
        assert old.is_dir()
    finally:
        released.set()
        preview.join(15)
        if delete.ident is not None:
            delete.join(15)
    assert not preview.is_alive() and not delete.is_alive()
    assert observed['preview']['eligible_jobs'] == 1
    assert observed['deleted'] == 1
    assert newest.is_dir() and not old.exists()
