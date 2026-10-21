"""Real delayed synthetic prefill; runner-only fixture readiness contracts."""
import pytest

from coretax_json import JsonSafetyError, ORIGIN
from masa_json_fixtures import SCOPE
from masa_observer_fixture import FRAME, Fixture
from support_masa_native import browser, observed


@pytest.mark.parametrize('tax,defect,status', [
    ('PPN', None, 200),
    ('PPN', 'unauthorized', 403),
    ('PPh Unifikasi', None, 200),
    ('PPh Unifikasi', 'unauthorized', 403),
], ids=['ppn-success', 'ppn-unauthorized', 'unifikasi-success', 'unifikasi-unauthorized'])
def test_observed_waits_for_delayed_prefill_status(browser, tmp_path, monkeypatch, tax, defect, status):
    original_document = Fixture.document
    primary = 'send(cfg.primary,{RecordId:cfg.record,OnManualClick:false})'

    def delayed_document(self):
        document = original_document(self)
        assert document.count(primary) == 1
        # Tunda request di browser: tidur di callback route akan memblokir
        # pemrosesan event Playwright dan menyamarkan kelemahan jeda 200 ms.
        delayed = 'new Promise(resolve=>setTimeout(resolve,750)).then(()=>'+primary+')'
        return document.replace(primary, delayed)

    monkeypatch.setattr(Fixture, 'document', delayed_document)
    endpoint = ORIGIN + '/returnsheet/api/prefillreturnsheet/' + (
        'nvat' if tax == 'PPN' else 'withholding-tax')
    with observed(browser, tmp_path, monkeypatch, tax, defect=defect) as (module, fixture, capture):
        initial = [event for event in capture.request_observations() if event['url'] == endpoint]
        assert len(initial) == 1, 'Fixture yielded before the initial prefill was observed'
        assert initial[0]['status'] == status, 'Fixture yielded before the prefill status was observed'
        assert initial[0]['method'] == 'POST'
        assert initial[0]['frame_url'] == FRAME
        assert initial[0]['request_json'] == {
            'RecordId': fixture.record['record_id'], 'OnManualClick': False,
        }
        if status == 403:
            with pytest.raises(JsonSafetyError, match='authorization was rejected'):
                module.observe_masa_forms(fixture.page, fixture.record, SCOPE, capture, max_pages=5)
        result = capture.drain()
        assert result['complete'] is (status == 200)
        assert result['counts']['accepted'] == (1 if status == 200 else 0)
        assert result['counts']['failed'] == (1 if status == 403 else 0)
        assert result['reasons'] == ([] if status == 200 else ['authorization-rejected'])
        assert fixture.page.evaluate('window.valueReads') == 0
        assert fixture.page.evaluate('window.forbiddenClicks') == 0
        assert not fixture.unexpected
