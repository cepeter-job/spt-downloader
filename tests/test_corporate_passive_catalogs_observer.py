"""Actual synthetic SPA -> passive producer -> held native replay -> workbook."""
from copy import deepcopy
import json

import pytest
from openpyxl import load_workbook

import coretax
import coretax_build_pins
import coretax_corporate as observer
import coretax_corporate_projection as projection
import coretax_json as adapter
from coretax_json_capture import DetailJsonCapture, checkpoint_bodies
from l3_observer_fixture import Fixture as L3Fixture, ASSET
from test_corporate_l3_observer import open_selected
from test_corporate_l3_native import REFERENCES, DETAIL
from test_corporate_passive_catalogs import BASE, KINDS as L10_KINDS, NEW_KINDS as L10_NEW_KINDS, catalog
from test_corporate_shared_dependency_catalogs import ADDITIONAL_KINDS
from test_json_hybrid_native import browser as browser
import support_json_corpus as corpus


KINDS = (*L10_KINDS, *ADDITIONAL_KINDS)
NEW_KINDS = (*L10_NEW_KINDS, *ADDITIONAL_KINDS)


class Fixture(L3Fixture):
    def __init__(self, browser, monkeypatch):
        super().__init__(browser, monkeypatch)
        self.reference_raw.update({BASE + kind: corpus.wire({
            'IsSuccessful': True, 'Payload': catalog(kind)}).encode() for kind in NEW_KINDS})
        monkeypatch.setattr(adapter, 'load_build_pins', lambda: dict(self.pins))
        monkeypatch.setattr(coretax_build_pins, 'load_build_pins', lambda: dict(self.pins))

    def document(self):
        # Only this synthetic application's natural initial request list changes.
        # The product/agent never calls a reference endpoint to obtain evidence.
        before = 'const refs=' + json.dumps(list(REFERENCES.values()))
        after = 'const refs=' + json.dumps([*REFERENCES.values(), *(BASE + kind for kind in NEW_KINDS)])
        return super().document().replace(before, after)


@pytest.mark.parametrize('defect', ['corporate-fetch-only', 'corporate-preload-only',
    'main-fetch-only', 'main-preload-only', 'vendor-fetch-only', 'vendor-preload-only'])
def test_fetch_or_preload_only_cannot_supply_the_new_loaded_provider_fact(
        browser, tmp_path, monkeypatch, defect):
    fixture = L3Fixture(browser, monkeypatch, defect=defect)
    monkeypatch.setattr(adapter, 'load_build_pins', lambda: dict(fixture.pins))
    monkeypatch.setattr(coretax_build_pins, 'load_build_pins', lambda: dict(fixture.pins))
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            open_selected(fixture, capture)
            assert capture.observe_corporate_reference_providers() is None
            saved = capture.drain()
            assert saved['complete'] and 'corporate_reference_providers' not in saved
            assert fixture.page.evaluate('window.businessReads') == 0
    finally:
        fixture.close()


def test_owned_passive_populated_catalogs_keep_native_held_replay_and_saved_descriptions(
        browser, tmp_path, monkeypatch):
    fixture = Fixture(browser, monkeypatch)
    calls = []
    original = getattr(projection, 'bind_corporate_reference_catalogs', None)
    assert callable(original), 'Source-only RED: shared producer binding not implemented'
    def bound(*args, **kwargs):
        calls.append(tuple(kwargs['kinds']))
        return original(*args, **kwargs)
    monkeypatch.setattr(projection, 'bind_corporate_reference_catalogs', bound)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            forms = observer.observe_forms(page, fixture.record, corpus.SCOPE, capture,
                                           approved_digest=fixture.pins[ASSET])
            assert forms is not None
            refs = observer.corporate_reference_bindings(capture, KINDS)
            assert refs is not None and refs['builds'] == fixture.pins
            saved = capture.drain()
            assert saved['complete'] and saved['corporate_reference_providers']['builds'] == fixture.pins
            raw = list(capture.iter_bodies())
            result = adapter.adapt_corporate_detail(raw, fixture.record, corpus.SCOPE, forms)
            assert result['eligible'] and result['coverage']['complete'], result['reason']
            # The existing populated L3 consumer exercises the stronger shared
            # binder when the optional provider fact exists, without changing
            # its legacy contract or inventing an A/C semantic capability.
            assert tuple(REFERENCES) in calls
            primary = next(e for e in result['provenance']['events'] if e['url'] == corpus.PRIMARY_URL)
            events = {e['sequence']: e for e in result['provenance']['events']}
            packets = {item['context']['sequence']: {
                'payload': adapter._corporate_json(item['body'])['Payload'],
                'event': events[item['context']['sequence']], 'successful': True}
                for item in raw if item['context']['url'] in adapter.CORPORATE_REFERENCE_REQUESTS}
            catalogs = original(refs['references'], packets, kinds=KINDS, event=primary, builds=refs['builds'])
            for kind in NEW_KINDS:
                assert catalogs[kind]['lookups'] == {'SYN_CODE': 'A SYNTHETIC FIRST'}
                assert catalogs[kind]['selected']['SYN_CODE']['path'] == [0, 'Details', 1, 'CodeDescription']
                assert next(item['body'] for item in raw if item['context']['url'] == BASE + kind) == fixture.reference_raw[BASE + kind]
            fixture.record['detail_url'] = DETAIL
            before = deepcopy((forms, result))
            replay = adapter.adapt_corporate_detail(checkpoint_bodies(tmp_path, saved, fixture.record, corpus.SCOPE),
                                                   fixture.record, corpus.SCOPE, forms)
            assert replay['eligible'] and replay['sections'] == result['sections']
            assert replay['provenance'] == result['provenance'] and (forms, result) == before
            assert page.evaluate('window.businessReads') == page.evaluate('window.forbiddenClicks') == 0
        fixture.record.update(capture_complete=True, sections=result['sections'])
        run = {'npwp': corpus.NPWP, 'year': 2025, 'year_basis': 'period', 'inventory_complete': True,
               'complete': True, 'errors': [], 'records': [fixture.record]}
        coretax.save_output(run, tmp_path / 'export')
        coretax.verify_outputs(run, tmp_path / 'export')
        name, = [name for name in run['output_files'] if name != 'resume.xlsx']
        book = load_workbook(tmp_path / 'export' / name)
        try:
            values = [cell.value for row in book['L3'] for cell in row]
            assert 'SYNTHETIC COUNTRY' in values and 'SYNTHETIC TAX' in values
        finally:
            book.close()
        assert not next(report for report in run['template_mapping'] if report['form'] == 'L3')['complete']
        assert fixture.unexpected == []
        for kind in NEW_KINDS:
            assert fixture.requests.count((BASE + kind, 'GET')) == 1
    finally:
        fixture.close()
