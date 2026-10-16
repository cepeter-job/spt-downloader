"""Synthetic templates helpers; no collected tests or shared mutable test state."""
from copy import copy
from openpyxl import load_workbook
import coretax
import coretax_exporter as exporter


COMMON_HEADERS = ['NO.', 'NIK/NPWP', 'NAMA', 'NOMOR BUKTI POTONG',
                  'TANGGAL BUKTI PEMOTONGAN', 'KODE OBJEK PAJAK',
                  'PENGHASILAN BRUTO (Rp)', 'PAJAK PENGHASILAN (Rp)',
                  'FASILITAS PERPAJAKAN', 'Negara', 'ID TEMPAT KEGIATAN USAHA',
                  'KAP-KJS', 'STATUS']


IA_HEADERS = COMMON_HEADERS[:7] + ['TARIF PAJAK (%)'] + COMMON_HEADERS[7:]


def table(name, values, *, ia=False, headers=None, complete=True):
    return {'name': name, 'headers': list(headers or (IA_HEADERS if ia else COMMON_HEADERS)),
            'rows': values, 'complete': complete}


def section(name, *, tables=None, fields=None, text=''):
    return {'name': name, 'fields': fields or [], 'tables': tables or [], 'text': text}


def run_for(sections, *, model='Normal', key='synthetic-21-normal'):
    return {'npwp': '0000000000000001', 'year': 2025, 'year_basis': 'period',
            'taxpayer_name': 'SYNTHETIC FIXTURE ONLY', 'complete': False,
            'started_at': 'fixture', 'audit': [], 'errors': [],
            'records': [{'key': key, 'record_id': key, 'source_status': 'Fixture',
                         'meta': {'Jenis Pajak': 'PPh Pasal 21/26',
                                  'Masa Pajak': 'Januari 2025', 'Model SPT': model},
                         'capture_complete': True, 'detail_url': '', 'sections': sections}]}


def cells_with(workbook, value):
    return [c for ws in workbook for cells in ws for c in cells if c.value == value]


def assert_format(actual, reference):
    # Style IDs are workbook-local; compare rendered style components instead.
    for attribute in ('font', 'fill', 'border', 'alignment', 'protection'):
        assert copy(getattr(actual, attribute)) == copy(getattr(reference, attribute))
    assert actual.number_format == reference.number_format


def assert_layout(actual, reference):
    assert set(str(r) for r in actual.merged_cells.ranges) == set(str(r) for r in reference.merged_cells.ranges)
    for key, dimension in reference.column_dimensions.items():
        got = actual.column_dimensions[key]
        for attr in ('width', 'hidden', 'min', 'max', 'bestFit', 'outlineLevel', 'collapsed'):
            assert getattr(got, attr) == getattr(dimension, attr)
    for key, dimension in reference.row_dimensions.items():
        got = actual.row_dimensions[key]
        for attr in ('height', 'hidden', 'outlineLevel', 'collapsed'):
            assert getattr(got, attr) == getattr(dimension, attr)
    for attr in ('sheet_format', 'page_margins', 'print_options'):
        assert copy(getattr(actual, attr)) == copy(getattr(reference, attr))
    for attr in ('orientation', 'paperSize', 'fitToWidth', 'fitToHeight'):
        assert getattr(actual.page_setup, attr) == getattr(reference.page_setup, attr)
    for cells in reference:
        for c in cells:
            assert_format(actual[c.coordinate], c)


TYPES = {
    'PPN': {'reference': 'ppn_format.xlsx',
            'sha256': 'f426a2e428d62fa0af679024f8038195f6198780a2fc15817301982aa4d3fa16',
            'styles': 'c9bae8ced0551e1993d6d09c16fc304e0bc8bb98c1d2d7f6e06657ff7d5c3cc8',
            'forms': ['Induk', 'A1', 'A2', 'B1', 'B2', 'B3', 'C'],
            'path': 'SPT Masa PPN/SPT_PPN_Januari 2025_Normal.xlsx',
            'resource': 'resources/ppn_format.xlsx'},
    'PPh Unifikasi': {'reference': 'unifikasi_format.xlsx',
                     'sha256': '2ad49e997b6404a687c273dc7d895245e6d03593b8d76678b0928f8573efc7a2',
                     'styles': 'e4fb3f3684fc70914742af99a321fb17d950cc75b44b8b553df49ca071f37f0c',
                     'forms': ['Induk', 'Daftar I', 'Daftar II', 'Lampiran I'],
                     'path': 'SPT Masa Unifikasi/SPT_Unifikasi_Januari 2025_Normal.xlsx',
                     'resource': 'resources/unifikasi_format.xlsx'},
}


def source_run(tax, sections):
    run = run_for(sections, key='synthetic-template-normal')
    run['records'][0]['meta']['Jenis Pajak'] = tax
    return run


def export(tax, run, folder):
    files = exporter.export_split_workbooks(run, folder)
    coretax.verify_outputs(run, folder)
    assert set(files) == {'resume.xlsx', TYPES[tax]['path']}
    return load_workbook(folder / TYPES[tax]['path'])
