"""Same-Document synthetic L7 SPA; no live data or business DOM reads."""
from copy import deepcopy
import json
import coretax_corporate as observer
import coretax_corporate_projection as projection
import support_json_corpus as corpus
from l1d_observer_fixture import Fixture as BaseFixture
from test_corporate_l7_native import l7_html, envelope
from test_corporate_l7_projection import ROOT, BODY, SUFFIXES
from test_corporate_l7_negative_native import negative_envelope


class Fixture(BaseFixture):
    def __init__(self, browser, monkeypatch, *, defect=None, negative=True, large_main=False, duplicate_rows=False):
        self.large_main = large_main
        super().__init__(browser, monkeypatch, defect=defect)
        monkeypatch.setattr(projection, 'BUILD_DIGESTS', {url: digest for url, digest in self.pins.items()
                            if url != projection.VENDOR_SOURCE})
        monkeypatch.setattr(projection, 'L7_NEGATIVE_BUILD_DIGESTS', dict(self.pins))
        value = negative_envelope() if negative else envelope()
        if duplicate_rows:
            current = json.loads(value['Payload']['CurrentFormData'], parse_int=corpus.Number, parse_float=corpus.Number)
            for year, profit in (('2025', '0'), ('02025', '-7')):
                row = deepcopy(current[ROOT][BODY][1])
                row.update(TaxYear=year, FiscalNetProfitIncome=corpus.Number(profit))
                current[ROOT][BODY].append(row)
            for index, suffix in enumerate(SUFFIXES):
                current[ROOT]['TotalFiscalLossCompensation' + suffix] = corpus.Number(str(400 * (index + 1)))
            value['Payload']['CurrentFormData'] = corpus.wire(current)
        self.raw = corpus.wire(value).encode()

    def route(self, route):
        if self.large_main and route.request.url == projection.MAIN_SOURCE:
            # Actual loaded MAIN remains above 4MiB and below the existing 5MiB cap.
            raw = b'/*' + b' ' * (4 * 1024 * 1024) + b'*/'
            import hashlib
            self.assets[projection.MAIN_SOURCE] = raw
            self.pins[projection.MAIN_SOURCE] = hashlib.sha256(raw).hexdigest()
        return super().route(route)

    def detail(self):
        form = l7_html().replace('<rsh-citr-l7-grid1>',
            '<div id="l7-wrapper"><rsh-citr-l7-grid1>').replace(
            '</rsh-citr-l7-grid1>', '</rsh-citr-l7-grid1></div>')
        if self.defect == 'table-outside-p-table':
            form = form.replace('<p-table><table>', '<p-table></p-table><table>').replace('</table></p-table>', '</table>')
        if self.defect in ('foreign-form', 'foreign-grid'):
            tag = 'rshshr-citr-l6-form' if self.defect == 'foreign-form' else 'synthetic-foreign-grid'
            form = form.replace('<rsh-citr-l7-grid1>', '<'+tag+'><rsh-citr-l7-grid1>').replace(
                '</rsh-citr-l7-grid1>', '</rsh-citr-l7-grid1></'+tag+'>')
        tabs, panels = [], []
        for index, (name, (selector, _)) in enumerate(observer.FORMS.items()):
            enabled = name in ('Induk', 'L7')
            tabs.append('<li' + ('' if enabled else ' class="p-disabled"') + '><a role="tab" '
                'aria-controls="panel-' + str(index) + '" href="#" onclick="show(' + str(index)
                + ');return false">' + name + '</a></li>')
            body = ('<rshshr-citr-main-form><label>SYNTHETIC STRUCTURE</label></rshshr-citr-main-form>'
                    if name == 'Induk' else form if name == 'L7' else '')
            panels.append('<div class="p-tabview-panel" role="tabpanel" id="panel-' + str(index)
                + '"' + ('' if name == 'Induk' else ' style="display:none"') + '>' + body + '</div>')
        return ('<rshshr-corporate-income-tax-return><div id="unrelated-l3"><table><tbody></tbody></table></div>'
            '<div class="main-content"><div class="p-tabview"><ul class="p-tabview-nav">'
            + ''.join(tabs) + '</ul><div class="p-tabview-panels">' + ''.join(panels)
            + '</div></div></div></rshshr-corporate-income-tax-return>')

    def document(self):
        source = super().document().replace('</head>',
            '<style>rshshr-citr-l7-form,rsh-citr-l7-grid1{display:block}</style></head>')
        if self.defect in ('hidden-initial-root', 'hidden-initial-l7'):
            tag = ('rshshr-corporate-income-tax-return' if self.defect == 'hidden-initial-root'
                   else 'rshshr-citr-l7-form')
            source = source.replace('<body>', '<body><' + tag + ' hidden></' + tag + '>')
        return source


def mutate(page, selector, mode):
    page.evaluate('''({selector,mode})=>{
        const node=document.querySelector(selector), parent=node.parentNode;
        if(mode==='remove-reinsert'){node.remove();parent.append(node);}
        if(mode==='replace')node.replaceWith(node.cloneNode(true));
        if(mode==='duplicate'){const other=node.cloneNode(true);parent.append(other);other.remove();}
        if(mode==='nested-duplicate'){
            const wrap=document.createElement('div'),other=node.cloneNode(true);
            wrap.append(other);parent.append(wrap);wrap.remove();
        }
        if(mode==='removed-wrapper-move-child'){
            const wrapper=document.querySelector('#l7-wrapper'), target=wrapper.parentNode;
            wrapper.remove();target.append(node);target.append(wrapper);
        }
    }''', {'selector': selector, 'mode': mode})


def churn(page, count=5000):
    page.evaluate('''count=>{
        const body=document.querySelector('#unrelated-l3 tbody');
        for(let i=0;i<count;i++){
            const row=document.createElement('tr');row.append(document.createElement('td'));
            body.append(row);row.remove();
        }
    }''', count)
