"""Closed L10-D original-data custody, never checkbox/calendar presentation.

The raw response and generic evidence table remain authoritative. This owner
cannot enable a native capture or a worksheet by itself.
"""
from datetime import date
import re

from coretax_build_pins import load_build_pins
from coretax_json import (ORIGIN, JsonSafetyError, _CorporateNumber, _UnsupportedMetadata,
                          _capture_component_lifetime)

PROVIDERS = tuple(ORIGIN + '/returnsheets/id-ID/' + name for name in (
    '525.32c49782948fc5ef.js', 'main.bed1449c3647a8ca.js', 'vendor.c32c4ee39d966e30.js'))
KIND = 'corporate-l10d-originals-v1'
FLAG = 'IsObligationTransferPricing'
FINAL_CUSTODY_BLOCKER = 'unverified_corporate_l10d_final_selection_custody'


def validate_binding(binding):
    """An original-only offer must not smuggle display or capture authority."""
    offer = binding.get('original_custody')
    if (binding.get('name') != 'L10-D' or binding.get('paths') != [['L10dFormData']]
            or any(key in binding for key in ('disabled', 'primary', 'projection', 'raw_negative_projection'))
            or any(binding.get(key) for key in ('grids', 'responses', 'dependencies'))
            or not isinstance(offer, dict)
            or set(offer) != {'kind', 'builds', 'route', 'owner_binding'}
            or offer['kind'] != KIND or type(offer['route']) is not str
            or offer['owner_binding'] != 'observed-enabled-after-induk-v1'
            or not isinstance(offer['builds'], dict)
            or any(type(key) is not str or value is not None and type(value) is not str
                   for key, value in offer['builds'].items())):
        raise JsonSafetyError('Observed L10-D original custody is malformed or misplaced')


def approved_builds(builds):
    """Positive exact equality with all three reviewed loader pins, never None == None."""
    pins = load_build_pins()
    return (isinstance(builds, dict) and set(builds) == set(PROVIDERS)
            and all(type(pins.get(url)) is str and re.fullmatch(r'[a-f0-9]{64}', pins[url])
                    and type(builds[url]) is str and re.fullmatch(r'[a-f0-9]{64}', builds[url])
                    and builds[url] == pins[url] for url in PROVIDERS))


def collect_original_custody(binding, observed_forms, *, root, payload, record, event):
    """Collect a finite original-only candidate; this is NEVER native admission.

    Current Document/owner evidence and equal saved flags do not independently
    prove final Induk selection or continuous child lifetime. Keep that precise
    blocker explicit. Do not manufacture a finality fact from this observation.
    """
    validate_binding(binding)
    offer = binding['original_custody']
    if not approved_builds(offer['builds']):
        raise _UnsupportedMetadata('unverified_corporate_l10d_loaded_pins')
    fields = record.get('source_fields', {})
    route = (ORIGIN + '/returnsheets/id-ID/corporate-income-tax-return/' + '/'.join(
        str(value) for value in (fields.get('TaxpayerAggregateIdentifier'), record['record_id'],
                                fields.get('TaxTypeCode'), fields.get('AggregateIdentifier'))) + '?view=true')
    if (offer['route'] != route or offer['route'] != event['frame_url']
            or record.get('source_status') != 'SPT Dilaporkan'
            or fields.get('TaxTypeCode') != 'ICT_RCIT' or fields.get('ReturnSheetTypeCode') != 'ICT_RCITR'
            or fields.get('ReturnSheetModel') != 'Normal'
            or record.get('meta', {}).get('Model SPT') != 'Normal'
            or payload.get('ReturnSheetStatusCode') != 'SUBMITTED'
            or payload.get('ReturnSheetModel') != 'NORMAL' or root.get('TaxType') != 'ICT_RCIT'
            or any(key not in payload or payload[key] is not None
                   for key in ('PreviousFormData', 'LastSubmittedFormData'))
            or not isinstance(root.get('MainFormData'), dict)
            or any(type(owner.get(FLAG)) is not _CorporateNumber or owner[FLAG] != '1'
                   for owner in (payload, root['MainFormData']))
            or not any(form.get('name') == 'Induk'
                       for form in observed_forms[:observed_forms.index(binding)])
            or event.get('component_lifetime') is None):
        raise _UnsupportedMetadata('unverified_corporate_l10d_source_profile')
    _capture_component_lifetime(event['component_lifetime'], attempt=event['attempt'],
        record_id=record['record_id'], source_url=record['list_url'], detail_url=route)
    originals = retain_originals(root, payload, sequence=event['sequence'])
    predicates = []
    for owner, keys, container, prefix in (
            (payload, (FLAG, 'PreviousFormData', 'LastSubmittedFormData', 'ReturnSheetStatusCode',
                       'ReturnSheetModel'), ['Payload'], []),
            (root['MainFormData'], (FLAG,), ['Payload', 'CurrentFormData'], ['MainFormData'])):
        for key in keys:
            value = owner[key]
            predicates.append({'container': list(container), 'path': [*prefix, key], 'present': True,
                'type': 'null' if value is None else 'number' if type(value) is _CorporateNumber else 'string',
                'value': str(value) if type(value) is _CorporateNumber else value,
                'response_sequence': event['sequence'], 'rule': 'retained-original-custody-predicate'})
    return {'form': 'L10-D', 'kind': KIND, 'builds': dict(offer['builds']),
        'native_admission': False, 'blocker': FINAL_CUSTODY_BLOCKER,
        'source': {'response_sequence': event['sequence'], 'body_sha256': event['sha256'],
                   'attempt': event['attempt'], 'container': ['Payload', 'CurrentFormData'], 'path': [ROOT]},
        'originals': originals, 'predicate_values': predicates}

