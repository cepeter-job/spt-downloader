"""PPN header and amendment display contracts; only synthetic records."""
import pytest

import coretax_exporter as exporter
from test_pph21_template import section
from test_ppn_form_completion import APPENDICES, GROUP_III, RAW_MARKER, export_ppn, source_appendix


@pytest.mark.parametrize('period', ['022031', '02022031'])
@pytest.mark.parametrize('status', ['Normal', 'Pembetulan'])
def test_induk_period_and_status_use_exact_observed_header_not_inventory_model(tmp_path, period, status):
    fields = [
        {'field': 'BookkeepingPeriod', 'label': 'Periode * / Periode Pembukuan', 'group': 'HEADER', 'value': 'Other'},
        {'field': 'Period', 'label': 'Periode * / Periode Pembukuan', 'group': 'HEADER', 'value': period},
        {'field': '', 'label': 'Normal/Pembetulan', 'group': 'HEADER', 'value': status},
        {'field': '', 'label': 'Status Penyampaian', 'value': 'SYNTHETIC DELIVERY'},
    ]
    workbook, _, source = export_ppn(tmp_path, [section('Induk', fields=fields)])
    try:
        sheet = workbook['Induk']
        assert [sheet[c].value for c in ('D4', 'D5', 'D6')] == ['02', '2031', status]
        assert sheet['A7'].value is None and sheet['D7'].value is None
        assert sheet['B48'].value == 'Diminta Untuk'
        assert sheet.max_row == 78
        proof = exporter.read_workbook_proof(workbook)
        assert proof['records'][0]['meta'] == source['records'][0]['meta']
    finally:
        workbook.close()


@pytest.mark.parametrize('period', ['2/2031', '132031', ' 022031', '022031 ', '0220310'])
def test_malformed_period_is_not_silently_repaired(tmp_path, period):
    fields = [{'field': 'Period', 'label': 'Periode * / Periode Pembukuan', 'group': 'HEADER', 'value': period}]
    workbook, reports, _ = export_ppn(tmp_path, [section('Induk', fields=fields)])
    try:
        assert workbook['Induk']['D4'].value is None
        assert workbook['Induk']['D5'].value is None
        assert not all(report['complete'] for report in reports)
        assert workbook['Induk'].max_row == 78
    finally:
        workbook.close()


@pytest.mark.parametrize('values', [['true', '-17,00'], ['false', '0'], ['-17,00', 'true'],
                                    ['false', '1.234.567,89'], ['true', '1,234,567.89']])
def test_amendment_difference_maps_numeric_control_not_same_label_checkbox(tmp_path, values):
    fields = [{'field': '', 'label': 'Ganti SPT sebelumnya', 'group': GROUP_III, 'value': value}
              for value in values]
    workbook, _, _ = export_ppn(tmp_path, [section('Induk', fields=fields)])
    try:
        expected = next(value for value in values if value not in ('true', 'false'))
        expected = {'-17,00': -17, '0': 0, '1.234.567,89': 1234567.89}.get(expected, expected)
        assert workbook['Induk']['E47'].value == expected
        assert workbook['Induk']['E46'].value is None
    finally:
        workbook.close()


@pytest.mark.parametrize('values', [['true'], ['17', '19'], ['=1+1'], [True], ['NaN']])
def test_amendment_ambiguous_or_nonnumeric_controls_do_not_become_tax_amounts(tmp_path, values):
    fields = [{'field': '', 'label': 'Ganti SPT sebelumnya', 'group': GROUP_III, 'value': value}
              for value in values]
    workbook, _, _ = export_ppn(tmp_path, [section('Induk', fields=fields)])
    try:
        assert workbook['Induk']['E47'].value is None
        assert workbook['Induk'].max_row == 78
    finally:
        workbook.close()


def test_ppn_omits_unknown_fields_context_and_extra_grid_columns_without_mutating_capture(tmp_path):
    table, _ = source_appendix(*APPENDICES[0], count=1)
    table['headers'].append('Masa Pajak')
    table['rows'][0].append('SYNTHETIC EXTRA PERIOD')
    table['footer'][0].append('')
    table['footer_spans'][0].append(1)
    fields = [{'label': 'SYNTHETIC UNKNOWN FIELD', 'value': 'SYNTHETIC OMITTED VALUE'}]
    workbook, reports, _ = export_ppn(tmp_path, [section('A1', tables=[table], fields=fields,
                                                         text='SYNTHETIC CONTEXT')])
    try:
        values = [cell.value for row in workbook['A1'] for cell in row]
        assert not set(values) & {RAW_MARKER, 'SYNTHETIC OMITTED VALUE',
                                  'SYNTHETIC EXTRA PERIOD', 'SYNTHETIC CONTEXT'}
        assert workbook['A1']['E7'].value == 0
        assert reports[0]['unmapped_fields'] == 1
    finally:
        workbook.close()
