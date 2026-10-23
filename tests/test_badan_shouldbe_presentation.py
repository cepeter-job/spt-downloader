"""Sanitized operator layout behavior through saved public exports."""
from copy import deepcopy
import pytest
from support_templates import section
from test_corporate_compact_export import export


IDENTITY = [
    ('HEADER','TaxYear','Tahun Pajak/Bagian Tahun Pajak','2025'),
    ('HEADER','Status','Status','Amendment 001'),
    ('HEADER','AccountingPeriodStart','Periode Pembukuan','01/01/2025'),
    ('HEADER','AccountingPeriodEnd','Periode Pembukuan','31/12/2025'),
    ('A. IDENTITAS WAJIB PAJAK','Tin','1. NPWP','0000000000000002'),
    ('A. IDENTITAS WAJIB PAJAK','Name','2. Nama','SYNTHETIC FIXTURE ONLY'),
    ('B. INFORMASI LAPORAN KEUANGAN','TinAccountant','2.b. NPWP Kantor Akuntan Publik','0000000000000003'),
    ('B. INFORMASI LAPORAN KEUANGAN','NameAccountant','2.c. Nama Kantor Akuntan Publik','SYNTHETIC AUDITOR'),
    ('A. IDENTITAS WAJIB PAJAK','EmailAddress','3. Alamat Email','synthetic@example.invalid'),
    ('A. IDENTITAS WAJIB PAJAK','PhoneNumber','4. Nomor Telepon','0000123456'),
]
MONEY = [
    ('D. PENGHITUNGAN PPh','4. Penghasilan Neto Fiskal sebelum Fasilitas Pajak','0'),
    ('D. PENGHITUNGAN PPh','7. Penghasilan Neto Fiskal Setelah Fasilitas Pajak','-2.000'),
    ('D. PENGHITUNGAN PPh','9. Penghasilan Kena Pajak','1.234,50'),
    ('D. PENGHITUNGAN PPh','12. PPh Terutang','0'),
    ('E. PENGURANG PPh TERUTANG','13. Apakah terdapat kredit pajak yang dibayarkan di luar negeri dan/atau dipotong/pungut oleh pihak lain? / Tidak / Ya','1.234,50'),
    ('E. PENGURANG PPh TERUTANG','14. Angsuran PPh Pasal 25','0'),
    ('E. PENGURANG PPh TERUTANG','15. Surat Tagihan Pajak PPh Pasal 25 (hanya pokok pajak)','0'),
    ('E. PENGURANG PPh TERUTANG','16. Apakah Wajib Pajak memperoleh Fasilitas Pengurangan PPh Badan? * / Tidak / Ya','0'),
    ('F. PPh KURANG/LEBIH BAYAR','17.a. PPh yang Kurang/Lebih Bayar','-2.000'),
    ('F. PPh KURANG/LEBIH BAYAR','17.b. Apakah terdapat Surat Keputusan Persetujuan Pengangsuran atau Penundaan Pembayaran Pajak? / Tidak / Ya','0'),
    ('F. PPh KURANG/LEBIH BAYAR','17.c. PPh yang masih harus dibayar atau lebih dibayar','0'),
    ('F. PPh KURANG/LEBIH BAYAR','18.a. PPh yang kurang atau lebih bayar pada SPT yang dibetulkan / Ganti SPT sebelumnya','1.234,50'),
    ('F. PPh KURANG/LEBIH BAYAR','18.b. PPh yang kurang atau lebih bayar karena pembetulan','0'),
]


def fields():
    result=[{'group':g,'field':f,'label':label,'value':value} for g,f,label,value in IDENTITY]
    result += [{'group':g,'field':'','label':label,'value':value} for g,label,value in MONEY]
    result += [
        {'group':'F. PPh KURANG/LEBIH BAYAR','field':'','label':'Ganti SPT sebelumnya','value':'SYNTHETIC CHOICE'},
        {'group':'D. PENGHITUNGAN PPh','field':'TaxRate','label':'11. Tarif Pajak *',
         'value':'3.Tarif Fasilitas sebagaimana Pasal 31E ayat (1) UU PPh'},
    ]
    return result


