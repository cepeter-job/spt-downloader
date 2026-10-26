"""Collector orchestration uses synthetic UI snapshots, independent of browser tests."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

import pytest

from coretax_mpn import decode_mpn, MpnUnsupported, MpnSafetyError, require_mpn
from test_mpn import scope_run, payment_source, HEADER, DETAIL


def snapshot(rows, *, kind='list', first=0, total=None, parent=None):
    # Encode numeric markers as original numeric literals, including their scale.
    from coretax_mpn import MpnNumber
    def wire(value):
        if type(value) is MpnNumber:
            return str(value)
        if isinstance(value, dict):
            return '{' + ','.join(json.dumps(k) + ':' + wire(v) for k, v in value.items()) + '}'
        if isinstance(value, list):
            return '[' + ','.join(map(wire, value)) + ']'
        return json.dumps(value)
    total = len(rows) if total is None else total
    raw = wire({'IsSuccessful': True, 'Payload': {'TotalRecords': total, 'Data': rows}}).encode()
    data = decode_mpn(raw)['Payload']['Data']
    request = {'First': first, 'Rows': 10, 'SortField': 'PostingDate' if kind == 'list' else 'TransactionDate',
               'SortOrder': -1, 'LanguageId': 'en-US', 'Filters': [] if kind == 'detail' else
               [{'PropertyName': 'IsCancelled', 'Value': '0', 'MatchMode': 'equals'}]}
    from test_mpn import TAXPAYER
    request['TaxpayerAggregateIdentifier' if kind == 'list' else 'RecordId'] = TAXPAYER if kind == 'list' else parent
    return {'kind': kind, 'rows': data, 'raw': raw, 'total': total,
            'first': first, 'page_size': 10, 'sequence': first + 1, 'parent_id': parent, 'request': request}


class SyntheticUI:
    headers = []
    children = {}
    dom = None
    failure = None

    def __init__(self, page, run, folder, *, check_cancel=None):
        self.check_cancel = check_cancel
        self.opened = []
        self.closed = False
        self.pins = {'main': 'synthetic-main', 'vendor': 'synthetic-vendor'}
        self.catalog = {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True

    def open(self):
        if self.failure:
            raise self.failure('Synthetic UI refusal')

    def list_pages(self, max_pages):
        if self.check_cancel:
            self.check_cancel()
        yield snapshot(deepcopy(self.headers))

    def detail_pages(self, header, max_pages):
        self.opened.append(header['RecordId'])
        rows = deepcopy(self.children[header['RecordId']])
        yield snapshot(rows, kind='detail', parent=header['RecordId']), deepcopy(self.dom)

    def finish(self):
        if self.check_cancel:
            self.check_cancel()


def prepare(monkeypatch, *, dom=None, duplicate=False):
    import coretax_mpn_browser as browser
    header, detail = payment_source(amount='-1250.501')
    # A zero-valued, later-year header still owns the selected-year payment.
    header.update(Amount=decode_mpn(b'{"n":0}')['n'], PeriodCode='01012026')
    positive = deepcopy(detail)
    positive.update(RecordId='00000000-0000-4000-8000-000000000004',
                    Amount=decode_mpn(b'{"n":40}')['n'])
    class UI(SyntheticUI):
        headers = [header]
        children = {HEADER: [positive, detail, deepcopy(detail)] if duplicate else [positive, detail]}
    UI.dom = dom
    instances = []
    def make(*args, **kwargs):
        ui = UI(*args, **kwargs)
        instances.append(ui)
        return ui
    monkeypatch.setattr(browser, 'AccountingUI', make, raising=False)
    return browser, instances


def test_all_zero_later_year_headers_are_inspected_and_raw_bytes_stay_private(monkeypatch, tmp_path):
    browser, instances = prepare(monkeypatch)
    run = scope_run()
    require_mpn(run, 'dom')
    run['complete'] = True  # The preceding SPT detail component has completed.
    browser.collect_mpn(object(), run, tmp_path)
    assert run['complete'] and run['mpn']['status'] == 'COMPLETE'
    assert instances[0].opened == [HEADER] and instances[0].closed
    assert run['mpn']['headers'] == 1 and run['mpn']['details'] == 2
    assert [row['record_id'] for row in run['mpn']['rows']] == [DETAIL]
    assert run['mpn']['rows'][0]['amount'] == '-1250.501'
    assert len(run['mpn']['evidence']) == 2
    for item in run['mpn']['evidence']:
        raw = (tmp_path / item['path']).read_bytes()
        assert len(raw) == item['bytes'] and hashlib.sha256(raw).hexdigest() == item['sha256']
    assert (tmp_path / 'run.json').is_file()
    assert not (tmp_path / 'json').exists()


def test_complete_dom_detail_requires_all_numbers_then_falls_back_as_a_whole(monkeypatch, tmp_path):
    # A partial DOM page cannot be spliced with the second source row.
    browser, _ = prepare(monkeypatch, dom=[['synthetic partial DOM']])
    run = scope_run()
    browser.collect_mpn(object(), run, tmp_path)
    assert run['mpn']['rows'][0]['source'] == 'json'
    assert run['mpn']['status'] == 'COMPLETE'


def test_exact_transport_duplicates_are_coalesced_with_occurrences_retained(monkeypatch, tmp_path):
    browser, _ = prepare(monkeypatch, duplicate=True)
    run = scope_run()
    browser.collect_mpn(object(), run, tmp_path)
    assert len(run['mpn']['rows']) == 1
    occurrence = next(item for item in run['mpn']['provenance'] if item['record_id'] == DETAIL)
    assert len(occurrence['occurrences']) == 2


def test_changed_duplicate_detail_is_fatal_before_completion(monkeypatch, tmp_path):
    browser, instances = prepare(monkeypatch, duplicate=True)
    original = browser.AccountingUI
    def make(*args, **kwargs):
        ui = original(*args, **kwargs)
        ui.children = deepcopy(ui.children)
        ui.children[HEADER][-1]['ReferenceNumber'] = 'SYNTHETIC CHANGED'
        return ui
    monkeypatch.setattr(browser, 'AccountingUI', make)
    run = scope_run()
    with pytest.raises(MpnSafetyError):
        browser.collect_mpn(object(), run, tmp_path)
    assert not run['complete'] and run['mpn']['status'] != 'COMPLETE'
    assert instances[0].closed


def test_recoverable_mpn_refusal_keeps_spt_records_and_partial_state(monkeypatch, tmp_path):
    browser, _ = prepare(monkeypatch)
    class Refused(SyntheticUI):
        failure = MpnUnsupported
    monkeypatch.setattr(browser, 'AccountingUI', Refused)
    run = scope_run()
    run['records'] = [{'record_id': 'synthetic-preserved'}]
    before = deepcopy(run['records'])
    browser.collect_mpn(object(), run, tmp_path)
    assert run['records'] == before and not run['complete']
    assert run['mpn']['status'] == 'PARTIAL'
    assert run['mpn']['audit'] and (tmp_path / 'run.json').is_file()


def test_stop_precedes_every_mpn_browser_action_and_no_checkpoint_is_created(tmp_path):
    import coretax_mpn_browser as browser
    from coretax_browser import CaptureCancelled
    def stop():
        raise CaptureCancelled('Synthetic Stop')
    with pytest.raises(CaptureCancelled):
        browser.collect_mpn(object(), scope_run(), tmp_path, check_cancel=stop)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('field,value', [('amount', '-17'), ('reference', 'SYNTHETIC MUTATION'),
                                         ('period_code', '02022025')])
def test_canonical_rows_must_reconcile_to_held_original_evidence(monkeypatch, tmp_path, field, value):
    from coretax_mpn import mpn_custody
    browser, _ = prepare(monkeypatch)
    run = scope_run()
    browser.collect_mpn(object(), run, tmp_path)
    run['mpn']['rows'][0][field] = value
    if field == 'period_code':
        run['mpn']['rows'][0]['period_label'] = value
    with pytest.raises(MpnSafetyError):
        with mpn_custody(run, tmp_path):
            pass


def test_case_alias_private_evidence_is_refused_before_reading(monkeypatch, tmp_path):
    from coretax_mpn import mpn_custody
    browser, _ = prepare(monkeypatch)
    run = scope_run()
    browser.collect_mpn(object(), run, tmp_path)
    (tmp_path / 'mpn').rename(tmp_path / 'MPN')
    with pytest.raises(MpnSafetyError):
        with mpn_custody(run, tmp_path):
            pass


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows native deny-write sharing')
def test_original_mpn_reader_denies_mutation_during_custody(monkeypatch, tmp_path):
    from coretax_mpn import mpn_custody
    browser, _ = prepare(monkeypatch)
    run = scope_run()
    browser.collect_mpn(object(), run, tmp_path)
    path = tmp_path / run['mpn']['evidence'][0]['path']
    with mpn_custody(run, tmp_path):
        with pytest.raises(OSError):
            with path.open('wb') as stream:
                stream.write(b'{}')


def test_identical_dom_rows_with_different_hidden_periods_require_whole_json_fallback(monkeypatch, tmp_path):
    browser, _ = prepare(monkeypatch)
    original = browser.AccountingUI
    def make(*args, **kwargs):
        ui = original(*args, **kwargs)
        row = deepcopy(ui.children[HEADER][-1])
        other = deepcopy(row)
        other.update(RecordId='00000000-0000-4000-8000-000000000005', PeriodCode='01012024')
        ui.children = {HEADER: [row, other]}
        visible = ['01-02-2026', '01-02-2026', '0000000000000007', 'OtherTaxReturn',
                   'DBP', '-1.250,501', '1,00', '-1.250,501', '=SYNTHETIC-REFERENCE']
        ui.dom = [visible, deepcopy(visible)]
        return ui
    monkeypatch.setattr(browser, 'AccountingUI', make)
    run = scope_run()
    browser.collect_mpn(object(), run, tmp_path)
    assert len(run['mpn']['rows']) == 1 and run['mpn']['rows'][0]['source'] == 'json'


def test_complete_capture_cannot_drop_original_negative_rows_from_its_proof(monkeypatch, tmp_path):
    from coretax_mpn import mpn_custody
    browser, _ = prepare(monkeypatch)
    run = scope_run()
    browser.collect_mpn(object(), run, tmp_path)
    run['mpn']['rows'] = []
    run['mpn']['provenance'] = []
    with pytest.raises(MpnSafetyError):
        with mpn_custody(run, tmp_path):
            pass