ROOT = 'L10dFormData'
CHECKS = tuple(f'{owner}Documentary{i}' for owner in ('Master', 'Local') for i in range(1, 6))
DATES = ('MasterDocumentAvailableDate', 'LocalDocumentAvailableDate')


def _original_date(value):
    # A closed ORIGINAL string grammar, not new Date()/calendar equivalence.
    # Do not borrow a renderer's timezone, sentinel, default or clock rules.
    if value is None:
        return
    if (type(value) is not str or not re.fullmatch(
            r'[0-9]{4}-[0-9]{2}-[0-9]{2}(?:T00:00:00(?:\.000)?(?:Z|\+07:00)?)?', value)):
        raise _UnsupportedMetadata('unsupported_corporate_l10d_date_original')
    try:
        day = date.fromisoformat(value[:10])
        if not 1970 <= day.year <= 2100:
            raise ValueError
    except ValueError:
        raise _UnsupportedMetadata('unsupported_corporate_l10d_date_original') from None


def retain_originals(root, payload, *, sequence):
    """Retain the exact closed source-root shape and fourteen typed originals.

    Missing, null, false and an empty object are different facts. Unsupported
    shapes refuse rather than manufacture a control or erase a guarded operand.
    The caller owns packet privacy, selected identity, and lifecycle validation.
    """
    form = root.get(ROOT) if isinstance(root, dict) else None
    if not isinstance(form, dict) or set(form) != {*CHECKS, *DATES}:
        raise _UnsupportedMetadata('unsupported_corporate_l10d_original_shape')
    if any(type(form[key]) is not bool for key in CHECKS):
        raise _UnsupportedMetadata('unsupported_corporate_l10d_checklist_original')
    for key in DATES:
        _original_date(form[key])
    if (not isinstance(payload, dict) or type(payload.get('TIN')) is not str
            or not re.fullmatch(r'[0-9]{16}', payload['TIN'])
            or type(payload.get('PeriodYear')) is not _CorporateNumber
            or not re.fullmatch(r'[0-9]{4}', payload['PeriodYear'])
            or not 1970 <= int(payload['PeriodYear']) <= 2100
            or type(sequence) is not int or sequence <= 0):
        raise _UnsupportedMetadata('unsupported_corporate_l10d_header_originals')
    values = []
    for owner, keys, container, prefix in (
            (form, form, ['Payload', 'CurrentFormData'], [ROOT]),
            (payload, ('TIN', 'PeriodYear'), ['Payload'], [])):
        for key in keys:
            value = owner[key]
            kind = ('boolean' if type(value) is bool else 'number' if type(value) is _CorporateNumber
                    else 'null' if value is None else 'string')
            values.append({'container': list(container), 'path': [*prefix, key],
                'present': True, 'type': kind,
                'value': str(value) if type(value) is _CorporateNumber else value,
                'response_sequence': sequence, 'rule': 'original-only-no-display'})
    return {'kind': 'corporate-l10d-originals-v1',
        'root': {'container': ['Payload', 'CurrentFormData'], 'path': [ROOT],
                 'present': True, 'type': 'object', 'keys': list(form)},
        'values': values,
        'dependencies': [{'target': [ROOT, DATES[1]],
            'operands': [[ROOT, DATES[0]], [ROOT, DATES[1]]],
            'rule': 'pinned-local-date-guarded-by-master-originals-only'}]}