def test_induk_shouldbe_preserves_values_with_typed_whole_accounting_and_spacing(tmp_path):
    raw=fields()
    before=deepcopy(raw)
    book,reports=export(tmp_path,[section('Induk',fields=raw)])
    try:
        sheet=book['Induk']
        assert sheet.max_row==28 and sheet.max_column==2
        assert all(cell.value is None for row in sheet.iter_rows(min_row=12,max_row=13) for cell in row)
        assert sheet['A14'].value=='Penghasilan Neto Fiskal sebelum Fasilitas Pajak'
        for row,value in [(14,0),(15,-2000),(16,1234.5),(17,0),(18,1234.5),(19,0),
                          (20,0),(21,0),(22,-2000),(23,0),(24,0),(26,1234.5),(27,0)]:
            cell=sheet.cell(row,2)
            assert cell.value==value and cell.data_type=='n'
            assert 'Rp' in cell.number_format and '#,##0' in cell.number_format
            assert '#,##0.' not in cell.number_format
        assert sheet['B6'].value=='0000000000000002' and sheet['B6'].data_type=='s'
        assert sheet['B2'].value=='2025' and sheet['B2'].data_type=='s'
        assert sheet['B25'].value=='SYNTHETIC CHOICE' and sheet['B25'].data_type=='s'
        assert sheet['B28'].value=='Tarif Fasilitas sebagaimana Pasal 31E ayat (1) UU PPh'
        assert reports[0]['complete'] and raw==before
    finally:
        book.close()


def test_induk_shouldbe_styles_apply_only_to_populated_blocks(tmp_path):
    book,_=export(tmp_path,[section('Induk',fields=fields())])
    try:
        sheet=book['Induk']
        assert sheet['A1'].font.bold and sheet.column_dimensions['B'].width==49.7109375
        for first,last in [(2,11),(14,28)]:
            for row in sheet.iter_rows(min_row=first,max_row=last,min_col=1,max_col=2):
                for cell in row:
                    assert all(getattr(cell.border,side).style=='thin' for side in ('top','bottom','left','right'))
        for row in sheet.iter_rows(min_row=12,max_row=13,min_col=1,max_col=2):
            assert all(cell.border.bottom.style is None for cell in row)
    finally:
        book.close()


@pytest.mark.parametrize('value', ['1234567890123456','1.23,00','1.234,567','=1+1',False])
def test_induk_bad_money_is_literal_and_unresolved(tmp_path,value):
    raw=[{'group':'D. PENGHITUNGAN PPh','field':'',
          'label':'4. Penghasilan Neto Fiskal sebelum Fasilitas Pajak','value':value}]
    book,reports=export(tmp_path,[section('Induk',fields=raw)])
    try:
        assert book['Induk']['B2'].value==value
        assert book['Induk']['B2'].data_type!='f'
        assert not reports[0]['complete'] and reports[0]['unmapped_fields']==1
    finally:
        book.close()


def test_induk_numeric_tariff_text_is_not_an_ordinal_caption(tmp_path):
    raw=[{'group':'D. PENGHITUNGAN PPh','field':'TaxRate','label':'11. Tarif Pajak *','value':'0.22'}]
    book,reports=export(tmp_path,[section('Induk',fields=raw)])
    try:
        assert book['Induk']['B2'].value=='0.22' and book['Induk']['B2'].data_type=='s'
        assert reports[0]['complete']
    finally:
        book.close()


@pytest.mark.parametrize('form,area',[('L6',(2,8,1,2)),('L8',(1,2,1,3))])
def test_clean_reference_borders_cover_empty_and_populated_form_slots(tmp_path,form,area):
    book,_=export(tmp_path,[section(form)])
    try:
        first,last,left,right=area
        for row in book[form].iter_rows(min_row=first,max_row=last,min_col=left,max_col=right):
            for cell in row:
                assert all(getattr(cell.border,side).style=='thin' for side in ('top','bottom','left','right'))
    finally:
        book.close()
