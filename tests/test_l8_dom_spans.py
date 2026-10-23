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


@pytest.mark.parametrize('lose_owner', [False, True])
def test_l8_pagination_preserves_raw_rows_but_never_maps_multipage_proof(browser, tmp_path, lose_owner):
    page = browser.new_page()
    try:
        page.set_content(html())
        page.evaluate('''loseOwner => {
            const owner = document.querySelector('p-table');
            const paginator = document.createElement('div');
            paginator.className = 'p-paginator';
            paginator.innerHTML = '<button class="p-paginator-page p-highlight">1</button>' +
                '<button class="p-paginator-next">Next</button>';
            owner.append(paginator);
            paginator.querySelector('.p-paginator-next').onclick = event => {
                owner.querySelector('tbody').innerHTML = '<tr><td></td><td>SYNTHETIC PAGE TWO</td><td>44</td></tr>';
                paginator.querySelector('.p-highlight').textContent = '2';
                event.currentTarget.disabled = true;
                if (loseOwner) {
                    const grid = owner.parentElement;
                    grid.replaceWith(owner);
                }
            };
        }''', lose_owner)
        captured = driver.capture_table(page, page.locator('table'), 1, 3)
        assert captured['pages'] == 2 and captured['body_row_count'] == 9
        assert captured['rows'] == source()['rows'][:-1] + [['', 'SYNTHETIC PAGE TWO', '44']] + source()['footer']
        assert captured['complete'] is (not lose_owner)
        assert len(captured['body_spans']) == (8 if lose_owner else 9)
        assert len(captured['body_rowspans']) == (8 if lose_owner else 9)
        if lose_owner:
            assert captured['warning'] == 'Table structural identity changed during pagination'
        else:
            book, reports = export(tmp_path, [section('L8', tables=[captured])])
            try:
                assert book['L8'].max_row == 2 and reports[0]['unmapped_rows'] == 10
                assert not reports[0]['complete']
            finally:
                book.close()
    finally:
        page.close()
