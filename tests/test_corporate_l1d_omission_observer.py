"""Owned 34-row omission proof, without reading DOM financial values; CI only."""
from copy import deepcopy

import pytest
from openpyxl import load_workbook

import coretax
import coretax_corporate as observer
from coretax_json import adapt_corporate_detail
from coretax_json_capture import DetailJsonCapture, checkpoint_bodies
from l1d_observer_fixture import Fixture, ASSET
from test_corporate_l1d_native import DETAIL
from test_corporate_l1d_observer import open_selected
from test_json_hybrid_native import browser as browser
import support_json_corpus as corpus

LAYOUT = 'absent-5322-34x10-v1'


@pytest.mark.parametrize('model', ['Normal', 'Amendment 002'])
@pytest.mark.parametrize('migrated', [False, True])
def test_owned_omitted_5322_reaches_native_held_replay_and_verified_workbook(
        browser, tmp_path, monkeypatch, model, migrated):
    fixture = Fixture(browser, monkeypatch, model=model, migrated=migrated,
                      classification_source='current', omitted_5322=True)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            forms = observer.observe_forms(page, fixture.record, corpus.SCOPE, capture,
                                           approved_digest=fixture.pins[ASSET])
            assert forms is not None
            assert forms[1]['projection'].get('body_layout') == LAYOUT
            assert forms[1]['projection']['visibility_binding'] == 'current-induk-enabled-v1'
            manifest = capture.drain()
            assert manifest['complete']
            bodies = list(capture.iter_bodies())
            assert len(bodies) == 1 and bodies[0]['body'] == fixture.raw
            before = deepcopy((bodies, forms, fixture.record))
            result = adapt_corporate_detail(bodies, fixture.record, corpus.SCOPE, forms)
            assert result['eligible'] and result['coverage']['complete'], result['reason']
            assert (bodies, forms, fixture.record) == before
            section, = [s for s in result['sections'] if s['name'] == 'L1-D']
            assert [t['body_row_count'] for t in section['tables']] == [34, 26, 29]
            assert all(row[0] != '5322' for row in section['tables'][0]['rows'])
            proof, = [p for p in result['provenance']['projections'] if p['form'] == 'L1-D']
            assert proof['body_layout'] == LAYOUT and proof['omitted_account_codes'] == ['5322']
            fixture.record['detail_url'] = DETAIL
            replay = adapt_corporate_detail(checkpoint_bodies(tmp_path, manifest, fixture.record, corpus.SCOPE),
                                            fixture.record, corpus.SCOPE, forms)
            assert replay['eligible'] and replay['coverage']['complete'], replay['reason']
            assert replay['sections'] == result['sections']
            assert replay['provenance'] == result['provenance']
            assert page.evaluate('window.businessReads') == 0
            assert page.evaluate('window.forbiddenClicks') == 0
        fixture.record.update(capture_complete=True, sections=result['sections'])
        run = {'npwp': corpus.NPWP, 'year': 2025, 'year_basis': 'period', 'inventory_complete': True,
               'complete': True, 'errors': [], 'records': [fixture.record]}
        coretax.save_output(run, tmp_path / 'export')
        coretax.verify_outputs(run, tmp_path / 'export')
        name, = [n for n in run['output_files'] if n != 'resume.xlsx']
        workbook = load_workbook(tmp_path / 'export' / name)
        try:
            sheet = workbook['L1-D']
            assert sheet.max_row == 97
            assert all(row[0] != '5322' for row in sheet.iter_rows(values_only=True))
            assert sheet['A36'].value == '4800' and sheet['J36'].value == (13 if migrated else 0)
            assert sheet['A97'].value == '3300'
        finally:
            workbook.close()
        report, = [r for r in run['template_mapping'] if r['form'] == 'L1-D']
        assert report['complete'] and report['unmapped_rows'] == report['unmapped_tables'] == 0
        assert fixture.unexpected == []
    finally:
        fixture.close()


@pytest.mark.parametrize('defect', ['short-body', 'long-body', 'short-row', 'long-row',
    'colspan', 'rowspan', 'hidden-row', 'extra-body', 'present-5322'])
def test_omission_requires_exact_owned_34_by_10_unspanned_layout(
        browser, tmp_path, monkeypatch, defect):
    fixture = Fixture(browser, monkeypatch, classification_source='current',
                      omitted_5322=True, body_layout_defect=defect)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            forms = observer.observe_forms(page, fixture.record, corpus.SCOPE, capture,
                                           approved_digest=fixture.pins[ASSET])
            assert capture.drain()['complete']
            result = adapt_corporate_detail(capture.iter_bodies(), fixture.record, corpus.SCOPE, forms or [])
            assert not result['eligible'] and not result['coverage']['complete'] and result['sections'] == []
            assert page.evaluate('window.businessReads') == 0
            assert page.evaluate('window.forbiddenClicks') == 0
            assert fixture.unexpected == []
    finally:
        fixture.close()


def test_omission_layout_change_during_observation_does_not_leave_a_stale_proof(
        browser, tmp_path, monkeypatch):
    fixture = Fixture(browser, monkeypatch, classification_source='current', omitted_5322=True)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            original = page.evaluate
            changed = False

            def evaluate(expression, *args, **kwargs):
                nonlocal changed
                if (not changed and 'timezone:Intl.DateTimeFormat()' in expression
                        and page.locator('rsh-citr-l1d-grid1 table').is_visible()):
                    original('document.querySelector("rsh-citr-l1d-grid1 table tbody tr").remove()')
                    changed = True
                return original(expression, *args, **kwargs)

            monkeypatch.setattr(page, 'evaluate', evaluate)
            forms = observer.observe_forms(page, fixture.record, corpus.SCOPE, capture,
                                           approved_digest=fixture.pins[ASSET])
            assert changed
            assert forms is None
            assert capture.drain()['complete']
            result = adapt_corporate_detail(capture.iter_bodies(), fixture.record, corpus.SCOPE, forms or [])
            assert not result['eligible'] and result['sections'] == []
            assert original('window.businessReads') == 0
    finally:
        fixture.close()
