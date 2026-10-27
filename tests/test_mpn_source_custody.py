"""Source request admission uses synthetic bytes and protocol objects only."""
from types import SimpleNamespace
import hashlib
import json

import pytest

from coretax_mpn import MpnSafetyError, MpnUnsupported, ORIGIN
from coretax_mpn_ui import AccountingUI, REFERENCE_PATH
from test_mpn import scope_run
from test_mpn_browser import Page


def source_ui(tmp_path, monkeypatch):
    import coretax_mpn_ui as module
    page = Page()
    ui = AccountingUI(page, scope_run(), tmp_path)
    ui.observer.begin_navigation(ui.url)
    ui.observer.on_navigation(page.main_frame)
    raw = b'/* synthetic script */'
    path = '/accounting/id-ID/main.synthetic.js'
    monkeypatch.setattr(module, 'SOURCE_PINS', {path: hashlib.sha256(raw).hexdigest()})
    return ui, path, raw


@pytest.mark.parametrize('reference_type,kind,detail,number,expected', [
    ('Payment','OtherTaxReturn','DBP','0007','0007'),
    ('ICT_RCIT','OtherTaxReturn','DBP','0007','Tax Return Reference'),
    ('ICT_RCIT Replacement','OtherTaxReturn','DBP','0007','Tax Return Reference'),
    ('ICT_RCIT Replacement','TaxNotice','DBP','0007','0007'),
    ('ICT_RCIT','Adjustment','AIP','0007','0007'),
    (None,'OtherTaxReturn','DBP','0007',None),
    ('Payment',None,'DBP','0007',None),
    ('Payment','OtherTaxReturn','DBP',None,None)])
def test_parent_reference_caption_uses_pinned_defined_string_branch_without_raw_alias(
        reference_type,kind,detail,number,expected):
    from copy import deepcopy
    ui=AccountingUI.__new__(AccountingUI)
    header={'ReferenceType':reference_type,'AccountingTypeCode':kind,'AccountingTypeDetailCode':detail,
            'ReferenceNumber':number,'Reference':'SYNTHETIC RAW LINK FIELD'}
    before=deepcopy(header)
    assert ui._reference_caption(header)==expected
    assert header==before


@pytest.mark.parametrize('later', ['grid_failure', 'deadline'])
def test_grid_failure_cannot_mask_an_earlier_fatal_source_refusal(tmp_path, monkeypatch, later):
    ui, _, _ = source_ui(tmp_path, monkeypatch)
    ui._reject_source('ownership', safety=True, ownership_reason='page_route')
    if later == 'grid_failure':
        ui.observer._reject()
    else:
        ui.preparation_deadline = 0
    with pytest.raises(MpnSafetyError):
        ui._stop()
    ui.observer.close()


@pytest.mark.parametrize('stage', ['before', 'response', 'body'])
def test_grid_failure_during_original_source_read_is_not_an_identity_contradiction(tmp_path, monkeypatch, stage):
    from test_mpn_browser import Request, Response
    ui, path, raw = source_ui(tmp_path, monkeypatch)
    bad = Request(ui.page)
    ui.observer.on_request(bad)
    observed, reads = request(ui, path, raw)
    response = observed.response()
    def body():
        reads.append(True)
        ui.observer.on_response(Response(bad, status=403, html=True))
        return raw
    if stage == 'body':
        response.body = body
    def get_response():
        if stage == 'response':
            ui.observer.on_response(Response(bad, status=403, html=True))
        return response
    observed.response = get_response
    ui._source_request(observed)
    if stage == 'before':
        ui.observer.on_response(Response(bad, status=403, html=True))
    ui._source_finished(observed)
    with pytest.raises(MpnUnsupported):
        ui._stop()
    assert not ui.source_safety and ui.pins == {}
    assert len(reads) == (1 if stage == 'body' else 0)
    ui.observer.close()


@pytest.mark.parametrize('safety', [False, True])
def test_source_refusal_pumped_by_final_identity_rpc_prevents_actual_click(tmp_path, monkeypatch, safety):
    ui, _, _ = source_ui(tmp_path, monkeypatch)
    trials, actual = [], []
    class Control:
        def click(self, *, trial=False, timeout):
            (trials if trial else actual).append(True)
    handle = ui.page.handles[-1]
    original = handle.evaluate
    def evaluate(script):
        if trials:
            ui._reject_source('ownership' if safety else 'response', safety=safety,
                              ownership_reason='page_route' if safety else None)
        return original(script)
    handle.evaluate = evaluate
    with pytest.raises(MpnSafetyError if safety else MpnUnsupported):
        ui._click_ready(Control())
    assert trials and actual == []
    ui.observer.close()


