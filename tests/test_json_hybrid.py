"""Synthetic hybrid collector contracts; execute on GitHub Windows only.

Keep real source decoding, capture events, manifests and checkpoint reads. Only
browser navigation/DOM observation and financial network I/O are substituted.
"""
from copy import deepcopy
import hashlib
import inspect
import json
from pathlib import Path

import pytest

import coretax_browser as driver
import coretax_json as native
import test_browser_safety as protocol
import test_financial_export as financial
import test_json_adapter as corpus
import test_json_capture as network

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


def checkpoint_reader():
    parameter = inspect.signature(driver.read_detail_checkpoint).parameters.get('detail_source')
    assert parameter is not None, 'Missing checkpoint source validation: intentional feature RED'
    assert parameter.default == 'dom'
    return driver.read_detail_checkpoint


def source_fields(result):
    return [row for section in result['records'][0]['sections']
            for table in section.get('tables', []) for row in table['rows']]


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


def test_default_dom_does_not_enter_private_capture(tmp_path, monkeypatch):
    collector()
    case = Scenario(tmp_path, monkeypatch, mode='dom')
    result = driver.collect_details(case.page, case.run, tmp_path)
    assert result['complete'] is True
    assert result['records'][0]['sections'] == DOM_SECTIONS
    assert len(case.dom_calls) == 1
    assert not case.observation_calls
    assert not (tmp_path / 'returns' / 'json').exists()
    case.assert_closed()


@pytest.mark.parametrize('mode', ['', 'JSON-FIRST', 'json', ' dom ', None, True, 1, {}])
def test_invalid_collector_mode_precedes_directories_browser_and_run_mutation(tmp_path, mode):
    target = collector()
    run = {'npwp': corpus.NPWP, 'year': 2025, 'year_basis': 'period', 'records': []}
    original = deepcopy(run)
    folder = tmp_path / 'must-not-exist'
    class ForbiddenPage:
        def __getattribute__(self, key):
            raise AssertionError('Invalid mode reached browser access')
    with pytest.raises(ValueError):
        target(ForbiddenPage(), run, folder, detail_source=mode)
    assert not folder.exists() and run == original


def test_real_capture_and_decoder_supply_json_sections_without_dom_value_capture(tmp_path, monkeypatch):
    collector()
    case = Scenario(tmp_path, monkeypatch)
    from coretax_json_capture import DetailJsonCapture
    real_adapter, real_stream = native.adapt_corporate_detail, DetailJsonCapture.iter_bodies
    adapted, streams, packets = [], [], []
    def stream(capture, *args, **kwargs):
        streams.append(capture)
        for packet in real_stream(capture, *args, **kwargs):
            packets.append(packet['context']['sha256'])
            yield packet
    def adapt(bodies, record, scope, observed_forms):
        adapted.append((record, scope, deepcopy(observed_forms)))
        return real_adapter(bodies, record=record, scope=scope, observed_forms=observed_forms)
    monkeypatch.setattr(DetailJsonCapture, 'iter_bodies', stream)
    monkeypatch.setattr(native, 'adapt_corporate_detail', adapt)
    monkeypatch.setattr(driver, 'adapt_corporate_detail', adapt, raising=False)
    result = case.collect()
    assert len(streams) == 1 and len(adapted) == 1
    assert adapted[0] == (case.record, corpus.SCOPE, case.forms)
    assert packets == [hashlib.sha256(case.page.exchanges[0]['raw']).hexdigest()]
    assert result['complete'] is True and result['errors'] == []
    assert case.dom_calls == []
    assert case.observation_calls == [corpus.RECORD_ID]
    assert len(case.pdf_calls) == 1
    assert ['/MainFormData/NetIncomeBeforeTax', 'number', '123.4500'] in source_fields(result)
    mode = result['records'][0]['detail_source']
    assert mode['requested'] == 'json-first' and mode['used'] == 'json' and mode['version'] == 1
    capture = mode['capture']
    manifest = json.loads((tmp_path / capture['manifest']).read_text(encoding='utf-8'))
    assert capture['manifest_sha256'] == hashlib.sha256((tmp_path / capture['manifest']).read_bytes()).hexdigest()
    assert manifest['record_id'] == corpus.RECORD_ID and manifest['scope'] == corpus.SCOPE
    assert len(manifest['responses']) == 1 and case.page.body_responses[0].reads == 1
    assert (tmp_path / manifest['responses'][0]['relative_path']).read_bytes() == case.page.exchanges[0]['raw']
    case.assert_closed()


