"""Observed PPN DOM structure, tested only with synthetic values."""
from test_pph21_template import section


import pytest


from playwright.sync_api import sync_playwright


import coretax_browser as driver


from test_ppn_unifikasi_templates import export, source_run


PPN_COLUMNS = ['Harga Jual/Penggantian/ Nilai Ekspor/DPP (Rupiah)',
               'DPP Nilai Lain/ DPP (Rupiah)', 'PPN (Rupiah)', 'PPnBM (Rupiah)']


def _grid_cells(values, inputs=False):
    return '<div class="col-md-5"><div class="row">' + ''.join(
        '<div class="col-md-3">' +
        (f'<p-inputnumber><span><input disabled value="{value}"></span></p-inputnumber>'
         if inputs and value is not None else ('' if inputs else value)) + '</div>'
        for value in values) + '</div></div>'


def test_ppn_observed_four_column_layout_binds_headers_not_input_order(tmp_path):
    label='Penyerahan yang PPN atau PPN dan PPnBM-nya harus dipungut sendiri lainnya (dengan Faktur Pajak Kode 01, 09 dan 10)'
    html='<div class="p-tabview-panel"><div class="p-accordion-header"><span class="p-accordion-header-text">I. PENYERAHAN BARANG DAN JASA</span></div><div class="p-accordion-content">'
    html+='<div class="row"><div class="col-md-7"></div>'+_grid_cells(PPN_COLUMNS)+'</div>'
    html+='<div class="row"><div class="col-md-7"><label>'+label+'</label></div>'+_grid_cells(['11',None,'17','19'],True)+'</div></div></div>'
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True)
        try:
            page=browser.new_page();page.set_content(html)
            fields=page.locator('.p-tabview-panel').evaluate(driver.FIELDS_JS)
            assert [f.get('column_label') for f in fields] == [PPN_COLUMNS[0],PPN_COLUMNS[2],PPN_COLUMNS[3]]
        finally:
            browser.close()
    wb=export('PPN',source_run('PPN',[section('INDUK',fields=fields)]),tmp_path)
    try:
        assert [wb['INDUK'].cell(15,c).value for c in range(5,9)] == ['11',None,'17','19']
    finally:
        wb.close()


def test_ppn_grid_never_borrows_sibling_accordion_headers():
    html='<div class="p-tabview-panel"><div class="p-accordion-content">'
    html+='<div class="row">'+_grid_cells(PPN_COLUMNS)+'</div></div>'
    html+='<div class="p-accordion-content"><div class="row"><div class="col-md-7"><label>SYNTHETIC LABEL</label></div>'+_grid_cells(['17',None,None,None],True)+'</div></div></div>'
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True)
        try:
            page=browser.new_page();page.set_content(html)
            fields=page.locator('.p-tabview-panel').evaluate(driver.FIELDS_JS)
            assert len(fields)==1 and 'column_label' not in fields[0]
        finally:
            browser.close()


@pytest.mark.parametrize('group,label,column,target', [
    ('II. PEROLEHAN BARANG DAN JASA','Impor BKP, Pemanfaatan BKP Tidak Berwujud dan/atau JKP dari luar Daerah Pabean di dalam Daerah Pabean yang Pajak Masukannya dapat dikreditkan','Harga Jual/Penggantian/Nilai Impor/DPP (Rupiah)','E28'),
    ('II. PEROLEHAN BARANG DAN JASA','Kompensasi kelebihan Pajak Masukan','PPN (Rupiah)','G32'),
    ('V. PEMBAYARAN KEMBALI PAJAK MASUKAN YANG TIDAK DAPAT DIKREDITKAN','PPN yang wajib dibayar kembali','PPN (Rupiah)','E56'),
    ('VII. PEMUNGUTAN PPN ATAU PPN DAN PPNBM OLEH PEMUNGUT PPN','Jumlah PPN dan PPnBM yang dipungut','HARGA JUAL/PENGGANTIAN/DPP (Rupiah)','E69'),
    ('VIII. PEMUNGUTAN PPN ATAU PPN DAN PPNBM OLEH PIHAK LAIN','Jumlah PPN dan PPnBM yang dipungut','HARGA JUAL/PENGGANTIAN/DPP (Rupiah)','E75'),
])
def test_ppn_observed_labels_bind_reference_slots_without_restating_template(tmp_path,group,label,column,target):
    fields=[{'label':label,'field':'','group':group,'column_label':column,'value':'17,00'}]
    wb=export('PPN',source_run('PPN',[section('INDUK',fields=fields)]),tmp_path)
    try:
        assert wb['INDUK'][target].value=='17,00'
        assert wb['INDUK']['B26'].value.strip()=='PENYERAHAN BARANG DAN JASA'
    finally:
        wb.close()


def test_ppn_semantic_aliases_do_not_escape_their_verified_sections(tmp_path):
    fields=[{'label':'Kompensasi kelebihan Pajak Masukan','field':'','group':'I. PEROLEHAN BARANG DAN JASA','column_label':'PPN (Rupiah)','value':'17,00'},
            {'label':'PPN yang wajib dibayar kembali','field':'','group':'','column_label':'PPN (Rupiah)','value':'19,00'}]
    wb=export('PPN',source_run('PPN',[section('INDUK',fields=fields)]),tmp_path)
    try:
        assert wb['INDUK']['G32'].value is None
        assert wb['INDUK']['E56'].value is None
        assert any(c.value=='19,00' for cells in wb['INDUK'] for c in cells)
    finally:
        wb.close()


def test_ppn_grid_does_not_assign_amount_units_to_plain_text_metadata():
    html='<div class="p-tabview-panel"><div class="p-accordion-content">'
    html+='<div class="row">'+_grid_cells(PPN_COLUMNS)+'</div>'
    html+='<div class="row"><div class="col-md-7"><label>Nama Bank</label></div>'
    html+='<div class="col-md-5"><div class="row"><div class="col-md-3"></div><div class="col-md-3"></div><div class="col-md-3"><input value="SYNTHETIC BANK" disabled></div><div class="col-md-3"></div></div></div></div></div></div>'
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True)
        try:
            page=browser.new_page();page.set_content(html)
            fields=page.locator('.p-tabview-panel').evaluate(driver.FIELDS_JS)
            assert len(fields)==1 and 'column_label' not in fields[0]
        finally:
            browser.close()
