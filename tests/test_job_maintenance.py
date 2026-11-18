"""Synthetic, offline contracts for manual incomplete-job maintenance."""
import json
import os

import pytest

from spt_desktop import job_pruning as pruning
from spt_desktop import job_maintenance as maintenance


def _setup(tmp_path, monkeypatch):
    root = tmp_path / 'workspace'
    (root / 'jobs').mkdir(parents=True)
    downloads = tmp_path / 'Downloads'
    downloads.mkdir()
    (downloads / 'resume.xlsx').write_bytes(b'SYNTHETIC VERIFIED EXCEL')
    monkeypatch.setattr(pruning, '_windows', lambda: True)
    return root, downloads


def _job(root, n, *, complete=None, status=None, sealed=False):
    folder = root / 'jobs' / f'{n:032x}'
    folder.mkdir()
    (folder / 'source.json').write_text('{"synthetic":true}', encoding='utf-8')
    if complete is not None:
        (folder / 'run.json').write_text(json.dumps({
            'complete': complete, 'records': [], 'npwp': 'SYNTHETIC',
            'year': 2025, 'year_basis': 'period'}), encoding='utf-8')
    if sealed:
        (folder / pruning.SEAL).write_text('{"synthetic":true}', encoding='utf-8')
    if complete is False and status is None:
        status = 'PARTIAL'
    if status is not None:
        assert maintenance.record_terminal_status(root, folder.name, status)
    return folder


def _approve(snapshot):
    return tuple((entry['id'], entry['digest']) for entry in snapshot['removable'])


def test_inventory_counts_and_manual_deletion_preserve_complete_and_downloads(tmp_path, monkeypatch):
    root, downloads = _setup(tmp_path, monkeypatch)
    complete = _job(root, 1, complete=True, sealed=True)
    partial = _job(root, 2, complete=False)
    failed = _job(root, 3, complete=False, status='ERROR')
    cancelled = _job(root, 4, complete=False, status='CANCELLED')
    for index, path in enumerate((complete, partial, failed, cancelled), 1):
        os.utime(path, (1_700_000_000 + index, 1_700_000_000 + index))
    inventory = maintenance.inspect_job_storage(root, keep=1)
    assert inventory['scan_complete']
    assert (inventory['total'], inventory['complete'], inventory['partial'],
            inventory['failed']) == (4, 1, 1, 2)
    assert inventory['protected'] >= 3
    assert inventory['estimated_bytes'] > 0
    assert {x['id'] for x in inventory['removable']} == {
        partial.name, failed.name, cancelled.name}
    assert pruning.prune_published_jobs(root, downloads, keep=1) == 0
    assert maintenance.delete_incomplete_jobs(root, _approve(inventory)) == {
        'removed': 3, 'incomplete': False}
    assert complete.is_dir()
    assert not partial.exists() and not failed.exists() and not cancelled.exists()
    assert (downloads / 'resume.xlsx').read_bytes() == b'SYNTHETIC VERIFIED EXCEL'


def test_selected_subset_is_only_removal_authorization(tmp_path, monkeypatch):
    root, _ = _setup(tmp_path, monkeypatch)
    first = _job(root, 1, complete=False)
    second = _job(root, 2, complete=False, status='BLOCKED')
    preview = maintenance.inspect_job_storage(root)
    item = next(row for row in preview['removable'] if row['id'] == first.name)
    assert maintenance.delete_incomplete_jobs(root, ((item['id'], item['digest']),)) == {
        'removed': 1, 'incomplete': False}
    assert not first.exists() and second.is_dir()


@pytest.mark.parametrize('change', ['bytes', 'new-file', 'recovery', 'seal'])
def test_snapshot_change_or_recovery_prevents_manual_deletion(tmp_path, monkeypatch, change):
    root, downloads = _setup(tmp_path, monkeypatch)
    old = _job(root, 1, complete=False)
    preview = maintenance.inspect_job_storage(root)
    assert preview['scan_complete'] and len(preview['removable']) == 1
    if change == 'bytes':
        (old / 'source.json').write_text('{"synthetic":"changed"}')
    elif change == 'new-file':
        (old / 'new.txt').write_text('late')
    elif change == 'recovery':
        (old / 'publication-recovery-late.json').write_text('late')
    else:
        (old / pruning.SEAL).write_text('late')
    result = maintenance.delete_incomplete_jobs(root, _approve(preview))
    assert result == {'removed': 0, 'incomplete': True}
    assert old.exists() and (old / 'source.json').is_file()
    assert (downloads / 'resume.xlsx').is_file()


def test_ongoing_job_is_never_inspectable_for_manual_deletion(tmp_path, monkeypatch):
    root, _ = _setup(tmp_path, monkeypatch)
    running = _job(root, 1, complete=False)
    assert not maintenance.inspect_job_storage(root, active_id=running.name)['removable']
    row = maintenance.inspect_job_storage(root)['removable'][0]
    assert maintenance.delete_incomplete_jobs(
        root, ((row['id'], row['digest']),), active_id=running.name) == {
            'removed': 0, 'incomplete': True}
    assert running.is_dir()


