"""Real isolated Edge extraction of invented owned L8 rows; no portal access."""
from copy import deepcopy
import pytest
import coretax_browser as driver
from support_financial_browser import browser as browser
from support_l8_spans import html, source
from support_templates import section
from test_corporate_compact_export import export


def test_l8_dom_cells_and_span_proof_reach_saved_public_export(browser, tmp_path):
    page = browser.new_page()
    try:
        page.set_content(html())
        captured = driver.capture_table(page, page.locator('table'), 1, 2)
        expected = source()
        assert captured['rows'] == expected['rows']
        assert captured.get('body_spans') == expected['body_spans']
        assert captured.get('body_rowspans') == expected['body_rowspans']
        assert captured.get('source_structure') == expected['source_structure']
        assert captured['body_row_count'] == 8 and captured['complete']
        before = deepcopy(captured)
        book, reports = export(tmp_path, [section('L8', tables=[captured])])
        try:
            assert book['L8']['C3'].value == 8000 and book['L8']['C10'].value == 44
            assert 'B2:C2' in book['L8'].merged_cells and reports[0]['complete']
            assert captured == before
        finally:
            book.close()
    finally:
        page.close()


@pytest.mark.parametrize('component,form', [('synthetic-foreign-grid','rshshr-citr-l8-form'),
    ('rsh-citr-l8-form-grid1','synthetic-foreign-form')])
def test_foreign_l8_dom_owner_cannot_supply_merge_proof(browser, component, form):
    page = browser.new_page()
    try:
        page.set_content(html(component=component,form=form))
        captured = driver.capture_table(page,page.locator('table'),1,2)
        assert 'body_spans' not in captured and 'source_structure' not in captured
        assert captured['body_row_count'] == 8
    finally:
        page.close()
