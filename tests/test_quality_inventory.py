"""Audit coordinates must describe committed bytes even in a dirty checkout."""
import subprocess

import pytest

from scripts.quality_inventory import inventory


@pytest.mark.parametrize('mutation', ['edit', 'delete'])
def test_inventory_reads_its_named_commit_instead_of_dirty_working_files(tmp_path, mutation):
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=tmp_path, text=True).strip()

    git('init', '-q')
    source = tmp_path / 'coretax_fixture.py'
    source.write_text('def committed():\n    return 1\n', encoding='utf-8')
    git('add', 'coretax_fixture.py')
    git('-c', 'user.name=Synthetic', '-c', 'user.email=synthetic@example.invalid',
        'commit', '-qm', 'synthetic source snapshot')
    commit = git('rev-parse', 'HEAD')
    if mutation == 'edit':
        source.write_text('def unrelated_dirty_code():\n    return 2\n', encoding='utf-8')
    else:
        source.unlink()
    observed = inventory(tmp_path)
    assert observed['revision'] == commit
    assert observed['source_kind'] == 'git-commit'
    assert [row['name'] for row in observed['functions']] == ['committed']