def test_incomplete_json_grid_falls_back_as_one_record_without_blocking_error(tmp_path, monkeypatch):
    collector()
    case = Scenario(tmp_path, monkeypatch)
    request = {'ReturnSheetRecordId': corpus.RECORD_ID, 'GroupType': 'Group 1',
               'First': 0, 'Rows': 10, 'SortField': '', 'SortOrder': 1, 'Filters': {}, 'LanguageId': 'id-ID'}
    endpoint = corpus.ORIGIN + '/returnsheet/api/loadcit/l9-table-1-grid'
    case.forms[0]['grids'] = [{'name': 'SYNTHETIC L9 GROUP', 'endpoint': endpoint,
                               'pages': [{'request_json': request, 'offset': 0}]}]
    raw = corpus.wire({'IsSuccessful': True, 'Payload': {
        'Data': [corpus.source_row() for _ in range(10)], 'TotalRecords': 60, 'Index': None}}).encode()
    case.page.exchanges.append({'url': endpoint, 'post': request, 'raw': raw})
    result = case.collect()
    assert result['complete'] is True and result['errors'] == []
    assert result['records'][0]['sections'] == DOM_SECTIONS
    assert len(case.dom_calls) == 1
    mode = result['records'][0]['detail_source']
    assert mode['used'] == 'dom' and 'incomplete_corporate_grid_source' in mode['reason']
    assert not any('/MainFormData/' in str(row) for row in source_fields(result))
    case.assert_closed()


def test_unknown_native_masa_retains_audited_whole_dom_fallback(tmp_path, monkeypatch):
    collector()
    case = Scenario(tmp_path, monkeypatch, tax_kind='PPN',
                    raw=b'{"IsSuccessful":true,"Payload":{"UnknownNativeMasa":[]}}')
    result = case.collect()
    assert result['complete'] is True and result['errors'] == []
    assert result['records'][0]['sections'] == DOM_SECTIONS and len(case.dom_calls) == 1
    mode = result['records'][0]['detail_source']
    assert mode['requested'] == 'json-first' and mode['used'] == 'dom' and mode['reason']
    assert case.pdf_calls == []
    case.assert_closed()


@pytest.mark.parametrize('failure', ['foreign_record', 'http401', 'http403', 'secret_body'])
def test_unsafe_source_never_uses_dom_or_publishes_complete(tmp_path, monkeypatch, failure):
    collector()
    form = corpus.current_form()
    status = 200
    if failure == 'foreign_record':
        form['ReturnSheetRecordIdentifier'] = corpus.FOREIGN_ID
    if failure == 'secret_body':
        form['MainFormData']['password'] = 'SYNTHETIC-NOT-A-CREDENTIAL'
    if failure.startswith('http'):
        status = int(failure[4:])
    case = Scenario(tmp_path, monkeypatch, raw=corpus.primary(form)['body'], status=status)
    with pytest.raises(native.JsonSafetyError):
        case.collect()
    assert case.dom_calls == [] and case.pdf_calls == []
    assert case.run['complete'] is False and not case.record.get('capture_complete')
    assert case.record.get('sections', []) == []
    case.assert_closed()


def test_stop_during_body_read_does_not_trigger_dom_and_releases_capture(tmp_path, monkeypatch):
    collector()
    case = Scenario(tmp_path, monkeypatch)
    case.cancel_on_body = True
    with pytest.raises(StopRequested):
        case.collect()
    assert case.dom_calls == [] and case.pdf_calls == []
    assert not case.record.get('capture_complete') and case.run['complete'] is False
    case.assert_closed()


