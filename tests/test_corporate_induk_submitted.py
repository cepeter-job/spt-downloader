"""Populated submitted Induk tracer: original bytes to approved amount slots, CI only."""
from copy import deepcopy
import json

import pytest

import coretax_corporate_projection as projection
from coretax_json import JsonSafetyError, adapt_corporate_detail
import support_json_corpus as corpus
from test_corporate_induk_projection import main_form
from test_corporate_l7_native import FRAME, REQUEST, selected
from test_corporate_l8_native import packet as lifetime_packet

DETAIL = FRAME + '?view=true'
# Independent expected captions, not imports from the production slot inventory.
SLOTS = (
    ('D. PENGHITUNGAN PPh', 'NetIncomeBeforeTax', '4. Penghasilan Neto Fiskal sebelum Fasilitas Pajak'),
    ('D. PENGHITUNGAN PPh', 'IncomeTaxInAYear', '12. PPh Terutang'),
    ('E. PENGURANG PPh TERUTANG', 'TotalIncomeTaxOverseas', '13. Apakah terdapat kredit pajak yang dibayarkan di luar negeri dan/atau dipotong/pungut oleh pihak lain? / Tidak / Ya'),
    ('E. PENGURANG PPh TERUTANG', 'InstallmentOfIncome', '14. Angsuran PPh Pasal 25'),
    ('E. PENGURANG PPh TERUTANG', 'NoticeOfCollection', '15. Surat Tagihan Pajak PPh Pasal 25 (hanya pokok pajak)'),
    ('F. PPh KURANG/LEBIH BAYAR', 'UnderpaymentIncomeTax', '17.a. PPh yang Kurang/Lebih Bayar'),
    ('F. PPh KURANG/LEBIH BAYAR', 'TotalApprovalInstallment', '17.b. Apakah terdapat Surat Keputusan Persetujuan Pengangsuran atau Penundaan Pembayaran Pajak? / Tidak / Ya'),
    ('F. PPh KURANG/LEBIH BAYAR', 'IncomeTaxMustPaid', '17.c. PPh yang masih harus dibayar atau lebih dibayar'),
)


def source(**overrides):
    # Deliberately non-reconciling saved finals: submitted callbacks DO NOT run
    # the editing writes. Guessing arithmetic would corrupt these source values.
    values = dict(NetIncomeBeforeTax=1234567, IncomeTaxInAYear=123456,
        TotalIncomeTaxOverseas=2345, InstallmentOfIncome=3456, NoticeOfCollection=4567,
        UnderpaymentIncomeTax=-5678, TotalApprovalInstallment=6789, IncomeTaxMustPaid=7890)
    values.update(overrides)
    identity = {key: (corpus.Number(value) if type(value).__name__ == '_CorporateNumber' else value)
                for key, value in main_form().items()}
    identity.update(IsIncomeUnder=0, IsIncomeSolely=None)
    identity.update(values)
    current = corpus.current_form()
    current['MainFormData'] = identity
    return {'IsSuccessful': True, 'Payload': {'TIN': corpus.NPWP, 'Name': 'SYNTHETIC COMPANY',
        'Email': 'SYNTHETIC@EXAMPLE.INVALID', 'PhoneNumber': '0000000000',
        'PeriodYear': 2025, 'PeriodMonthStart': 1, 'PeriodMonthEnd': 12,
        'IsDraft': True, 'IsMigrated': False,
        'ReturnSheetStatusCode': 'SUBMITTED', 'ReturnSheetModel': 'NORMAL',
        'PreviousFormData': None, 'LastSubmittedFormData': None,
        'CurrentFormData': corpus.wire(current)}}


def bindings():
    return [{'name': 'Induk', 'paths': [['MainFormData']], 'grids': [],
        'primary': {'endpoint': corpus.PRIMARY_URL, 'request_json': dict(REQUEST)},
        'projection': {'kind': 'corporate-induk-submitted-v2',
            'builds': dict(projection.L11C_BUILD_DIGESTS), 'route': DETAIL,
            'locale': 'id-ID', 'timezone': 'Asia/Jakarta',
            'controls': [s[1] for s in SLOTS]}}]


def packet(value=None):
    raw = lifetime_packet(source() if value is None else value)
    # L8 owns a separate child history; this projection must not consume it.
    del raw['context']['corporate_l8_lifetime']
    return raw


def adapt(raw=None, observed=None, record=None):
    return adapt_corporate_detail([packet() if raw is None else raw],
        selected() if record is None else record, corpus.SCOPE,
        bindings() if observed is None else observed)


