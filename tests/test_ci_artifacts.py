"""Artifact verification rejects extra files, altered bytes and wrong build reports."""
import importlib.util
import json
from pathlib import Path

import pytest
from spt_desktop.runtime import WORKER_FILES, python_version


def verifier():
    source = Path(__file__).resolve().parents[1] / 'scripts' / 'ci_artifact.py'
    assert source.is_file(), 'Exact artifact verification is missing'
    spec = importlib.util.spec_from_file_location('ci_artifact', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def artifact(tmp_path):
    for name in ('SPTDownloader.exe', 'LICENSE.txt', 'README.txt'):
        (tmp_path / name).write_bytes(b'SYNTHETIC CHECKSUM FIXTURE; NOT A REAL EXECUTABLE')
    (tmp_path / 'build-selftest.json').write_text(json.dumps({
        'ok': True, 'frozen': True, 'uv_bundled': True, 'bits': 64,
        'credentials_accessed': False, 'live_scrape': False,
        'python': '3.14.8', 'python_implementation': 'CPython', 'free_threaded': False,
        'tcl': '8.6.15', 'tk': '8.6.15', 'worker_python': python_version(),
        'worker_resources': list(WORKER_FILES), 'credential_check_controls': True,
        'gui_controls': ['Cek Kredensial'], 'build_profile': 'candidate',
        'personal_use_labels': ['Coretax → Excel · for personal use only', 'for personal use : punto ap'],
    }))
    return tmp_path


def test_readback_checks_each_allowed_file_and_actual_selftest_version(artifact):
    module = verifier()
    module.write_checksums(artifact, '3.14.8')
    module.verify(artifact, '3.14.8')
    assert len((artifact / 'SHA256SUMS.txt').read_text().splitlines()) == 4
    with pytest.raises(ValueError, match='Python'):
        module.verify(artifact, '3.11.17')


@pytest.mark.parametrize('damage', ['extra_file', 'extra_directory', 'changed', 'missing',
                                   'unsafe_report', 'incomplete_checksums'])
def test_artifact_damage_cannot_receive_provenance(artifact, damage):
    module = verifier()
    module.write_checksums(artifact, '3.14.8')
    if damage == 'extra_file':
        (artifact / 'private.json').write_text('SYNTHETIC FORBIDDEN FILE')
    elif damage == 'extra_directory':
        (artifact / 'profile').mkdir()
    elif damage == 'changed':
        (artifact / 'SPTDownloader.exe').write_bytes(b'SYNTHETIC TAMPERED CONTENT')
    elif damage == 'missing':
        (artifact / 'LICENSE.txt').unlink()
    elif damage == 'unsafe_report':
        path = artifact / 'build-selftest.json'
        report = json.loads(path.read_text())
        report['credentials_accessed'] = True
        path.write_text(json.dumps(report))
        with pytest.raises(ValueError):
            module.write_checksums(artifact, '3.14.8')
    else:
        path = artifact / 'SHA256SUMS.txt'
        path.write_text(path.read_text().splitlines()[0] + '\n')
    with pytest.raises(ValueError):
        module.verify(artifact, '3.14.8')


@pytest.mark.parametrize('key,value', [('tk', ''), ('worker_resources', []),
                                      ('credential_check_controls', False),
                                      ('build_profile', 'production')])
def test_incomplete_frozen_runtime_evidence_cannot_be_checksummed(artifact, key, value):
    path = artifact / 'build-selftest.json'
    report = json.loads(path.read_text())
    report[key] = value
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError):
        verifier().write_checksums(artifact, '3.14.8')
