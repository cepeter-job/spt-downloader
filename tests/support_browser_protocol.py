"""Synthetic browser protocol helpers; no collected tests or shared mutable test state."""
from types import SimpleNamespace
import json
import coretax_browser as driver


TAXPAYER = 'fixture-taxpayer'


RECORD = 'fixture-record'


LIST_URL = driver.ORIGIN + '/returnsheets/id-ID/submitted-returnsheets/' + TAXPAYER


DETAIL_URL = driver.ORIGIN + '/returnsheets/id-ID/fixture-return/' + TAXPAYER + '/' + RECORD


META = {'Jenis Pajak': 'Fixture', 'Masa Pajak': 'Januari 2025', 'Model SPT': 'Normal'}


class SignalSource:
    def __init__(self):
        self.listeners = {}

    def on(self, name, callback):
        self.listeners.setdefault(name, []).append(callback)

    def remove_listener(self, name, callback):
        self.listeners[name].remove(callback)

    def emit(self, name, value):
        for callback in list(self.listeners.get(name, [])):
            callback(value)


def response(rows=None, *, url=None, total=None, successful=True, status=200):
    rows = [{'RecordId': RECORD}] if rows is None else rows
    payload = {'IsSuccessful': successful, 'Payload': {
        'Data': rows, 'TotalRecords': len(rows) if total is None else total}}
    return SimpleNamespace(
        url=url or driver.ORIGIN + '/returnsheet/api/returnsheetsfixture',
        request=SimpleNamespace(url=url or driver.ORIGIN + '/returnsheet/api/returnsheetsfixture',
                                resource_type='xhr', method='POST', post_data_json={
            'TaxpayerAggregateIdentifier': TAXPAYER, 'First': 0, 'Rows': 50, 'Filters': []}),
        headers={'content-type': 'application/json'}, status=status,
        json=lambda: payload,
    )


class Container:
    def query_selector(self, selector):
        return None

    def dispose(self):
        pass


class View:
    def __init__(self, page):
        self.page = page

    def count(self):
        return 1

    def click(self, **kwargs):
        # Retain the same event observers when the real driver uses a pointer.
        return self.evaluate('(e)=>e.click()')

    def evaluate(self, script):
        if self.page.unrelated_popup is not None:
            self.page.context.emit('page', self.page.unrelated_popup)
        self.page.emit('popup', self.page.popup)
        self.page.context.emit('page', self.page.popup)


class Table:
    def __init__(self, page):
        self.page = page
        self.first = self

    def element_handle(self):
        return self

    def evaluate_handle(self, script):
        return Container()

    def evaluate(self, script):
        return {'headers': list(META), 'rows': [list(META.values())], 'footer': []}

    def locator(self, selector):
        return View(self.page) if selector == 'button[id=ViewButton]' else self

    def nth(self, index):
        assert index == 0
        return self


class DetailPage:
    def __init__(self, url):
        self.url = url
        self.closed = False

    def wait_for_load_state(self, state, timeout):
        pass

    def set_viewport_size(self, size):
        pass

    def close(self):
        self.closed = True


class SourcePage(SignalSource):
    def __init__(self, popup_url=DETAIL_URL):
        super().__init__()
        self.context = SignalSource()
        self.main_frame = self
        self.url = LIST_URL
        self.navigated = []
        self.popup = DetailPage(popup_url)
        self.unrelated_popup = None

    def commit_navigation(self, url):
        self.navigated.append(url)
        self.url = url
        self.emit('framenavigated', self.main_frame)

    def emit_grid_response(self, item):
        if not hasattr(item.request, 'frame'):
            item.request.frame = self.main_frame
        self.emit('request', item.request)
        self.emit('response', item)

    def goto(self, url, **kwargs):
        self.commit_navigation(url)
        self.emit_grid_response(response())

    def locator(self, selector):
        return Table(self)


def run_fixture(list_url=LIST_URL):
    return {'npwp': '0000000000000001', 'year': 2025, 'year_basis': 'period',
            'inventory_complete': True, 'errors': [], 'records': [
                {'key': 'fixture-key', 'record_id': RECORD, 'meta': dict(META),
                 'list_url': list_url, 'list_page': 1, 'list_page_size': None,
                 'capture_complete': False, 'sections': []}]}


def write_checkpoint(folder, record, ordinal=1, **changes):
    checkpoint_dir = folder / 'returns'
    checkpoint_dir.mkdir(exist_ok=True)
    saved = {**record, 'scope': ['0000000000000001', 2025, 'period'],
             'capture_complete': True, 'detail_url': DETAIL_URL,
             'sections': [{'name': 'Synthetic saved section', 'fields': [], 'tables': []}], **changes}
    (checkpoint_dir / f'{ordinal:04d}.json').write_text(json.dumps(saved), encoding='utf-8')
