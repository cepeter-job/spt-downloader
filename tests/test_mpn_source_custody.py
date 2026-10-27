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
