"""Synthetic DOM metadata; never live taxpayer data."""
from support_isolated_browser import browser as browser, isolated_context


def test_dom_keeps_visible_group_and_footer_boundary(browser):
    import coretax_browser as driver
    html = '''<div class="main-content"><div class="p-tabview-panel">
    <section><h3>LAMPIRAN PPN</h3><p-table><table>
    <thead><tr><th>No.</th><th>Nama</th><th>Nilai</th></tr></thead>
    <tbody><tr><td>1</td><td>SYNTHETIC</td><td>17</td></tr></tbody>
    <tfoot><tr><td colspan="2">Jumlah</td><td>17</td></tr></tfoot>
    </table></p-table></section></div></div>'''
    with isolated_context(browser) as context:
        page = context.new_page()
        page.set_content(html)
        table = driver.capture_table(page, page.locator('table'), 1, 5)
        assert 'LAMPIRAN PPN' in table['group']
        assert table['body_row_count'] == 1
        assert table['footer'] == [['Jumlah', '17']]
        assert table['footer_spans'] == [[2, 1]]
        assert table['rows'] == [['1', 'SYNTHETIC', '17'], ['Jumlah', '17']]


def test_dom_field_context_keeps_visible_group_and_column_label(browser):
    import coretax_browser as driver
    html = '''<div class="p-tabview-panel"><section>
    <h3>VII. PEMUNGUTAN PPN ATAU PPN DAN PPNBM OLEH PEMUNGUT PPN</h3>
    <div class="row"><label for="amount">Jumlah PPN dan PPnBM yang dipungut</label>
    <div><label>PPN (Rupiah)</label><input id="amount" disabled value="17"></div></div>
    </section></div>'''
    with isolated_context(browser) as context:
        page = context.new_page()
        page.set_content(html)
        fields = page.locator('.p-tabview-panel').evaluate(driver.FIELDS_JS)
        assert fields[0]['label'] == 'Jumlah PPN dan PPnBM yang dipungut'
        assert fields[0]['group'].startswith('VII.')
        assert fields[0]['column_label'] == 'PPN (Rupiah)'
        assert fields[0]['value'] == '17'


def test_dom_does_not_take_group_from_sibling_table(browser):
    import coretax_browser as driver
    html = '''<div class="p-tabview-panel"><section><h3>BPA1</h3>
    <table><thead><tr><th>No.</th></tr></thead></table></section>
    <section><table id="second"><thead><tr><th>No.</th></tr></thead></table></section></div>'''
    with isolated_context(browser) as context:
        page = context.new_page()
        page.set_content(html)
        table = driver.capture_table(page, page.locator('#second'), 2, 5)
        assert not table.get('group')
