"""Strict synthetic raw-negative admission; new slices are source-only RED until CI."""
from copy import deepcopy
import json

import pytest

from coretax_json import JsonSafetyError, adapt_corporate_detail
import coretax_corporate_projection as projection
import support_json_corpus as corpus
from test_corporate_l7_native import selected, envelope, bindings, packet, FRAME, PINS
from test_corporate_l7_projection import ROOT, BODY, SUFFIXES

ROUTE = FRAME + '?view=true'
CHAIN = ['rshshr-corporate-income-tax-return', 'rshshr-citr-l7-form',
         'rsh-citr-l7-grid1', 'p-table', 'table']
NEGATIVE_PINS = {**PINS, projection.VENDOR_SOURCE: 'd' * 64}


def lifetime(attempt='a' * 32, *, record_id=corpus.RECORD_ID,
             source_url=corpus.LIST_URL, detail_url=ROUTE):
    return {'kind': 'corporate-l7-spa-v1', 'attempt': attempt,
            'record_id': record_id, 'source_url': source_url, 'detail_url': detail_url,
            **dict.fromkeys(('fresh_root', 'fresh_l7', 'stable_root', 'stable_form',
                             'stable_grid', 'stable_table', 'enabled_boundaries'), True)}


def component(fact):
    return {key: value for key, value in fact.items() if key in
            ('attempt', 'record_id', 'source_url', 'detail_url')} | {
                'kind': 'corporate-submitted-spa-v1', 'transition_count': 1,
                'same_document': True, 'source_owner': True, 'detail_owner': True}


def negative_envelope():
    value = envelope()
    current = corpus.current_form()
    current['MainFormData'].update(NetIncomeBeforeTax=corpus.Number('-1234'),
        TaxYear=corpus.Number('2025'), IsIncomeUnder=corpus.Number('0'),
        IsIncomeSolely=None, IsCarriedForward=corpus.Number('1'))
    from test_corporate_l7_projection import raw_source
    current[ROOT] = raw_source()
    current[ROOT][BODY][1]['FiscalNetProfitIncome'] = corpus.Number('-1234')
    value['Payload']['CurrentFormData'] = corpus.wire(current)
    return value


def offer(observed=None, *, pins=None):
    observed = bindings() if observed is None else observed
    proof = observed[1]['projection']
    proof['route'] = ROUTE
    observed[1]['raw_negative_projection'] = {
        **deepcopy(proof), 'kind': 'corporate-l7-stable-negative-v1',
        'builds': dict(NEGATIVE_PINS if pins is None else pins),
        'timezone': 'Asia/Jakarta', 'visibility_binding': 'current-induk-enabled-v1'}
    observed[1]['raw_negative_projection']['tables'][0]['owner_chain'] = list(CHAIN)
    return observed


def negative_packet(value=None):
    raw = packet(negative_envelope() if value is None else value)
    ctx = raw['context']
    ctx['frame_url'] = ROUTE
    ctx['corporate_l7_lifetime'] = lifetime(ctx['attempt'])
    ctx['component_lifetime'] = component(ctx['corporate_l7_lifetime'])
    return raw


def adapt(raw=None, observed=None):
    return adapt_corporate_detail([negative_packet() if raw is None else raw], selected(),
                                 corpus.SCOPE, offer() if observed is None else observed)


@pytest.fixture(autouse=True)
def synthetic_pins(monkeypatch):
    monkeypatch.setattr(projection, 'L7_NEGATIVE_BUILD_DIGESTS', dict(NEGATIVE_PINS), raising=False)


def test_negative_admission_preserves_raw_profit_typed_owners_and_separate_absence():
    raw, observed = negative_packet(), offer()
    before = deepcopy((raw, observed))
    result = adapt(raw, observed)
    assert result['eligible'], result['reason']
    report, = result['provenance']['projections']
    assert report['kind'] == 'corporate-l7-stable-negative-v1'
    assert report['builds'] == NEGATIVE_PINS and report['route'] == ROUTE
    section, = [s for s in result['sections'] if s['name'] == 'L7']
    assert section['tables'][0]['rows'][1][2] == '-1.234'
    for key in ('PeriodYear', 'ReturnSheetStatusCode', 'ReturnSheetModel',
                'PreviousFormData', 'LastSubmittedFormData'):
        entry, = [e for e in report['values'] if e['path'] == [key]]
        assert entry['container'] == ['Payload']
    for key in ('TaxYear', 'IsIncomeUnder', 'IsIncomeSolely', 'IsCarriedForward', 'NetIncomeBeforeTax'):
        entry, = [e for e in report['values'] if e['path'] == ['MainFormData', key]]
        assert entry['container'] == ['Payload', 'CurrentFormData']
    assert report['presence_facts'] == [{'response_sequence': raw['context']['sequence'],
        'container': ['Payload'], 'path': ['IsCarriedForward'], 'present': False,
        'rule': 'outer-carry-absent/current-induk-enable'}]
    assert not any(e['path'] == ['IsCarriedForward'] for e in report['values'])
    assert (raw, observed) == before