@pytest.mark.parametrize('entry', ['action', 'wait', 'readiness'])
def test_combined_fatal_source_and_grid_failure_pumped_by_identity_rpc_stays_fatal(tmp_path, monkeypatch, entry):
    ui, _, _ = source_ui(tmp_path, monkeypatch)
    actual = []
    class Control:
        def click(self, **kwargs):
            if not kwargs.get('trial'):
                actual.append(True)
    handle = ui.page.handles[-1]
    original = handle.evaluate
    def evaluate(script):
        ui._reject_source('ownership', safety=True, ownership_reason='page_route')
        ui.observer._reject()
        return original(script)
    handle.evaluate = evaluate
    with pytest.raises(MpnSafetyError):
        if entry == 'action':
            ui._click_ready(Control())
        elif entry == 'wait':
            # The first search response wait is an observer RPC boundary too.
            ui._wait(0, 'list')
        else:
            ui._ready_one('synthetic')
    assert actual == []
    ui.observer.close()


@pytest.mark.parametrize('late', ['source_safety', 'document', 'grid_failure', 'pending', 'sequence', 'source_sequence'])
def test_final_provider_rpc_cannot_hide_owned_failure_or_late_evidence(tmp_path, monkeypatch, late):
    import coretax_mpn_ui as module
    ui, path, _ = source_ui(tmp_path, monkeypatch)
    clock = iter([10, 11])
    monkeypatch.setattr(module.time, 'monotonic', lambda: next(clock, 11))
    def evaluate(script):
        if late == 'source_safety':
            ui._reject_source('catalog_snapshot', safety=True)
        elif late == 'document':
            ui.observer._reject(safety=True)
        elif late == 'grid_failure':
            ui.observer._reject()
        elif late == 'pending':
            ui.source_pending[7] = object()
        elif late == 'sequence':
            ui.observer.sequence += 1
        else:
            ui.source_sequence += 1
        return [ORIGIN + path]
    ui.page.evaluate = evaluate
    with pytest.raises(MpnSafetyError if late in ('source_safety', 'document') else MpnUnsupported):
        ui.finish()
    ui.observer.close()


def request(ui, path, raw, *, method='GET', kind='script'):
    value = SimpleNamespace(url=ORIGIN + path, frame=ui.page.main_frame,
                            method=method, resource_type=kind)
    reads = []
    def body():
        reads.append(True)
        return raw
    value.response = lambda: SimpleNamespace(url=value.url, status=200,
                                             from_service_worker=False, body=body)
    return value, reads


@pytest.mark.parametrize('method,kind', [('GET', 'fetch'), ('HEAD', 'script'), ('POST', 'script')])
def test_nonqualifying_script_observations_neither_read_nor_establish_proof(tmp_path, monkeypatch, method, kind):
    ui, path, raw = source_ui(tmp_path, monkeypatch)
    observed, reads = request(ui, path, raw, method=method, kind=kind)
    ui._source_request(observed)
    assert not ui.source_pending, 'Nonqualifying script observation was admitted'
    ui._source_finished(observed)
    ui._stop()
    assert reads == [] and ui.pins == {} and ui.source_sequence == 0


@pytest.mark.parametrize('method,kind', [('POST', 'xhr'), ('HEAD', 'fetch'), ('GET', 'script')])
def test_nonqualifying_reference_observations_are_ignored(tmp_path, monkeypatch, method, kind):
    ui, _, _ = source_ui(tmp_path, monkeypatch)
    observed, reads = request(ui, REFERENCE_PATH, b'{}', method=method, kind=kind)
    ui._source_request(observed)
    assert not ui.source_pending, 'Nonqualifying reference observation was admitted'
    ui._source_finished(observed)
    ui._stop()
    assert reads == [] and ui.reference_raw is None


def test_actual_reviewed_get_script_establishes_original_byte_proof(tmp_path, monkeypatch):
    ui, path, raw = source_ui(tmp_path, monkeypatch)
    observed, reads = request(ui, path, raw)
    ui._source_request(observed)
    ui._source_finished(observed)
    ui._stop()
    assert reads == [True] and ui.pins == {path: hashlib.sha256(raw).hexdigest()}


