"""Issue #187: source-owned JSON versus isolated DOM capture-boundary contracts.

The JSON route decodes real synthetic wire bytes. The DOM route uses the
existing Scenario's stubbed DOM capture boundary; it does not execute the
browser DOM parser. Both paths must preserve business facts and honest status
before separate workbook mapping/publication eligibility is considered.
"""
import json
from pathlib import Path

import pytest
from openpyxl import load_workbook

import coretax_exporter as exporter
import support_json_corpus as corpus
import support_json_hybrid as hybrid


@pytest.fixture
def contract():
    path = Path(__file__).parent / 'fixtures' / 'capture_semantic_pair_v1.json'
    document = json.loads(path.read_text(encoding='utf-8'))
    assert document['version'] == 1
    return document


def collect_synthetic(tmp_path, monkeypatch, contract, mode, *, financial_complete=True):
    folder = tmp_path / ('json' if mode == 'json-first' else 'dom')
    folder.mkdir()
    with monkeypatch.context() as patch:
        patch.setattr(hybrid, 'DOM_SECTIONS', contract['dom_sections'])
        case = hybrid.Scenario(folder, patch, mode=mode, financial_complete=financial_complete)
        result = case.collect()
        case.assert_closed()
    return result, case, folder


def test_same_business_identity_and_literal_values_cross_capture_modes(tmp_path, monkeypatch, contract):
    json_run, native, _ = collect_synthetic(tmp_path, monkeypatch, contract, 'json-first')
    dom_run, dom, _ = collect_synthetic(tmp_path, monkeypatch, contract, 'dom')

    assert native.dom_calls == [] and native.observation_calls == [corpus.RECORD_ID]
    assert len(dom.dom_calls) == 1 and dom.observation_calls == []
    assert json_run['complete'] is dom_run['complete'] is True
    for run in (json_run, dom_run):
        assert [run['npwp'], run['year'], run['year_basis']] == contract['scope']
        record, = run['records']
        assert record['record_id'] == contract['record_id']
        assert record['scope'] == contract['scope']
        assert record['meta'] == contract['meta']
        assert record['capture_complete'] is True
        assert [section['name'] for section in record['sections']] == ['Induk']

    native_record, = json_run['records']
    dom_record, = dom_run['records']
    assert native_record['detail_source']['used'] == 'json'

    wanted = {fact['json_path']: fact['literal'] for fact in contract['facts']}
    native_rows = [row for section in native_record['sections']
                   for table in section.get('tables', []) for row in table['rows']
                   if row[0] in wanted]
    assert {path: value for path, kind, value in native_rows} == wanted
    assert len(native_rows) == len(wanted)
    assert dict((field['field'], field['value'])
                for field in dom_record['sections'][0]['fields']) == {
                    fact['dom_field']: fact['literal'] for fact in contract['facts']}

    # Proofs can differ in source-specific capture details but not identity.
    json_proof = exporter.workbook_proof(json_run)
    dom_proof = exporter.workbook_proof(dom_run)
    for key in ('format', 'version', 'npwp', 'year', 'year_basis', 'complete'):
        assert json_proof[key] == dom_proof[key]
    for key in ('record_id', 'scope', 'source_status', 'meta', 'capture_complete', 'sections'):
        assert json_proof['records'][0][key] == dom_proof['records'][0][key]


@pytest.mark.parametrize('mode', ['json-first', 'dom'])
def test_capture_identity_survives_synthetic_xlsx_proof(tmp_path, monkeypatch, contract, mode):
    run, case, folder = collect_synthetic(tmp_path, monkeypatch, contract, mode)
    before = exporter.workbook_proof(run)
    files = exporter.export_split_workbooks(run, folder)
    filename, = set(files) - {'resume.xlsx'}
    workbook = load_workbook(files[filename])
    try:
        proof = exporter.read_workbook_proof(workbook)
        assert proof == before
        assert proof['records'][0]['record_id'] == contract['record_id']
        assert proof['records'][0]['scope'] == contract['scope']
        assert proof['complete'] is True
    finally:
        workbook.close()
    assert case.run == run


@pytest.mark.parametrize('mode', ['json-first', 'dom'])
def test_incomplete_financial_evidence_remains_partial_in_saved_proof(tmp_path, monkeypatch, contract, mode):
    run, _, folder = collect_synthetic(
        tmp_path, monkeypatch, contract, mode, financial_complete=False)

    assert run['complete'] is False
    record, = run['records']
    assert record['capture_complete'] is False
    assert record['attachments'][0]['status'] == 'PARTIAL'
    assert record['scope'] == contract['scope']
    files = exporter.export_split_workbooks(run, folder)
    filename, = set(files) - {'resume.xlsx'}
    workbook = load_workbook(files[filename])
    resume = load_workbook(files['resume.xlsx'])
    try:
        proof = exporter.read_workbook_proof(workbook)
        assert proof['complete'] is False
        assert proof['records'][0]['capture_complete'] is False
        assert proof['records'][0]['attachments'][0]['status'] == 'PARTIAL'
        assert resume['Ringkasan']['B6'].value == 'PARTIAL'
        assert resume['Daftar SPT']['I5'].value == 'PARTIAL'
    finally:
        workbook.close()
        resume.close()
