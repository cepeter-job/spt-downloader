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

    def attempt_concurrent_mutations(*args, **kwargs):
        # The verified source inventory is passed as a keyword-only argument.
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
        return original_remove(*args, **kwargs)

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


def test_preview_only_authorizes_exact_verified_ids_and_ignores_later_eligibility(
        tmp_path, monkeypatch):
    root, downloads, published = _root(tmp_path, monkeypatch)
    skipped = _job(root, 1, complete=True, sealed=True, final=published)
    approved = _job(root, 2, complete=True, sealed=True, final=published)
    recent = _job(root, 3, complete=False)
    for index, job in enumerate((skipped, approved, recent)):
        os.utime(job, (1_700_000_000 + index, 1_700_000_000 + index))
    original = prune._eligible

    def fail_first_during_preview(job, *args, **kwargs):
        if job == skipped and kwargs.get('preview_bytes') is not None:
            raise TimeoutError('synthetic preview-only timeout')
        return original(job, *args, **kwargs)

    monkeypatch.setattr(prune, '_eligible', fail_first_during_preview)
    preview = prune.preview_published_jobs(root, downloads, keep=1)
    assert preview['eligible_jobs'] == 1
    assert preview['scan_complete'] is False
    assert preview['candidate_ids'] == (approved.name,)
    # The skipped job now passes checks, but can NEVER expand a confirmation.
    assert prune.prune_published_jobs(root, downloads, keep=1,
                                      allowed_ids=preview['candidate_ids']) == 1
    assert skipped.is_dir() and recent.is_dir() and not approved.exists()
    assert (published / 'resume.xlsx').is_file()


def test_missing_legacy_seal_does_not_make_entire_preview_incomplete(
        tmp_path, monkeypatch):
    root, downloads, published = _root(tmp_path, monkeypatch)
    legacy = _job(root, 1, complete=True)
    sealed = _job(root, 2, complete=True, sealed=True, final=published)
    _job(root, 3, complete=False)
    for index, job in enumerate((legacy, sealed)):
        os.utime(job, (1_700_000_000 + index, 1_700_000_000 + index))
    preview = prune.preview_published_jobs(root, downloads, keep=1)
    assert preview['scan_complete'] is True
    assert preview['candidate_ids'] == (sealed.name,)
    assert legacy.exists()


@pytest.mark.parametrize('ids', [
    ('../escape',), ('ABC',), (None,), ('a' * 32, 'a' * 32),
    ['a' * 32], 'a' * 32,
])
def test_untrusted_candidate_sets_fail_closed(tmp_path, monkeypatch, ids):
    root, downloads, _ = _root(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match='approved prune'):
        prune.prune_published_jobs(root, downloads, keep=1, allowed_ids=ids)


def test_source_guard_is_held_before_eligibility_and_until_removal(
        tmp_path, monkeypatch):
    root, downloads, published = _root(tmp_path, monkeypatch)
    old = _job(root, 1, complete=True, sealed=True, final=published)
    recent = _job(root, 2, complete=False)
    os.utime(old, (1_700_000_000, 1_700_000_000))
    os.utime(recent, (1_700_000_001, 1_700_000_001))
    original_guard = prune.DirectoryGuard
    original_eligible = prune._eligible
    from spt_desktop import profile_lifecycle
    original_remove = profile_lifecycle._remove_tree
    guards, checks = [], []

    class ObservedGuard(original_guard):
        def __enter__(self):
            guards.append(self)
            return super().__enter__()

        def __exit__(self, *exc):
            try:
                return super().__exit__(*exc)
            finally:
                guards.remove(self)

    def require_guard(*args, **kwargs):
        assert any(old in guard._entries for guard in guards)
        checks.append('verify')
        return original_eligible(*args, **kwargs)

    def require_guard_for_delete(*args, **kwargs):
        assert any(old in guard._entries for guard in guards)
        assert checks == ['verify']
        return original_remove(*args, **kwargs)

    monkeypatch.setattr(prune, 'DirectoryGuard', ObservedGuard)
    monkeypatch.setattr(prune, '_eligible', require_guard)
    monkeypatch.setattr(profile_lifecycle, '_remove_tree', require_guard_for_delete)
    assert prune.prune_published_jobs(root, downloads, keep=1) == 1
    assert not guards and not old.exists()


