# Synthetic routed Edge fixture. Never copies portal code or taxpayer data.
import html
import json
from coretax_json import ORIGIN
from masa_json_fixtures import FOREIGN, RECORD, TAXPAYER, selected

MAIN = ORIGIN + '/returnsheets/id-ID/main.cccfdb820c20596c.js'
ASSETS = {
    'PPN': ORIGIN + '/returnsheets/id-ID/640.36c042afd2381189.js',
    'PPh Unifikasi': ORIGIN + '/returnsheets/id-ID/693.4de61c6eb2000c7e.js',
}
BUILD = b'/* synthetic observer build, not portal code */'
FRAME = ORIGIN + '/returnsheets/id-ID/synthetic-masa/' + TAXPAYER + '/' + RECORD
FORMS = {
    'PPN': [('INDUK', None, []),
            ('A-1', 'rshshr-nvat-la1-form', [('rshshr-nvat-la1-grid', 'la1', 'A-1')]),
            ('A-2', 'rshshr-nvat-la2-form', [('rshshr-nvat-la2-grid', 'la2', 'A-2')]),
            ('B-1', 'rshshr-nvat-lb1-form', [('rshshr-nvat-lb1-grid', 'lb1', 'B-1')]),
            ('B-2', 'rshshr-nvat-lb2-form', [('rshshr-nvat-lb2-grid', 'lb2', 'B-2')]),
            ('B-3', 'rshshr-nvat-lb3-form', [('rshshr-nvat-lb3-grid', 'lb3', 'B-3')]),
            ('C', 'rshshr-nvat-lc-form', [('rshshr-nvat-lc-grid', 'lc', 'C')])],
    'PPh Unifikasi': [('INDUK', 'rshshr-spt-unifikasi', []),
        ('DAFTAR-I', 'rshshr-list-i', [('rshshr-list-i-grid-a', 'list-i-bpu', 'TABEL I. BPPU'),
                                    ('rshshr-list-i-grid-b', 'list-i-bpnr', 'TABEL II. BPNR')]),
        ('DAFTAR-II', 'rshshr-list-ii', [('rshshr-list-ii-grid-a', 'list-ii-sp', 'TABEL I. SETOR SENDIRI'),
                                      ('rshshr-list-ii-grid-b', 'list-ii-cy', 'TABEL II. CY')]),
        ('LAMPIRAN-I', 'rshshr-attachment-i', [('rshshr-attachment-i-grid', 'attachment-i', 'LAMPIRAN-I')])],
}


