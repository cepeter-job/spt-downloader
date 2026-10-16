"""Public portal structure; synthetic values only, never taxpayer captures."""
import pytest
from playwright.sync_api import sync_playwright
import coretax_browser as driver
from test_pph21_template import COMMON_HEADERS, INDUK_HEADERS, export, row, run_for, section, table


def test_nested_primeng_titles_bind_own_tables():
    html = '<div class="p-tabview-panel"><h3>Outer form title</h3>'
    for group in ['BPA1', 'BPA2']:
        html += f'''<div class="p-panel"><div class="p-panel-header"><span class="p-panel-title">{group}</span></div>
        <div class="p-toggleable-content"><div class="p-panel-content"><table id="{group}">
        <thead><tr><th>NO.</th></tr></thead><tbody></tbody></table></div></div></div>'''
    html += '</div>'
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        try:
            page = browser.new_page()
            page.set_content(html)
            actual = [driver.capture_table(page, page.locator('#'+group), i, 5)['group']
                      for i, group in enumerate(['BPA1', 'BPA2'], 1)]
            assert actual == ['BPA1', 'BPA2']
        finally:
            browser.close()


@pytest.mark.parametrize('tax,amount_row', [('21', 21), ('26', 35)])
def test_named_government_block_accepts_observed_label(tmp_path, tax, amount_row):
    data = table('Tabel 2', [['1.', f'PAJAK PENGHASILAN PASAL {tax} DITANGGUNG PEMERINTAH',
                              'SYNTHETIC-KAP', '23,00']], headers=INDUK_HEADERS)
    data['group'] = f'II. PAJAK PENGHASILAN PASAL {tax} YANG DITANGGUNG OLEH PEMERINTAH'
    wb = export(run_for([section('Induk', tables=[data])]), tmp_path)
    try:
        assert wb['Induk'].cell(amount_row, 4).value == '23,00'
        assert wb['Induk'].cell(12 if tax == '21' else 26, 4).value is None
    finally:
        wb.close()


@pytest.mark.parametrize('tax,amount_row', [('21', 16), ('26', 30)])
def test_induk_annotation_keeps_amount_and_literal_label(tmp_path, tax, amount_row):
    label = f'PPH PASAL {tax} YANG KURANG (LEBIH) DISETOR PADA SPT YANG DIBETULKAN'
    label += ' This row contain the total amount of payment before amendment.'
    data = table('Tabel 1', [['5.', label, '', '31,00']], headers=INDUK_HEADERS)
    data['group'] = f'I. PAJAK PENGHASILAN PASAL {tax} YANG DIPOTONG'
    wb = export(run_for([section('Induk', tables=[data])]), tmp_path)
    try:
        assert wb['Induk'].cell(amount_row, 4).value == '31,00'
        assert wb['Induk'].cell(amount_row, 2).value == label
    finally:
        wb.close()


@pytest.mark.parametrize('form,group,extra', [
    ('L-II', 'BPA2', ['MASA PEEROLEHAN PENGHASILAN']),
    ('L-III', 'BP26', ['JENIS PAJAK', 'OBJEK PAJAK']),
])
def test_appendix_projects_known_extras_but_not_footer(tmp_path, form, group, extra):
    headers = [name for name in COMMON_HEADERS if name not in (
        ('FASILITAS PERPAJAKAN', 'KAP-KJS') if form == 'L-II' else ('Negara',))]
    if form == 'L-II':
        headers.insert(8, extra[0])
    else:
        headers.insert(3, extra[0])
        headers.insert(7, extra[1])
    source = dict(zip(COMMON_HEADERS, row()))
    source.update({name: 'SYNTHETIC EXTRA ' + name for name in extra})
    values = [source[name] for name in headers]
    expected = [source[name] if name in headers else None for name in COMMON_HEADERS]
    headers[headers.index('TANGGAL BUKTI PEMOTONGAN')] += ' (dd-mm-yyyy)'
    footer = ['SYNTHETIC FOOTER', '47,00']
    data = table('Tabel 2', [values, footer], headers=headers)
    data.update(group=group, body_row_count=1)
    wb = export(run_for([section(form, tables=[data])]), tmp_path)
    try:
        assert [wb[form].cell(11, c).value for c in range(1, 14)] == expected
        assert wb[form]['A12'].value is None
        for value in [source[name] for name in extra] + [footer[0]]:
            assert any(cell.value == value for cells in wb[form] for cell in cells)
    finally:
        wb.close()


@pytest.mark.parametrize('tax', ['21', '26'])
def test_government_alias_never_fills_deducted_block(tmp_path, tax):
    data = table('Tabel 1', [['1.', f'PAJAK PENGHASILAN PASAL {tax} DITANGGUNG PEMERINTAH',
                              'SYNTHETIC-KAP', '53,00']], headers=INDUK_HEADERS)
    data['group'] = f'I. PAJAK PENGHASILAN PASAL {tax} YANG DIPOTONG'
    wb = export(run_for([section('Induk', tables=[data])]), tmp_path)
    try:
        assert all(wb['Induk'].cell(r, 4).value is None for r in (12, 21, 26, 35))
        assert any(cell.value == '53,00' for cells in wb['Induk'] for cell in cells)
    finally:
        wb.close()


def test_unknown_appendix_column_still_blocks_projection(tmp_path):
    data = table('BP21', [row() + ['SYNTHETIC UNKNOWN']], headers=COMMON_HEADERS + ['Unknown source column'])
    wb = export(run_for([section('L-III', tables=[data])]), tmp_path)
    try:
        assert wb['L-III']['A5'].value is None
        assert any(cell.value == 'SYNTHETIC UNKNOWN' for cells in wb['L-III'] for cell in cells)
    finally:
        wb.close()
