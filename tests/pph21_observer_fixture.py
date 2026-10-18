"""Synthetic routed Edge PPh21 fixture; never executes portal JavaScript."""
from contextlib import contextmanager
import html
import json

import pytest
from playwright.sync_api import sync_playwright

from coretax_json import ORIGIN
from coretax_json_capture import DetailJsonCapture
from masa_json_fixtures import FOREIGN, RECORD, SCOPE, TAXPAYER, selected
from support_pph21_dom import appendix_table, induk_tables

MAIN = ORIGIN + '/returnsheets/id-ID/main.cccfdb820c20596c.js'
ARTICLE = ORIGIN + '/returnsheets/id-ID/803.8681206e4827011e.js'
BUILD = b'/* synthetic observer build, not portal code */'
FRAME = ORIGIN + '/returnsheets/id-ID/article-21-26-tax-return/' + TAXPAYER + '/' + RECORD + '/ICT_WIT/00000000-0000-4000-8000-000000000002'
REFERENCE = ORIGIN + '/referencedata/api/currentreferencedata/id-ID/EBUPOT_TAX_CERTIFICATE,COUNTRY_CODE,EBUPOT_STATUS'
PRIMARY_URL = ORIGIN + '/returnsheet/api/prefillreturnsheet/article-2126'
GRID_API_URL = ORIGIN + '/returnsheet/api/loadarticle2126/'
FIRST, TOTAL = 10, 12
FORMS = {
    'Induk': ('rshshr-art2126-main-form', None, ()),
    'L-IA': ('rshshr-art2126-l1a-form', 'rshshr-art2126-l1a-grid', (('l1a', 'LIST-IA'),)),
    'L-IB': ('rshshr-art2126-l1b-form', 'rshshr-art2126-l1b-grid', (('l1b-bpa1', 'BPA1'), ('l1b-bpa2', 'BPA2'))),
    'L-II': ('rshshr-art2126-l2-form', 'rshshr-art2126-l2-grid', (('l2-bpa1', 'BPA1'), ('l2-bpa2', 'BPA2'))),
    'L-III': ('rshshr-art2126-l3-form', 'rshshr-art2126-l3-grid', (('l3-bp21', 'BP21'), ('l3-bp26', 'BP26'))),
}
GRIDS = [suffix for _, _, grids in FORMS.values() for suffix, _ in grids]
INDUK_CONTROLS = tuple(article + suffix for article in ('A21', 'A26') for suffix in (
    'IncomeTaxWithheld', 'CarryForward', 'PaymentWithSP2D', 'IncomeTaxUnderpaidOverpaid',
    'IncomeTaxPaidOnAmended', 'IncomeTaxUnderpaidOverpaidDueToAmendment', 'IncomeTaxBorneByGovernment'))


