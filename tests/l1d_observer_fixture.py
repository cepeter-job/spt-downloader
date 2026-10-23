"""Owned, synthetic SPA transport and structure for native L1-D tests."""
import hashlib
import html
import json

import coretax_corporate_projection as projection
from test_corporate_l1d_native import DETAIL, envelope
from test_corporate_l1d_projection import HEADERS
from test_corporate_l7_native import ASSET, BUILD, MAIN, MAIN_BUILD, selected
from test_corporate_l11c_native import VENDOR, VENDOR_BUILD
import support_json_corpus as corpus


class Fixture:
    def __init__(self, browser, monkeypatch, *, model='Normal', migrated=False, defect=None):
        self.record, self.defect = selected(model), defect
        self.context = browser.new_context(locale='id-ID', timezone_id='Asia/Jakarta', service_workers='block')
        if defect != 'external-context':
            self.context._spt_financial_route_policy = 'service_workers_blocked'
        self.assets = {ASSET: BUILD, MAIN: MAIN_BUILD, VENDOR: VENDOR_BUILD}
        self.pins = {url: hashlib.sha256(raw).hexdigest() for url, raw in self.assets.items()}
        monkeypatch.setattr(projection, 'L1D_BUILD_DIGESTS', self.pins, raising=False)
        value = envelope(model, migrated)
        if defect == 'non-services':
            value['Payload']['BusinessClassification'] = 'BC01'
        if defect == 'missing-5322':
            form = corpus.current_form()
            from test_corporate_l1d_projection import source
            form['L1dFormData'] = source()
            form['L1dFormData']['L1dTreeData'] = [n for n in form['L1dFormData']['L1dTreeData']
                                                 if n['Data']['AccountCode'] != '5322']
            value['Payload']['CurrentFormData'] = corpus.wire(form)
        self.raw = corpus.wire(value).encode()
        self.requests, self.unexpected = [], []
        self.context.route('**/*', self.route)
        self.page = self.context.new_page()
        self.page.goto(corpus.LIST_URL)

    def close(self):
        self.context.close()

    def route(self, route):
        request = route.request
        self.requests.append((request.url, request.method))
        if request.url == corpus.LIST_URL:
            return route.fulfill(content_type='text/html', body=self.document())
        if request.url in self.assets:
            raw = self.assets[request.url]
            if self.defect == 'vendor-pin' and request.url == VENDOR:
                raw += b'/* SYNTHETIC CHANGED */'
            return route.fulfill(content_type='application/javascript', body=raw)
        if request.url == corpus.PRIMARY_URL:
            assert request.method == 'POST'
            assert request.post_data_json == {'RecordId': corpus.RECORD_ID, 'OnManualClick': False}
            return route.fulfill(content_type='application/json', body=self.raw)
        self.unexpected.append((request.url, request.method))
        return route.abort()

    def detail(self):
        tables = []
        for index, headings in enumerate(HEADERS):
            owner = f'rsh-citr-l1d-grid{index + 1}'
            if self.defect == 'owner' and index == 1:
                owner = 'synthetic-foreign-owner'
            labels = list(headings)
            if self.defect == 'header' and index == 0:
                labels[0] = 'SYNTHETIC UNKNOWN HEADER'
            table = ('<p-table><table><thead><tr>' + ''.join('<th>' + html.escape(v) + '</th>' for v in labels)
                + '</tr></thead><tbody><tr>'
                + '<td>SYNTHETIC DOM BAIT<input value="SYNTHETIC DOM INPUT"></td>' * len(labels)
                + '</tr></tbody><tfoot><tr>' + '<td>SYNTHETIC DOM BAIT</td>' * len(labels)
                + '</tr></tfoot></table></p-table>')
            if index == 0:
                table = '<rshshr-citr-financial-statement-grid>' + table + '</rshshr-citr-financial-statement-grid>'
            tables.append('<' + owner + '>' + table + '</' + owner + '>')
        if self.defect == 'duplicate-owner':
            tables.append(tables[1])
        a, b = 'A. LAPORAN LABA RUGI', 'B. LAPORAN POSISI KEUANGAN'
        if self.defect == 'wrong-group':
            b = 'SYNTHETIC UNREVIEWED GROUP'
        first, second = tables[:1], tables[1:]
        if self.defect == 'misplaced-grid':
            first, second = tables[:2], tables[2:]
        accordions = ''.join('<p-accordiontab><div class="p-accordion-header">'
            '<a href="#" aria-expanded="true"><span class="p-accordion-header-text">'
            + caption + '</span></a></div><div class="p-accordion-content">' + ''.join(body)
            + '</div></p-accordiontab>' for caption, body in ((a, first), (b, second)))
        style = ' style="display:none"' if self.defect == 'hidden-owner' else ''
        l1d = ('<rshshr-citr-l1d-form' + style + '><h2>REKONSILIASI LAPORAN KEUANGAN - JASA</h2>'
               '<p-accordion>' + accordions + '</p-accordion></rshshr-citr-l1d-form>')
        tabs = ''.join('<li><a role="tab" aria-controls="panel-' + str(i) + '" href="#" onclick="show('
                       + str(i) + ');return false">' + name + '</a></li>' for i, name in enumerate(('Induk', 'L1-D')))
        return ('<rshshr-corporate-income-tax-return><div class="main-content"><div class="p-tabview">'
            '<ul class="p-tabview-nav">' + tabs + '</ul><div class="p-tabview-panels">'
            '<div class="p-tabview-panel" role="tabpanel" id="panel-0"><rshshr-citr-main-form>'
            '<label>SYNTHETIC STRUCTURAL PLACEHOLDER</label></rshshr-citr-main-form></div>'
            '<div class="p-tabview-panel" role="tabpanel" id="panel-1" style="display:none">' + l1d
            + '</div></div></div></div></rshshr-corporate-income-tax-return>')

    def document(self):
        assets = ''.join('<script src="' + url + '"></script>' for url in self.assets)
        return ('<html><head><link rel="icon" href="data:,"><style>'
            'rshshr-submitted-returnsheets,rshshr-corporate-income-tax-return,rshshr-citr-main-form,'
            'rshshr-citr-l1d-form,rsh-citr-l1d-grid1,rsh-citr-l1d-grid2,rsh-citr-l1d-grid3,'
            'rshshr-citr-financial-statement-grid,p-table,p-accordion,p-accordiontab{display:block}</style>' + assets + '</head><body>'
            '<rshshr-submitted-returnsheets><table><tbody><tr><td><button id="ViewButton" title="Lihat" '
            'onclick="if(event.isTrusted)openDetail()">View</button></td></tr></tbody></table></rshshr-submitted-returnsheets>'
            '<script>window.businessReads=0;window.forbiddenClicks=0;window.primaryDone=false;'
            'function show(i){document.querySelectorAll(".p-tabview-panel").forEach((p,j)=>p.style.display=i===j?"block":"none")}'
            'function openDetail(){history.pushState({},"",' + json.dumps(DETAIL) + ');'
            'document.querySelector("rshshr-submitted-returnsheets").remove();'
            'document.body.insertAdjacentHTML("beforeend",' + json.dumps(self.detail()) + ');'
            'fetch(' + json.dumps(corpus.PRIMARY_URL) + ',{method:"POST",headers:{"Content-Type":"application/json"},'
            'body:JSON.stringify({RecordId:' + json.dumps(corpus.RECORD_ID) + ',OnManualClick:false})})'
            '.then(r=>r.json()).then(()=>window.primaryDone=true);}'
            'document.addEventListener("click",e=>{if(e.target.closest("button")?.id!=="ViewButton"&&'
            '!e.target.closest("a[role=tab]"))window.forbiddenClicks++;});'
            'for(const [proto,key] of [[HTMLInputElement.prototype,"value"],[HTMLInputElement.prototype,"checked"],'
            '[HTMLElement.prototype,"innerText"],[Node.prototype,"textContent"]]){'
            'const d=Object.getOwnPropertyDescriptor(proto,key);Object.defineProperty(proto,key,{...d,get(){'
            'const owner=this.closest?.("rshshr-corporate-income-tax-return")||this.parentElement?.closest("rshshr-corporate-income-tax-return");'
            'if(owner&&(this.matches?.("input,tbody,tbody *,tfoot,tfoot *")||this.querySelector?.("tbody,tfoot")||'
            'this.parentElement?.closest("tbody,tfoot")))'
            '{window.businessReads++;throw Error("DOM business values forbidden");}return d.get.call(this);}});}'
            '</script></body></html>')
