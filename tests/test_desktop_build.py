"""The frozen GUI payload is explicit; no outputs or browser profiles are globbed."""
import importlib
import importlib.util
from pathlib import Path
from spt_desktop.runtime import WORKER_FILES


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
