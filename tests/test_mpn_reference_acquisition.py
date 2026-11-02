"""Synthetic bounded adapter GET; no live records or authentication material."""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest
from playwright.sync_api import Error as PlaywrightError

from coretax_mpn import MpnSafetyError, MpnUnsupported, ORIGIN, require_mpn, validate_mpn
from coretax_mpn_ui import AccountingUI, REFERENCE_PATH, SOURCE_PINS
from test_mpn import scope_run, payment_source
from test_mpn_capture_protocol import snapshot
from test_mpn_parent_binding_diagnostics import InspectedControls, COLUMNS


def catalog_bytes():
    groups = []
    for name, code, label in (
            ('ACCOUNTING_TYPE', 'OtherTaxReturn', 'Synthetic accounting label'),
            ('ACCOUNTING_TYPE_DETAIL', 'DBP', 'Synthetic detail label'),
            ('REVENUE_CHART_OF_ACCOUNTS_6_DIGITS_SEGMENT', '411211', 'Synthetic revenue label'),
            ('PERIOD', '01012026', 'Synthetic period label')):
        groups.append({'ReferenceDataType': name, 'Checksum': 'SYNTHETIC-V1',
                       'Details': [{'Code': code, 'CodeDescription': label,
                                    'AppLanguageId': 'id-ID', 'ValidTo': None}]})
    return json.dumps({'IsSuccessful': True, 'Payload': groups}).encode()


def acquisition_ui():
    ui = AccountingUI.__new__(AccountingUI)
    header, _ = payment_source()
    header.update(AccountingTypeCode='OtherTaxReturn', AccountingTypeDetailCode='DBP',
                  CurrencyCode='IDR', RevenueCode='411211', PaymentCode='100',
                  TransactionNumber='SYNTHETIC-TRANSACTION')
    ui.run = scope_run()
    ui.taxpayer = header['TaxpayerAggregateIdentifier']
    ui.url = ORIGIN + '/accounting/id-ID/balancesheet/' + ui.taxpayer
    ui.list_snapshot = snapshot([header])
    ui.observer = SimpleNamespace(latest={'list': ui.list_snapshot}, committed=True,
        _navigation_attempt=object(), _document=object(), _binding_document=False,
        safety_failed=False, failed=False, closed=False)
    ui.closed = ui.source_failed = ui.source_safety = ui.source_rejection_recorded = False
    ui.check_cancel = None
    ui.source_pending, ui.source_ready = {}, {}
    ui.source_sequence = 0
    ui.catalogs, ui.catalog_codes, ui.catalog = {}, {}, {}
    ui.reference_raw = ui.reference_origin = None
    ui.reference_acquisition_attempted = False
    ui.catalog_frozen = False
    ui.pins = deepcopy(SOURCE_PINS)
    ui.preparation_deadline = None
    ui._owned = lambda: ui._stop()
    ui._state = lambda **kwargs: ui._stop()
    calls, rpc, disposed = [], [], []
    raw = catalog_bytes()
    response = SimpleNamespace(status=200, url=ORIGIN + REFERENCE_PATH,
                               body=lambda: raw, dispose=lambda: disposed.append(True))
    def get(url, **kwargs):
        calls.append((url, kwargs))
        return response
    def evaluate(expression, document, **kwargs):
        rpc.append(kwargs)
        return {'same': document is ui.observer._document,
                'scripts': [ORIGIN + path for path in SOURCE_PINS]}
    context = SimpleNamespace(_spt_financial_route_policy='service_workers_blocked',
                              request=SimpleNamespace(get=get))
    ui.page = SimpleNamespace(context=context, url=ui.url,
                              locator=lambda _: SimpleNamespace(evaluate=evaluate))
    ui.list_owner = InspectedControls()
    expected = list(ui._header_projection(header))
    expected[0:2] = ['Synthetic accounting label', 'Synthetic detail label']
    expected[5] = 'Synthetic period label'
    rendered = [''] * 24
    for column, value in zip(COLUMNS, expected):
        rendered[column] = value
    ui._table = lambda *args: (None, [rendered])
    return ui, header, rendered, calls, rpc, response, disposed


def test_warm_cache_missing_packet_acquires_once_before_strict_parent_binding():
    ui, header, _, calls, rpc, _, disposed = acquisition_ui()
    ui._prepare_header_catalog(header)
    assert ui._bind_header(header) is ui.list_owner
    ui._prepare_header_catalog(header)
    assert len(calls) == 1 and calls[0][0] == ORIGIN + REFERENCE_PATH
    assert calls[0][1]['max_redirects'] == calls[0][1]['max_retries'] == 0
    assert 0 < calls[0][1]['timeout'] <= 5000
    assert not {'headers', 'data', 'params', 'form'} & calls[0][1].keys()
    assert all(0 < item['timeout'] <= 1000 for item in rpc)
    assert ui.reference_raw == catalog_bytes()
    assert ui.reference_origin == 'adapter-get-v1' and disposed == [True]


