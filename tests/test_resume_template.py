"""The operator layout is exercised using invented scope and zero source rows."""
from pathlib import Path

from openpyxl import load_workbook
import pytest


def empty_run():
    return {'npwp': '0000000000000001', 'year': 2025, 'year_basis': 'period',
            'taxpayer_name': 'Synthetic template taxpayer', 'records': [],
            'audit': [], 'errors': [], 'complete': False, 'started_at': 'synthetic'}


def test_resume_uses_the_operator_reference_coordinates_without_sample_rows(tmp_path):
    from coretax_exporter import export_workbook
    run = empty_run()
    path = tmp_path / 'resume.xlsx'
    export_workbook(run, path, include_details=False)
    wb = load_workbook(path)
    try:
        assert wb.sheetnames == ['Ringkasan', 'Daftar SPT', 'Audit']
        summary = wb['Ringkasan']
        assert summary['B2'].value == run['npwp']
        assert summary['B2'].data_type == 's'
        assert summary['B3'].value == run['year']
        assert summary['B4'].value == run['taxpayer_name']
        assert summary['B5'].value == 'Masa/Tahun Pajak'
        assert summary['B6'].value == 'PARTIAL'
        assert summary['B7'].value == summary['B8'].value == 0
        assert summary.column_dimensions['A'].width == 30
        assert summary.column_dimensions['B'].width == 58
        assert 'A1:H1' in summary.merged_cells
        assert summary.freeze_panes is None
        index = wb['Daftar SPT']
        assert index.max_row == 4
        assert index.freeze_panes is None
        assert index['A5'].hyperlink is None
        assert wb['Audit']['A3'].value == 'Status / Objek'
        assert wb['Audit'].freeze_panes == 'A4'
    finally:
        wb.close()


def test_new_resume_scope_is_verified_independently_from_display_status(tmp_path):
    from coretax_exporter import export_workbook
    from coretax import verify_workbook
    run = empty_run()
    path = tmp_path / 'resume.xlsx'
    export_workbook(run, path, include_details=False)
    verify_workbook(path, run, include_details=False)
    wb = load_workbook(path)
    wb['Ringkasan']['B2'] = '0000000000000002'
    wb.save(path)
    wb.close()
    with pytest.raises(ValueError, match='NPWP'):
        verify_workbook(path, run, include_details=False)
