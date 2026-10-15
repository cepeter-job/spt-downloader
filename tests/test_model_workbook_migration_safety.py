"""Synthetic negative migration contracts added from actual source review."""
from copy import deepcopy

import pytest
from openpyxl import load_workbook

from spt_desktop import output
from test_financial_publication import CHANGED_PDF
from test_model_workbook_publication import legacy_export, physical_bytes


@pytest.mark.parametrize('format_name', ['forms', 'legacy'])
@pytest.mark.parametrize('mutation', ['missing', 'hash'])
def test_legacy_migration_verifies_unselected_old_complete_pdf(tmp_path, format_name, mutation):
    downloads = tmp_path / 'Downloads'
    run, old = legacy_export(downloads, format_name=format_name)
    selected = deepcopy(run)
    selected['records'] = selected['records'][:1]
    unselected = old / run['records'][2]['attachments'][0]['relative_path']
    if mutation == 'missing':
        unselected.unlink()
    else:
        unselected.write_bytes(CHANGED_PDF)
    before = physical_bytes(old)
    with pytest.raises((ValueError, OSError), match='(?i)pdf|financial|attachment|file|directory'):
        output.existing_outputs(selected, downloads)
    assert physical_bytes(old) == before


@pytest.mark.parametrize('format_name', ['forms', 'legacy'])
@pytest.mark.parametrize('mutation', ['missing-sheet', 'wrong-amendment'])
def test_legacy_migration_resume_binds_first_physical_form_of_the_right_model(tmp_path, format_name, mutation):
    downloads = tmp_path / 'Downloads'
    run, old = legacy_export(downloads, format_name=format_name)
    workbook = load_workbook(old / 'resume.xlsx')
    try:
        link = workbook['Daftar SPT']['A6'].hyperlink
        assert link.target == 'SPT_Badan.xlsx' and link.location == "'Induk (2)'!A1"
        link.location = "'SYNTHETIC MISSING'!A1" if mutation == 'missing-sheet' else "'Induk'!A1"
        workbook.save(old / 'resume.xlsx')
    finally:
        workbook.close()
    before = physical_bytes(old)
    with pytest.raises(ValueError, match='(?i)scope|link|sheet|form|detail|resume'):
        output.existing_outputs(run, downloads)
    assert physical_bytes(old) == before
