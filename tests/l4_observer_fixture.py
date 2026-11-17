"""Owned synthetic submitted L4 SPA; no portal code or taxpayer bytes."""
import html
import json

import coretax_corporate_projection as projection
from l1d_observer_fixture import Fixture as BaseFixture, ASSET as ASSET
from test_corporate_l4_populated_native import GRID, FOOTER, REFS, original_packets
from test_corporate_l4_projection import request


class Fixture(BaseFixture):
    def __init__(self, browser, monkeypatch, *, defect=None):
        raw = original_packets()
        self.grid_raw = {p['context']['request_json']['First']: p['body']
                         for p in raw if p['context']['url'] == GRID}
        self.footer_raw = next(p['body'] for p in raw if p['context']['url'] == FOOTER)
        self.reference_raw = {p['context']['url']: p['body'] for p in raw
                              if p['context']['method'] == 'GET'}
        if defect in ('locale', 'timezone'):
            new_context = browser.new_context
            key, value = ('locale', 'en-US') if defect == 'locale' else ('timezone_id', 'UTC')
            monkeypatch.setattr(browser, 'new_context', lambda **options: new_context(**{**options, key: value}))
        super().__init__(browser, monkeypatch, defect=defect)
        self.raw = raw[0]['body']
        monkeypatch.setattr(projection, 'L4_POPULATED_BUILD_DIGESTS', dict(self.pins))

    def route(self, route):
        req = route.request
        if req.url == GRID:
            self.requests.append((req.url, req.method))
            assert req.method == 'POST' and req.post_data_json == request(First=req.post_data_json['First'])
            return route.fulfill(content_type='application/json', body=self.grid_raw[req.post_data_json['First']])
        if req.url == FOOTER:
            self.requests.append((req.url, req.method))
            assert req.method == 'POST' and req.post_data_json == {
                'ReturnSheetRecordId': self.record['record_id'], 'PeriodYear': '2025'}
            return route.fulfill(content_type='application/json', body=self.footer_raw)
        if req.url in self.reference_raw:
            self.requests.append((req.url, req.method))
            assert req.method == 'GET' and req.post_data is None
            return route.fulfill(content_type='application/json', body=self.reference_raw[req.url])
        return super().route(route)

    def detail(self):
        blocks = []
        for index, item in enumerate(projection.l4_tables()):
            owner = item['component']
            if self.defect == 'owner' and index == 1: owner = 'synthetic-foreign-grid'
            host = 'ui-grid' if index == 0 else 'ui-grid-offline'
            if self.defect == 'wrong-ui-owner' and index == 1: host = 'ui-grid'
            headers = list(item['headers'])
            if self.defect == 'header' and index == 1: headers[1] = 'SYNTHETIC FOREIGN HEADER'
            spans = list(item['footer_spans'][0])
            if self.defect == 'footer' and index == 1: spans[-1] = 2
            body = '<tr>' + '<td>SYNTHETIC BODY BAIT<input value="SYNTHETIC INPUT BAIT"></td>' * len(headers) + '</tr>'
            paginator = '' if index else ('<div class="p-paginator">'
                '<button class="p-paginator-prev" disabled onclick="moveL4(0)">Previous</button>'
                '<span class="p-paginator-current">1 of 2</span>'
                '<button class="p-paginator-next" onclick="moveL4(10)">Next</button></div>')
            table = ('<p-table><table><thead><tr>' + ''.join('<th>' + html.escape(h) + '</th>' for h in headers)
                + '</tr></thead><tbody>' + body * (10 if index == 0 else 2) + '</tbody><tfoot><tr>'
                + ''.join('<td colspan="' + str(span) + '">SYNTHETIC FOOTER BAIT</td>' for span in spans)
                + '</tr></tfoot></table>' + paginator + '</p-table>')
            if self.defect == 'table-outside-p-table' and index == 1:
                table = table.replace('<p-table><table>', '<p-table></p-table><table>').removesuffix('</p-table>')
            blocks.append('<' + owner + '><' + host + '>' + table + '</' + host + '></' + owner + '>')
        form = '<rshshr-citr-l4-form>' + ''.join(blocks) + '</rshshr-citr-l4-form>'
        if self.defect == 'duplicate-owner': form += form
        tabs = ''.join('<li><a role="tab" aria-controls="panel-' + str(i)
            + '" href="#" onclick="show(' + str(i) + ');return false">' + name + '</a></li>'
            for i, name in enumerate(('Induk', 'L4')))
        return ('<rshshr-corporate-income-tax-return><div class="main-content"><div class="p-tabview">'
            '<ul class="p-tabview-nav">' + tabs + '</ul><div class="p-tabview-panels">'
            '<div class="p-tabview-panel" role="tabpanel" id="panel-0"><rshshr-citr-main-form>'
            'SYNTHETIC STRUCTURE</rshshr-citr-main-form></div>'
            '<div class="p-tabview-panel" role="tabpanel" id="panel-1" style="display:none">'
            + form + '</div></div></div></div></rshshr-corporate-income-tax-return>')

    def document(self):
        base = super().document().replace('</head>', '<style>rshshr-citr-l4-form,rshshr-citr-l4-grid1,'
            'rsh-citr-l4-grid2,ui-grid,ui-grid-offline{display:block}</style></head>')
        base = base.replace('!e.target.closest("a[role=tab]"))window.forbiddenClicks++;',
            '!e.target.closest("a[role=tab]")&&!e.target.closest(".p-paginator button"))window.forbiddenClicks++;')
        refs = list(REFS.values())
        if self.defect == 'missing-reference': refs.pop()
        changes = ''
        if self.defect == 'changed-header-after-page':
            changes = 'g.querySelector("thead th").textContent="SYNTHETIC CHANGED HEADER";'
        elif self.defect == 'changed-b-header-after-page':
            changes = 'document.querySelector("rsh-citr-l4-grid2 thead th").textContent="SYNTHETIC CHANGED B";'
        return base.replace('</body>', '<script>window.l4Started=false;window.l4Replies=0;'
            'const baseShowL4=window.show;window.show=function(i){baseShowL4(i);if(i===1&&!window.l4Started){'
            'window.l4Started=true;moveL4(0);fetch(' + json.dumps(FOOTER) + ',{method:"POST",'
            'headers:{"Content-Type":"application/json"},body:JSON.stringify(' + json.dumps({
                'ReturnSheetRecordId': self.record['record_id'], 'PeriodYear': '2025'}) + ')});'
            + json.dumps(refs) + '.forEach(u=>fetch(u).then(r=>r.json()));}};'
            'function moveL4(first){const req=' + json.dumps(request()) + ';req.First=first;'
            'return fetch(' + json.dumps(GRID) + ',{method:"POST",headers:{"Content-Type":"application/json"},'
            'body:JSON.stringify(req)}).then(r=>r.json()).then(()=>{window.l4Replies++;'
            'const g=document.querySelector("rshshr-citr-l4-grid1");'
            'g.querySelector(".p-paginator-current").textContent=first===0?"1 of 2":"2 of 2";'
            'g.querySelector(".p-paginator-prev").disabled=first===0;'
            'g.querySelector(".p-paginator-next").disabled=first===10;'
            'if(first===10){' + changes + '}});}</script></body>')