@pytest.mark.parametrize('kind', ['xhr', 'fetch'])
def test_exact_get_reference_still_binds_original_bytes_and_reviewed_catalogs(tmp_path, monkeypatch, kind):
    ui, _, _ = source_ui(tmp_path, monkeypatch)
    raw = json.dumps({'IsSuccessful': True, 'Payload': [
        {'ReferenceDataType': name, 'Checksum': 'synthetic-version', 'Details': []}
        for name in ('ACCOUNTING_TYPE', 'ACCOUNTING_TYPE_DETAIL',
                     'REVENUE_CHART_OF_ACCOUNTS_6_DIGITS_SEGMENT', 'PERIOD')]}).encode()
    observed, reads = request(ui, REFERENCE_PATH, raw, kind=kind)
    ui._source_request(observed)
    ui._source_finished(observed)
    ui._stop()
    assert reads == [True] and ui.reference_raw == raw
    assert len(ui.catalogs) == 4 and ui.catalog == {}
    changed, _ = request(ui, REFERENCE_PATH, raw + b' ', kind=kind)
    ui._source_request(changed)
    ui._source_finished(changed)
    with pytest.raises(MpnSafetyError):
        ui._stop()


@pytest.mark.parametrize('field,value', [('method', 'POST'), ('resource_type', 'fetch'),
                                        ('url', ORIGIN + '/accounting/id-ID/vendor.other.js')])
def test_changed_admitted_request_is_fatal_before_body_access(tmp_path, monkeypatch, field, value):
    ui, path, raw = source_ui(tmp_path, monkeypatch)
    observed, reads = request(ui, path, raw)
    ui._source_request(observed)
    setattr(observed, field, value)
    ui._source_finished(observed)
    with pytest.raises(MpnSafetyError):
        ui._stop()
    assert reads == []


def test_later_unknown_script_cannot_clear_an_existing_fatal_refusal(tmp_path, monkeypatch):
    ui, path, raw = source_ui(tmp_path, monkeypatch)
    observed, _ = request(ui, path, raw)
    ui._source_request(observed)
    observed.method = 'POST'
    ui._source_finished(observed)
    unknown, _ = request(ui, '/accounting/id-ID/main.unknown.js', raw)
    ui._source_request(unknown)
    with pytest.raises(MpnSafetyError):
        ui._stop()


def test_first_source_rejection_is_recorded_once_without_retained_exception(tmp_path, monkeypatch):
    from spt_desktop import diagnostics as d
    from test_diagnostics import records
    ui, path, raw = source_ui(tmp_path, monkeypatch)
    observed, _ = request(ui, path, raw)
    with d.session(tmp_path, 'worker') as log:
        ui._source_request(observed)
        observed.method = 'POST'
        ui._source_finished(observed)
        unknown, _ = request(ui, '/accounting/id-ID/main.unknown.js', raw)
        ui._source_request(unknown)
        assert log.flush()
    events = [r for r in records(tmp_path) if r['event'] == 'mpn.source_rejected']
    assert len(events) == 1, 'Original callback rejection is missing or replaced'
    assert events[0]['mpn_source_stage'] == 'ownership'
    assert events[0]['error']['type'] == 'MpnSafetyError'
    assert not any(isinstance(v, BaseException) for v in vars(ui).values())


def test_unsupported_script_digest_remains_partial_not_identity_failure(tmp_path, monkeypatch):
    ui, path, _ = source_ui(tmp_path, monkeypatch)
    observed, _ = request(ui, path, b'/* synthetic changed source */')
    ui._source_request(observed)
    ui._source_finished(observed)
    with pytest.raises(MpnUnsupported):
        ui._stop()
    assert ui.pins == {}


@pytest.mark.parametrize('reason', [
    'navigation', 'frame', 'method', 'page_route', 'request_url', 'resource_kind',
])
def test_ownership_refusal_identifies_failed_predicate_before_reading_response(tmp_path, monkeypatch, reason):
    from spt_desktop import diagnostics as d
    from test_diagnostics import records
    ui, path, raw = source_ui(tmp_path, monkeypatch)
    observed, reads = request(ui, path, raw)
    ui._source_request(observed)
    if reason == 'navigation':
        ui.observer.committed = False
    elif reason == 'frame':
        observed.frame = SimpleNamespace()
    elif reason == 'method':
        observed.method = 'POST'
    elif reason == 'page_route':
        ui.page.url += '?synthetic=changed'
    elif reason == 'request_url':
        observed.url += '?synthetic=changed'
    else:
        observed.resource_type = 'fetch'

    def response():
        pytest.fail('A refused source request must not acquire a response')
    observed.response = response
    with d.session(tmp_path, 'worker') as log:
        ui._source_finished(observed)
        with pytest.raises(MpnSafetyError):
            ui._stop()
        assert log.flush()
    event, = [r for r in records(tmp_path) if r['event'] == 'mpn.source_rejected']
    assert event.get('mpn_ownership_reason') == reason, 'Exact failed ownership predicate is missing'
    assert event['mpn_source_stage'] == 'ownership'
    assert event['error']['type'] == 'MpnSafetyError'
    assert reads == [] and ui.pins == {} and not ui.source_pending


