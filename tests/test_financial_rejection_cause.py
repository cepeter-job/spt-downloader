"""Keep the first safe callback failure; never leak the synthetic secret envelope."""
from copy import deepcopy
import json

import pytest

from spt_desktop import diagnostics
from support_financial_browser import browser as browser, attachments, downloaded
from support_financial_post import post_routed as post_routed
from support_financial_post import AUTHORIZATION, DOCUMENT, ENDPOINT, TAXPAYER
from test_diagnostics import records
from test_financial_actual_route import DETAIL, CONTEXT, record


@pytest.mark.parametrize('case,stage', [
    ('wrong-taxpayer', 'body'), ('extra-body-key', 'body'), ('oversized-body', 'body'),
    ('authorization', 'authentication'), ('request-from', 'authentication'),
    ('content-type', 'authentication'), ('route', 'route'), ('duplicate', 'count'),
    ('scope', 'context'), ('row-changed', 'context'),
])
def test_first_financial_callback_rejection_keeps_safe_stage_and_origin(post_routed, tmp_path, case, stage):
    options = {'detail_url': DETAIL + '?view=true'}
    if case == 'wrong-taxpayer':
        options['payload'] = {'DocumentId': DOCUMENT, 'TaxpayerAggregateIdentifier': 'OTHER_SYNTHETIC_TAXPAYER'}
    elif case == 'extra-body-key':
        options['payload'] = {'DocumentId': DOCUMENT, 'TaxpayerAggregateIdentifier': TAXPAYER, 'Generate': True}
    elif case == 'oversized-body':
        options['payload'] = {'DocumentId': 'SYNTHETIC_PRIVATE_' * 400, 'TaxpayerAggregateIdentifier': TAXPAYER}
    elif case == 'route':
        options['endpoint'] = ENDPOINT + '?generate=true'
    elif case == 'duplicate':
        options['count'] = 2
    elif case == 'scope':
        options['change_scope'] = DETAIL.replace(CONTEXT, '66666666-7777-4888-8999-000000000000') + '?view=true'
    page, wire = post_routed(**options)
    if case in ('authorization', 'request-from', 'content-type'):
        header, value = {'authorization': ('Authorization', ''),
                         'request-from': ('Request_From', 'https://private.synthetic.invalid/'),
                         'content-type': ('Content-Type', 'text/plain')}[case]
        page.evaluate('''({header, value}) => {
            const original = XMLHttpRequest.prototype.setRequestHeader;
            XMLHttpRequest.prototype.setRequestHeader = function(name, content) {
                original.call(this, name, name === header ? value : content);
            };
        }''', {'header': header, 'value': value})
    elif case == 'row-changed':
        page.evaluate('''() => {
            const original = XMLHttpRequest.prototype.send;
            XMLHttpRequest.prototype.send = function(body) {
                document.querySelector('tbody td:nth-child(2)').textContent = 'SYNTHETIC_CHANGED_PRIVATE.pdf';
                original.call(this, body);
            };
        }''')
    selected = record()
    before = deepcopy(selected)
    with diagnostics.session(tmp_path / 'diagnostics', 'worker') as log:
        result = attachments().download_financial_attachments(page, selected, tmp_path)
        assert log.flush()
    events = records(tmp_path / 'diagnostics')
    rejected = [row for row in events if row['event'] == 'pdf.request_rejected']
    assert len(rejected) == 1 and rejected[0]['pdf_guard'] == stage
    assert any(frame['file'] == 'coretax_financial_post.py' and
               frame['function'] in ('_route', '_capture', 'check')
               for frame in rejected[0]['error']['frames'])
    text = json.dumps(events)
    for private in (DETAIL, TAXPAYER, DOCUMENT, AUTHORIZATION, 'SYNTHETIC_PRIVATE_',
                    'OTHER_SYNTHETIC_TAXPAYER', 'private.synthetic.invalid',
                    'SYNTHETIC_CHANGED_PRIVATE.pdf', '?generate=true'):
        assert private not in text
    assert all(item['status'] == 'PARTIAL' and item['bytes'] == 0 for item in result)
    assert selected == before and wire == [] and not list(tmp_path.rglob('*.pdf'))


def test_successful_financial_post_emits_no_rejection_and_replays_once(post_routed, tmp_path):
    page, wire = post_routed(detail_url=DETAIL + '?view=true')
    with diagnostics.session(tmp_path / 'diagnostics', 'worker') as log:
        result = attachments().download_financial_attachments(page, record(), tmp_path)
        assert log.flush()
    downloaded(result, tmp_path)
    assert len(wire) == 1 and not any(row['event'] == 'pdf.request_rejected' for row in records(tmp_path / 'diagnostics'))


def test_financial_rejection_schema_keeps_only_fixed_stage_and_safe_frames(tmp_path):
    class Untrusted:
        def __str__(self):
            raise AssertionError('Never stringify diagnostic objects')
    with diagnostics.session(tmp_path, 'worker') as log:
        for value in ('context', 'route', 'count', 'body', 'authentication', 'replay',
                      'SYNTHETIC_PRIVATE_STAGE', Untrusted(), None, 123, True):
            diagnostics.record('pdf.request_rejected', pdf_guard=value, url=AUTHORIZATION,
                               body=DOCUMENT, headers=TAXPAYER, message=AUTHORIZATION)
        assert log.flush()
    events = [row for row in records(tmp_path) if row['event'] == 'pdf.request_rejected']
    assert len(events) == 11
    assert [row.get('pdf_guard') for row in events[:6]] == ['context', 'route', 'count', 'body', 'authentication', 'replay']
    assert all('pdf_guard' not in row for row in events[6:])
    assert all(not {'url','body','headers','message'} & row.keys() for row in events)
    assert not any(secret in json.dumps(events) for secret in (AUTHORIZATION, DOCUMENT, TAXPAYER, 'SYNTHETIC_PRIVATE_STAGE'))
