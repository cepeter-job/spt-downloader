"""Strict Corporate JSON source: synthetic runs only; no live identifiers or network."""
from copy import deepcopy

import pytest

import coretax
import coretax_browser as driver
import support_json_corpus as corpus
from support_json_hybrid import DOM_SECTIONS, Scenario


def test_json_only_complete_uses_native_sections_without_dom(tmp_path, monkeypatch):
    case = Scenario(tmp_path, monkeypatch, mode='json-only')
    result = case.collect()
    assert result['complete'] is True
    assert result['errors'] == []
    assert case.dom_calls == []
    assert len(case.pdf_calls) == 1  # Existing financial-PDF custody is not a detail fallback.
    assert result['records'][0]['sections'] != DOM_SECTIONS
    assert result['records'][0]['detail_source']['requested'] == 'json-only'
    assert result['records'][0]['detail_source']['used'] == 'json'
    case.assert_closed()


def test_json_only_incomplete_is_partial_with_no_dom_fallback(tmp_path, monkeypatch):
    case = Scenario(tmp_path, monkeypatch, mode='json-only')
    case.forms = []  # No proven observed forms, even though JSON body was captured.
    result = case.collect()
    record = result['records'][0]
    assert result['complete'] is False
    assert record['capture_complete'] is False
    assert record['sections'] == [] and record['attachments'] == []
    assert len(result['errors']) == 1
    assert 'DOM fallback disabled' in result['errors'][0]['message']
    assert record['detail_source']['requested'] == 'json-only'
    assert record['detail_source']['used'] == 'none'
    assert record['detail_source']['capture']['manifest']
    assert case.dom_calls == [] and case.pdf_calls == []
    case.assert_closed()
    # Repeated run never restores the partial result as a COMPLETE checkpoint.
    case.page.mode = 'json-only'
    restored = driver.read_detail_checkpoint(tmp_path / 'returns' / '0001.json',
                                             case.record, corpus.SCOPE,
                                             detail_source='json-only')
    assert restored['capture_complete'] is False
    assert restored['sections'] == []

def test_json_only_missing_native_grid_pages_does_not_fallback(tmp_path, monkeypatch):
    case = Scenario(tmp_path, monkeypatch, mode='json-only')
    request = {'ReturnSheetRecordId': corpus.RECORD_ID, 'GroupType': 'Group 1',
               'First': 0, 'Rows': 10, 'SortField': '', 'SortOrder': 1,
               'Filters': {}, 'LanguageId': 'id-ID'}
    endpoint = corpus.ORIGIN + '/returnsheet/api/loadcit/l9-table-1-grid'
    case.forms[0]['grids'] = [{'name': 'SYNTHETIC L9 GROUP', 'endpoint': endpoint,
                               'pages': [{'request_json': request, 'offset': 0}]}]
    raw = corpus.wire({'IsSuccessful': True, 'Payload': {
        'Data': [corpus.source_row() for _ in range(10)],
        'TotalRecords': 60, 'Index': None}}).encode()
    case.page.exchanges.append({'url': endpoint, 'post': request, 'raw': raw})
    result = case.collect()
    assert result['complete'] is False
    assert len(result['errors']) == 1
    assert result['records'][0]['detail_source']['used'] == 'none'
    assert 'incomplete_corporate_grid_source' in result['records'][0]['detail_source']['reason']
    assert result['records'][0]['sections'] == []
    assert case.dom_calls == [] and case.pdf_calls == []
    case.assert_closed()


def test_json_only_rejects_incomplete_dom_and_cross_mode_checkpoints(tmp_path, monkeypatch):
    case = Scenario(tmp_path, monkeypatch, mode='json-first')
    case.forms = []
    result = case.collect()
    assert result['complete'] is True and case.dom_calls
    with pytest.raises(driver.JsonSafetyError):
        driver.read_detail_checkpoint(tmp_path / 'returns' / '0001.json',
                                      case.record, corpus.SCOPE,
                                      detail_source='json-only')
    case.assert_closed()


def test_json_only_identity_violation_never_uses_dom(tmp_path, monkeypatch):
    altered = corpus.current_form()
    altered['ReturnSheetRecordIdentifier'] = corpus.FOREIGN_ID
    case = Scenario(tmp_path, monkeypatch, mode='json-only',
                    raw=corpus.primary(altered)['body'])
    with pytest.raises(driver.JsonSafetyError):
        case.collect()
    assert case.dom_calls == [] and case.pdf_calls == []
    case.assert_closed()


def test_json_only_collector_rejects_non_corporate_before_side_effects(tmp_path):
    record = deepcopy(corpus.selected_record())
    record['meta']['Jenis Pajak'] = 'PPN'
    run = {'records': [record], 'npwp': corpus.NPWP, 'year': 2025,
           'year_basis': 'period'}
    class ForbiddenPage:
        def __getattribute__(self, _):
            raise AssertionError('Non-corporate mode reached browser')
    with pytest.raises(ValueError, match='PPh Badan only'):
        driver.collect_details(ForbiddenPage(), run, tmp_path / 'not-created',
                               detail_source='json-only')
    assert not (tmp_path / 'not-created').exists()


def test_json_only_cli_requires_explicit_corporate_scope(capsys):
    with pytest.raises(SystemExit, match='2'):
        coretax._main(['--npwp', corpus.NPWP, '--year', '2025',
                       '--detail-source', 'json-only', '--non-interactive'])
    assert 'requires --spt-badan-only' in capsys.readouterr().err
    assert coretax.parser().parse_args(['--detail-source', 'json-only',
                                        '--spt-badan-only']).detail_source == 'json-only'


def test_json_only_rejects_unaudited_dom_checkpoint(tmp_path, monkeypatch):
    case = Scenario(tmp_path, monkeypatch, mode='dom')
    case.collect()
    assert case.dom_calls
    with pytest.raises(driver.JsonSafetyError, match='Unaudited DOM checkpoint'):
        driver.read_detail_checkpoint(tmp_path / 'returns' / '0001.json',
                                      case.record, corpus.SCOPE,
                                      detail_source='json-only')
    case.assert_closed()


def test_desktop_controller_does_not_offer_cli_only_source(tmp_path, monkeypatch):
    from spt_desktop.controller import JobController
    from spt_desktop.app import save_preferences
    job = JobController(tmp_path, lambda _: None)
    monkeypatch.setattr(job, '_start_worker',
                        lambda *_: pytest.fail('CLI-only source launched desktop worker'))
    with pytest.raises(ValueError, match='Corporate CLI-only'):
        job.start(corpus.NPWP, '2025', detail_source='json-only')
    assert job.active is False
    with pytest.raises(ValueError, match='CLI SPT Badan'):
        save_preferences(tmp_path / 'no-write', {'detail_source':'json-only'})
    assert not (tmp_path / 'no-write').exists()

def test_json_only_partial_export_keeps_audited_json_and_exit_two(tmp_path):
    from test_json_output_folder import captured_run, assert_evidence
    source = tmp_path / 'job'
    run = captured_run(source, partial=True)
    record = run['records'][0]
    record['detail_source']['requested'] = 'json-only'
    record['detail_source']['used'] = 'none'
    record['sections'] = []
    record['attachments'] = []
    coretax.save_output(run, source)
    assert run['complete'] is False
    assert_evidence(run, source, source)
    rebuilt = tmp_path / 'rebuilt'
    assert coretax._main(['--from-json', str(source / 'run.json'),
                          '--output', str(rebuilt)]) == 2
    assert_evidence(run, source, rebuilt)
