"""Synthetic split-file contract fixtures; never presented as taxpayer output."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import coretax
from openpyxl import load_workbook


def fixture_run():
    rows = [('badan-normal', 'PPh Badan', 'Januari - Desember 2025', 'Normal'),
            ('badan-amendment', 'PPh Badan', 'Januari - Desember 2025', 'Amendment 001'),
            ('21-january', 'PPh Pasal 21/26', 'Januari 2025', 'Normal'),
            ('21-february', 'PPh Pasal 21/26', 'Februari 2025', 'Normal'),
            ('unifikasi', 'PPh Unifikasi', 'Januari 2025', 'Normal')]
    return {'npwp': '0000000000000001', 'year': 2025, 'year_basis': 'period',
            'taxpayer_name': 'SYNTHETIC TEST FIXTURE ONLY', 'complete': False,
            'started_at': 'fixture', 'audit': [], 'errors': [],
            'records': [{'key': key, 'record_id': key, 'source_status': 'Fixture',
                         'meta': {'Jenis Pajak': tax, 'Masa Pajak': period, 'Model SPT': model},
                         'capture_complete': True, 'detail_url': '',
                         'sections': [{'name': 'Induk', 'text': '', 'tables': [],
                                       'fields': [{'label': 'Record marker', 'field': 'Marker', 'value': key}]}]}
                        for key, tax, period, model in rows]}


def test_save_output_separates_resume_and_one_file_per_tax_type(tmp_path):
    run = fixture_run()
    path = coretax.save_output(run, tmp_path)
    assert path.name == 'resume.xlsx', 'Separate resume workbook not implemented'
    assert {p.name for p in tmp_path.glob('*.xlsx')} == {'resume.xlsx', 'SPT_Badan.xlsx', 'SPT_21.xlsx', 'SPT_Unifikasi.xlsx'}
    resume = load_workbook(path)
    assert resume.sheetnames == ['Ringkasan', 'Daftar SPT', 'Audit'], 'Detailed SPT must not be embedded in resume.xlsx'
    assert resume['Daftar SPT'].max_row == 4 + len(run['records'])
    assert resume['Ringkasan']['B4'].value == run['npwp']
    assert resume['Ringkasan']['B4'].data_type == 's'
    expected = {'SPT_Badan.xlsx': run['records'][:2], 'SPT_21.xlsx': run['records'][2:4], 'SPT_Unifikasi.xlsx': run['records'][4:]}
    for filename, records in expected.items():
        wb = load_workbook(tmp_path / filename)
        assert len(wb.sheetnames[3:]) == len(records), 'Periods/amendments were split into separate files or lost'
        assert wb['Daftar SPT'].max_row == 4 + len(records)
        assert [wb['Daftar SPT'].cell(5+i, 4).value for i in range(len(records))] == [r['meta']['Masa Pajak'] for r in records]
        assert [wb['Daftar SPT'].cell(5+i, 5).value for i in range(len(records))] == [r['meta']['Model SPT'] for r in records]
        markers = [cell.value for ws in wb.worksheets[3:] for row in ws for cell in row if cell.value in {r['key'] for r in run['records']}]
        assert markers == [r['key'] for r in records], 'Another tax type leaked into this workbook'
        for row in wb['Daftar SPT'].iter_rows(min_row=5):
            assert row[1].value == records[0]['meta']['Jenis Pajak']
        wb.close()
    resume.close()


def test_resume_links_to_correct_external_detail_and_back(tmp_path):
    run = fixture_run()
    coretax.save_output(run, tmp_path)
    assert (tmp_path / 'resume.xlsx').is_file(), 'Separate resume workbook missing'
    resume = load_workbook(tmp_path / 'resume.xlsx')
    links = [resume['Daftar SPT'].cell(5+i, 1).hyperlink for i in range(len(run['records']))]
    assert [link.target for link in links] == ['SPT_Badan.xlsx', 'SPT_Badan.xlsx', 'SPT_21.xlsx', 'SPT_21.xlsx', 'SPT_Unifikasi.xlsx']
    for link in links:
        target = load_workbook(tmp_path / link.target)
        sheet_name = link.location.rsplit('!', 1)[0].strip("'")
        assert sheet_name in target.sheetnames
        back = target[sheet_name]['A2'].hyperlink
        assert back.target == 'resume.xlsx'
        assert back.location == "'Daftar SPT'!A1"
        target.close()
    resume.close()


def test_empty_scope_produces_only_resume_and_no_fake_type_files(tmp_path):
    run = fixture_run()
    run['records'] = []
    path = coretax.save_output(run, tmp_path)
    assert path.name == 'resume.xlsx'
    assert [p.name for p in tmp_path.glob('*.xlsx')] == ['resume.xlsx']
    wb = load_workbook(path)
    assert wb.sheetnames == ['Ringkasan', 'Daftar SPT', 'Audit']
    assert wb['Ringkasan']['B9'].value == 0
    wb.close()


def test_split_filename_collision_is_rejected_before_writing(tmp_path):
    import pytest
    run = fixture_run()
    run['records'] = run['records'][:2]
    run['records'][0]['meta']['Jenis Pajak'] = 'A/B'
    run['records'][1]['meta']['Jenis Pajak'] = 'A:B'
    with pytest.raises(ValueError, match='filename collision'):
        coretax.save_output(run, tmp_path)
    assert not list(tmp_path.glob('*.xlsx')), 'A colliding type must not overwrite another type file'


def test_another_npwp_cannot_overwrite_existing_output_scope(tmp_path):
    import pytest
    import json
    original = fixture_run()
    coretax.save_output(original, tmp_path)
    other = fixture_run()
    other['npwp'] = '0000000000000002'
    with pytest.raises(FileExistsError, match='scope'):
        coretax.save_output(other, tmp_path)
    saved = json.loads((tmp_path / 'run.json').read_text(encoding='utf-8'))
    assert saved['npwp'] == original['npwp']
