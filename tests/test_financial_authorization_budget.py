"""Large invented interceptor credentials retain one read-only scoped replay."""
from copy import deepcopy
import json

import pytest

from spt_desktop import diagnostics
from support_financial_browser import browser as browser, attachments, downloaded
from support_financial_post import post_routed as post_routed
from test_diagnostics import records
from test_financial_actual_route import DETAIL, record


MARKER = 'SYNTHETIC_LARGE_AUTH_'


def authorization(length):
    return ('Bearer ' + MARKER + 'A' * length)[:length]


def final_authorization(page, value):
    page.evaluate('''value => {
        const original = XMLHttpRequest.prototype.setRequestHeader;
        XMLHttpRequest.prototype.setRequestHeader = function(name, content) {
            if (name === 'Authorization') {
                if (value !== null) original.call(this, name, value);
            } else original.call(this, name, content);
        };
    }''', value)


@pytest.mark.parametrize('length', [8192, 8193, 16384, 32768, 65536])
def test_large_captured_authorization_replays_identically_once_without_logging(post_routed, tmp_path, length):
    page, wire = post_routed(detail_url=DETAIL + '?view=true')
    value = authorization(length)
    final_authorization(page, value)
    selected = record()
    before = deepcopy(selected)
    with diagnostics.session(tmp_path / 'diagnostics', 'worker') as log:
        result = attachments().download_financial_attachments(page, selected, tmp_path)
        assert log.flush()
    downloaded(result, tmp_path)
    assert selected == before and page.evaluate('window.syntheticClicks') == 1
    assert len(wire) == 1 and wire[0]['headers']['authorization'] == value
    assert wire[0]['headers']['request_from'] == DETAIL + '?view=true'
    assert not any(key.startswith('x-spt') for key in wire[0]['headers'])
    events = records(tmp_path / 'diagnostics')
    assert not any(row['event'] == 'pdf.request_rejected' for row in events)
    captured = [row for row in events if row['event'] == 'pdf.request_captured']
    assert len(captured) == 1
    assert captured[0]['authorization_budget'] == ('within_8k' if length <= 8192 else 'above_8k')
    assert MARKER not in json.dumps(events)
    assert page.evaluate("() => Object.keys(window).filter(key=>key.startsWith('_spt_financial_'))") == []


@pytest.mark.parametrize('value', [None, '', 'Bearer ' + MARKER + 'A\tB',
                                  authorization(65537), authorization(131072)],
                         ids=['missing', 'empty', 'unsafe-control', 'above-budget', 'far-above-budget'])
def test_missing_or_over_budget_authorization_never_reaches_backend(post_routed, tmp_path, value):
    page, wire = post_routed(detail_url=DETAIL + '?view=true')
    final_authorization(page, value)
    selected = record()
    before = deepcopy(selected)
    with diagnostics.session(tmp_path / 'diagnostics', 'worker') as log:
        result = attachments().download_financial_attachments(page, selected, tmp_path)
        assert log.flush()
    assert result and all(item['status'] == 'PARTIAL' and item['bytes'] == 0 for item in result)
    assert selected == before and wire == [] and not list(tmp_path.rglob('*.pdf'))
    rejected = [row for row in records(tmp_path / 'diagnostics') if row['event'] == 'pdf.request_rejected']
    assert len(rejected) == 1 and rejected[0]['pdf_guard'] == 'authentication'
    assert MARKER not in json.dumps(records(tmp_path / 'diagnostics'))
    assert not any(row['event'] == 'pdf.request_captured' for row in records(tmp_path / 'diagnostics'))
    assert page.evaluate("() => Object.keys(window).filter(key=>key.startsWith('_spt_financial_'))") == []


def test_authorization_budget_diagnostics_accept_only_fixed_categories(tmp_path):
    class Untrusted:
        def __str__(self):
            raise AssertionError('Never stringify credentials or diagnostic inputs')
    values = ['within_8k', 'above_8k', Untrusted(), MARKER, None, 8193, True]
    with diagnostics.session(tmp_path / 'diagnostics', 'worker') as log:
        for value in values:
            diagnostics.record('pdf.request_captured', authorization_budget=value,
                               authorization=MARKER, headers=MARKER, body=MARKER)
        assert log.flush()
    events = [row for row in records(tmp_path / 'diagnostics') if row['event'] == 'pdf.request_captured']
    assert len(events) == len(values)
    assert [row.get('authorization_budget') for row in events[:2]] == values[:2]
    assert all('authorization_budget' not in row for row in events[2:])
    assert all(not {'authorization','headers','body'} & row.keys() for row in events)
    assert MARKER not in json.dumps(events)
