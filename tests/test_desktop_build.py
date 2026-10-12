"""The frozen GUI payload is explicit; no outputs or browser profiles are globbed."""
import importlib
import importlib.util
from pathlib import Path
import pytest
from spt_desktop.runtime import WORKER_FILES, python_version


def builder():
    assert importlib.util.find_spec('build_desktop'), 'Windows packaging script is missing'
    return importlib.import_module('build_desktop')


def test_packaging_command_is_thin_windowed_and_explicit(tmp_path):
    command=builder().build_command(tmp_path/'source',tmp_path/'output',tmp_path/'uv.exe')
    assert '--onefile' in command and '--windowed' in command and '--noupx' in command
    data=[command[i+1].rsplit(';',1)[0] for i,v in enumerate(command) if v=='--add-data']
    expected={str(tmp_path/'source'/n) for n in WORKER_FILES}|{str(tmp_path/'source'/'LICENSE')}
    assert set(data)==expected
    assert not any('*' in arg for arg in command)
    exclusions=[command[i+1] for i,v in enumerate(command) if v=='--exclude-module']
    assert {'playwright','openpyxl','pytest'}.issubset(exclusions)


def test_workflow_tests_builds_and_verifies_before_explicit_artifact_upload():
    path=Path(__file__).resolve().parents[1]/'.github/workflows/windows-build.yml'
    assert path.is_file(), 'GitHub Windows workflow is missing'
    text=path.read_text()
    assert 'workflow_dispatch:' in text and 'contents: read' in text
    assert 'pytest tests' in text and 'build_desktop.py' in text
    assert 'upload-artifact@' in text and 'SPTDownloader.exe' in text
    assert 'secrets.' not in text and 'coretax.intranet' not in text


def report(profile='production'):
    return {'ok': True, 'frozen': True, 'uv_bundled': True, 'bits': 64,
            'python': python_version(profile), 'python_implementation': 'CPython',
            'free_threaded': False, 'tcl': '8.6.15', 'tk': '8.6.15',
            'worker_python': python_version(), 'worker_resources': list(WORKER_FILES),
            'credential_check_controls': True, 'gui_controls': ['Cek Kredensial'],
            'personal_use_labels': ['Coretax → Excel · for personal use only', 'for personal use : punto ap'],
            'credentials_accessed': False, 'live_scrape': False}


@pytest.mark.parametrize('profile', ['production', 'candidate'])
def test_frozen_report_accepts_only_the_requested_patched_python(profile):
    builder().validate_report(report(profile), profile)
    wrong = report(profile)
    wrong['python'] = '3.11.9' if profile == 'production' else python_version()
    with pytest.raises(RuntimeError, match='self-test'):
        builder().validate_report(wrong, profile)


@pytest.mark.parametrize('key,value', [('python_implementation', 'PyPy'), ('free_threaded', True),
                                      ('tcl', ''), ('tk', None), ('bits', 32),
                                      ('worker_python', '3.11.9'), ('worker_resources', []),
                                      ('credentials_accessed', True), ('live_scrape', True)])
def test_frozen_report_rejects_missing_runtime_evidence(key, value):
    data = report()
    data[key] = value
    with pytest.raises(RuntimeError, match='self-test'):
        builder().validate_report(data)


@pytest.mark.parametrize('version', [(3, 11, 9), (3, 11, 16), (3, 14, 8)])
def test_production_build_rejects_unsupported_interpreter_before_writing(monkeypatch, tmp_path, version):
    build = builder()
    monkeypatch.setattr(build.sys, 'platform', 'win32')
    monkeypatch.setattr(build.sys, 'version_info', version)
    output = tmp_path / 'artifact'
    with pytest.raises(RuntimeError, match='3.11.17'):
        build.build(output)
    assert not output.exists()