@pytest.mark.parametrize('case', ['raw_match', 'existing_catalog', 'currency', 'known_label'])
def test_no_unnecessary_get_or_fetch_to_repair_known_contradiction(case):
    ui, header, rendered, calls, _, _, _ = acquisition_ui()
    if case == 'raw_match':
        for column, value in zip(COLUMNS, ui._header_projection(header)):
            rendered[column] = value
    elif case in ('existing_catalog', 'known_label'):
        ui.reference_raw = catalog_bytes()
        ui._catalog(ui.reference_raw)
        if case == 'known_label':
            rendered[3] = 'SYNTHETIC CONTRADICTION'
    else:
        rendered[5] = 'SYNTHETIC OTHER CURRENCY'
    ui._prepare_header_catalog(header)
    assert calls == []
    if case in ('currency', 'known_label'):
        with pytest.raises(MpnSafetyError):
            ui._bind_header(header)


@pytest.mark.parametrize('case', ['context', 'pins', 'attempt', 'document', 'route', 'query',
                                  'scope', 'changed_list', 'pending', 'closed', 'source_safety'])
def test_acquisition_refuses_unproved_owner_before_transport(case):
    ui, _, _, calls, _, _, _ = acquisition_ui()
    if case == 'context':
        ui.page.context._spt_financial_route_policy = None
    elif case == 'pins':
        ui.pins = {}
    elif case == 'attempt':
        ui.observer._navigation_attempt = None
    elif case == 'document':
        ui.observer._document = None
    elif case == 'route':
        ui.page.url += '#changed'
    elif case == 'query':
        ui.list_snapshot['request']['Filters'] = []
    elif case == 'scope':
        ui.list_snapshot['request']['TaxpayerAggregateIdentifier'] = 'SYNTHETIC-OTHER'
    elif case == 'changed_list':
        ui.observer.latest['list'] = {'sequence': 99}
    elif case == 'pending':
        ui.source_pending[1] = object()
    elif case == 'closed':
        ui.closed = True
    else:
        ui.source_safety = True
    with pytest.raises((MpnUnsupported, MpnSafetyError)):
        ui._acquire_reference(ui.list_snapshot)
    assert not calls


@pytest.mark.parametrize('case', ['redirect', 'status', 'oversize', 'malformed', 'envelope', 'locale'])
def test_unavailable_or_unsupported_acquisition_authorizes_no_binding(case):
    ui, header, _, calls, _, response, disposed = acquisition_ui()
    error = MpnUnsupported
    if case == 'redirect':
        response.status = 302
        response.url += '/other'
    elif case == 'status':
        response.status = 503
    elif case == 'oversize':
        response.body = lambda: b' ' * (8 * 1024 * 1024 + 1)
    elif case == 'malformed':
        response.body = lambda: b'{'
    elif case == 'envelope':
        response.body = lambda: b'{"IsSuccessful":false,"Payload":[]}'
    else:
        response.body = lambda: catalog_bytes().replace(b'id-ID', b'en-US')
        error = MpnSafetyError
    with pytest.raises(error):
        ui._prepare_header_catalog(header)
    assert len(calls) == 1 and disposed == [True]
    assert ui.reference_raw is None
    with pytest.raises(MpnUnsupported):
        ui._acquire_reference(ui.list_snapshot)
    assert len(calls) == 1


@pytest.mark.parametrize('stage', ['transport', 'body', 'dispose'])
@pytest.mark.parametrize('terminal', ['stop', 'safety'])
def test_callback_terminal_state_wins_on_exceptional_rpc_exit(stage, terminal):
    ui, _, _, calls, _, response, _ = acquisition_ui()
    def cancelled():
        raise KeyboardInterrupt
    def fail(*args, **kwargs):
        if terminal == 'stop':
            ui.check_cancel = cancelled
        else:
            ui.source_safety = True
        raise PlaywrightError('SYNTHETIC TRANSPORT FAILURE')
    if stage == 'transport':
        ui.page.context.request.get = fail
    elif stage == 'body':
        response.body = fail
    else:
        response.dispose = fail
    with pytest.raises(KeyboardInterrupt if terminal == 'stop' else MpnSafetyError):
        ui._acquire_reference(ui.list_snapshot)
    assert len(calls) <= 1


@pytest.mark.parametrize('origin', [None, 'observed-get-v1', 'adapter-get-v1'])
def test_catalog_origin_allows_explicit_and_legacy_private_descriptors(origin):
    run = scope_run()
    value = require_mpn(run, 'dom')
    value['bindings'] = [{'path': 'SYNTHETIC', 'kind': 'catalog'}]
    if origin is not None:
        value['bindings'][0]['origin'] = origin
    validate_mpn(run)


@pytest.mark.parametrize('kind,origin', [('catalog', 'other'), ('catalog', None),
                                        ('catalog', {}), ('list', 'adapter-get-v1')])
def test_unknown_explicit_origin_or_origin_on_grid_is_refused(kind, origin):
    run = scope_run()
    value = require_mpn(run, 'dom')
    value['bindings'] = [{'path': 'SYNTHETIC', 'kind': kind, 'origin': origin}]
    with pytest.raises(MpnSafetyError, match='origin'):
        validate_mpn(run)