@pytest.mark.parametrize('defect', ['legacy', 'missing-history', 'missing-offer', 'pin', 'null-pins',
    'missing-vendor', 'timezone', 'visibility', 'owner-chain', 'previous-encoded-null',
    'last-missing', 'outer-null', 'outer-zero', 'outer-false', 'year-string', 'under-string',
    'sole-missing', 'carry-bool', 'first-zero', 'first-different', 'current-tax'])
def test_negative_profile_is_closed_without_weakening_legacy(defect):
    value, observed = negative_envelope(), offer()
    current = json.loads(value['Payload']['CurrentFormData'], parse_int=corpus.Number, parse_float=corpus.Number)
    proof = observed[1]['raw_negative_projection']
    if defect in ('legacy', 'missing-offer'): del observed[1]['raw_negative_projection']
    elif defect == 'pin': proof['builds'][projection.VENDOR_SOURCE] = '0' * 64
    elif defect == 'null-pins': proof['builds'] = dict.fromkeys(NEGATIVE_PINS)
    elif defect == 'missing-vendor': del proof['builds'][projection.VENDOR_SOURCE]
    elif defect == 'timezone': proof['timezone'] = 'UTC'
    elif defect == 'visibility': proof['visibility_binding'] = 'unknown'
    elif defect == 'owner-chain': proof['tables'][0]['owner_chain'] = CHAIN[:-1]
    elif defect == 'previous-encoded-null': value['Payload']['PreviousFormData'] = 'null'
    elif defect == 'last-missing': del value['Payload']['LastSubmittedFormData']
    elif defect.startswith('outer-'):
        value['Payload']['IsCarriedForward'] = {'outer-null': None, 'outer-zero': 0, 'outer-false': False}[defect]
    elif defect == 'year-string': current['MainFormData']['TaxYear'] = '2025'
    elif defect == 'under-string': current['MainFormData']['IsIncomeUnder'] = '0'
    elif defect == 'sole-missing': del current['MainFormData']['IsIncomeSolely']
    elif defect == 'carry-bool': current['MainFormData']['IsCarriedForward'] = True
    elif defect.startswith('first-'):
        current[ROOT][BODY][1]['FiscalNetProfitIncome'] = corpus.Number('0' if defect == 'first-zero' else '-1233')
    elif defect == 'current-tax': current['TaxType'] = 'ICT_ROGCIT'
    value['Payload']['CurrentFormData'] = corpus.wire(current)
    raw = negative_packet(value)
    if defect in ('legacy', 'missing-history'): raw['context'].pop('corporate_l7_lifetime')
    if defect in ('year-string', 'current-tax'):
        # These are existing primary identity/type contradictions, not a new
        # semantic fallback. The stricter profile cannot demote them.
        with pytest.raises(JsonSafetyError): adapt(raw, observed)
        return
    result = adapt(raw, observed)
    assert not result['eligible'] and result['sections'] == []


@pytest.mark.parametrize('optional', ['absent', 'offered-no-final', 'vendor-missing', 'history-only'])
def test_nonnegegative_v1_is_independent_of_missing_new_capability(optional):
    observed = offer()
    raw = negative_packet(envelope())
    if optional != 'history-only': raw['context'].pop('corporate_l7_lifetime')
    if optional == 'absent':
        del observed[1]['raw_negative_projection']
        raw['context'].pop('component_lifetime')
    if optional == 'vendor-missing':
        del observed[1]['raw_negative_projection']['builds'][projection.VENDOR_SOURCE]
    result = adapt(raw, observed)
    assert result['eligible'], result['reason']
    report, = result['provenance']['projections']
    assert report['kind'] == 'corporate-l7-v1' and report['builds'] == PINS
    assert 'presence_facts' not in report


