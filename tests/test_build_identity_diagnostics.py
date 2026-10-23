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


@pytest.mark.parametrize('run_id,run_attempt', [('123456789', 2), ('9' * 24, 1_000_000)])
def test_diagnostics_include_validated_packaged_commit_and_run(tmp_path, monkeypatch, run_id, run_attempt):
    module = build_info()
    identity = {'schema': 1, 'commit': 'a' * 40, 'run_id': run_id, 'run_attempt': run_attempt}
    (tmp_path / 'build-info.json').write_text(json.dumps(identity), encoding='utf-8')
    monkeypatch.setattr(module, 'resource_root', lambda: tmp_path)
    with diagnostics.session(tmp_path, 'worker') as log:
        diagnostics.record('operation.started', operation='export')
        assert log.flush()
    rows = records(tmp_path)
    assert rows and all(row['build_commit'] == identity['commit'] for row in rows)
    assert all(row['build_run_id'] == run_id and row['build_run_attempt'] == run_attempt for row in rows)


@pytest.mark.parametrize('bad', [None, {'schema': 1, 'commit': 'SYNTHETIC_PRIVATE_TOKEN'},
    {'schema': 1, 'commit': 'b' * 40, 'run_id': '123', 'run_attempt': True},
    {'schema': 1, 'commit': 'b' * 40, 'run_id': '9' * 25, 'run_attempt': 1},
    {'schema': 1, 'commit': 'b' * 40, 'run_id': '123', 'run_attempt': 1_000_001},
    {'schema': 1, 'commit': 'b' * 40, 'run_id': '123', 'run_attempt': 1, 'secret': 'PRIVATE'}])
def test_invalid_or_missing_build_metadata_never_enters_diagnostics(tmp_path, monkeypatch, bad):
    module = build_info()
    if bad is not None:
        (tmp_path / 'build-info.json').write_text(json.dumps(bad), encoding='utf-8')
    monkeypatch.setattr(module, 'resource_root', lambda: tmp_path)
    monkeypatch.setenv('GITHUB_SHA', 'c' * 40)
    assert module.read_build_info() is None
    with diagnostics.session(tmp_path, 'worker') as log:
        assert log.flush()
    rows = records(tmp_path)
    assert rows and all(row.get('build_commit') == 'unknown' for row in rows)
    assert 'PRIVATE' not in json.dumps(rows)
    assert all('build_run_id' not in row for row in rows)


def test_deeply_nested_metadata_is_unknown_without_disabling_diagnostics(tmp_path, monkeypatch):
    module = build_info()
    (tmp_path / 'build-info.json').write_text('[' * 1500 + '0' + ']' * 1500, encoding='utf-8')
    monkeypatch.setattr(module, 'resource_root', lambda: tmp_path)
    assert module.read_build_info() is None
    with diagnostics.session(tmp_path, 'worker') as log:
        assert log.flush()
    assert all(row['build_commit'] == 'unknown' for row in records(tmp_path))
