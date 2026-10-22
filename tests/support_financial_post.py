"""Synthetic authenticated financial-button transport; no portal access."""
import hashlib
import json

import pytest

import coretax_browser as source_browser
from support_financial_browser import DETAIL, LABEL, ORIGIN, PDF, attachments


ENDPOINT = ORIGIN + '/documentmanagement/api/download'
TAXPAYER = 'SYNTHETIC_TAXPAYER'
DOCUMENT = 'SYNTHETIC_FINANCIAL_DOCUMENT'
AUTHORIZATION = 'Bearer SYNTHETIC_NOT_A_REAL_TOKEN'
SCRIPT_PATH = '/returnsheets/id-ID/synthetic-financial.js'
SCRIPT = r'''
document.querySelector('#financial-download').addEventListener('click', () => {
    window.syntheticClicks += 1;
    const options = window.syntheticOptions;
    if (options.changeScope) history.replaceState({}, '', options.changeScope);
    for (let n = 0; n < options.count; n++) {
        const request = new XMLHttpRequest();
        request.open('POST', options.endpoint);
        request.setRequestHeader('Content-Type', 'application/json');
        request.setRequestHeader('Authorization', 'Bearer SYNTHETIC_NOT_A_REAL_TOKEN');
        request.setRequestHeader('Request_From', window.location.toString());
        request.responseType = 'blob';
        request.send(JSON.stringify(options.payload));
    }
});
'''


@pytest.fixture
def post_routed(browser, monkeypatch):
    monkeypatch.setattr(source_browser, 'ORIGIN', ORIGIN)
    module = attachments()
    monkeypatch.setattr(module, 'POST_SOURCE_PINS', {
        SCRIPT_PATH: hashlib.sha256(SCRIPT.encode()).hexdigest(),
    }, raising=False)
    contexts = []

    def create(*, payload=None, endpoint=ENDPOINT, label=LABEL,
               component='rshshr-citr-main-form', body=PDF,
               content_type='application/pdf', status=200, headers=None,
               count=1, change_scope=None, script=SCRIPT):
        context = browser.new_context(service_workers='block')
        context._spt_financial_route_policy = 'service_workers_blocked'
        contexts.append(context)
        wire = []
        options = {
            'payload': payload if payload is not None else {
                'DocumentId': DOCUMENT, 'TaxpayerAggregateIdentifier': TAXPAYER},
            'endpoint': endpoint, 'count': count, 'changeScope': change_scope,
        }
        html = ('<main class="main-content"><h1>Induk</h1><' + component + '>'
                '<section><label id="financial-label">' + label + '</label>'
                '<ui-grid-documents><table aria-labelledby="financial-label">'
                '<thead><tr><th>NO.</th><th>FILENAME</th><th>TINDAKAN</th></tr></thead>'
                '<tbody><tr><td>1</td><td>synthetic-statement.pdf</td><td>'
                '<button id="financial-download" type="button" title="Unduh" '
                'class="p-button-secondary"><span class="pi pi-download"></span></button>'
                '</td></tr></tbody></table></ui-grid-documents></section></' + component + '></main>'
                '<script>window.syntheticClicks=0;window.syntheticOptions=' + json.dumps(options) + ';</script>'
                '<script src="' + SCRIPT_PATH + '"></script>')

        def route(intercept):
            request = intercept.request
            if request.method == 'POST':
                wire.append({'url': request.url, 'body': request.post_data_json,
                             'headers': request.all_headers()})
                if request.url == ENDPOINT:
                    intercept.fulfill(body=body, content_type=content_type,
                                      status=status, headers=headers or {})
                else:
                    intercept.abort('blockedbyclient')
            elif request.url == DETAIL:
                intercept.fulfill(body=html, content_type='text/html')
            elif request.url == ORIGIN + SCRIPT_PATH:
                intercept.fulfill(body=script, content_type='application/javascript')
            else:
                intercept.abort('blockedbyclient')

        context.route('**/*', route)
        page = context.new_page()
        page.goto(DETAIL, wait_until='load')
        return page, wire

    yield create
    for context in contexts:
        context.close()
