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
        'diagnostics': {'schema': 1, 'safe_logging': True},
        'selection_sorting_control': sorting_report(),
            'python': python_version(profile), 'python_implementation': 'CPython',
            'free_threaded': False, 'tcl': '8.6.15', 'tk': '8.6.15',
            'worker_python': python_version(), 'worker_resources': list(WORKER_FILES),
            'credential_check_controls': True, 'gui_controls': ['Cek Kredensial'],
            'personal_use_labels': ['Coretax → Excel · for personal use only'],
            'ui_text': {'title': 'Coretax SPT downloader : kalau bisa ribet, kenapa dibikin gampang',
                        'background': 'jalankan proses sedot di background',
                        'results': 'Hasil Sedot berada di folder Downloads Windows'},
            'credentials_accessed': False, 'live_scrape': False}




def sorting_report():
    return {'heading': 'Jenis pajak', 'directions': ['Jenis pajak ▲', 'Jenis pajak ▼'],
            'hierarchy': ['type', 'year', 'month', 'model'],
            'ordered_ids': [
                ['synthetic-badan-two', 'synthetic-badan-one', 'synthetic-21',
                 'synthetic-ppn-normal', 'synthetic-ppn-one', 'synthetic-ppn-two',
                 '::synthetic {return}; [literal] / id', 'synthetic-ppn-feb'],
                ['synthetic-ppn-normal', 'synthetic-ppn-one', 'synthetic-ppn-two',
                 '::synthetic {return}; [literal] / id', 'synthetic-ppn-feb',
                 'synthetic-21', 'synthetic-badan-two', 'synthetic-badan-one']],
            'selection_preserved': True,
            'confirmed_ids': ['::synthetic {return}; [literal] / id', 'synthetic-badan-two']}


def test_frozen_gate_accepts_complete_observed_chronological_sorting():
    builder().validate_report(report())


@pytest.mark.parametrize('mutation', ['missing', 'empty', 'hierarchy', 'ascending',
    'descending', 'missing_row', 'selection', 'reply', 'directions'])
def test_frozen_gate_rejects_missing_or_wrong_chronological_evidence(mutation):
    data = report()
    builder().validate_report(data)
    if mutation == 'missing':
        del data['selection_sorting_control']
    elif mutation == 'empty':
        data['selection_sorting_control'] = {}
    else:
        sorting = data['selection_sorting_control']
        if mutation == 'hierarchy':
            sorting['hierarchy'] = ['type']
        elif mutation in ('ascending', 'descending'):
            index = 0 if mutation == 'ascending' else 1
            sorting['ordered_ids'][index] = list(reversed(sorting['ordered_ids'][index]))
        elif mutation == 'missing_row':
            sorting['ordered_ids'][0].pop()
        elif mutation == 'selection':
            sorting['selection_preserved'] = False
        elif mutation == 'reply':
            sorting['confirmed_ids'].reverse()
        elif mutation == 'directions':
            sorting['directions'] = ['Jenis pajak ▲']
    with pytest.raises(RuntimeError, match='self-test'):
        builder().validate_report(data)


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


def test_frozen_gate_accepts_removed_punto_footer_with_other_credit_intact():
    data = report()
    data['personal_use_labels'] = ['Coretax → Excel · for personal use only']
    builder().validate_report(data)


def test_frozen_gate_rejects_the_obsolete_visible_punto_footer():
    data = report()
    data['personal_use_labels'] = ['Coretax → Excel · for personal use only', 'for personal use : punto ap']
    with pytest.raises(RuntimeError, match='self-test'):
        builder().validate_report(data)