@pytest.mark.skipif(os.name != 'nt', reason='Win32 native directory identity lease')
def test_win32_source_directory_cannot_be_replaced_during_verification(
        tmp_path, monkeypatch):
    root, downloads, published = _root(tmp_path, monkeypatch)
    old = _job(root, 1, complete=True, sealed=True, final=published)
    recent = _job(root, 2, complete=False)
    os.utime(old, (1_700_000_000, 1_700_000_000))
    os.utime(recent, (1_700_000_001, 1_700_000_001))
    original = prune._eligible

    def try_replace(job, *args, **kwargs):
        replacement = job.with_name(job.name + '-renamed')
        with pytest.raises(OSError):
            os.replace(job, replacement)
        assert job.exists()
        return original(job, *args, **kwargs)

    monkeypatch.setattr(prune, '_eligible', try_replace)
    assert prune.prune_published_jobs(root, downloads, keep=1) == 1
    assert not old.exists() and recent.is_dir()


def test_source_and_published_file_hashing_respects_chunk_deadline(
        tmp_path, monkeypatch):
    root, downloads, published = _root(tmp_path, monkeypatch)
    source = root / 'hash-synthetic.bin'
    source.write_bytes(b'X' * (3 * 1024 * 1024))
    real_clock = prune.time.monotonic

    def force_midstream_expiration(func):
        ticks = iter([0.1 * n for n in range(1, 100)])
        monkeypatch.setattr(prune.time, 'monotonic', lambda: next(ticks))
        try:
            with pytest.raises(TimeoutError):
                func()
        finally:
            monkeypatch.setattr(prune.time, 'monotonic', real_clock)

    force_midstream_expiration(lambda: prune._hash_file(source, deadline=0.35))
    with source.open('rb') as stream:
        force_midstream_expiration(
            lambda: prune._hash_held_output(stream, deadline=0.35))
    assert source.read_bytes() == b'X' * (3 * 1024 * 1024)


def test_crash_mid_prune_is_fail_closed_on_restart_and_preserves_downloads(
        tmp_path, monkeypatch):
    from spt_desktop import profile_lifecycle
    root, downloads, published = _root(tmp_path, monkeypatch)
    old = _job(root, 1, complete=True, sealed=True, final=published)
    recent = _job(root, 2, complete=False)
    os.utime(old, (1_700_000_000, 1_700_000_000))
    os.utime(recent, (1_700_000_001, 1_700_000_001))
    real_remove = profile_lifecycle._remove_tree

    def interrupted_remove(*args, **kwargs):
        (old / 'source.txt').unlink()
        raise OSError('synthetic interruption after initial deletion')

    monkeypatch.setattr(profile_lifecycle, '_remove_tree', interrupted_remove)
    assert prune.prune_published_jobs(root, downloads, keep=1) == 0
    assert old.is_dir() and recent.is_dir()
    assert (published / 'resume.xlsx').read_bytes() == b'SYNTHETIC PUBLISHED WORKBOOK'
    monkeypatch.setattr(profile_lifecycle, '_remove_tree', real_remove)
    # A restart cannot treat the now-broken seal as authorization.
    assert prune.prune_published_jobs(root, downloads, keep=1) == 0
    assert old.is_dir()


def test_preview_space_accounting_is_exact_for_unmodified_synthetic_tree(
        tmp_path, monkeypatch):
    root, downloads, published = _root(tmp_path, monkeypatch)
    old = _job(root, 1, complete=True, sealed=True, final=published)
    recent = _job(root, 2, complete=False)
    os.utime(old, (1_700_000_000, 1_700_000_000))
    os.utime(recent, (1_700_000_001, 1_700_000_001))
    expected = sum(path.stat().st_size for path in old.rglob('*') if path.is_file())
    preview = prune.preview_published_jobs(root, downloads, keep=1)
    assert preview['scan_complete'] is True
    assert preview['estimated_bytes'] == expected
    assert old.is_dir()  # preview must not change the file count or bytes
    assert prune.prune_published_jobs(
        root, downloads, keep=1, allowed_ids=preview['candidate_ids']) == 1
    assert recent.is_dir()
    assert (published / 'resume.xlsx').read_bytes() == b'SYNTHETIC PUBLISHED WORKBOOK'