def test_populated_submitted_slots_preserve_original_finals_and_typed_provenance():
    raw, observed = packet(), bindings()
    before = deepcopy((raw, observed))
    result = adapt(raw, observed)
    assert result['eligible'] and result['coverage']['complete'], result['reason']
    section, = result['sections']
    assert len(section['fields']) == 18
    assert [(f['group'], f['field'], f['label'], f['value']) for f in section['fields'][10:]] == [
        (group, '', caption, value) for (group, _, caption), value in zip(SLOTS,
        ('1.234.567', '123.456', '2.345', '3.456', '4.567', '-5.678', '6.789', '7.890'))]
    assert section['projection_complete'] is False
    assert section['projection_reason'] == 'unprojected_induk_captions'
    assert section['tables'][0]['headers'] == ['JSON path', 'JSON type', 'Source value']
    report, = result['provenance']['projections']
    assert report['kind'] == 'corporate-induk-submitted-v2'
    assert report['locale'] == 'id-ID' and report['timezone'] == 'Asia/Jakarta'
    assert report['controls'] == [s[1] for s in SLOTS]
    predicate, = [v for v in report['values'] if v['path'] == ['TaxType']]
    assert predicate['value'] == 'ICT_RCIT' and predicate['type'] == 'string'
    assert predicate['container'] == ['Payload', 'CurrentFormData']
    for _, control, caption in SLOTS:
        entry, = [v for v in report['values'] if v['path'] == ['MainFormData', control]]
        assert entry['type'] == 'number' and entry['response_sequence'] == 1
        assert entry['container'] == ['Payload', 'CurrentFormData']
        assert entry['destination'] == {'form': 'Induk', 'field': '', 'label': caption}
    assert (raw, observed) == before


@pytest.mark.parametrize('control', [s[1] for s in SLOTS])
@pytest.mark.parametrize('value', ['123', False, [], {}, corpus.Number('0.5'),
    corpus.Number('-0'), corpus.Number('-0.0'), corpus.Number('1e1000000'),
    corpus.Number('1000000000000000')])
def test_unsafe_submitted_control_refuses_whole_native_record(control, value):
    result = adapt(packet(source(**{control: value})))
    assert not result['eligible'] and result['sections'] == []
    assert result['reason'] == 'unsupported_corporate_induk_submitted_number'


@pytest.mark.parametrize('control', [s[1] for s in SLOTS])
def test_absent_control_is_not_null_or_invented_zero(control):
    value = source()
    current = json.loads(value['Payload']['CurrentFormData'])
    del current['MainFormData'][control]
    value['Payload']['CurrentFormData'] = corpus.wire(current)
    result = adapt(packet(value))
    assert not result['eligible'] and result['reason'] == 'unsupported_corporate_induk_submitted_presence'


@pytest.mark.parametrize('control', [s[1] for s in SLOTS[1:]])
def test_explicit_null_uses_only_the_reviewed_setter_default_and_keeps_raw_null(control):
    result = adapt(packet(source(**{control: None})))
    assert result['eligible'], result['reason']
    caption = next(label for _, key, label in SLOTS if key == control)
    field, = [f for f in result['sections'][0]['fields'] if f['label'] == caption]
    defaulted = control in ('InstallmentOfIncome', 'NoticeOfCollection', 'TotalApprovalInstallment')
    assert field['value'] == ('0' if defaulted else '')
    report, = result['provenance']['projections']
    entry, = [e for e in report['values'] if e['path'] == ['MainFormData', control]]
    assert entry['type'] == 'null' and entry['value'] is None
    assert entry['rule'] == ('submitted-nullish-zero/input-number-id-0' if defaulted
                             else 'submitted-control/input-number-id-0')


@pytest.mark.parametrize('defect', ['pin', 'pins-missing', 'missing-component', 'previous',
    'migrated', 'missing-migrated', 'locale', 'timezone', 'kind-extra', 'negative-net', 'null-net'])
def test_unproved_profile_or_capability_refuses(defect):
    value, observed = source(), bindings()
    if defect == 'pin': observed[0]['projection']['builds'][projection.CIT_SOURCE] = '0' * 64
    elif defect == 'pins-missing': observed[0]['projection']['builds'] = {}
    elif defect == 'previous': value['Payload']['PreviousFormData'] = '{}'
    elif defect == 'migrated': value['Payload']['IsMigrated'] = True
    elif defect == 'missing-migrated': del value['Payload']['IsMigrated']
    elif defect == 'locale': observed[0]['projection']['locale'] = 'en-US'
    elif defect == 'timezone': observed[0]['projection']['timezone'] = 'UTC'
    elif defect == 'kind-extra': observed[0]['projection']['invented'] = True
    elif defect in ('negative-net', 'null-net'):
        value = source(NetIncomeBeforeTax=-1, IsIncomeSolely=1) if defect == 'negative-net' else source(NetIncomeBeforeTax=None)
    raw = packet(value)
    if defect == 'missing-component': del raw['context']['component_lifetime']
    result = adapt(raw, observed)
    assert not result['eligible'] and result['sections'] == []


@pytest.mark.parametrize(('outer', 'inner'), [
    ('PeriodYear', 'TaxYear'), ('PeriodMonthStart', 'AccountingPeriodStart'),
    ('PeriodMonthEnd', 'AccountingPeriodEnd'), ('ReturnSheetModel', 'Status'),
    ('TIN', 'Tin'), ('Name', 'Name'), ('Email', 'EmailAddress'), ('PhoneNumber', 'PhoneNumber')])
