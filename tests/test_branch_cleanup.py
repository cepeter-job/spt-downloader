"""Pembersihan hanya menyentuh cabang selesai yang riwayatnya aman di main."""
from copy import deepcopy
import json
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


@pytest.fixture
def cleanup_cli(monkeypatch):
    from scripts import cleanup_branches as module

    api, removed = Metadata(), []
    monkeypatch.setenv('GH_TOKEN', 'SYNTHETIC-NOT-A-REAL-TOKEN')
    monkeypatch.setattr(module, 'GitHubAPI', lambda *args: api)
    monkeypatch.setattr(module, 'delete_with_lease',
                        lambda remote, branch, sha, **kwargs: removed.append((branch, sha)))
    argv = ['--repository', REPOSITORY, '--base', 'main', '--expected-base', BASE, '--apply']
    return module, api, removed, argv


@pytest.mark.parametrize('move_when', ['initial', 'recheck', 'after_first_delete'])
def test_cleanup_cli_stops_successfully_when_valid_main_has_moved(
        cleanup_cli, monkeypatch, capsys, move_when):
    module, api, removed, argv = cleanup_cli
    next_head, moved_base = 'd' * 40, 'c' * 40
    api.branches.append({'name': 'work/next', 'protected': False, 'commit': {'sha': next_head}})
    api.closed.append(pull('work/next', next_head))
    original_get = api.get
    observed_move = False

    def get(path=''):
        nonlocal observed_move
        assert not observed_move, 'No more API work is allowed after observing a moved main'
        if path == 'branches/main':
            if move_when == 'initial':
                api.main = moved_base
            observed_move = api.main == moved_base
        if path.startswith('compare/'):
            if move_when == 'recheck':
                api.main = moved_base
            return {'status': 'ahead', 'behind_by': 0,
                    'merge_base_commit': {'sha': path.split('/')[1].split('...')[0]}}
        if path == 'branches/work%2Fnext':
            return {'name': 'work/next', 'protected': False, 'commit': {'sha': next_head}}
        return original_get(path)

    def delete(remote, branch, sha, **kwargs):
        assert api.main == BASE, 'A branch must not be deleted after main moves'
        removed.append((branch, sha))
        if move_when == 'after_first_delete':
            api.main = moved_base

    monkeypatch.setattr(api, 'get', get)
    monkeypatch.setattr(module, 'delete_with_lease', delete)
    assert module.main(argv) == 0
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    expected_deleted = ['work/done'] if move_when == 'after_first_delete' else []
    assert result == {'status': 'stopped', 'reason': 'base_changed', 'base': 'main',
                      'expected_base': BASE, 'current_base': moved_base,
                      'deleted': expected_deleted, 'eligible': expected_deleted}
    assert removed == ([('work/done', HEAD)] if expected_deleted else [])
    assert observed_move and captured.err == ''


@pytest.mark.parametrize('read_when', ['initial', 'recheck'])
@pytest.mark.parametrize('response', [
    None, [], {'commit': None}, {'commit': {}},
    {'commit': {'sha': 'C' * 40}}, {'commit': {'sha': 'c' * 39}},
])
def test_cleanup_cli_keeps_missing_or_malformed_main_as_failure(
        cleanup_cli, monkeypatch, capsys, read_when, response):
    module, api, removed, argv = cleanup_cli
    original_get, main_reads = api.get, 0

    def get(path=''):
        nonlocal main_reads
        if path == 'branches/main':
            main_reads += 1
            if main_reads == (1 if read_when == 'initial' else 2):
                return deepcopy(response)
        return original_get(path)

    monkeypatch.setattr(api, 'get', get)
    assert module.main(argv) == 1
    captured = capsys.readouterr()
    assert removed == [] and captured.out == '' and captured.err


@pytest.mark.parametrize('failure', ['missing_token', 'api_error', 'deletion_lease'])
def test_cleanup_cli_does_not_hide_auth_api_or_deletion_failures(
        cleanup_cli, monkeypatch, capsys, failure):
    module, api, removed, argv = cleanup_cli

    def refused(*args, **kwargs):
        raise module.CleanupError('Synthetic authorization, API or lease failure')

    if failure == 'missing_token':
        monkeypatch.delenv('GH_TOKEN')
    elif failure == 'api_error':
        monkeypatch.setattr(api, 'get', refused)
    else:
        monkeypatch.setattr(module, 'delete_with_lease', refused)
    assert module.main(argv) == 1
    captured = capsys.readouterr()
    assert removed == [] and captured.out == '' and captured.err


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