class Fixture:
    def __init__(self, browser, *, defect=None):
        self.defect = defect
        self.context = browser.new_context(locale='id-ID', timezone_id='Asia/Jakarta')
        self.page = self.context.new_page()
        self.record = selected('PPh Pasal 21/26')
        self.unexpected = []
        self.context.route('**/*', self.route)

    def route(self, route):
        request = route.request
        if request.url == self.record['list_url']:
            route.fulfill(content_type='text/html', body='<link rel="icon" href="data:,">')
        elif request.url == FRAME:
            route.fulfill(content_type='text/html', body=self.document())
        elif request.url in (MAIN, ARTICLE):
            route.fulfill(content_type='application/javascript', body=BUILD +
                          (b'/* changed */' if self.defect == 'changed-build' else b''))
        elif request.url == REFERENCE and request.method == 'GET':
            catalogs = [{'ReferenceDataType': t, 'language': 'id-ID', 'Details': []}
                        for t in ('EBUPOT_TAX_CERTIFICATE', 'COUNTRY_CODE', 'EBUPOT_STATUS')]
            route.fulfill(content_type='application/json', body=json.dumps({'IsSuccessful': True, 'Payload': catalogs}))
        elif request.method == 'POST' and (request.url == PRIMARY_URL or request.url in {
                GRID_API_URL + name + '-grid' for name in GRIDS}):
            status = {'unauthorized': 401, 'forbidden': 403}.get(self.defect, 200)
            route.fulfill(status=status, content_type='application/json',
                          body=json.dumps({'IsSuccessful': True, 'Payload': {'Data': [], 'TotalRecords': TOTAL}}))
        else:
            self.unexpected.append(request.url)
            route.abort()

    def table(self, suffix, form, group):
        config = html.escape(json.dumps({'endpoint': GRID_API_URL + suffix + '-grid', 'first': FIRST}), quote=True)
        headers = appendix_table(form, group, 0)[0]['headers']
        spans = {'l1a': [5, 3, 1, 1, 1, 5], 'l1b-bpa2': [5, 3, 1, 1, 5],
                 'l2-bpa2': [5, 5, 1, 1, 4], 'l3-bp21': [4, 4, 1, 1, 4], 'l3-bp26': [5, 7, 1, 1, 4]}.get(suffix)
        count = 1 if suffix == 'l2-bpa2' else 2 if suffix == 'l3-bp21' else 3
        footer = '' if spans is None else '<tfoot><tr></tr>' + ''.join(
            '<tr>' + ''.join('<td colspan="' + str(span) + '">DOM-TOTAL-TRAP</td>' for span in spans) + '</tr>'
            for _ in range(count)) + '</tfoot>'
        return ('<ui-grid><p-table data-config="' + config + '"><table><thead><tr>' +
                ''.join('<th>' + html.escape(h) + '</th>' for h in headers) + '</tr></thead>'
                '<tbody><tr><td>DOM-ROW-TRAP</td></tr></tbody>' + footer + '</table>'
                '<div class="p-paginator"><span class="p-paginator-current"></span>'
                '<button class="p-paginator-prev" onclick="turn(this,-10)">Previous</button>'
                '<button class="p-paginator-next" onclick="turn(this,10)">Next</button>'
                '</div></p-table></ui-grid>')

    def document(self):
        forms = [(name, *spec) for name, spec in FORMS.items()]
        if self.defect == 'missing-form':
            forms.pop()
        if self.defect == 'extra-form':
            forms.append(('UNREVIEWED', 'rshshr-unreviewed', None, ()))
        tabs, panels = [], []
        for index, (name, selector, container, grids) in enumerate(forms):
            tabs.append(f'<li><a role="tab" href="#" aria-controls="p{index}" onclick="show({index});return false">{name}</a></li>')
            if name == 'Induk':
                content, position = '', 0
                if self.defect in ('with-status', 'unknown-status-label', 'ambiguous-status'):
                    label = 'UNREVIEWED STATUS' if self.defect == 'unknown-status-label' else 'Status SPT'
                    control = ('<div class="form-group row"><label>' + label + '</label><div><ui-dropdown>'
                               '<p-dropdown><span class="p-dropdown-label">DOM-STATUS-TRAP</span>'
                               '</p-dropdown></ui-dropdown></div></div>')
                    content += ('<p-panel><div class="p-panel-header"><span class="p-panel-title">HEADER</span>'
                                '</div><div class="p-panel-content">' + control +
                                (control if self.defect == 'ambiguous-status' else '') + '</div></p-panel>')
                tables, _ = induk_tables()
                for table in tables:
                    content += '<h2>' + html.escape(table['group']) + '</h2><table><thead><tr>'
                    content += ''.join('<th>' + html.escape(header) + '</th>' for header in table['headers'])
                    content += '</tr></thead><tbody>'
                    for _ in table['rows']:
                        field = INDUK_CONTROLS[position]
                        position += 1
                        content += ('<tr><td>DOM-NO-TRAP</td><td>DOM-LABEL-TRAP</td><td>DOM-CODE-TRAP</td>'
                                    '<td><p-inputnumber formcontrolname="' + field + '"><input id="' + field +
                                    '" value="DOM-AMOUNT-TRAP" readonly></p-inputnumber></td></tr>')
                    content += '</tbody></table>'
                content += '<textarea hidden>DOM-BODY-TRAP</textarea><button onclick="forbidden()">Submit</button>'
            else:
                content = ''
                for suffix, group in grids:
                    label = 'UNKNOWN' if self.defect == 'invalid-group' and suffix == 'l1b-bpa2' else group
                    content += ('<p-panel><div class="p-panel-header"><span class="p-panel-title">' + label +
                                '</span></div><div class="p-panel-content">' + self.table(suffix, name, group) + '</div></p-panel>')
                if self.defect == 'extra-ui-grid' and name == 'L-IA':
                    content += self.table('l1a', name, 'LIST-IA')
                if container:
                    content = '<' + container + '>' + content + '</' + container + '>'
            content = '<' + selector + '>' + content + '</' + selector + '>'
            panels.append(f'<div data-main-panel class="p-tabview-panel" id="p{index}" style="display:{"block" if index == 0 else "none"}">{content}</div>')
        config = {'record': FOREIGN if self.defect == 'foreign-request' else RECORD, 'primary': PRIMARY_URL, 'defect': self.defect}
        return ('<html lang="id-ID"><head><link rel="icon" href="data:,"><style>ui-grid,p-table,p-panel{display:block}</style>'
                '<script src="' + MAIN + '"></script><script src="' + ARTICLE + '"></script></head><body>'
                '<div class="main-content"><div class="p-tabview"><ul class="p-tabview-nav">' + ''.join(tabs) +
                '</ul><div class="p-tabview-panels">' + ''.join(panels) + '</div></div></div>'
                '<script>const cfg=' + json.dumps(config) + ';' + SCRIPT + '</script></body></html>')


