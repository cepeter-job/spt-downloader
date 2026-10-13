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
            'ui_text': {'title': 'Coretax SPT downloader : kalau bisa ribet, kenapa dibikin gampang',
                        'background': 'jalankan proses sedot di background',
                        'results': 'Hasil Sedot berada di folder Downloads Windows'},
            'credentials_accessed': False, 'live_scrape': False}


def test_frozen_report_requires_python_314_for_gui_and_worker():
    builder().validate_report(report(), 'production')
    for key in ('python', 'worker_python'):
        wrong = report()
        wrong[key] = '3.11.17'
        with pytest.raises(RuntimeError, match='self-test'):
            builder().validate_report(wrong, 'production')


@pytest.mark.parametrize('key,value', [('python_implementation', 'PyPy'), ('free_threaded', True),
                                      ('tcl', ''), ('tk', None), ('bits', 32),
                                      ('worker_python', '3.11.9'), ('worker_resources', []),
                                      ('credentials_accessed', True), ('live_scrape', True)])
def test_frozen_report_rejects_missing_runtime_evidence(key, value):
    data = report()
    data[key] = value
    with pytest.raises(RuntimeError, match='self-test'):
        builder().validate_report(data)


@pytest.mark.parametrize('version', [(3, 11, 17), (3, 14, 7), (3, 14, 9)])
def test_production_build_rejects_unsupported_interpreter_before_writing(monkeypatch, tmp_path, version):
    build = builder()
    monkeypatch.setattr(build.sys, 'platform', 'win32')
    monkeypatch.setattr(build.sys, 'version_info', version)
    output = tmp_path / 'artifact'
    with pytest.raises(RuntimeError, match='3.14.8'):
        build.build(output)
    assert not output.exists()