def test_fresh_foreign_row_rejected_before_private_capture_or_view(tmp_path, monkeypatch):
    collector()
    case = Scenario(tmp_path, monkeypatch)
    case.page.rows[0]['TaxpayerAggregateIdentifier'] = corpus.FOREIGN_ID
    result = case.collect()
    assert result['complete'] is False and case.page.view_calls == 0
    assert case.dom_calls == [] and case.observation_calls == [] and case.pdf_calls == []
    assert not (tmp_path / 'returns' / 'json').exists()
    assert not any(case.page.context.listeners.values())


def test_json_eligibility_does_not_complete_a_failed_financial_download(tmp_path, monkeypatch):
    collector()
    case = Scenario(tmp_path, monkeypatch, financial_complete=False)
    result = case.collect()
    assert result['complete'] is False and result['errors']
    assert result['records'][0]['detail_source']['used'] == 'json'
    assert result['records'][0]['capture_complete'] is False
    assert result['records'][0]['attachments'][0]['status'] == 'PARTIAL'
    assert case.dom_calls == [] and len(case.pdf_calls) == 1
    assert ['/MainFormData/NetIncomeBeforeTax', 'number', '123.4500'] in source_fields(result)
    case.assert_closed()


@pytest.mark.parametrize('mutation', ['version', 'requested_mode', 'used_source', 'manifest_hash', 'body_bytes'])
def test_json_checkpoint_rejects_changed_source_descriptor_or_custody(tmp_path, monkeypatch, mutation):
    collector()
    reader = checkpoint_reader()
    case = Scenario(tmp_path, monkeypatch)
    result = case.collect()
    assert result['complete'] is True and result['records'][0]['detail_source']['used'] == 'json'
    checkpoint = tmp_path / 'returns' / '0001.json'
    saved = json.loads(checkpoint.read_text(encoding='utf-8'))
    mode = saved['detail_source']
    if mutation == 'version':
        mode['version'] = 999
    elif mutation == 'requested_mode':
        mode['requested'] = 'JSON-FIRST'
    elif mutation == 'used_source':
        mode['used'] = 'csv'
    elif mutation == 'manifest_hash':
        mode['capture']['manifest_sha256'] = '0' * 64
    else:
        manifest = json.loads((tmp_path / mode['capture']['manifest']).read_text())
        body = tmp_path / manifest['responses'][0]['relative_path']
        raw = body.read_bytes()
        changed = raw.replace(b'SYNTHETIC COMPANY', b'CHANGED!! COMPANY')
        assert len(changed) == len(raw) and changed != raw
        body.write_bytes(changed)
    checkpoint.write_text(json.dumps(saved), encoding='utf-8')
    with pytest.raises((native.JsonSafetyError, RuntimeError, ValueError)):
        reader(checkpoint, result['records'][0], corpus.SCOPE, detail_source='json-first')


def test_compatible_json_checkpoint_reuses_sections_without_new_browser_or_pdf(tmp_path, monkeypatch):
    collector()
    checkpoint_reader()
    case = Scenario(tmp_path, monkeypatch)
    result = case.collect()
    original_sections = deepcopy(result['records'][0]['sections'])
    checkpoint = tmp_path / 'returns' / '0001.json'
    saved_bytes = checkpoint.read_bytes()
    second = Scenario(tmp_path, monkeypatch)
    resumed = second.collect()
    assert resumed['complete'] is True and second.page.navigated == []
    assert second.dom_calls == second.pdf_calls == second.observation_calls == []
    assert resumed['records'][0]['sections'] == original_sections
    assert checkpoint.read_bytes() == saved_bytes


