"""Publication fixtures are synthetic and never live taxpayer output."""
import importlib
import importlib.util
from pathlib import Path
import pytest
import coretax
from test_split_output import fixture_run
from openpyxl import load_workbook


def module():
    assert importlib.util.find_spec('spt_desktop.output'), 'Downloads publication is missing'
    return importlib.import_module('spt_desktop.output')


def test_publish_preserves_raw_name_links_and_only_excel_files(tmp_path):
    run = fixture_run()
    run['taxpayer_name'] = 'SYNTHETIC / 日本 WP'
    source = tmp_path / 'local-job'
    coretax.save_output(run, source)
    downloads = tmp_path / 'OneDrive - Fixture' / 'Downloads 日本'
    final = module().publish_workbooks(run, source, downloads, 'synthetic-job')
    assert final.parent.name == '2025'
    assert final.parent.parent.name == '0000000000000001 - SYNTHETIC _ 日本 WP'
    assert {p.relative_to(final).as_posix() for p in final.rglob('*.xlsx')} == set(run['output_files'])
    assert not list(downloads.rglob('*.json'))
    wb = load_workbook(final/'resume.xlsx')
    try:
        assert wb['Ringkasan']['B6'].value == run['taxpayer_name']
        assert wb['Ringkasan']['B8'].value == 'PARTIAL'
        assert (final / wb['Daftar SPT']['A5'].hyperlink.target).is_file()
    finally: wb.close()
    coretax.verify_outputs(run, final)


def test_missing_taxpayer_name_blocks_publication(tmp_path):
    run = fixture_run()
    run['taxpayer_name'] = ''
    coretax.save_output(run,tmp_path/'local')
    with pytest.raises(ValueError, match='Nama WP'):
        module().publish_workbooks(run,tmp_path/'local',tmp_path/'Downloads','synthetic-job')
    assert not (tmp_path/'Downloads').exists()


def test_traversal_output_name_is_rejected_before_copy(tmp_path):
    run = fixture_run()
    coretax.save_output(run,tmp_path/'local')
    run['output_files'].append('../private.xlsx')
    with pytest.raises(ValueError, match='filename|nama|workbook'):
        module().publish_workbooks(run,tmp_path/'local',tmp_path/'Downloads','synthetic-job')


def test_copy_failure_cannot_advertise_finished_result(tmp_path,monkeypatch):
    output = module()
    run = fixture_run()
    coretax.save_output(run,tmp_path/'local')
    def fail(*args,**kwargs): raise OSError('Synthetic disk full')
    monkeypatch.setattr(output.shutil,'copy2',fail)
    with pytest.raises(OSError,match='disk full'):
        output.publish_workbooks(run,tmp_path/'local',tmp_path/'Downloads','synthetic-job')
    assert not list((tmp_path/'Downloads').rglob('*.xlsx'))
    assert (tmp_path/'local'/'run.json').is_file()


def test_previous_exports_are_never_overwritten(tmp_path):
    run = fixture_run()
    coretax.save_output(run,tmp_path/'local')
    first = module().publish_workbooks(run,tmp_path/'local',tmp_path/'Downloads','first-job')
    before = (first/'resume.xlsx').read_bytes()
    second = module().publish_workbooks(run,tmp_path/'local',tmp_path/'Downloads','second-job')
    assert first != second and first.parent == second.parent
    assert (first/'resume.xlsx').read_bytes() == before


def test_preexisting_taxpayer_directory_cannot_redirect_publication_outside_downloads(tmp_path):
    import subprocess
    import sys

    run = fixture_run()
    run['taxpayer_name'] = 'SYNTHETIC WP'
    source = tmp_path/'local'
    coretax.save_output(run,source)
    downloads = tmp_path/'Downloads'
    downloads.mkdir()
    outside = tmp_path/'outside'
    outside.mkdir()
    redirected = downloads/'0000000000000001 - SYNTHETIC WP'
    if sys.platform == 'win32':
        # Directory junctions do not need the symlink privilege on Windows CI.
        subprocess.run(['cmd','/d','/c','mklink','/J',str(redirected),str(outside)],
                       check=True,capture_output=True,text=True,timeout=10)
    else:
        redirected.symlink_to(outside,target_is_directory=True)
    with pytest.raises(ValueError,match='Downloads'):
        module().publish_workbooks(run,source,downloads,'synthetic-redirect')
    assert list(outside.iterdir()) == []
    assert (source/'resume.xlsx').is_file()
