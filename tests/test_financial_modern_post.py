"""Synthetic modern tracer through the real FinancialPost and PDF declaration."""
from copy import deepcopy

import pytest

from support_financial_browser import browser as browser
from support_financial_browser import ORIGIN, RECORD, attachments, downloaded
from support_financial_modern import CURRENT_LABEL, modern_content
from support_financial_post import AUTHORIZATION, DOCUMENT, ENDPOINT, SCRIPT, TAXPAYER
from support_financial_post import post_routed as post_routed


def selected_return():
    selected = deepcopy(RECORD)
    selected['list_url'] = ORIGIN + '/returnsheets/id-ID/submitted-returnsheets/' + TAXPAYER
    detail = (ORIGIN + '/returnsheets/id-ID/corporate-income-tax-return/' + TAXPAYER + '/'
              + selected['record_id'] + '/ICT_RCIT/11111111-2222-4333-8444-555555555555?view=true')
    return selected, detail


def assert_partial(result, folder):
    assert result and all(item['status'] == 'PARTIAL' for item in result)
    assert all(not item['relative_path'] and not item['hash'] and item['bytes'] == 0 for item in result)
    assert not list(folder.rglob('*.pdf'))


@pytest.mark.parametrize('modern', [False, True], ids=['default-legacy', 'modern'])
def test_real_financial_post_aborts_original_and_declares_only_one_replayed_pdf(post_routed, tmp_path, modern):
    selected, detail = selected_return()
    options = {'content': modern_content()} if modern else {}
    page, wire = post_routed(detail_url=detail, **options)
    traffic, aborted = [], []
    page.on('request', lambda value: traffic.append(value.resource_type)
            if value.method == 'POST' and value.url == ENDPOINT else None)
    page.on('requestfailed', lambda value: aborted.append(value.resource_type)
            if value.method == 'POST' and value.url == ENDPOINT else None)
    page.evaluate('''() => {
        window.syntheticActionTrace = [];
        document.addEventListener('click', event => {
            const button = event.target.closest('button');
            if (button) window.syntheticActionTrace.push(button.id);
        }, true);
    }''')

    result = attachments().download_financial_attachments(page, selected, tmp_path)

    item, _ = downloaded(result, tmp_path)
    assert set(item) == {'label', 'relative_path', 'status', 'bytes', 'hash'}
    if modern:
        assert item['label'] == CURRENT_LABEL
    assert page.evaluate('window.syntheticClicks') == 1
    assert page.evaluate('window.syntheticActionTrace') == ['financial-download']
    # The genuine application XHR is aborted by FinancialPost's page route;
    # only its authenticated fetch replay may fall through to fixture backend.
    assert traffic == ['xhr', 'fetch']
    assert aborted == ['xhr']
    assert len(wire) == 1
    assert wire[0]['url'] == ENDPOINT
    assert wire[0]['body'] == {'DocumentId': DOCUMENT, 'TaxpayerAggregateIdentifier': TAXPAYER}
    assert wire[0]['headers']['authorization'] == AUTHORIZATION
    assert wire[0]['headers']['request_from'] == detail
    assert not any(name.startswith('x-spt') for name in wire[0]['headers'])
    assert page.evaluate('''() => Object.getOwnPropertyNames(window).filter(
        key => key.startsWith('_spt_financial_'))''') == []


@pytest.mark.parametrize('mutation', [
    "document.querySelector('#financial-download').replaceWith(document.querySelector('#financial-download').cloneNode(true))",
    "document.querySelector('#financial-grid').replaceWith(document.querySelector('#financial-grid').cloneNode(true))",
    "document.querySelector('#financial-table').tHead.rows[1].cells[0].append(document.querySelector('#financial-table input').parentElement)",
    "document.querySelector('#financial-table').tBodies[0].rows[0].cells[1].textContent = 'synthetic-changed.pdf'",
], ids=['cloned-button', 'cloned-grid', 'changed-filter-placement', 'changed-filename'])
def test_modern_financial_post_rechecks_original_snapshot_before_click(post_routed, tmp_path, monkeypatch, mutation):
    module = attachments()
    page, wire = post_routed(content=modern_content())
    page.evaluate('''() => {
        window.syntheticActionTrace = [];
        document.addEventListener('click', event => {
            const button = event.target.closest('button');
            if (button) window.syntheticActionTrace.push(button.id);
        }, true);
    }''')
    evaluate, changed = page.evaluate, []

    def change_after_scan(expression, *args, **kwargs):
        value = evaluate(expression, *args, **kwargs)
        # Dispatch by exact production-script identity, not a shared substring.
        if expression == module._SCAN and not changed:
            changed.append(True)
            evaluate('() => {' + mutation + '}')
        return value

    monkeypatch.setattr(page, 'evaluate', change_after_scan)
    result = module.download_financial_attachments(page, deepcopy(RECORD), tmp_path)

    assert_partial(result, tmp_path)
    assert changed == [True]
    assert page.evaluate('window.syntheticClicks') == 0 and wire == []
    assert page.evaluate('window.syntheticActionTrace') == []


def test_modern_immediate_preclick_scanner_rejects_change_after_last_python_check(post_routed, tmp_path, monkeypatch):
    module = attachments()
    page, wire = post_routed(content=modern_content())
    real_check, changed = module.FinancialPost.check, []

    def change_after_real_check(transport):
        real_check(transport)
        if transport.armed and transport.phase == 'capture' and transport.count == 0 and not changed:
            changed.append(True)
            page.evaluate('''() => document.querySelector('#financial-download').setAttribute('title', 'Generate')''')

    # Keep the real class/check/route/click machinery. This seam changes only
    # fixture DOM after the final armed check, before its atomic JS rescan.
    monkeypatch.setattr(module.FinancialPost, 'check', change_after_real_check)
    result = module.download_financial_attachments(page, deepcopy(RECORD), tmp_path)

    assert_partial(result, tmp_path)
    assert changed == [True]
    assert page.evaluate('window.syntheticClicks') == 0 and wire == []


def test_modern_shape_is_revalidated_after_complete_stream_before_declaration(post_routed, tmp_path, monkeypatch):
    module = attachments()
    page, wire = post_routed(content=modern_content())
    evaluate, changed = page.evaluate, []

    def change_after_stream(expression, *args, **kwargs):
        value = evaluate(expression, *args, **kwargs)
        if expression == module._READ and value.get('done') and not changed:
            changed.append(True)
            evaluate('''() => document.querySelector('#financial-table').tHead.rows[1].cells[1].colSpan = 2''')
        return value

    monkeypatch.setattr(page, 'evaluate', change_after_stream)
    result = module.download_financial_attachments(page, deepcopy(RECORD), tmp_path)

    assert_partial(result, tmp_path)
    assert changed == [True]
    assert page.evaluate('window.syntheticClicks') == 1 and len(wire) == 1


@pytest.mark.parametrize('options,clicks', [
    ({'script': SCRIPT + '\n// SYNTHETIC_UNAPPROVED_BUILD'}, 0),
    ({'payload': {'DocumentId': DOCUMENT, 'TaxpayerAggregateIdentifier': 'OTHER_SYNTHETIC_TAXPAYER'}}, 1),
    ({'count': 2}, 1),
])
def test_modern_discovery_does_not_bypass_source_identity_or_request_count(post_routed, tmp_path, options, clicks):
    page, wire = post_routed(content=modern_content(), **options)
    result = attachments().download_financial_attachments(page, deepcopy(RECORD), tmp_path)
    assert_partial(result, tmp_path)
    assert page.evaluate('window.syntheticClicks') == clicks
    assert wire == []