@pytest.mark.parametrize('mode', ['dom', 'json-first'])
def test_old_dom_checkpoint_remains_readable_and_is_not_relabelled_json(tmp_path, monkeypatch, mode):
    target = collector()
    reader = checkpoint_reader()
    monkeypatch.setattr(driver, 'wait_idle', lambda page: None)
    run = protocol.run_fixture()
    protocol.write_checkpoint(tmp_path, run['records'][0])
    path = tmp_path / 'returns' / '0001.json'
    original = path.read_bytes()
    page = protocol.SourcePage()
    result = target(page, run, tmp_path, detail_source=mode)
    assert result['complete'] is True and page.navigated == []
    assert result['records'][0]['sections'][0]['name'] == 'Synthetic saved section'
    assert path.read_bytes() == original
    saved = reader(path, run['records'][0], corpus.SCOPE, detail_source=mode)
    assert saved.get('detail_source', {}).get('used', 'dom') == 'dom'


@pytest.mark.parametrize('target', ['manifest', 'body'])
def test_capture_checkpoint_rejects_escape_before_reading_outside_path(tmp_path, monkeypatch, target):
    collector()
    reader = checkpoint_reader()
    case = Scenario(tmp_path, monkeypatch)
    assert case.collect()['complete'] is True
    checkpoint = tmp_path / 'returns' / '0001.json'
    saved = json.loads(checkpoint.read_text(encoding='utf-8'))
    descriptor = saved['detail_source']['capture']
    manifest_path = tmp_path / descriptor['manifest']
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    outside = tmp_path.parent / (tmp_path.name + '-outside-' + target + '.json')
    if target == 'manifest':
        outside.write_bytes(manifest_bytes)
        descriptor['manifest'] = '../' + outside.name
    else:
        outside.write_bytes((tmp_path / manifest['responses'][0]['relative_path']).read_bytes())
        manifest['responses'][0]['relative_path'] = '../' + outside.name
        changed = json.dumps(manifest).encode()
        manifest_path.write_bytes(changed)
        descriptor['manifest_sha256'] = hashlib.sha256(changed).hexdigest()
    checkpoint.write_text(json.dumps(saved), encoding='utf-8')
    import builtins
    import io
    import os
    from contextlib import contextmanager
    import coretax_json_capture as capture_module
    from spt_desktop import output_windows as custody
    accessed = []
    def guard(path):
        if isinstance(path, (str, bytes, os.PathLike)) and Path(os.fsdecode(path)).resolve() == outside.resolve():
            accessed.append(path)
            raise AssertionError('Checkpoint escaped the declared job directory')
    real_open, real_builtin, real_io, real_locked = Path.open, builtins.open, io.open, custody.locked_file
    def safe_open(path, *args, **kwargs):
        guard(path)
        return real_open(path, *args, **kwargs)
    def safe_builtin(path, *args, **kwargs):
        guard(path)
        return real_builtin(path, *args, **kwargs)
    def safe_io(path, *args, **kwargs):
        guard(path)
        return real_io(path, *args, **kwargs)
    @contextmanager
    def safe_locked(path, *args, **kwargs):
        guard(path)
        with real_locked(path, *args, **kwargs) as stream:
            yield stream
    monkeypatch.setattr(Path, 'open', safe_open)
    monkeypatch.setattr(builtins, 'open', safe_builtin)
    monkeypatch.setattr(io, 'open', safe_io)
    monkeypatch.setattr(custody, 'locked_file', safe_locked)
    monkeypatch.setattr(capture_module, 'locked_file', safe_locked)
    monkeypatch.setattr(driver, 'locked_file', safe_locked, raising=False)
    with pytest.raises((native.JsonSafetyError, RuntimeError, ValueError)):
        reader(checkpoint, case.record, corpus.SCOPE, detail_source='json-first')
    assert accessed == []


def test_interrupted_checkpoint_commit_preserves_previous_partial_bytes(tmp_path, monkeypatch):
    collector()
    checkpoint_reader()
    first = Scenario(tmp_path, monkeypatch, financial_complete=False)
    assert first.collect()['complete'] is False
    checkpoint = tmp_path / 'returns' / '0001.json'
    previous = checkpoint.read_bytes()
    retry = Scenario(tmp_path, monkeypatch)
    import os
    actual_replace = os.replace
    commits = []
    def replace(source, target, *args, **kwargs):
        if Path(target) == checkpoint:
            commits.append((source, target))
            raise OSError('SYNTHETIC CHECKPOINT COMMIT INTERRUPTION')
        return actual_replace(source, target, *args, **kwargs)
    monkeypatch.setattr(os, 'replace', replace)
    try:
        result = retry.collect()
    except OSError:
        assert retry.run['complete'] is False
    else:
        assert result['complete'] is False
    assert commits, 'Checkpoint was written without atomic publication'
    assert checkpoint.read_bytes() == previous
    assert not list(checkpoint.parent.glob('*.tmp'))
    retry.assert_closed()


