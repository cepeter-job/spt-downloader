"""Pembersihan hanya menyentuh cabang selesai yang riwayatnya aman di main."""
from copy import deepcopy
import os
import subprocess

import pytest


REPOSITORY = 'fixture/repo'
HEAD = 'a' * 40
BASE = 'b' * 40


def pull(branch, sha=HEAD, *, state='closed', repository=REPOSITORY):
    return {'state': state, 'head': {'ref': branch, 'sha': sha,
                                   'repo': {'full_name': repository}}}


class Metadata:
    """Respons API sintetis; tidak mengakses GitHub atau token."""
    repository = REPOSITORY

    def __init__(self):
        self.main = BASE
        self.default = 'main'
        self.branches = [{'name': 'main', 'protected': False, 'commit': {'sha': BASE}},
                         {'name': 'work/done', 'protected': False, 'commit': {'sha': HEAD}}]
        self.closed = [pull('work/done')]
        self.open = []
        self.comparison = {'status': 'ahead', 'behind_by': 0,
                           'merge_base_commit': {'sha': HEAD}}
        self.latest = HEAD

    def get(self, path=''):
        if not path:
            return {'default_branch': self.default}
        if path == 'branches/main':
            return {'name': 'main', 'protected': False, 'commit': {'sha': self.main}}
        if path == 'branches/work%2Fdone':
            return {'name': 'work/done', 'protected': False, 'commit': {'sha': self.latest}}
        if path.startswith('compare/'):
            return self.comparison
        raise AssertionError(f'Endpoint tidak diharapkan: {path}')

    def pages(self, path):
        return deepcopy({'branches': self.branches,
                         'pulls?state=closed': self.closed,
                         'pulls?state=open': self.open}[path])


def test_cleanup_preview_has_no_side_effect_and_reports_safe_branch():
    from scripts.cleanup_branches import cleanup
    removed = []
    result = cleanup(Metadata(), base='main', expected_base=BASE,
                     apply=False, delete=lambda *args: removed.append(args))
    assert result == {'deleted': [], 'eligible': ['work/done']}
    assert removed == []


@pytest.mark.parametrize('change', [
    lambda api: api.branches[1].update(protected=True),
    lambda api: api.branches[1].pop('protected'),
    lambda api: api.branches[1]['commit'].update(sha='c' * 40),
    lambda api: api.closed[0]['head']['repo'].update(full_name='someone/fork'),
    lambda api: api.closed[0].update(state='open'),
    lambda api: api.closed[0]['head'].update(ref='main', sha=BASE),
    lambda api: api.open.append(pull('work/done', state='open')),
    lambda api: api.comparison.update(status='diverged', behind_by=1),
    lambda api: api.comparison.update(merge_base_commit={'sha': 'c' * 40}),
    lambda api: setattr(api, 'latest', 'c' * 40),
])
def test_cleanup_retains_unmerged_protected_open_or_changed_branches(change):
    from scripts.cleanup_branches import cleanup
    api, removed = Metadata(), []
    change(api)
    result = cleanup(api, base='main', expected_base=BASE,
                     apply=True, delete=lambda *args: removed.append(args))
    assert result['deleted'] == []
    assert removed == []


def test_cleanup_refuses_main_that_is_not_the_tested_commit():
    from scripts.cleanup_branches import CleanupError, cleanup
    api = Metadata()
    api.main = 'c' * 40
    with pytest.raises(CleanupError, match='main'):
        cleanup(api, base='main', expected_base=BASE, apply=True,
                delete=lambda *args: pytest.fail('Tidak boleh menghapus cabang'))


@pytest.mark.parametrize('head_repository', [REPOSITORY, 'someone/fork'])
def test_cleanup_preserves_a_branch_used_as_base_by_an_open_pr(head_repository):
    from scripts.cleanup_branches import cleanup
    api, removed = Metadata(), []
    active = pull('work/next', state='open', repository=head_repository)
    active['base'] = {'ref': 'work/done', 'repo': {'full_name': REPOSITORY}}
    api.open = [active]
    result = cleanup(api, base='main', expected_base=BASE, apply=True,
                     delete=lambda *args: removed.append(args))
    assert result['deleted'] == []
    assert removed == []


def test_git_deletion_lease_preserves_a_concurrent_push(tmp_path):
    from scripts.cleanup_branches import CleanupError, delete_with_lease

    def git(*args, cwd=tmp_path):
        return subprocess.run(['git', *args], cwd=cwd, check=True,
                              capture_output=True, text=True).stdout.strip()

    remote, source = tmp_path / 'remote.git', tmp_path / 'source'
    git('init', '--bare', str(remote))
    git('init', str(source))
    git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
        'commit', '--allow-empty', '-m', 'Synthetic base', cwd=source)
    old = git('rev-parse', 'HEAD', cwd=source)
    git('push', str(remote), 'HEAD:refs/heads/work/done', cwd=source)
    git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
        'commit', '--allow-empty', '-m', 'Synthetic concurrent change', cwd=source)
    current = git('rev-parse', 'HEAD', cwd=source)
    git('push', str(remote), 'HEAD:refs/heads/work/done', cwd=source)

    with pytest.raises(CleanupError):
        delete_with_lease(str(remote), 'work/done', old, env=os.environ.copy(), cwd=source)
    assert git('rev-parse', 'refs/heads/work/done', cwd=remote) == current

    delete_with_lease(str(remote), 'work/done', current, env=os.environ.copy(), cwd=source)
    assert git('for-each-ref', '--format=%(refname)', 'refs/heads/work/done', cwd=remote) == ''