@pytest.mark.parametrize('first', [
    'navigation', 'frame', 'method', 'page_route', 'request_url', 'resource_kind',
])
def test_multiple_ownership_conflicts_keep_original_short_circuit_and_first_event(tmp_path, monkeypatch, first):
    from spt_desktop import diagnostics as d
    from test_diagnostics import records
    ui, path, raw = source_ui(tmp_path, monkeypatch)
    original, reads = request(ui, path, raw)
    class GuardedRequest(SimpleNamespace):
        def __getattribute__(self, name):
            if name in object.__getattribute__(self, 'forbidden'):
                pytest.fail('Ownership guard read a later predicate')
            return super().__getattribute__(name)
    observed = GuardedRequest(**vars(original), forbidden=set())
    ui._source_request(observed)
    order = ['navigation', 'frame', 'method', 'page_route', 'request_url', 'resource_kind']
    conflicts = set(order[order.index(first):])
    if 'navigation' in conflicts:
        ui.observer.committed = False
    if 'frame' in conflicts:
        observed.frame = SimpleNamespace()
    if 'method' in conflicts:
        observed.method = 'POST'
    if 'page_route' in conflicts:
        ui.page.url += '?synthetic=changed'
    if 'request_url' in conflicts:
        observed.url += '?synthetic=changed'
    if 'resource_kind' in conflicts:
        observed.resource_type = 'fetch'
    observed.forbidden = {field for reason, field in [
        ('frame', 'frame'), ('method', 'method'), ('resource_kind', 'resource_type')]
        if order.index(reason) > order.index(first)}
    if order.index(first) < order.index('page_route'):
        def later_route(page):
            pytest.fail('Ownership guard read the later page route')
        monkeypatch.setattr(type(ui.page), 'url', property(later_route), raising=False)
    with d.session(tmp_path, 'worker') as log:
        ui._source_finished(observed)
        ui._reject_source('provider')
        with pytest.raises(MpnSafetyError):
            ui._stop()
        assert log.flush()
    event, = [r for r in records(tmp_path) if r['event'] == 'mpn.source_rejected']
    assert event.get('mpn_ownership_reason') == first
    assert event['mpn_source_stage'] == 'ownership' and reads == []


def test_earlier_nonownership_event_stays_first_when_later_ownership_failure_becomes_fatal(tmp_path, monkeypatch):
    from spt_desktop import diagnostics as d
    from test_diagnostics import records
    ui, path, raw = source_ui(tmp_path, monkeypatch)
    observed, reads = request(ui, path, raw)
    with d.session(tmp_path, 'worker') as log:
        ui._reject_source('pending_budget')
        ui._source_request(observed)
        observed.method = 'POST'
        ui._source_finished(observed)
        with pytest.raises(MpnSafetyError):
            ui._stop()
        assert log.flush()
    event, = [r for r in records(tmp_path) if r['event'] == 'mpn.source_rejected']
    assert event['mpn_source_stage'] == 'pending_budget'
    assert 'mpn_ownership_reason' not in event and reads == []


def test_nonownership_source_refusal_has_no_ownership_reason(tmp_path, monkeypatch):
    from spt_desktop import diagnostics as d
    from test_diagnostics import records
    ui, path, _ = source_ui(tmp_path, monkeypatch)
    observed, _ = request(ui, path, b'/* synthetic changed source */')
    with d.session(tmp_path, 'worker') as log:
        ui._source_request(observed)
        ui._source_finished(observed)
        assert log.flush()
    event, = [r for r in records(tmp_path) if r['event'] == 'mpn.source_rejected']
    assert event['mpn_source_stage'] == 'script_digest'
    assert 'mpn_ownership_reason' not in event
    with pytest.raises(MpnUnsupported):
        ui._stop()
