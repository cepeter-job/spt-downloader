"""Real synthetic browser traffic for four-form native Unifikasi."""
import html
import json
import re
from masa_observer_fixture import Fixture
from unifikasi_projection_fixture import URL, case
from test_masa_json_field_observation import PERIOD


class NativeFixture(Fixture):
    def __init__(self, browser, tax, **kwargs):
        self.native = case()
        super().__init__(browser, tax, **kwargs)
        self.record = self.native['record']

    @staticmethod
    def json(route, payload):
        return route.fulfill(content_type="application/json", body=json.dumps(payload))

    def route(self, route):
        url = route.request.url
        if url == URL:
            return self.json(route, json.loads(self.native['packets'][-1]['body']))
        if '/prefillreturnsheet/withholding-tax' in url:
            return self.json(route, json.loads(self.native['packets'][0]['body']))
        if '/loadwtr/' in url:
            source = next(p for p in self.native['packets'] if p['context']['url'] == url)
            row = json.loads(source['body'])['Payload']['Data'][0]
            request = route.request.post_data_json
            rows = [row] * 12
            return self.json(route, {'IsSuccessful': True, 'Payload': {
                'Data': rows[request['First']:request['First'] + request['Rows']], 'TotalRecords': 12}})
        return super().route(route)

    def shape(self, name):
        return next(table for form in self.native['forms'] for table in form['tables'] if table['name'] == name)

    @staticmethod
    def table_html(shape):
        headers = ''.join('<th>' + html.escape(label) + '</th>' for label in shape['headers'])
        footer = ''.join('<tr>' + ''.join('<td colspan="' + str(span) + '">DOM-FOOTER-TRAP</td>'
                          for span in row) + '</tr>' for row in shape['footer_spans'])
        return ('<table><thead><tr>' + headers + '</tr></thead><tbody><tr><td>DOM-BODY-TRAP</td></tr></tbody>'
                + ('<tfoot>' + footer + '</tfoot>' if footer else '') + '</table>')

    def table(self, selector, suffix, group):
        original = super().table(selector, suffix, group)
        return re.sub(r'<table>.*?</table>', lambda _: self.table_html(self.shape(suffix)), original)

    def document(self):
        self.induk_fields = '<p-accordion>' + PERIOD + '</p-accordion>'
        original = super().document()
        tree = '<rshshr-spt-unifikasi-grid><p-treetable>' + self.table_html(self.shape('income-taxes'))
        tree += '</p-treetable></rshshr-spt-unifikasi-grid>'
        original = re.sub(r'<rshshr-spt-unifikasi-grid>.*?</rshshr-spt-unifikasi-grid>', lambda _: tree, original)
        traps = '''
for(const node of document.querySelectorAll('tbody td,tfoot td,.p-dropdown-label')){
 for(const property of ['textContent','innerText']) Object.defineProperty(node,property,{get(){window.valueReads++;throw Error('DOM business values forbidden');}});
}
'''
        return original.replace('</script></body>', traps + '</script></body>')