SCRIPT = r"""
window.forbiddenClicks=0;window.valueReads=0;
function forbidden(){window.forbiddenClicks++;}
function send(url,body){return fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});}
function load(g){const c=JSON.parse(g.dataset.config);
 g.querySelector('.p-paginator-current').textContent='Showing '+(c.first+1)+' to '+Math.min(c.first+10,12)+' of 12';
 g.querySelector('.p-paginator-prev').disabled=c.first===0;g.querySelector('.p-paginator-next').disabled=c.first+10>=12;
 if(cfg.defect==='missing-request')return;
 return send(c.endpoint,{ReturnSheetRecordId:cfg.record,First:c.first,Rows:10,Filters:[],SortField:'',SortOrder:1});}
function turn(button,delta){const g=button.closest('p-table'),c=JSON.parse(g.dataset.config);c.first+=delta;g.dataset.config=JSON.stringify(c);load(g);}
function show(i){document.querySelectorAll('[data-main-panel]').forEach((p,j)=>{
 p.style.display=i===j?'block':'none';if(i===j)p.querySelectorAll('p-table').forEach(g=>{if(!g.dataset.loaded){g.dataset.loaded='1';load(g);}});});}
window.primaryDone=false;send(cfg.primary,{RecordId:cfg.record,onManualClick:false}).finally(()=>window.primaryDone=true);
function valueTrap(){window.valueReads++;throw Error('DOM values forbidden');}
for(const property of ['value','checked'])Object.defineProperty(HTMLInputElement.prototype,property,{get:valueTrap});
Object.defineProperty(HTMLTextAreaElement.prototype,'value',{get:valueTrap});
const text=Object.getOwnPropertyDescriptor(Node.prototype,'textContent');
Object.defineProperty(Node.prototype,'textContent',{get(){const e=this.nodeType===1?this:this.parentElement;
 if(e&&e.closest('tbody,tfoot,ui-dropdown .p-dropdown-label'))return valueTrap();return text.get.call(this);},set:text.set});
const inner=Object.getOwnPropertyDescriptor(HTMLElement.prototype,'innerText');
Object.defineProperty(HTMLElement.prototype,'innerText',{get(){if(this.closest('tbody,tfoot,ui-dropdown .p-dropdown-label'))return valueTrap();return inner.get.call(this);},set:inner.set});
const attr=Element.prototype.getAttribute;Element.prototype.getAttribute=function(name){
 if(this.matches('input,textarea')&&['value','checked'].includes(name.toLowerCase()))return valueTrap();return attr.call(this,name);};
"""


@pytest.fixture(scope='module')
def browser():
    with sync_playwright() as playwright:
        instance = playwright.chromium.launch(channel='msedge', headless=True)
        yield instance
        instance.close()


@contextmanager
def observed(browser, tmp_path, *, defect=None):
    fixture = Fixture(browser, defect=defect)
    try:
        fixture.page.goto(fixture.record['list_url'])
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, SCOPE, tmp_path) as capture:
            fixture.page.goto(FRAME)
            capture.bind_detail_page(fixture.page)
            fixture.page.wait_for_function('window.primaryDone===true')
            yield fixture, capture
    finally:
        fixture.context.close()