def test_global_publication_recovery_blocks_all_incomplete_cleaning(tmp_path, monkeypatch):
    root, _ = _setup(tmp_path, monkeypatch)
    partial = _job(root, 1, complete=False)
    preview = maintenance.inspect_job_storage(root)
    (root / 'jobs' / '.spt-publish-pending').mkdir()
    assert maintenance.inspect_job_storage(root)['removable'] == ()
    assert maintenance.delete_incomplete_jobs(root, _approve(preview)) == {
        'removed': 0, 'incomplete': True}
    assert partial.is_dir()


def test_corrupt_or_unknown_job_retained_and_preview_fails_closed(tmp_path, monkeypatch):
    root, _ = _setup(tmp_path, monkeypatch)
    safe = _job(root, 1, complete=False)
    unknown = _job(root, 2)
    (unknown / 'run.json').write_text('invalid JSON')
    preview = maintenance.inspect_job_storage(root)
    assert not preview['scan_complete']
    assert preview['removable'] == ()
    assert preview['protected'] >= 1
    assert safe.is_dir() and unknown.is_dir()


def test_unsealed_error_without_run_can_be_manually_deleted_after_terminal(tmp_path, monkeypatch):
    root, _ = _setup(tmp_path, monkeypatch)
    failed = _job(root, 1, status='ERROR')
    preview = maintenance.inspect_job_storage(root)
    assert preview['failed'] == 1
    assert maintenance.delete_incomplete_jobs(root, _approve(preview)) == {
        'removed': 1, 'incomplete': False}
    assert not failed.exists()


def test_sealed_or_unknown_complete_never_eligible_for_incomplete_deletion(tmp_path, monkeypatch):
    root, _ = _setup(tmp_path, monkeypatch)
    sealed = _job(root, 1, complete=True, sealed=True)
    unknown = _job(root, 2)
    assert not maintenance.record_terminal_status(root, sealed.name, 'ERROR')
    assert {i['id'] for i in maintenance.inspect_job_storage(root)['removable']} == set()
    assert sealed.is_dir() and unknown.is_dir()


@pytest.mark.parametrize('approvals', [
    ('bad',), (('../escape', '0' * 64),),
    ((None, '0' * 64),), (('a' * 32, 'not-a-digest'),),
    ((('a' * 32, '0' * 64)), (('a' * 32, '0' * 64))),
    [['a' * 32, '0' * 64]],
])
def test_manual_deletion_rejects_untrusted_approval_sets(tmp_path, monkeypatch, approvals):
    root, _ = _setup(tmp_path, monkeypatch)
    _job(root, 1, complete=False)
    with pytest.raises(ValueError):
        maintenance.delete_incomplete_jobs(root, approvals)


def test_interrupted_manual_delete_is_not_reported_complete(tmp_path, monkeypatch):
    root, _ = _setup(tmp_path, monkeypatch)
    failed = _job(root, 1, complete=False)
    preview = maintenance.inspect_job_storage(root)
    original = maintenance._remove_tree

    def interrupted(*args, **kwargs):
        (failed / 'source.json').unlink()
        raise OSError('SYNTHETIC_INTERRUPTION')

    monkeypatch.setattr(maintenance, '_remove_tree', interrupted)
    assert maintenance.delete_incomplete_jobs(root, _approve(preview)) == {
        'removed': 0, 'incomplete': True}
    assert failed.is_dir()
    monkeypatch.setattr(maintenance, '_remove_tree', original)
    assert maintenance.delete_incomplete_jobs(root, _approve(preview)) == {
        'removed': 0, 'incomplete': True}


def test_symlink_is_never_followed_for_manual_cleanup(tmp_path, monkeypatch):
    root, downloads = _setup(tmp_path, monkeypatch)
    partial = _job(root, 1, complete=False)
    try:
        (partial / 'linked').symlink_to(downloads / 'resume.xlsx')
    except (OSError, NotImplementedError):
        pytest.skip('Symlink creation unavailable')
    preview = maintenance.inspect_job_storage(root)
    assert not preview['scan_complete'] and not preview['removable']
    assert (downloads / 'resume.xlsx').is_file()


def test_same_bytes_replacement_after_preview_invalidates_native_snapshot(
        tmp_path, monkeypatch):
    root, _ = _setup(tmp_path, monkeypatch)
    incomplete = _job(root, 1, complete=False)
    preview = maintenance.inspect_job_storage(root)
    assert len(preview['removable']) == 1
    original = (incomplete / 'source.json').read_bytes()
    replacement = incomplete / 'incoming.tmp'
    replacement.write_bytes(original)
    os.replace(replacement, incomplete / 'source.json')
    assert (incomplete / 'source.json').read_bytes() == original
    assert maintenance.delete_incomplete_jobs(root, _approve(preview)) == {
        'removed': 0, 'incomplete': True}
    assert incomplete.is_dir()


def test_unmarked_legacy_partial_is_counted_but_not_authorized(
        tmp_path, monkeypatch):
    root, _ = _setup(tmp_path, monkeypatch)
    old = _job(root, 1, complete=False)
    (old / maintenance.TERMINAL).unlink()
    inventory = maintenance.inspect_job_storage(root)
    assert inventory['partial'] == 1 and inventory['protected'] == 1
    assert inventory['removable'] == ()
    assert old.is_dir()
