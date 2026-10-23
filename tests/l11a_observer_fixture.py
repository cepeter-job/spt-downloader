"""Synthetic owned L11-A SPA, four page inventories and catalog custody."""
import html
import json

import coretax_corporate_projection as projection
from l1d_observer_fixture import Fixture as BaseFixture, ASSET as ASSET
from test_corporate_l11a_native import GRIDS, OWNERS, GROUPS, packets, request
from test_corporate_l11a_projection import HEADERS, CAPTIONS
import support_json_corpus as corpus


class Fixture(BaseFixture):
    def __init__(self, browser, monkeypatch, *, model='Normal', transport='pair-reordered', defect=None):
        self.transport = transport
        if defect in ('timezone', 'locale'):
            new_context = browser.new_context
            key, value = ('timezone_id', 'UTC') if defect == 'timezone' else ('locale', 'en-US')
            monkeypatch.setattr(browser, 'new_context', lambda **options: new_context(**{**options, key: value}))
        raw = packets(model, transport)
        self.grid_raw = {(p['context']['url'], p['context']['request_json']['First']): p['body']
                         for p in raw if p['context']['url'] in GRIDS.values()}
        self.reference_raw = {p['context']['url']: p['body'] for p in raw if p['context']['method'] == 'GET'}
        super().__init__(browser, monkeypatch, model=model, defect=defect)
        self.raw = raw[0]['body']
        monkeypatch.setattr(projection, 'L11A_BUILD_DIGESTS', self.pins, raising=False)

    def route(self, route):
        req = route.request
        if req.url in GRIDS.values():
            self.requests.append((req.url, req.method))
            assert req.method == 'POST'
            assert req.post_data_json == request(req.post_data_json['First'])
            raw = self.grid_raw[(req.url, req.post_data_json['First'])]
            if self.defect == 'failed-page' and req.url == list(GRIDS.values())[1]:
                return route.fulfill(status=500, content_type='application/json',
                    body=corpus.wire({'IsSuccessful': False, 'Payload': None}))
            if self.defect == 'changed-count' and req.post_data_json['First'] == 10:
                value = json.loads(raw)
                value['Payload']['TotalRecords'] = 13
                value['Payload']['Data'].append(value['Payload']['Data'][-1])
                raw = corpus.wire(value).encode()
            return route.fulfill(content_type='application/json', body=raw)
        if req.url in self.reference_raw:
            self.requests.append((req.url, req.method))
            assert req.method == 'GET' and req.post_data is None
            return route.fulfill(content_type='application/json', body=self.reference_raw[req.url])
        return super().route(route)

    def detail(self):
        tables = []
        for index, owner in enumerate(OWNERS):
            if index == 3:
                headers = ('<tr><th rowspan="2">NO.</th><th rowspan="2">JENIS HARTA BERWUJUD</th>'
                    '<th rowspan="2">TAHUN PEROLEHAN</th><th rowspan="2">NILAI PEROLEHAN</th>'
                    '<th colspan="3">PENYUSUTAN</th></tr><tr><th>S.D. TAHUN LALU</th>'
                    '<th>PENYUSUTAN TAHUN INI</th><th>S.D. TAHUN INI</th></tr>')
            else:
                headers = '<tr>' + ''.join('<th>' + html.escape(label) + '</th>' for label in HEADERS[index]) + '</tr>'
            if self.defect == 'header' and index == 0: headers = headers.replace('No.', 'SYNTHETIC FOREIGN HEADER')
            body = '<tr>' + '<td>SYNTHETIC BODY BAIT<input value="SYNTHETIC INPUT"></td>' * len(HEADERS[index]) + '</tr>'
            footer = '<tfoot><tr><td>SYNTHETIC FOOTER BAIT</td></tr></tfoot>' if self.defect == 'footer' and index == 4 else ''
            paginator = ''
            if index != 3:
                paginator = ('<div class="p-paginator"><button class="p-paginator-prev" disabled '
                    'onclick="moveL11A(' + str(index) + ',0)">Previous</button>'
                    '<span class="p-paginator-current">1 of ' + ('2' if index == 0 else '1') + '</span>'
                    '<button class="p-paginator-next" ' + ('' if index == 0 else 'disabled ')
                    + 'onclick="moveL11A(' + str(index) + ',10)">Next</button></div>')
            table = '<p-table><table><thead>' + headers + '</thead><tbody>' + body * (10 if index == 0 else 2)
            table += '</tbody>' + footer + '</table>' + paginator + '</p-table>'
            if self.defect == 'table-outside-p-table' and index == 1:
                table = table.replace('<p-table><table>', '<p-table></p-table><table>').removesuffix('</p-table>')
            wrapper = 'ui-grid-offline' if index == 3 else 'ui-grid'
            if self.defect == 'wrong-ui-owner' and index == 3: wrapper = 'ui-grid'
            table = '<' + wrapper + '>' + table + '</' + wrapper + '>'
            if self.defect == 'owner' and index == 1: owner = 'synthetic-foreign-grid'
            tables.append('<' + owner + '>' + table + '</' + owner + '>')
        if self.defect == 'misplaced-grid': tables[0], tables[1] = tables[1], tables[0]
        def accordion(caption, content):
            return ('<p-accordiontab><div class="p-accordion-header"><a href="#" aria-expanded="true">'
                '<span class="p-accordion-header-text">' + html.escape(caption) + '</span></a></div>'
                '<div class="p-accordion-content">' + content + '</div></p-accordiontab>')
        content = ''
        for index, captions in enumerate(GROUPS):
            groups = list(captions)
            if self.defect == 'wrong-group' and index == 1: groups[0] = 'SYNTHETIC FOREIGN GROUP'
            if self.defect == 'missing-outer-group' and index == 3: groups.pop(0)
            part = tables[index]
            if index == 3:
                recap = ''.join('<label>' + html.escape(caption) + '</label><input value="SYNTHETIC RECAP BAIT">' for caption in CAPTIONS)
                part = accordion(groups[-1], part) + accordion('IV.B RINCIAN PENGGANTIAN ATAU IMBALAN DALAM BENTUK NATURA DAN/ATAU KENIKMATAN YANG DIBERIKAN BERKENAAN DENGAN PELAKSANAAN PEKERJAAN DI DAERAH TERTENTU', recap)
                if len(groups) == 2: part = accordion(groups[0], part)
            else:
                for caption in reversed(groups): part = accordion(caption, part)
            content += part
        hidden = ' style="display:none"' if self.defect == 'hidden-owner' else ''
        form = '<rshshr-citr-l11a-form' + hidden + '><p-accordion>' + content + '</p-accordion></rshshr-citr-l11a-form>'
        if self.defect == 'duplicate-owner': form += form
        tabs = ''.join('<li><a role="tab" aria-controls="panel-' + str(i) + '" href="#" onclick="show('
            + str(i) + ');return false">' + caption + '</a></li>' for i, caption in enumerate(('Induk', 'L11-A')))
        return ('<rshshr-corporate-income-tax-return><div class="main-content"><div class="p-tabview">'
            '<ul class="p-tabview-nav">' + tabs + '</ul><div class="p-tabview-panels">'
            '<div class="p-tabview-panel" id="panel-0"><rshshr-citr-main-form>SYNTHETIC STRUCTURE</rshshr-citr-main-form></div>'
            '<div class="p-tabview-panel" id="panel-1" style="display:none">' + form
            + '</div></div></div></div></rshshr-corporate-income-tax-return>')

    def document(self):
        css = ','.join(['rshshr-citr-l11a-form', *OWNERS, 'ui-grid', 'ui-grid-offline']) + '{display:block}'
        base = super().document().replace('</head>', '<style>' + css + '</style></head>')
        base = base.replace('!e.target.closest("a[role=tab]"))window.forbiddenClicks++;',
            '!e.target.closest("a[role=tab]")&&!e.target.closest(".p-paginator button"))window.forbiddenClicks++;')
        references = list(self.reference_raw)
        if self.defect == 'missing-reference': references.pop()
        grids = {index: url for index, url in zip((0, 1, 2, 4), GRIDS.values())}
        active = list(grids)
        if self.defect == 'missing-grid': active.remove(1)
        script = ('<script>window.l11aStarted=false;window.l11aReplies=0;window.l11aNextDone=false;'
            'const baseShowL11A=window.show;window.show=function(i){baseShowL11A(i);if(i===1&&!window.l11aStarted)'
            '{window.l11aStarted=true;startL11A();}};'
            'function moveL11A(index,first){const req=' + json.dumps(request(0)) + ';req.First=first;'
            'const urls=' + json.dumps(grids) + ',owners=' + json.dumps(OWNERS) + ';return fetch(urls[index],'
            '{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(req)})'
            '.then(r=>r.json()).then(()=>{window.l11aReplies++;const grid=document.querySelector(owners[index]);'
            'if(!grid)return;const two=index===0;grid.querySelector(".p-paginator-current").textContent='
            'two?(first===0?"1 of 2":"2 of 2"):"1 of 1";'
            'grid.querySelector(".p-paginator-prev").disabled=first===0;'
            'grid.querySelector(".p-paginator-next").disabled=!two||first!==0;'
            'grid.querySelector("tbody").innerHTML=("<tr>"+"<td>SYNTHETIC BODY BAIT<input value=SYNTHETIC></td>"'
            '.repeat(index===0||index===1?10:8)+"</tr>").repeat(index===0&&first===0?10:2);'
            'if(first===10){window.l11aNextDone=true;'
            + ('grid.querySelector("thead th").textContent="SYNTHETIC CHANGED HEADER";' if self.defect == 'changed-header-after-page' else '')
            + ('grid.closest("p-accordiontab").querySelector(".p-accordion-header-text").textContent="SYNTHETIC CHANGED GROUP";' if self.defect == 'changed-group-after-page' else '')
            + ('document.querySelector(owners[3]).querySelector("thead th").textContent="SYNTHETIC CHANGED OFFLINE HEADER";' if self.defect == 'changed-offline-header-after-page' else '')
            + ('document.querySelector(owners[3]).closest("p-accordiontab").querySelector(".p-accordion-header-text").textContent="SYNTHETIC CHANGED OFFLINE GROUP";' if self.defect == 'changed-offline-group-after-page' else '')
            + '}});}'
            'function startL11A(){const active=' + json.dumps(active) + ',refs=' + json.dumps(references) + ';'
            'active.forEach(index=>moveL11A(index,0));refs.forEach(url=>fetch(url).then(r=>r.json()));}</script>')
        return base.replace('</body>', script + '</body>')