@pytest.mark.parametrize('observed', [[], offer()])
@pytest.mark.parametrize('defect', ['null', 'component-missing', 'cross-attempt', 'mixed-absence'])
def test_present_invalid_or_mixed_history_is_fatal_before_fallback(observed, defect):
    raw = negative_packet()
    packets = [raw]
    if defect == 'null': raw['context']['corporate_l7_lifetime'] = None
    elif defect == 'component-missing': del raw['context']['component_lifetime']
    elif defect == 'cross-attempt': raw['context']['corporate_l7_lifetime']['attempt'] = 'b' * 32
    else:
        other = deepcopy(raw)
        other['context']['sequence'] += 1
        del other['context']['corporate_l7_lifetime']
        packets.append(other)
    with pytest.raises(JsonSafetyError):
        adapt_corporate_detail(packets, selected(), corpus.SCOPE, deepcopy(observed))


@pytest.mark.parametrize('mutation', ['disabled', 'wrong-form', 'wrong-path', 'no-legacy', 'extra', 'null'])
def test_explicit_negative_offer_cannot_be_smuggled_at_binding_parser(mutation):
    observed = offer()
    form = observed[1]
    if mutation == 'disabled': form['disabled'] = True
    elif mutation == 'wrong-form': form['name'] = 'L6'
    elif mutation == 'wrong-path': form['paths'] = [['FiscalYearIncomeTax']]
    elif mutation == 'no-legacy': del form['projection']
    elif mutation == 'extra': form['raw_negative_projection']['unexpected'] = True
    else: form['raw_negative_projection'] = None
    with pytest.raises(JsonSafetyError):
        adapt(negative_packet(), observed)


@pytest.mark.parametrize('suffix', SUFFIXES)
def test_each_negative_reported_total_must_reconcile(suffix):
    value = negative_envelope()
    current = json.loads(value['Payload']['CurrentFormData'], parse_int=corpus.Number, parse_float=corpus.Number)
    current[ROOT]['TotalFiscalLossCompensation' + suffix] = corpus.Number('999')
    value['Payload']['CurrentFormData'] = corpus.wire(current)
    assert not adapt(negative_packet(value))['eligible']


@pytest.mark.parametrize('key', ['PreviousFormData', 'LastSubmittedFormData'])
@pytest.mark.parametrize('encoding', ['missing', 'encoded-null', 'encoded-object', 'object', 'bool', 'invalid'])
def test_negative_predecessors_are_present_literal_null_only(key, encoding):
    value = negative_envelope()
    if encoding == 'missing': del value['Payload'][key]
    else:
        value['Payload'][key] = {'encoded-null': 'null', 'encoded-object': '{}',
            'object': {}, 'bool': False, 'invalid': 'SYNTHETIC UNREVIEWED ENCODING'}[encoding]
    assert not adapt(negative_packet(value))['eligible']


def test_native_predicate_evidence_keeps_alternate_original_numeric_lexemes():
    value = negative_envelope()
    current = json.loads(value['Payload']['CurrentFormData'], parse_int=corpus.Number, parse_float=corpus.Number)
    current['MainFormData'].update(NetIncomeBeforeTax=corpus.Number('-1234e0'),
        IsIncomeUnder=corpus.Number('-0.0'), IsCarriedForward=corpus.Number('1e0'))
    current[ROOT][BODY][1]['FiscalNetProfitIncome'] = corpus.Number('-1234.00')
    value['Payload']['CurrentFormData'] = corpus.wire(current)
    result = adapt(negative_packet(value))
    assert result['eligible'], result['reason']
    report, = result['provenance']['projections']
    for key, lexeme in [('NetIncomeBeforeTax', '-1234e0'), ('IsIncomeUnder', '-0.0'), ('IsCarriedForward', '1e0')]:
        entry, = [e for e in report['values'] if e['path'] == ['MainFormData', key]]
        assert entry['value'] == lexeme and entry['type'] == 'number'
        assert entry['container'] == ['Payload', 'CurrentFormData']


@pytest.mark.parametrize('negative', [False, True])
@pytest.mark.parametrize('defect', ['missing', 'none', 'short', 'uppercase'])
def test_both_approved_and_observed_new_pins_must_be_positive_without_touching_v1(monkeypatch, negative, defect):
    pins = dict(NEGATIVE_PINS)
    if defect == 'missing': del pins[projection.VENDOR_SOURCE]
    elif defect == 'none': pins = dict.fromkeys(pins)
    elif defect == 'short': pins[projection.VENDOR_SOURCE] = 'd'
    else: pins[projection.VENDOR_SOURCE] = 'D' * 64
    monkeypatch.setattr(projection, 'L7_NEGATIVE_BUILD_DIGESTS', pins)
    observed = offer(pins=pins)
    result = adapt(negative_packet(negative_envelope() if negative else envelope()), observed)
    assert result['eligible'] is (not negative)
