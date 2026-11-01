"""Owned synthetic SPA L8 fixture with business-read traps; runners only."""
import html

import coretax_corporate_projection as projection
from l1d_observer_fixture import Fixture as BaseFixture
from test_corporate_l8_native import envelope, HEADERS, GROUP
import support_json_corpus as corpus


class Fixture(BaseFixture):
    def __init__(self, browser, monkeypatch, *, model='Normal', defect=None):
        super().__init__(browser, monkeypatch, model=model, defect=defect)
        monkeypatch.setattr(projection, 'L8_BUILD_DIGESTS', dict(self.pins), raising=False)
        self.raw = corpus.wire(envelope(model)).encode()

    def detail(self):
        labels = list(HEADERS)
        if self.defect == 'header': labels[1] = 'SYNTHETIC UNKNOWN HEADER'
        table = ('<p-table><table><thead><tr>'
            + ''.join('<th>'+html.escape(label)+'</th>' for label in labels)
            + '</tr></thead><tbody>'
            + ''.join('<tr><td>SYNTHETIC DOM BAIT<input value="DO NOT READ"></td>'
                      '<td>SYNTHETIC DOM BAIT</td><td>SYNTHETIC DOM BAIT</td></tr>' for _ in range(8))
            + '</tbody><tfoot><tr><td>SYNTHETIC DOM BAIT</td>'
              '<td>SYNTHETIC DOM BAIT</td><td>SYNTHETIC DOM BAIT</td></tr></tfoot></table></p-table>')
        if self.defect == 'footer': table = table.replace('<tfoot><tr><td>', '<tfoot><tr><td colspan="2">', 1)
        if self.defect == 'table-outside-p-table':
            table = table.replace('<p-table><table>', '<p-table></p-table><table>').replace('</table></p-table>', '</table>')
        grid = '<rsh-citr-l8-form-grid1>'+table+'</rsh-citr-l8-form-grid1>'
        if self.defect == 'duplicate-owner': grid += grid
        if self.defect == 'owner': grid = grid.replace('rsh-citr-l8-form-grid1', 'synthetic-foreign-grid')
        group = 'SYNTHETIC FOREIGN GROUP' if self.defect == 'wrong-group' else GROUP
        hidden = ' style="display:none"' if self.defect == 'hidden-owner' else ''
        form = ('<rshshr-citr-l8-form'+hidden+'><h2>'+html.escape(GROUP)+'</h2>'
            '<p-accordion><p-accordiontab><div class="p-accordion-header">'
            '<a href="#" aria-expanded="true"><span class="p-accordion-header-text">'
            + html.escape(group)+'</span></a></div><div class="p-accordion-content">'
            + grid+'</div></p-accordiontab></p-accordion></rshshr-citr-l8-form>')
        tabs = ''.join('<li><a role="tab" aria-controls="panel-'+str(i)+'" href="#" onclick="show('
            +str(i)+');return false">'+name+'</a></li>' for i, name in enumerate(('Induk', 'L8')))
        return ('<rshshr-corporate-income-tax-return><div class="main-content"><div class="p-tabview">'
            '<ul class="p-tabview-nav">'+tabs+'</ul><div class="p-tabview-panels">'
            '<div class="p-tabview-panel" role="tabpanel" id="panel-0"><rshshr-citr-main-form>'
            '<label>SYNTHETIC STRUCTURE</label></rshshr-citr-main-form></div>'
            '<div class="p-tabview-panel" role="tabpanel" id="panel-1" style="display:none">'
            +form+'</div></div></div></div></rshshr-corporate-income-tax-return>')

    def document(self):
        text = super().document()
        text = text.replace('</head>', '<style>rshshr-citr-l8-form,rsh-citr-l8-form-grid1{display:block}</style></head>')
        if self.defect == 'hidden-initial-root':
            text = text.replace('<body>', '<body><rshshr-corporate-income-tax-return style="display:none"></rshshr-corporate-income-tax-return>')
        if self.defect == 'hidden-initial-dependent':
            text = text.replace('<body>', '<body><rshshr-citr-l13b-form style="display:none"></rshshr-citr-l13b-form>')
        return text