def test_pruning_diagnostics_allow_only_bounded_aggregate_numbers():
    from spt_desktop import diagnostics
    assert {'jobs.prune_preview', 'jobs.manual_pruned'} <= diagnostics.EVENTS
    clean = diagnostics._safe_fields({
        'count': 2, 'estimated_bytes': 1048576,
        'candidate_ids': ('a' * 32,), 'npwp': 'SYNTHETIC_PRIVATE_ID',
        'path': 'SECRET'})
    assert clean == {'count': 2, 'estimated_bytes': 1048576}
    assert 'estimated_bytes' not in diagnostics._safe_fields(
        {'estimated_bytes': (1 << 50) + 1})


def test_late_recovery_marker_after_source_hash_aborts_without_deleting_anything(
        tmp_path, monkeypatch):
    """A marker inserted while validating published outputs was never sealed."""
    root, downloads, published = _root(tmp_path, monkeypatch)
    old = _job(root, 1, complete=True, sealed=True, final=published)
    latest = _job(root, 2, complete=False)
    os.utime(old, (1_700_000_000, 1_700_000_000))
    os.utime(latest, (1_700_000_001, 1_700_000_001))
    original = prune._hash_held_output
    marker = old / 'publication-recovery-late.json'
    seen = []

    def inject_after_source_validation(stream, *, deadline=None):
        marker.write_text('{"synthetic": true}', encoding='utf-8')
        seen.append(True)
        return original(stream, deadline=deadline)

    monkeypatch.setattr(prune, '_hash_held_output', inject_after_source_validation)
    result = prune.prune_published_jobs(root, downloads, keep=1, report=True)
    assert seen and result == {'removed': 0, 'incomplete': True}
    assert marker.exists()
    assert (old / prune.SEAL).is_file()
    assert (old / 'source.txt').read_bytes() == b'SYNTHETIC PRIVATE SOURCE'
    assert (published / 'resume.xlsx').read_bytes() == b'SYNTHETIC PUBLISHED WORKBOOK'


def test_marker_added_after_deletion_inventory_is_never_deleted(
        tmp_path, monkeypatch):
    """Only enumerated, previously sealed files may be touched during cleanup."""
    from spt_desktop import profile_lifecycle
    root, downloads, published = _root(tmp_path, monkeypatch)
    old = _job(root, 1, complete=True, sealed=True, final=published)
    newer = _job(root, 2, complete=False)
    os.utime(old, (1_700_000_000, 1_700_000_000))
    os.utime(newer, (1_700_000_001, 1_700_000_001))
    original = profile_lifecycle._tree
    marker = old / 'publication-recovery-after-scan'

    def inject_after_enumeration(*args, **kwargs):
        directories, files = original(*args, **kwargs)
        marker.write_text('SYNTHETIC RECOVERY IN PROGRESS', encoding='utf-8')
        return directories, files

    monkeypatch.setattr(profile_lifecycle, '_tree', inject_after_enumeration)
    result = prune.prune_published_jobs(root, downloads, keep=1, report=True)
    assert result == {'removed': 0, 'incomplete': True}
    assert marker.read_text(encoding='utf-8') == 'SYNTHETIC RECOVERY IN PROGRESS'
    assert old.is_dir() and newer.is_dir()
    assert (published / 'resume.xlsx').read_bytes() == b'SYNTHETIC PUBLISHED WORKBOOK'