class Fixture:
    def __init__(self, browser, tax, *, defect=None, layout='direct'):
        self.tax, self.defect, self.layout = tax, defect, layout
        self.context = browser.new_context(locale='id-ID', timezone_id='Asia/Jakarta')
        self.page = self.context.new_page()
        self.record = selected(tax)
        self.unexpected = []
        self.context.route('**/*', self.route)

    def route(self, route):
        request = route.request
        if request.url == self.record['list_url']:
            route.fulfill(content_type='text/html', body='<link rel="icon" href="data:,">')
        elif request.url == FRAME:
            route.fulfill(content_type='text/html', body=self.document())
        elif request.url in (MAIN, ASSETS[self.tax]):
            changed = self.defect == ('changed-main' if request.url == MAIN else 'changed-build')
            route.fulfill(content_type='application/javascript', body=BUILD + (b'/* changed */' if changed else b''))
        elif request.url.startswith(ORIGIN + '/returnsheet/api/'):
            assert request.method == 'POST'
            route.fulfill(status=403 if self.defect == 'unauthorized' else 200,
                content_type='application/json', body=json.dumps({
                    'IsSuccessful': True, 'Payload': {'Data': [], 'TotalRecords': 12}}))
        else:
            self.unexpected.append(request.url)
            route.abort()

    def table(self, selector, grid, group):
        endpoint = '/loadndvat/' if self.tax == 'PPN' else '/loadwtr/'
        config = html.escape(json.dumps({'endpoint': endpoint + grid + '-grid', 'first': 10}), quote=True)
        return ('<p-panel><div class="p-panel-header"><span class="p-panel-title">' + group +
            '</span></div><div class="p-panel-content"><' + selector + '><p-table data-config="' + config + '">'
            '<table><thead><tr><th rowspan="2">No.</th><th colspan="2">Document</th></tr>'
            '<tr><th>Number</th><th>Date</th></tr><tr><th><input value="FILTER-TRAP"></th></tr></thead>'
            '<tbody><tr><td>DOM-ROW-TRAP</td></tr></tbody>'
            '<tfoot><tr><td colspan="2">TOTAL</td><td>DOM-TOTAL-TRAP</td></tr></tfoot></table>'
            '<div class="p-paginator"><span class="p-paginator-current"></span>'
            '<button class="p-paginator-prev" onclick="turn(this,-10)">Previous</button>'
            '<button class="p-paginator-next" onclick="turn(this,10)">Next</button></div>'
            '</p-table></' + selector + '></div></p-panel>')

    def document(self):
        forms = list(FORMS[self.tax])
        if self.defect == 'missing-form':
            forms.pop()
        if self.defect == 'extra-form':
            forms.append(('UNREVIEWED', None, []))
        if self.defect == 'duplicate-form':
            forms.append(forms[-1])
        tabs, panels = [], []
        for index, (name, selector, grids) in enumerate(forms):
            tabs.append(f'<li><a role="tab" href="#" aria-controls="p{index}" onclick="show({index});return false">{name}</a></li>')
            control = ('<p-accordion><h3 class="p-accordion-header-text">OUTER</h3><div class="p-accordion-content">'
                '<p-panel><span class="p-panel-title">IDENTITY</span><div><label for="f' + str(index) + '">NAME</label>'
                '<input id="f' + str(index) + '" formcontrolname="FullName" value="DOM-INPUT-TRAP" readonly></div></p-panel>'
                '<div class="p-tabview"><ul class="p-tabview-nav"><li><a role="tab" onclick="forbidden()">NESTED</a></li></ul></div>'
                '<button onclick="forbidden()">Submit</button></div></p-accordion>')
            if name == 'INDUK' and self.tax == 'PPh Unifikasi':
                control += ('<rshshr-spt-unifikasi-grid><p-treetable><table><thead><tr><th>No.</th><th>DETAIL</th></tr></thead>'
                    '<tbody><tr><td>DOM-TREE-TRAP</td></tr></tbody><tfoot><tr><td colspan="2">TOTAL</td></tr></tfoot>'
                    '</table></p-treetable></rshshr-spt-unifikasi-grid>')
            content = control + ''.join(self.table(*grid) for grid in grids)
            if self.defect == 'extra-table' and index == 0:
                content += '<table><thead><tr><th>UNKNOWN</th></tr></thead><tbody></tbody></table>'
            if selector:
                content = '<' + selector + '>' + content + '</' + selector + '>'
            panel_id = f'p{index}'
            if self.defect == 'nested-panel-target' and index == 0:
                content = ('<div class="p-tabview"><div class="p-tabview-panels">'
                           '<div class="p-tabview-panel" id="p0">' + content + '</div></div></div>')
                panel_id = 'outer0'
            panel = f'<div data-main-panel class="p-tabview-panel" id="{panel_id}" style="display:{"block" if index == 0 else "none"}">{content}</div>'
            if self.layout == 'wrapped':
                panel = '<p-tabpanel>' + panel + '</p-tabpanel>'
            panels.append(panel)
            if self.defect == 'duplicate-panel-target' and index == 0:
                panels.append('<div class="p-tabview"><div class="p-tabview-panels">'
                              '<div class="p-tabview-panel" id="p0">DUPLICATE TARGET</div></div></div>')
        config = {'record': FOREIGN if self.defect == 'foreign-request' else RECORD,
                  'prefix': ORIGIN + '/returnsheet/api', 'defect': self.defect,
                  'primary': '/prefillreturnsheet/nvat' if self.tax == 'PPN' else '/prefillreturnsheet/withholding-tax'}
        return ('<html><head><link rel="icon" href="data:,"><style>p-table,p-panel,p-accordion,p-treetable{display:block}</style>'
            '<script src="' + MAIN + '"></script><script src="' + ASSETS[self.tax] + '"></script></head>'
            '<body><div class="main-content"><div class="p-tabview"><ul class="p-tabview-nav">' + ''.join(tabs) +
            '</ul><div class="p-tabview-panels">' + ''.join(panels) + '</div></div></div><script>const cfg=' + json.dumps(config) + ';' + SCRIPT + '</script></body></html>')


SCRIPT = r"""
window.forbiddenClicks=0;window.valueReads=0;
function forbidden(){window.forbiddenClicks++;}
function send(endpoint,body){return fetch(cfg.prefix+endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});}
function load(g){const c=JSON.parse(g.dataset.config);
    g.querySelector('.p-paginator-current').textContent='Showing '+(c.first+1)+' to '+Math.min(c.first+10,12)+' of 12';
    g.querySelector('.p-paginator-prev').disabled=c.first===0;
    g.querySelector('.p-paginator-next').disabled=c.first+10>=12;
    if(cfg.defect==='missing-request')return;
    return send(c.endpoint,{ReturnSheetRecordId:cfg.record,First:c.first,Rows:10,Filters:cfg.defect==='filtered'?[{Field:'X'}]:[],SortField:'',SortOrder:1});}
function turn(button,delta){const g=button.closest('p-table'),c=JSON.parse(g.dataset.config);c.first+=delta;g.dataset.config=JSON.stringify(c);load(g);}
function footer(g){const c=JSON.parse(g.dataset.config);
    if(c.endpoint!=='/loadndvat/lc-grid'||cfg.defect==='missing-footer')return;
    return send('/loadndvat/lc-grid/footer',{ReturnSheetRecordId:cfg.defect==='foreign-footer'?'00000000-0000-4000-8000-000000000099':cfg.record,
        IsNormalVAT:cfg.defect==='wrong-footer-kind'?false:cfg.defect==='untyped-footer-kind'?'true':true});}

function show(i){document.querySelectorAll('[data-main-panel]').forEach((p,j)=>{
    p.style.display=i===j?'block':'none';if(i===j)p.querySelectorAll('p-table').forEach(g=>{if(!g.dataset.loaded){g.dataset.loaded='1';load(g);footer(g);}});
});}
send(cfg.primary,{RecordId:cfg.record,OnManualClick:false});
for(const property of ['value','checked'])Object.defineProperty(HTMLInputElement.prototype,property,{get(){window.valueReads++;throw Error('DOM values are forbidden');}});
"""
