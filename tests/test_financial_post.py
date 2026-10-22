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


@pytest.mark.parametrize('header,value', [
    ('Authorization', ''),
    ('Request_From', 'https://unrelated.synthetic.invalid/'),
    ('Content-Type', 'text/plain'),
])
def test_final_interceptor_headers_are_validated_before_replay(post_routed, tmp_path, header, value):
    page, wire = post_routed()
    page.evaluate('''({header, value}) => {
        const original = XMLHttpRequest.prototype.setRequestHeader;
        XMLHttpRequest.prototype.setRequestHeader = function(name, content) {
            original.call(this, name, name === header ? value : content);
        };
    }''', {'header': header, 'value': value})

    assert_partial(attachments().download_financial_attachments(page, deepcopy(RECORD), tmp_path), tmp_path)

    assert page.evaluate('window.syntheticClicks') == 1
    assert wire == []


def test_download_route_query_is_not_an_approved_post(post_routed, tmp_path):
    page, wire = post_routed(endpoint=ENDPOINT + '?generate=true')

    assert_partial(attachments().download_financial_attachments(page, deepcopy(RECORD), tmp_path), tmp_path)

    assert page.evaluate('window.syntheticClicks') == 1
    assert wire == []


def test_replaced_inspected_button_is_rejected_before_click(post_routed, tmp_path, monkeypatch):
    module = attachments()
    page, wire = post_routed()
    evaluate = page.evaluate
    replaced = []

    def replace_after_scan(expression, *args, **kwargs):
        value = evaluate(expression, *args, **kwargs)
        if expression == module._SCAN and not replaced:
            replaced.append(True)
            evaluate('''() => {
                const button = document.querySelector('#financial-download');
                button.replaceWith(button.cloneNode(true));
            }''')
        return value

    monkeypatch.setattr(page, 'evaluate', replace_after_scan)
    assert_partial(module.download_financial_attachments(page, deepcopy(RECORD), tmp_path), tmp_path)
    assert page.evaluate('window.syntheticClicks') == 0 and wire == []


def test_unverified_reused_browser_context_never_clicks_or_posts(post_routed, tmp_path):
    page, wire = post_routed()
    del page.context._spt_financial_route_policy

    assert_partial(attachments().download_financial_attachments(page, deepcopy(RECORD), tmp_path), tmp_path)

    assert page.evaluate('window.syntheticClicks') == 0 and wire == []


def test_loaded_webpack_chunk_remains_verified_after_its_script_tag_is_removed(post_routed, tmp_path):
    page, wire = post_routed()
    page.evaluate('''() => document.querySelector('script[src]').remove()''')

    result = attachments().download_financial_attachments(page, deepcopy(RECORD), tmp_path)

    downloaded(result, tmp_path)
    assert page.evaluate('window.syntheticClicks') == 1 and len(wire) == 1


def test_changed_financial_row_after_stream_is_not_published(post_routed, tmp_path, monkeypatch):
    module = attachments()
    page, wire = post_routed()
    evaluate = page.evaluate
    changed = []

    def change_after_read(expression, *args, **kwargs):
        value = evaluate(expression, *args, **kwargs)
        if expression == module._READ and value.get('done') and not changed:
            changed.append(True)
            evaluate('''() => {
                document.querySelector('tbody tr td:nth-child(2)').innerText = 'other-statement.pdf';
            }''')
        return value

    monkeypatch.setattr(page, 'evaluate', change_after_read)
    assert_partial(module.download_financial_attachments(page, deepcopy(RECORD), tmp_path), tmp_path)
    assert changed == [True] and len(wire) == 1


def test_stop_cleans_the_scoped_route_and_browser_stream(post_routed, tmp_path):
    class StopRequested(BaseException):
        pass

    page, wire = post_routed()

    def stop_after_click():
        if page.evaluate('window.syntheticClicks'):
            raise StopRequested()

    with pytest.raises(StopRequested):
        attachments().download_financial_attachments(
            page, deepcopy(RECORD), tmp_path, check_cancel=stop_after_click)

    assert page.evaluate('''() => Object.keys(window).filter(key=>key.startsWith('_spt_financial_'))''') == []
    # This independent synthetic request reaches the context route only after
    # the adapter has removed its own temporary page route.
    page.evaluate('''async () => {
        try {await fetch('/synthetic-after-stop', {method:'POST',body:'{}'});} catch {}
    }''')
    assert len(wire) == 1 and wire[0]['url'] == ORIGIN + '/synthetic-after-stop'
    assert not list(tmp_path.rglob('*.pdf'))
