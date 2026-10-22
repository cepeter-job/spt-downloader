"""Only immutable public build coordinates may identify a diagnostic session."""
import importlib
import importlib.util
import json

import pytest

from spt_desktop import diagnostics
from test_diagnostics import records


def build_info():
    assert importlib.util.find_spec('spt_desktop.build_info'), 'Immutable build identity is missing'
    return importlib.import_module('spt_desktop.build_info')


def test_diagnostics_include_validated_packaged_commit_and_run(tmp_path, monkeypatch):
    module = build_info()
    identity = {'schema': 1, 'commit': 'a' * 40, 'run_id': '123456789', 'run_attempt': 2}
    (tmp_path / 'build-info.json').write_text(json.dumps(identity), encoding='utf-8')
    monkeypatch.setattr(module, 'resource_root', lambda: tmp_path)
    with diagnostics.session(tmp_path, 'worker') as log:
        diagnostics.record('operation.started', operation='export')
        assert log.flush()
    rows = records(tmp_path)
    assert rows and all(row['build_commit'] == identity['commit'] for row in rows)
    assert all(row['build_run_id'] == '123456789' and row['build_run_attempt'] == 2 for row in rows)


@pytest.mark.parametrize('bad', [None, {'schema': 1, 'commit': 'SYNTHETIC_PRIVATE_TOKEN'},
    {'schema': 1, 'commit': 'b' * 40, 'run_id': '123', 'run_attempt': True},
    {'schema': 1, 'commit': 'b' * 40, 'run_id': '123', 'run_attempt': 1, 'secret': 'PRIVATE'}])
def test_invalid_or_missing_build_metadata_never_enters_diagnostics(tmp_path, monkeypatch, bad):
    module = build_info()
    if bad is not None:
        (tmp_path / 'build-info.json').write_text(json.dumps(bad), encoding='utf-8')
    monkeypatch.setattr(module, 'resource_root', lambda: tmp_path)
    monkeypatch.setenv('GITHUB_SHA', 'c' * 40)
    with diagnostics.session(tmp_path, 'worker') as log:
        assert log.flush()
    rows = records(tmp_path)
    assert rows and all(row.get('build_commit') == 'unknown' for row in rows)
    assert 'PRIVATE' not in json.dumps(rows)
    assert all('build_run_id' not in row for row in rows)
