"""Saved candidate layout and unchanged fail-closed native path; CI only."""
from copy import deepcopy
import hashlib
from pathlib import Path

from openpyxl import load_workbook
import pytest

import coretax_browser as driver
import coretax_exporter as exporter
from coretax_json import adapt_corporate_detail, has_audit_dump_tables
import support_json_corpus as corpus
from support_templates import section, source_run
from test_corporate_compact_export import export
from test_corporate_l10c_projection import ROOT, HEADERS, project, raw_source
from test_corporate_l7_native import L7Fixture, selected, packet, bindings
from test_json_hybrid_native import browser as browser

RESOURCE = Path(__file__).resolve().parents[1] / 'resources/corporate_format.xlsx'
RESOURCE_SHA256 = '47770d95a613ed496c8f121cbe39f41ea17947855e709ab0f931adbe9ca58ab0'


def candidate_section():
    result = project()
    value = section('L10-C', tables=[result['table']])
    for key in ('projection_complete', 'projection_reason', 'projection_unresolved_fields'):
        value[key] = deepcopy(result[key])
    return value


def test_candidate_saved_layout_grows_rows_without_question_footer_or_false_complete(tmp_path):
    value = candidate_section()
    before = deepcopy(value)
    book, reports = export(tmp_path, [value])
    try:
        sheet = book['L10-C']
        assert sheet.max_row == 4 and sheet.max_column == 5
        assert [cell.value for cell in sheet[2]] == HEADERS
        assert [sheet.cell(row, 1).value for row in (3, 4)] == ['1', '2']
        assert sheet['B3'].value == sheet['B4'].value == '00012 SYNTHETIC PARTNER'
        assert sheet['C3'].value == 'SYNTHETIC TRANSACTION DESCRIPTION'
        assert sheet['D4'].value == 'SYNTHETIC COUNTRY DESCRIPTION'
        assert sheet['E3'].value == sheet['E4'].value == 1234.125
        for address in ('E3', 'E4'):
            assert sheet[address].data_type == 'n'
            assert 'Rp' in sheet[address].number_format and '0.00' not in sheet[address].number_format
        assert not sheet.merged_cells.ranges
        assert all('JUMLAH' not in str(cell.value) and 'PRINSIP KEWAJARAN' not in str(cell.value)
                   for row in sheet for cell in row)
        report, = reports
        assert not report['complete']
        assert report['derived_complete'] is False
        assert report['derived_reason'] == 'unprojected_l10c_controls'
        assert report['unmapped_fields'] == 3 and report['unmapped_tables'] == report['unmapped_rows'] == 0
        assert {field['field'] for field in report['unmapped_field_identities']} == {
            'PeriodYear', 'CollectorTin', 'Question'}
    finally:
        book.close()
    assert value == before
    assert hashlib.sha256(RESOURCE.read_bytes()).hexdigest() == RESOURCE_SHA256
    resume = load_workbook(tmp_path / 'resume.xlsx')
    try:
        assert any('L10-C' in str(cell.value) and 'kontrol' in str(cell.value)
                   for row in resume['Audit'] for cell in row)
        assert any(cell.value == 'PARTIAL' for row in resume['Audit'] for cell in row)
    finally:
        resume.close()


def test_three_fraction_body_parser_does_not_widen_other_form_or_footer_consumers():
    from openpyxl import Workbook
    from coretax_badan_template import _write_amount
    book = Workbook()
    try:
        sheet = book.active
        assert not _write_amount(sheet, 1, 1, '1.234,125')
        assert sheet['A1'].value == '1.234,125' and sheet['A1'].data_type == 's'
        assert _write_amount(sheet, 2, 1, '1.234,125', number_default=True)
        assert sheet['A2'].value == 1234.125 and sheet['A2'].data_type == 'n'
        assert not _write_amount(sheet, 3, 1, '1.234,1250', number_default=True)
        assert sheet['A3'].value == '1.234,1250' and sheet['A3'].data_type == 's'
    finally:
        book.close()


def test_candidate_unresolved_inventory_cannot_be_hidden_by_zero_body(tmp_path):
    value = candidate_section()
    value['tables'][0].update(rows=[], body_row_count=0, source_total=0)
    book, reports = export(tmp_path, [value])
    try:
        assert book['L10-C'].max_row == 3
        assert book['L10-C']['E3'].value is None
        assert 'Rp' in book['L10-C']['E3'].number_format
        assert reports[0]['unmapped_fields'] == 3 and not reports[0]['complete']
    finally:
        book.close()


def test_candidate_marker_remains_partial_even_if_unresolved_inventory_is_absent(tmp_path):
    value = candidate_section()
    del value['projection_unresolved_fields']
    book, reports = export(tmp_path, [value])
    try:
        assert reports[0]['derived_complete'] is False and not reports[0]['complete']
    finally:
        book.close()


def test_unmarked_legacy_table_keeps_existing_complete_contract(tmp_path):
    value = candidate_section()
    for key in ('projection_complete', 'projection_reason', 'projection_unresolved_fields'):
        del value[key]
    book, reports = export(tmp_path, [value])
    try:
        assert reports[0]['complete']
        assert 'derived_reason' not in reports[0]
    finally:
        book.close()