def test_partial_json_financial_checkpoint_is_retried_and_not_stuck_partial(tmp_path, monkeypatch):
    collector()
    checkpoint_reader()
    first = Scenario(tmp_path, monkeypatch, financial_complete=False)
    initial = first.collect()
    assert initial['complete'] is False and initial['records'][0]['detail_source']['used'] == 'json'
    second = Scenario(tmp_path, monkeypatch)
    result = second.collect()
    assert result['complete'] is True and len(second.pdf_calls) == 1
    assert result['records'][0]['attachments'][0]['status'] == 'COMPLETE'
    item = result['records'][0]['attachments'][0]
    assert (tmp_path / item['relative_path']).read_bytes() == financial.PDF
    second.assert_closed()


@pytest.mark.parametrize('mutation', ['missing', 'same_size_changed'])
def test_complete_json_checkpoint_does_not_trust_pdf_metadata_without_intact_bytes(tmp_path, monkeypatch, mutation):
    collector()
    checkpoint_reader()
    first = Scenario(tmp_path, monkeypatch)
    result = first.collect()
    assert result['complete'] is True
    item = result['records'][0]['attachments'][0]
    pdf = tmp_path / item['relative_path']
    if mutation == 'missing':
        pdf.unlink()
    else:
        previous = pdf.read_bytes()
        changed = previous.replace(b'1 0 obj', b'9 0 obj')
        assert len(changed) == len(previous) and changed != previous
        pdf.write_bytes(changed)
    second = Scenario(tmp_path, monkeypatch)
    try:
        resumed = second.collect()
    except (native.JsonSafetyError, RuntimeError, ValueError):
        assert second.run['complete'] is False
    else:
        if resumed['complete']:
            assert len(second.pdf_calls) == 1, 'Unverified COMPLETE PDF metadata was reused'
            assert pdf.read_bytes() == financial.PDF
        else:
            assert resumed['errors']
    assert second.dom_calls == [], 'A PDF custody error cannot silently switch data source'



def test_later_unsafe_packet_is_not_hidden_by_an_earlier_safe_ineligible_packet(tmp_path, monkeypatch):
    collector()
    case = Scenario(tmp_path, monkeypatch, raw=b'{"IsSuccessful":true,"Payload":{}}')
    foreign = corpus.current_form()
    foreign['ReturnSheetRecordIdentifier'] = corpus.FOREIGN_ID
    case.page.exchanges.append({'raw': corpus.primary(foreign)['body'], 'url': corpus.PRIMARY_URL,
                                'post': deepcopy(PRIMARY_REQUEST)})
    with pytest.raises(native.JsonSafetyError):
        case.collect()
    assert case.run['complete'] is False and not case.record.get('capture_complete')
    assert case.dom_calls == [] and case.pdf_calls == []
    case.assert_closed()


def test_dom_request_does_not_silently_reuse_json_sections_from_a_different_mode(tmp_path, monkeypatch):
    collector()
    checkpoint_reader()
    first = Scenario(tmp_path, monkeypatch)
    assert first.collect()['complete'] is True
    second = Scenario(tmp_path, monkeypatch, mode='dom')
    try:
        result = second.collect()
    except (native.JsonSafetyError, RuntimeError, ValueError):
        assert second.run['complete'] is False
    else:
        assert result['complete'] is True
        assert len(second.dom_calls) == 1 and result['records'][0]['sections'] == DOM_SECTIONS
        assert result['records'][0]['detail_source']['used'] == 'dom'
