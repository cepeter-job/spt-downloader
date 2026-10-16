"""Synthetic json hybrid helpers; no collected tests or shared mutable test state."""
from copy import deepcopy
import inspect
import coretax_browser as driver
import support_browser_protocol as protocol
import support_financial_evidence as financial
import support_json_corpus as corpus
import support_json_network as network


PRIMARY_REQUEST = {'RecordId': corpus.RECORD_ID, 'OnManualClick': False}


BASE_VIEW_EVALUATE = protocol.View.evaluate


DOM_SECTIONS = [{'name': 'DOM ONLY', 'fields': [
    {'label': 'Literal', 'field': 'literal', 'value': '0000099'}],
    'tables': [], 'text': 'SYNTHETIC DOM FALLBACK'}]


def collector():
    parameter = inspect.signature(driver.collect_details).parameters.get('detail_source')
    assert parameter is not None, 'Missing hybrid collector mode: intentional feature RED'
    assert parameter.default == 'dom'
    return driver.collect_details


class HybridDetail(protocol.DetailPage):
    def __init__(self, source):
        super().__init__(corpus.FRAME_URL)
        self.context = source.context
        self.main_frame = network.Frame(self)
        self.frames = [self.main_frame]
        self.source = source
        self.context.pages.append(self)

    def opener(self):
        return self.source

    def is_closed(self):
        return self.closed

    def wait_for_timeout(self, milliseconds):
        self.context.ticks += milliseconds / 1000


class HybridSource(protocol.SourcePage):
    def __init__(self, mode):
        super().__init__()
        self.context = network.Context()
        self.main_frame = network.Frame(self)
        self.context.pages.append(self)
        self.url = corpus.LIST_URL
        self.popup = HybridDetail(self)
        self.mode = mode
        self.view_calls = 0
        self.exchanges = []
        self.body_responses = []
        self.rows = [deepcopy(corpus.selected_record()['source_fields'])]

    def goto(self, url, **kwargs):
        self.navigated.append(url)
        self.url = url
        self.emit('response', protocol.response(
            rows=self.rows, url=corpus.ORIGIN + '/returnsheet/api/returnsheetssubmitted'))


class StopRequested(driver.CaptureCancelled):
    pass


class Scenario:
    def __init__(self, tmp_path, monkeypatch, *, mode='json-first', tax_kind='PPh Badan',
                 raw=None, status=200, financial_complete=True):
        self.folder = tmp_path
        self.run = {'npwp': corpus.NPWP, 'year': 2025, 'year_basis': 'period',
                    'inventory_complete': True, 'errors': [],
                    'records': [deepcopy(corpus.selected_record())]}
        self.record = self.run['records'][0]
        self.record.update(list_page=1, list_page_size=None)
        self.record['meta']['Jenis Pajak'] = tax_kind
        if tax_kind == 'PPN':
            self.record['meta']['Masa Pajak'] = 'Januari 2025'
            self.record['source_fields'].update(TaxTypeCode='SYNTHETIC UNKNOWN MASA CODE', TaxPeriodCode='01012025')
        monkeypatch.setattr(protocol, 'META', dict(self.record['meta']))
        monkeypatch.setattr(driver, 'wait_idle', lambda page: None)
        self.page = HybridSource(mode)
        self.page.rows = [deepcopy(self.record['source_fields'])]
        self.page.exchanges = [{'raw': corpus.primary()['body'] if raw is None else raw,
                                'url': corpus.PRIMARY_URL, 'status': status,
                                'post': deepcopy(PRIMARY_REQUEST)}]
        self.forms = corpus.observed()
        self.forms[0]['primary']['request_json'] = deepcopy(PRIMARY_REQUEST)
        if tax_kind == 'PPN':
            self.forms = []
            self.page.exchanges[0].update(
                url=corpus.ORIGIN + '/returnsheet/api/prefillreturnsheet/fixture-masa',
                post={'ReturnSheetRecordId': corpus.RECORD_ID})
        self.dom_calls = []
        self.pdf_calls = []
        self.observation_calls = []
        self.stop = False
        self.cancel_on_body = False
        self.financial_complete = financial_complete

        original_view = BASE_VIEW_EVALUATE
        def view(view, script):
            source = view.page
            assert source is self.page
            source.view_calls += 1
            for event in ('request', 'response', 'requestfinished'):
                assert bool(source.context.listeners.get(event)) is (source.mode == 'json-first'), (
                    'Capture must be entered after row validation and before View')
            original_view(view, script)
            for exchange in source.exchanges:
                response = network.exchange(source.context, source.popup, **exchange)
                if self.cancel_on_body:
                    response.on_read = lambda: setattr(self, 'stop', True)
                source.body_responses.append(response)
        monkeypatch.setattr(protocol.View, 'evaluate', view)

        def observe(page, record, scope, capture, **kwargs):
            assert page is self.page.popup and record is self.record
            assert scope == corpus.SCOPE
            self.observation_calls.append(record['record_id'])
            return deepcopy(self.forms)
        # This is the DOM boundary, not the decoder or hybrid eligibility branch.
        monkeypatch.setattr(driver, 'observe_corporate_forms', observe, raising=False)

        def dom(page, **kwargs):
            assert page is self.page.popup
            assert kwargs['record'] is self.record and kwargs['folder'] == self.folder
            self.dom_calls.append(kwargs)
            pdf = self.pdf(page, **kwargs) if tax_kind == 'PPh Badan' else {
                'attachments': [], 'capture_complete': True, 'errors': []}
            return {'sections': deepcopy(DOM_SECTIONS), **pdf}
        monkeypatch.setattr(driver, 'capture_detail', dom)
        monkeypatch.setattr(driver, 'capture_financial_detail', self.pdf, raising=False)

    def pdf(self, page, **kwargs):
        assert page is self.page.popup
        assert kwargs['record'] is self.record and kwargs['folder'] == self.folder
        self.pdf_calls.append(kwargs)
        item = financial.metadata(self.record['record_id'])
        if self.financial_complete:
            path = self.folder / item['relative_path']
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(financial.PDF)
        else:
            item.update(status='PARTIAL', relative_path='', bytes=0, hash='')
        return {'attachments': [item], 'capture_complete': self.financial_complete,
                'errors': [] if self.financial_complete else [
                    {'object': 'Induk/Laporan Keuangan', 'message': 'SYNTHETIC PDF RETRY'}]}

    def cancel(self):
        if self.stop:
            raise StopRequested('SYNTHETIC STOP')

    def collect(self):
        return collector()(self.page, self.run, self.folder,
                           detail_source=self.page.mode, check_cancel=self.cancel)

    def assert_closed(self):
        assert self.page.popup.closed
        assert not any(self.page.context.listeners.values())
        assert not self.page.listeners.get('response')
        assert not self.page.listeners.get('popup')