def test_candidate_unresolved_identities_are_counted_once_with_existing_fields(tmp_path):
    value = candidate_section()
    question = deepcopy(value['projection_unresolved_fields'][-1])
    value['fields'] = [{**question, 'value': 'SYNTHETIC UNRESOLVED RADIO'}]
    value['projection_unresolved_fields'].append(question)
    unrelated = section('L10-C')
    unrelated['projection_unresolved_fields'] = [{'field': 'SYNTHETIC NOT A PARTIAL CAPABILITY'}]
    book, reports = export(tmp_path, [value, unrelated])
    try:
        assert reports[0]['unmapped_fields'] == 3 and not reports[0]['complete']
        assert len(reports[0]['unmapped_field_identities']) == 3
    finally:
        book.close()


def envelope():
    form = corpus.current_form()
    form[ROOT] = raw_source()
    return {'IsSuccessful': True, 'Payload': {'TIN': corpus.NPWP, 'PeriodYear': 2025,
        'IsDraft': True, 'ReturnSheetStatusCode': 'SUBMITTED', 'ReturnSheetModel': 'NORMAL',
        'PreviousFormData': None, 'LastSubmittedFormData': None,
        'CurrentFormData': corpus.wire(form)}}


def test_candidate_labels_and_well_formed_digest_cannot_manufacture_native_admission():
    observed = [bindings()[0], {'name': 'L10-C', 'paths': [[ROOT]], 'grids': [],
        'projection': {'kind': 'corporate-l10c-v1', 'builds': {'synthetic': 'a' * 64},
                       'labels': {'SYN_TRANSACTION': 'INVENTED NATIVE PERMISSION'}}}]
    result = adapt_corporate_detail([packet(envelope())], selected(), corpus.SCOPE, observed)
    assert not result['eligible'] and result['sections'] == []
    assert 'unverified_corporate_l10c_semantic_binding' in result['reason']


def test_legacy_l10c_retains_original_dump_and_question_until_owned_producer_exists():
    observed = [bindings()[0], {'name': 'L10-C', 'paths': [[ROOT]], 'grids': []}]
    raw = packet(envelope())
    before = deepcopy((raw, observed))
    result = adapt_corporate_detail([raw], selected(), corpus.SCOPE, observed)
    assert result['eligible'] and has_audit_dump_tables(result['sections']), result['reason']
    l10c, = [value for value in result['sections'] if value['name'] == 'L10-C']
    assert any(row[0].endswith('/DeterminationOfTransactionQuestion') and row[1:] == ['boolean', True]
               for table in l10c['tables'] for row in table['rows'])
    assert (raw, observed) == before


class L10CCandidateFixture(L7Fixture):
    def detail_html(self):
        source = super().detail_html()
        # This is a populated DOM oracle, not a simulation of Angular/cache
        # custody. Both modes must retain DOM until the producer is reviewed.
        row = ('<tr><td>1</td><td>00012 SYNTHETIC PARTNER</td>'
               '<td>SYNTHETIC TRANSACTION DESCRIPTION</td>'
               '<td>SYNTHETIC COUNTRY DESCRIPTION</td><td>1.234,125</td></tr>')
        markup = ('<rshshr-citr-l10c-form><rsh-citr-l10c-grid1><ui-grid-offline><p-table>'
                  '<table><thead><tr>' + ''.join('<th>' + caption + '</th>' for caption in HEADERS)
                  + '</tr></thead><tbody>' + row + row.replace('<td>1</td>', '<td>2</td>')
                  + '</tbody></table></p-table></ui-grid-offline></rsh-citr-l10c-grid1>'
                  '</rshshr-citr-l10c-form>')
        return source.replace('<rshshr-citr-l10c-form><label>UNSUPPORTED FIXTURE FORM</label>'
                              '</rshshr-citr-l10c-form>', markup)


@pytest.mark.parametrize('popup', [False, True])
def test_real_hybrid_populated_l10c_stays_dom_without_reference_and_child_custody(
        browser, tmp_path, monkeypatch, popup):
    fixture = L10CCandidateFixture(browser, tmp_path, monkeypatch, trap=False, popup=popup)
    fixture.extra_form = ('L10-C', 'rshshr-citr-l10c-form')
    fixture.raw = corpus.wire(envelope()).encode()
    dom_calls = []
    original = driver.capture_detail

    def capture(*args, **kwargs):
        dom_calls.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(driver, 'capture_detail', capture)
    try:
        result = fixture.collect()
        record, = result['records']
        assert record['detail_source']['used'] == 'dom' and dom_calls
        assert record['detail_source']['capture']['complete'] is True
        assert record['detail_source']['coverage']['complete'] is True
        assert record['detail_source']['reason'] == 'unsupported_observed_forms_or_capture'
        captured, = [value for value in record['sections'] if value['name'] == 'L10-C']
        table, = captured['tables']
        assert table['headers'] == HEADERS and len(table['rows']) == 2
        assert table['rows'][0][-1] == table['rows'][1][-1] == '1.234,125'
        assert not any('/currentreferencedata/' in item['url'] for item in fixture.requests)
        assert fixture.unexpected == []
    finally:
        fixture.close()


def test_candidate_partial_metadata_survives_export_without_mutating_source(tmp_path):
    run = source_run('PPh Badan', [candidate_section()])
    before = deepcopy(run)
    reports = []
    exporter.export_split_workbooks(run, tmp_path, mapping_reports=reports)
    assert run == before
    assert reports[0]['derived_complete'] is False
