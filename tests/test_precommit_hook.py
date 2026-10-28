"""Exercise our hook arguments with the exact entry of the pinned Ruff hook."""
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import yaml


@pytest.mark.parametrize(('content', 'want_exit'), [('value = 1\n', 0), ('print(synthetic_missing)\n', 1)])
def test_configured_ruff_hook_checks_selected_files_without_spurious_paths(tmp_path, content, want_exit):
    root = Path(__file__).resolve().parents[1]
    config = yaml.safe_load((root / '.pre-commit-config.yaml').read_text(encoding='utf-8'))
    repo = next(r for r in config['repos'] if r['repo'] == 'https://github.com/astral-sh/ruff-pre-commit')
    hook = next(h for h in repo['hooks'] if h['id'] == 'ruff')
    shutil.copyfile(root / 'ruff.toml', tmp_path / 'ruff.toml')
    (tmp_path / 'selected.py').write_text(content, encoding='utf-8')
    # v0.17.2 .pre-commit-hooks.yaml declares: ruff check --force-exclude.
    result = subprocess.run([sys.executable, '-m', 'ruff', 'check', '--force-exclude',
        *hook.get('args', []), 'selected.py'], cwd=tmp_path, capture_output=True,
        text=True, timeout=30, check=False)
    assert result.returncode == want_exit, result.stdout + result.stderr
    assert 'E902' not in result.stdout + result.stderr
    if want_exit:
        assert 'F821' in result.stdout
