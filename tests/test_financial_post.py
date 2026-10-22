"""The inspected financial POST is a bounded read, never a general POST permit."""
from copy import deepcopy

import pytest

from support_financial_browser import browser as browser
from support_financial_browser import DETAIL, ORIGIN, PDF, RECORD, attachments, downloaded
from support_financial_post import AUTHORIZATION, DOCUMENT, ENDPOINT, SCRIPT, TAXPAYER
from support_financial_post import post_routed as post_routed


def assert_partial(result, folder):
    assert result and all(item['status'] == 'PARTIAL' for item in result)
    assert all(not item.get('relative_path') for item in result)
    assert not list(folder.rglob('*.pdf'))


def test_inspected_financial_button_downloads_one_authenticated_post(post_routed, tmp_path):
    page, wire = post_routed()
    result = attachments().download_financial_attachments(page, deepcopy(RECORD), tmp_path)
    downloaded(result, tmp_path)
    assert page.evaluate('window.syntheticClicks') == 1
    assert len(wire) == 1
    assert wire[0]['url'] == ENDPOINT
    assert wire[0]['body'] == {'DocumentId': DOCUMENT, 'TaxpayerAggregateIdentifier': TAXPAYER}
    assert wire[0]['headers']['authorization'] == AUTHORIZATION
    assert wire[0]['headers']['request_from'] == DETAIL
    assert not any(name.startswith('x-spt') for name in wire[0]['headers'])


@pytest.mark.parametrize('options', [
    {'label': 'Unrelated supporting documents'},
    {'component': 'unrelated-return-form'},
    {'script': SCRIPT + '\n// different served build'},
])
def test_unapproved_owner_or_source_never_clicks_or_posts(post_routed, tmp_path, options):
    page, wire = post_routed(**options)
    assert_partial(attachments().download_financial_attachments(page, deepcopy(RECORD), tmp_path), tmp_path)
    assert page.evaluate('window.syntheticClicks') == 0
    assert wire == []


@pytest.mark.parametrize('payload', [
    {'DocumentId': DOCUMENT, 'TaxpayerAggregateIdentifier': 'OTHER_SYNTHETIC_TAXPAYER'},
    {'DocumentId': '', 'TaxpayerAggregateIdentifier': TAXPAYER},
    {'DocumentId': DOCUMENT, 'TaxpayerAggregateIdentifier': TAXPAYER, 'Generate': True},
])
def test_wrong_final_body_never_reaches_the_backend(post_routed, tmp_path, payload):
    page, wire = post_routed(payload=payload)
    assert_partial(attachments().download_financial_attachments(page, deepcopy(RECORD), tmp_path), tmp_path)
    assert wire == []


@pytest.mark.parametrize('options', [
    {'endpoint': ORIGIN + '/documentmanagement/api/generate'},
    {'count': 2},
    {'change_scope': DETAIL.replace('SYNTHETIC_BADAN_RETURN', 'OTHER_SYNTHETIC_RETURN')},
])
def test_changed_or_multiple_requests_never_replay(post_routed, tmp_path, options):
    page, wire = post_routed(**options)
    assert_partial(attachments().download_financial_attachments(page, deepcopy(RECORD), tmp_path), tmp_path)
    assert wire == []


@pytest.mark.parametrize('options', [
    {'status': 302, 'headers': {'Location': ORIGIN + '/unrelated.pdf'}},
    {'content_type': 'text/html'},
    {'body': b'%PDF-1.4\nSYNTHETIC TRUNCATED'},
])
def test_unverified_post_response_is_not_published(post_routed, tmp_path, options):
    page, wire = post_routed(**options)
    assert_partial(attachments().download_financial_attachments(page, deepcopy(RECORD), tmp_path), tmp_path)
    assert len(wire) == 1 and wire[0]['url'] == ENDPOINT


def test_post_pdf_limit_rejects_oversized_bytes(post_routed, tmp_path, monkeypatch):
    module = attachments()
    monkeypatch.setattr(module, 'MAX_PDF_BYTES', len(PDF) - 1)
    page, wire = post_routed()
    assert_partial(module.download_financial_attachments(page, deepcopy(RECORD), tmp_path), tmp_path)
    assert len(wire) == 1


def test_stop_after_button_capture_prevents_post_replay(post_routed, tmp_path):
    class StopRequested(BaseException):
        pass

    page, wire = post_routed()

    def stop_after_click():
        if page.evaluate('window.syntheticClicks'):
            raise StopRequested()

    with pytest.raises(StopRequested):
        attachments().download_financial_attachments(
            page, deepcopy(RECORD), tmp_path, check_cancel=stop_after_click)
    assert wire == []
    assert not list(tmp_path.rglob('*.pdf'))