def test_base_form_identity_overwrite_cannot_leave_a_stale_main_identity(outer, inner):
    value = source()
    current = json.loads(value['Payload']['CurrentFormData'])
    current['MainFormData'][inner] = 'SYNTHETIC STALE' if outer not in ('TIN', 'PeriodYear') else None
    value['Payload']['CurrentFormData'] = corpus.wire(current)
    if outer in ('TIN', 'PeriodYear'):
        message = 'taxpayer number contradicts' if outer == 'TIN' else 'nonnegative JSON integer'
        with pytest.raises(JsonSafetyError, match=message):
            adapt(packet(value))
        return
    result = adapt(packet(value))
    assert not result['eligible'] and result['sections'] == []


@pytest.mark.parametrize('value', [corpus.Number('0'), corpus.Number('1000.000'),
    corpus.Number('1.2345e6'), corpus.Number('999999999999999')])
def test_safe_integral_lexemes_render_but_are_never_rewritten_in_evidence(value):
    result = adapt(packet(source(NoticeOfCollection=value)))
    assert result['eligible'], result['reason']
    report, = result['provenance']['projections']
    entry, = [v for v in report['values'] if v['path'] == ['MainFormData', 'NoticeOfCollection']]
    assert entry['type'] == 'number' and entry['value'] == value


def test_missing_configured_and_observed_pins_cannot_agree_into_permission(monkeypatch):
    observed = bindings()
    pins = dict.fromkeys(projection.INDUK_SUBMITTED_BUILD_DIGESTS)
    observed[0]['projection']['builds'] = dict(pins)
    monkeypatch.setattr(projection, 'INDUK_SUBMITTED_BUILD_DIGESTS', pins)
    result = adapt(observed=observed)
    assert not result['eligible'] and result['sections'] == []


def test_negative_main_is_literal_only_when_the_original_solely_reset_branch_is_excluded():
    result = adapt(packet(source(NetIncomeBeforeTax=corpus.Number('-1234.000'))))
    assert result['eligible'], result['reason']
    field, = [f for f in result['sections'][0]['fields'] if f['label'] == SLOTS[0][2]]
    assert field['value'] == '-1.234'
    report, = result['provenance']['projections']
    for key, kind, value in (('IsIncomeUnder', 'number', '0'), ('IsIncomeSolely', 'null', None)):
        entry, = [e for e in report['values'] if e['path'] == ['MainFormData', key]]
        assert entry['type'] == kind and entry['value'] == value
        assert entry['container'] == ['Payload', 'CurrentFormData']
        assert entry['rule'] == 'submitted-negative-main/no-solely-reset'


@pytest.mark.parametrize(('key', 'value'), [('IsIncomeUnder', False), ('IsIncomeUnder', '0'),
    ('IsIncomeUnder', None), ('IsIncomeUnder', 1), ('IsIncomeSolely', 0),
    ('IsIncomeSolely', False), ('IsIncomeSolely', '0'), ('IsIncomeSolely', 1)])
def test_negative_main_does_not_borrow_legacy_or_coercive_selection_proof(key, value):
    result = adapt(packet(source(NetIncomeBeforeTax=-1234, **{key: value})))
    assert not result['eligible'] and result['sections'] == []


@pytest.mark.parametrize('key', ['IsIncomeUnder', 'IsIncomeSolely'])
def test_negative_main_requires_explicit_original_reset_predicates(key):
    value = source(NetIncomeBeforeTax=-1234)
    current = json.loads(value['Payload']['CurrentFormData'])
    del current['MainFormData'][key]
    value['Payload']['CurrentFormData'] = corpus.wire(current)
    result = adapt(packet(value))
    assert not result['eligible'] and result['sections'] == []


def test_mixed_component_attempt_remains_fatal_before_projection():
    raw = packet()
    raw['context']['component_lifetime']['attempt'] = 'b' * 32
    with pytest.raises(JsonSafetyError, match='lifetime'):
        adapt(raw)


def test_submitted_inventory_does_not_emit_unproved_questions_or_tariff_aliases():
    result = adapt()
    assert result['eligible'], result['reason']
    assert not any(f['field'] == 'TaxRate' for f in result['sections'][0]['fields'])
    assert all(f['label'] != 'Ganti SPT sebelumnya' for f in result['sections'][0]['fields'])


def test_consistent_amendment_submitted_is_accepted():
    # Pembetulan (Amendment) SPTs are submitted with the same lifecycle; only the
    # model literal differs. A fully consistent amendment must project natively.
    raw = source()
    raw['Payload']['ReturnSheetModel'] = 'AMENDMENT'
    raw['Payload']['CurrentFormData'] = raw['Payload']['CurrentFormData'].replace(
        '"Status":"NORMAL"', '"Status":"AMENDMENT"')
    result = adapt(raw=packet(raw), record=selected('Amendment 001'))
    assert result['eligible'], result['reason']


def test_inconsistent_amendment_payload_model_still_refuses():
    # Record says Amendment but the prefill payload stays NORMAL → mismatch fails closed.
    result = adapt(raw=packet(source()), record=selected('Amendment 001'))
    assert not result['eligible']
    assert result['reason'] == 'unverified_corporate_induk_submitted_lifecycle'
