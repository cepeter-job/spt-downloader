"""Owned synthetic L3 SPA, transport and read traps; no portal source or values."""
import html
import json

import coretax_corporate_projection as projection
from l1d_observer_fixture import Fixture as BaseFixture, ASSET as ASSET
from test_corporate_l3_native import GRID, FOOTER, REFERENCES, OWNERS, GROUPS, packets, request
from test_corporate_l3_projection import HEADERS, SPANS
import support_json_corpus as corpus


class Fixture(BaseFixture):
    def __init__(self, browser, monkeypatch, *, model='Normal', defect=None, footer_order='early'):
        self.footer_order = footer_order
        if defect in ('timezone', 'locale'):
            new_context = browser.new_context
            key, value = ('timezone_id', 'UTC') if defect == 'timezone' else ('locale', 'en-US')
            monkeypatch.setattr(browser, 'new_context', lambda **options: new_context(**{**options, key: value}))
        raw = packets(model)
        self.footer_raw = raw[1]['body']
        self.grid_raw = {0: raw[2]['body'], 10: raw[3]['body']}
        self.reference_raw = {url: raw[index + 4]['body'] for index, url in enumerate(REFERENCES.values())}
        self.footer_count = 0
        super().__init__(browser, monkeypatch, model=model, defect=defect)
        self.raw = raw[0]['body']
        monkeypatch.setattr(projection, 'L3_BUILD_DIGESTS', self.pins, raising=False)

    def route(self, route):
        req = route.request
        if req.url == FOOTER:
            self.requests.append((req.url, req.method))
            assert req.method == 'POST' and req.post_data_json == {'ReturnSheetRecordId': corpus.RECORD_ID}
            self.footer_count += 1
            raw = self.footer_raw
            if self.defect == 'failed-footer':
                return route.fulfill(status=500, content_type='application/json',
                    body=corpus.wire({'IsSuccessful': False, 'Payload': None}))
            if self.defect == 'conflicting-footer' and self.footer_count > 1:
                value = json.loads(raw)
                value['Payload']['IncomeTax'] = 41
                raw = corpus.wire(value).encode()
            return route.fulfill(content_type='application/json', body=raw)
        if req.url == GRID:
            self.requests.append((req.url, req.method))
            assert req.method == 'POST' and req.post_data_json in (request(0), request(10))
            return route.fulfill(content_type='application/json', body=self.grid_raw[req.post_data_json['First']])
        if req.url in self.reference_raw:
            self.requests.append((req.url, req.method))
            assert req.method == 'GET' and req.post_data is None
            return route.fulfill(content_type='application/json', body=self.reference_raw[req.url])
        return super().route(route)

    def detail(self):
        first_headers = ('<tr><th rowspan="2">NO.</th><th colspan="2">PEMOTONG PAJAK</th>'
            '<th rowspan="2">TANGGAL TRANSAKSI/PEMBAYARAN PPh</th><th rowspan="2">JENIS PENGHASILAN</th>'
            '<th rowspan="2">PENGHASILAN NETO (RUPIAH)</th>'
            '<th colspan="3">PPh YANG DIBAYAR/DIPOTONG/TERUTANG DI LUAR NEGERI</th>'
            '<th rowspan="2">JUMLAH KREDIT PAJAK YANG DAPAT DIPERHITUNGKAN (Rp)</th></tr>'
            '<tr><th>NAMA</th><th>NEGARA</th><th>NILAI (Rp)</th><th>MATA UANG</th>'
            '<th>NILAI DALAM MATA UANG ASING</th></tr>')
        if self.defect == 'header':
            first_headers = first_headers.replace('NILAI (Rp)', 'SYNTHETIC UNKNOWN HEADER')
        tables = []
        for index, selector in enumerate(OWNERS):
            heading = first_headers if index == 0 else '<tr>' + ''.join(
                '<th>' + html.escape(value) + '</th>' for value in HEADERS[1]) + '</tr>'
            spans = SPANS[index]
            if self.defect == 'span' and index == 1:
                spans = [[8]] * 3
            footer = ''.join('<tr>' + ''.join('<td colspan="' + str(span)
                + '">SYNTHETIC FOOTER BAIT</td>' for span in row) + '</tr>' for row in spans)
            body = '<tr>' + '<td>SYNTHETIC BODY BAIT<input value="SYNTHETIC INPUT"></td>' * len(HEADERS[index]) + '</tr>'
            paginator = ('' if index == 0 else '<div class="p-paginator">'
                '<button class="p-paginator-prev" disabled onclick="moveL3(0)">Previous</button>'
                '<span class="p-paginator-current">1 of 2</span>'
                '<button class="p-paginator-next" onclick="moveL3(10)">Next</button></div>')
            table = '<p-table><table><thead>' + heading + '</thead><tbody>' + body * (2 if index == 0 else 10)
            table += '</tbody><tfoot>' + footer + '</tfoot></table>' + paginator + '</p-table>'
            if self.defect == 'table-outside-p-table' and index == 1:
                table = table.replace('<p-table><table>', '<p-table></p-table><table>').removesuffix('</p-table>')
            wrapper = 'ui-grid-offline' if index == 0 else 'ui-grid'
            if self.defect == 'wrong-ui-owner' and index == 0:
                wrapper = 'ui-grid'
            table = '<' + wrapper + '>' + table + '</' + wrapper + '>'
            if self.defect == 'owner' and index == 1:
                selector = 'synthetic-foreign-grid'
            tables.append('<' + selector + '>' + table + '</' + selector + '>')
        groups = list(GROUPS)
        if self.defect == 'wrong-group': groups[1] = 'SYNTHETIC FOREIGN GROUP'
        if self.defect == 'misplaced-grid': tables.reverse()
        content = ''.join('<p-accordiontab><div class="p-accordion-header"><a href="#" aria-expanded="true">'
            '<span class="p-accordion-header-text">' + caption + '</span></a></div>'
            '<div class="p-accordion-content">' + table + '</div></p-accordiontab>'
            for caption, table in zip(groups, tables))
        hidden = ' style="display:none"' if self.defect == 'hidden-owner' else ''
        form = '<rshshr-citr-l3-form' + hidden + '><p-accordion>' + content + '</p-accordion></rshshr-citr-l3-form>'
        if self.defect == 'visible-extra-form':
            # Synthetic third visible form-owned table is never an admitted
            # native owner and must not authorize any source packet replay.
            form = form.replace('</p-accordion>', '</p-accordion>'
                '<p-table><table><tbody><tr><td>SYNTHETIC_EXTRA</td></tr></tbody>'
                '</table></p-table>', 1)
        if self.defect == 'duplicate-owner': form += form
        tabs = ''.join('<li><a role="tab" aria-controls="panel-' + str(index)
            + '" href="#" onclick="show(' + str(index) + ');return false">' + caption + '</a></li>'
            for index, caption in enumerate(('Induk', 'L3')))
        return ('<rshshr-corporate-income-tax-return><div class="main-content"><div class="p-tabview">'
            '<ul class="p-tabview-nav">' + tabs + '</ul><div class="p-tabview-panels">'
            '<div class="p-tabview-panel" id="panel-0"><rshshr-citr-main-form>SYNTHETIC STRUCTURE</rshshr-citr-main-form></div>'
            '<div class="p-tabview-panel" id="panel-1" style="display:none">' + form
            + '</div></div></div></div></rshshr-corporate-income-tax-return>')

    def document(self):
        base = super().document().replace('</head>', '<style>rshshr-citr-l3-form,rsh-citr-l3-grid1,'
            'rshshr-citr-l3-grid2,ui-grid,ui-grid-offline{display:block}</style></head>')
        base = base.replace('!e.target.closest("a[role=tab]"))window.forbiddenClicks++;',
            '!e.target.closest("a[role=tab]")&&!e.target.closest(".p-paginator button"))window.forbiddenClicks++;')
        references = list(REFERENCES.values())
        if self.defect == 'missing-reference': references.pop()
        if self.defect == 'missing-footer': footer = 'Promise.resolve()'
        else: footer = 'fetchFooterL3()'
        script = ('<script>window.l3Started=false;window.l3Done=false;window.l3FooterDone=false;window.l3FooterReplies=0;'
            'const baseShowL3=window.show;window.show=function(i){baseShowL3(i);if(i===1&&!window.l3Started)'
            '{window.l3Started=true;startL3();}};'
            'function fetchFooterL3(){return fetch(' + json.dumps(FOOTER) + ',{method:"POST",'
            'headers:{"Content-Type":"application/json"},body:JSON.stringify({ReturnSheetRecordId:'
            + json.dumps(corpus.RECORD_ID) + '})}).then(r=>r.json()).then(()=>'
            '{window.l3FooterReplies++;window.l3FooterDone=true;});}'
            'function moveL3(first){const req=' + json.dumps(request(0)) + ';req.First=first;return fetch('
            + json.dumps(GRID) + ',{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(req)})'
            '.then(r=>r.json()).then(()=>{const grid=document.querySelector("rshshr-citr-l3-grid2");'
            'if(!grid)return;grid.querySelector(".p-paginator-current").textContent=first===0?"1 of 2":"2 of 2";'
            'grid.querySelector(".p-paginator-prev").disabled=first===0;'
            'grid.querySelector(".p-paginator-next").disabled=first!==0;'
            'grid.querySelector("tbody").innerHTML=("<tr>"+' + json.dumps(
                '<td>SYNTHETIC BODY BAIT<input value="SYNTHETIC INPUT"></td>' * 8)
            + '+"</tr>").repeat(first===0?10:2);window.l3Done=true;});}'
            'function startL3(){const refs=' + json.dumps(references) + ';'
            + ('moveL3(0).then(()=>{' + footer + ';});' if self.footer_order == 'late' else footer + ';moveL3(0);')
            + 'refs.forEach(url=>fetch(url).then(r=>r.json()));'
            + ('setTimeout(fetchFooterL3,200);' if self.defect == 'conflicting-footer' else '') + '}</script>')
        return base.replace('</body>', script + '</body>')
