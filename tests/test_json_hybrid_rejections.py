"""Review regressions: synthetic input, runner-only, never a live login."""
import json
import pytest
import coretax_json as native
import test_json_adapter as corpus
from test_json_hybrid import Scenario, collector


@pytest.mark.parametrize('status', [401, 403])
def test_html_authorization_rejection_cannot_become_dom_fallback(tmp_path, monkeypatch, status):
    collector()
    case = Scenario(tmp_path, monkeypatch, raw=b'<html>SYNTHETIC access rejected</html>', status=status)
    case.page.exchanges[0]['content_type'] = 'text/html'
    with pytest.raises(native.JsonSafetyError):
        case.collect()
    assert case.dom_calls == [] and case.pdf_calls == []
    assert not case.run['complete'] and not case.record.get('capture_complete')
    assert case.record.get('sections', []) == []
    assert all(response.reads == 0 for response in case.page.body_responses)
    case.assert_closed()


def test_unknown_binding_and_missing_form_never_hide_outer_taxpayer_clash(tmp_path, monkeypatch):
    collector()
    envelope = json.loads(corpus.primary()['body'])
    envelope['Payload'].pop('CurrentFormData')
    envelope['Payload']['TIN'] = '0000000000000099'
    case = Scenario(tmp_path, monkeypatch, raw=corpus.wire(envelope).encode())
    case.forms = None
    with pytest.raises(native.JsonSafetyError):
        case.collect()
    assert case.dom_calls == [] and case.pdf_calls == []
    assert not case.run['complete'] and not case.record.get('capture_complete')
    assert case.record.get('sections', []) == []
    case.assert_closed()
