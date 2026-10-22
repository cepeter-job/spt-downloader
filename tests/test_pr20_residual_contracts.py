"""Small residual contracts from PR20; synthetic fixtures, runner execution only."""
from copy import deepcopy


def test_nested_primeng_tables_use_their_own_visible_heading():
    """A generic outer heading must not replace either table's local owner."""
    from playwright.sync_api import sync_playwright
    import coretax_browser as driver

    html = '<div class="p-tabview-panel"><h3>Outer form title</h3>'
    for group in ('BPA1', 'BPA2'):
        html += f'''<div class="p-panel">
          <div class="p-panel-header"><span class="p-panel-title">{group}</span></div>
          <div class="p-toggleable-content"><div class="p-panel-content">
            <table id="{group}"><thead><tr><th>NO.</th></tr></thead>
              <tbody><tr><td>1</td></tr></tbody></table>
          </div></div></div>'''
    html += '</div>'
    with sync_playwright() as engine:
        browser = engine.chromium.launch(channel='msedge', headless=True)
        try:
            page = browser.new_page()
            page.set_content(html)
            captured = [driver.capture_table(page, page.locator('#' + group), index, 5)
                        for index, group in enumerate(('BPA1', 'BPA2'), 1)]
            assert [item['group'] for item in captured] == ['BPA1', 'BPA2']
            assert all(item['rows'] == [['1']] and item['body_row_count'] == 1
                       for item in captured)
        finally:
            browser.close()


def test_zero_only_body_row_is_not_confused_with_blank_or_footer():
    """Pin the shared boundary directly: other nonzero cells can mask this bug."""
    from coretax_template_cells import _body_rows

    table = {'headers': ['Nilai'], 'rows': [[0], [''], [None], ['TOTAL']],
             'body_row_count': 3}
    original = deepcopy(table)
    body, unresolved = _body_rows(table)
    assert body == [[0]]
    assert unresolved == [[''], [None], ['TOTAL']]
    assert table == original


def test_unifikasi_induk_wrong_footer_spans_remain_unmapped(tmp_path):
    """Retain the old safety scenario, not its obsolete row-27/string-money layout."""
    from support_templates import section
    from test_unifikasi_dom_repair import HEADERS, export, source_table

    footer = [['TOTAL OF INCOME TAX', '31', '37', '41', '43', '47', '53']]
    table = source_table(HEADERS, [], 'B. PAJAK PENGHASILAN', footer,
                         [[1, 2, 1, 1, 1, 1, 1]])
    original = deepcopy(table)
    book, reports = export(tmp_path, [section('INDUK', tables=[table])])
    try:
        assert all(book['INDUK'].cell(25, column).value is None
                   for column in range(3, 9))
        assert reports and not reports[0]['complete']
        assert reports[0]['unmapped_tables'] == 1
        assert reports[0]['unmapped_rows'] == 1
        assert not any(cell.value == '53' for cells in book['INDUK'] for cell in cells)
        assert table == original
    finally:
        book.close()