def test_interrupted_prune_reports_incomplete_and_restart_cannot_repeat_delete(
        tmp_path, monkeypatch):
    from spt_desktop import profile_lifecycle
    root, downloads, published = _root(tmp_path, monkeypatch)
    old = _job(root, 1, complete=True, sealed=True, final=published)
    newer = _job(root, 2, complete=False)
    os.utime(old, (1_700_000_000, 1_700_000_000))
    os.utime(newer, (1_700_000_001, 1_700_000_001))
    original = profile_lifecycle._remove_tree

    def interrupt_after_one_unlink(*args, **kwargs):
        (old / 'source.txt').unlink()
        raise OSError('Synthetic partial prune after first unlink')

    monkeypatch.setattr(profile_lifecycle, '_remove_tree', interrupt_after_one_unlink)
    result = prune.prune_published_jobs(root, downloads, keep=1, report=True)
    assert result == {'removed': 0, 'incomplete': True}
    assert old.is_dir() and newer.is_dir()
    monkeypatch.setattr(profile_lifecycle, '_remove_tree', original)
    restarted = prune.prune_published_jobs(root, downloads, keep=1, report=True)
    assert restarted == {'removed': 0, 'incomplete': True}
    assert old.is_dir()
    assert (published / 'resume.xlsx').read_bytes() == b'SYNTHETIC PUBLISHED WORKBOOK'


@pytest.mark.parametrize('mutation', ('invalid-json-replacement', 'same-bytes-replacement'))
def test_replaced_seal_during_published_output_verification_never_authorizes_deletion(
        tmp_path, monkeypatch, mutation):
    """Regression: an old valid seal cannot authorize deleting a later seal."""
    root, downloads, published = _root(tmp_path, monkeypatch)
    old = _job(root, 1, complete=True, sealed=True, final=published)
    newest = _job(root, 2, complete=False)
    os.utime(old, (1_700_000_000, 1_700_000_000))
    os.utime(newest, (1_700_000_001, 1_700_000_001))
    receipt = old / prune.SEAL
    first = receipt.read_bytes()
    original = prune._hash_held_output
    touched = []

    def replace_after_valid_seal_was_parsed(stream, *, deadline=None):
        if not touched:
            touched.append(True)
            if mutation == 'invalid-json-replacement':
                altered = dict(json.loads(first))
                altered['schema'] = 999  # Cannot authorize any pruning.
                receipt.write_text(json.dumps(altered), encoding='utf-8')
            else:
                replacement = old / 'replacement-seal-tmp'
                replacement.write_bytes(first)
                os.replace(replacement, receipt)
                assert receipt.read_bytes() == first  # Same bytes, new identity.
        return original(stream, deadline=deadline)

    monkeypatch.setattr(prune, '_hash_held_output',
                        replace_after_valid_seal_was_parsed)
    outcome = prune.prune_published_jobs(root, downloads, keep=1, report=True)
    assert touched and outcome == {'removed': 0, 'incomplete': True}
    assert receipt.is_file() and old.is_dir() and newest.is_dir()
    assert (old / 'run.json').is_file()
    assert (old / 'source.txt').read_bytes() == b'SYNTHETIC PRIVATE SOURCE'
    assert (published / 'resume.xlsx').read_bytes() == b'SYNTHETIC PUBLISHED WORKBOOK'


def test_original_seal_bytes_are_the_fingerprint_used_for_deletion(
        tmp_path, monkeypatch):
    """Changed seal metadata with the same shape is still not deletion authority."""
    root, downloads, published = _root(tmp_path, monkeypatch)
    old = _job(root, 1, complete=True, sealed=True, final=published)
    newest = _job(root, 2, complete=False)
    os.utime(old, (1_700_000_000, 1_700_000_000))
    os.utime(newest, (1_700_000_001, 1_700_000_001))
    receipt = old / prune.SEAL
    original = prune._hash_held_output

    def swap_valid_json_fields(stream, *, deadline=None):
        claim = json.loads(receipt.read_text(encoding='utf-8'))
        claim['run_sha256'] = '0' * 64
        receipt.write_text(json.dumps(claim), encoding='utf-8')
        return original(stream, deadline=deadline)

    monkeypatch.setattr(prune, '_hash_held_output', swap_valid_json_fields)
    assert prune.prune_published_jobs(root, downloads, keep=1, report=True) == {
        'removed': 0, 'incomplete': True}
    assert old.is_dir() and newest.is_dir()
    assert (published / 'resume.xlsx').is_file()
