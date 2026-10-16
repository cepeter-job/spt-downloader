"""Native Masa response safety; never grants eligibility from requests alone."""
from urllib.parse import urlparse
import re

from coretax_json import (
    JsonSafetyError,
    _CorporateNumber,
    _UnsupportedMetadata,
    _corporate_json,
    _corporate_packet,
    _corporate_request_key,
    _corporate_privacy,
    _corporate_selected,
    _corporate_url,
)

_PREFILL_PATHS = frozenset({
    '/returnsheet/api/prefillreturnsheet/nvat',
    '/returnsheet/api/prefillreturnsheet/withholding-tax',
})
_GRID_PREFIXES = ('/returnsheet/api/loadndvat/', '/returnsheet/api/loadwtr/')


def check_masa_request_identities(observations, record, scope):
    """Reject observed contradictions before build/form eligibility is tested.

    The existing selected-record helper validates literal scope and URL identity;
    it does not impose corporate tax codes or corporate primary payload shapes.
    Check both Masa families: an unexpected family must not hide another return.
    """
    selected = _corporate_selected(record, scope)
    for event in observations:
        if not isinstance(event, dict):
            raise JsonSafetyError('Masa request observation is invalid')
        _corporate_privacy(event)
        url = event.get('url')
        if not _corporate_url(url):
            raise JsonSafetyError('Masa request origin is unauthorized')
        path = urlparse(url).path
        if path in _PREFILL_PATHS:
            identity_key = 'RecordId'
        elif path.startswith(_GRID_PREFIXES):
            identity_key = 'ReturnSheetRecordId'
        else:
            continue
        request = event.get('request_json')
        if not isinstance(request, dict) or identity_key not in request:
            # Absence is not proof of identity. The adapter separately requires
            # full bindings; continue so a later contradiction cannot be hidden.
            continue
        if type(request[identity_key]) is not str or request[identity_key] != selected['record_id']:
            raise JsonSafetyError('Observed Masa request contradicts selected return')


_MONTHS = ('Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
           'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember')


def _selected_period(record, selected, scope, reasons):
    code = selected['native_fields'].get('TaxPeriodCode')
    if code is None:
        reasons.append('missing_native_masa_period_binding')
        return None
    if type(code) is not str or not re.fullmatch(r'[0-9]{8}', code):
        raise JsonSafetyError('Selected Masa period is not a literal native code')
    first, last, year = int(code[:2]), int(code[2:4]), int(code[4:])
    if not 1 <= first <= last <= 12:
        raise JsonSafetyError('Selected Masa period month bounds are invalid')
    if scope[2] == 'period' and year != scope[1]:
        raise JsonSafetyError('Selected Masa period contradicts scope year')
    # Only a single-month display has been verified for these Masa fixtures.
    # A different display is not repaired or interpreted as a month range.
    label = record.get('meta', {}).get('Masa Pajak')
    if first == last and label != f'{_MONTHS[first - 1]} {year}':
        raise JsonSafetyError('Selected Masa period label contradicts native code')
    if first != last:
        reasons.append('unsupported_masa_period_range')
    return code


def _identity_field(source, name, expected, reasons, *, scalar_type=str):
    if name not in source:
        reasons.append('missing_masa_identity_' + name)
        return
    if expected is None:
        reasons.append('unbound_masa_identity_' + name)
        return
    value = source[name]
    if type(value) is not scalar_type or value != expected:
        # Never include source values in exception text.
        raise JsonSafetyError('Masa source identity contradicts selection: ' + name)


def _check_period_evidence(code, record, scope, reasons):
    """Validate source period evidence even when the listing binding is absent."""
    if type(code) is not str or not re.fullmatch(r'[0-9]{8}', code):
        raise JsonSafetyError('Masa source period is not a literal native code')
    first, last, year = int(code[:2]), int(code[2:4]), int(code[4:])
    if not 1 <= first <= last <= 12:
        raise JsonSafetyError('Masa source period month bounds are invalid')
    if scope[2] == 'period' and year != scope[1]:
        raise JsonSafetyError('Masa source period contradicts scope year')
    label = record.get('meta', {}).get('Masa Pajak')
    known_label = isinstance(label, str) and any(
        re.fullmatch(re.escape(month) + r' [0-9]{4}', label) for month in _MONTHS)
    if known_label and (first != last or label != f'{_MONTHS[first - 1]} {year}'):
        raise JsonSafetyError('Masa source period contradicts selected display period')
    if not known_label:
        reasons.append('unverified_masa_display_period')
    return code


def _check_primary(payload, record, selected, scope, period, tax, reasons):
    if not isinstance(payload, dict):
        reasons.append('unsupported_masa_primary_payload')
        return None
    _identity_field(payload, 'TIN', scope[0], reasons)
    _identity_field(payload, 'TaxpayerIdentifier', selected['frame_taxpayer'], reasons)
    outer_period = None
    if 'PeriodCode' in payload:
        outer_period = _check_period_evidence(payload['PeriodCode'], record, scope, reasons)
    _identity_field(payload, 'PeriodCode', period, reasons)
    # This cross-check reference is not a substitute for the missing listing
    # binding: its missing/unbound reasons still prevent native eligibility.
    checked_period = period if period is not None else outer_period
    model = 'NORMAL' if record.get('meta', {}).get('Model SPT') == 'Normal' else None
    _identity_field(payload, 'ReturnSheetModel', model, reasons)
    if model is None:
        reasons.append('unsupported_masa_model_binding')
    if checked_period is not None:
        year, first, last = checked_period[4:], str(int(checked_period[:2])), str(int(checked_period[2:4]))
        if tax == 'PPN':
            _identity_field(payload, 'PeriodYear', year, reasons, scalar_type=_CorporateNumber)
            _identity_field(payload, 'PeriodMonth', first, reasons, scalar_type=_CorporateNumber)
        else:
            _identity_field(payload, 'PeriodYear', year, reasons)
            _identity_field(payload, 'PeriodStartMonth', first, reasons)
            _identity_field(payload, 'PeriodEndMonth', last, reasons)
    if tax == 'PPN':
        _identity_field(payload, 'ReturnSheetType', 'VAT_VATR', reasons)
    if payload.get('IsFound') is not True:
        reasons.append('masa_primary_not_found')
    raw_form = payload.get('FormData')
    if type(raw_form) is not str:
        reasons.append('missing_masa_form_data')
        return None
    form = _corporate_json(raw_form)
    _corporate_privacy(form)
    if not isinstance(form, dict):
        reasons.append('unsupported_masa_form_shape')
        return None
    _identity_field(form, 'ReturnSheetRecordIdentifier', selected['record_id'], reasons)
    _identity_field(form, 'ReturnSheetAggregateIdentifier', selected['aggregate_id'], reasons)
    if 'TaxPeriodCode' in form:
        _check_period_evidence(form['TaxPeriodCode'], record, scope, reasons)
    _identity_field(form, 'TaxPeriodCode', checked_period, reasons)
    _identity_field(form, 'TIN' if tax == 'PPN' else 'TaxIdentificationNumber', scope[0], reasons)
    if tax == 'PPN':
        _identity_field(form, 'TaxType', 'VAT_VAT', reasons)
        _identity_field(form, 'ReturnSheetModel', model, reasons)
    return form


def adapt_masa_detail(bodies, *, record, scope, observed_forms):
    """Check the whole captured attempt before deciding rendering eligibility.

    Packet custody primitives do not impose a corporate schema. In contrast,
    the corporate primary decoder must not be used for these FormData payloads.
    Semantic form projections are deliberately gated separately from safety.
    """
    selected = _corporate_selected(record, scope)
    tax = record.get('meta', {}).get('Jenis Pajak')
    reasons = []
    period = _selected_period(record, selected, scope, reasons)
    if tax not in ('PPN', 'PPh Unifikasi'):
        reasons.append('unsupported_masa_tax_kind')
    if not selected['aggregate_id'] or not selected['taxpayer_id']:
        reasons.append('missing_native_masa_identity_binding')
    provenance = {'events': []}
    coverage = {'complete': False, 'source_root_count': 0, 'evidence_row_count': 0, 'grids': []}
    from coretax_masa_bindings import FORMS
    from coretax_masa_projection import project_masa_forms

    sequences, snapshots, packets = set(), {}, {}
    primary_seen = False
    grid_paths = {
        '/returnsheet/api/' + ('loadndvat/' if kind == 'PPN' else 'loadwtr/') + suffix + '-grid'
        for kind, forms in FORMS.items() for _, roles in forms.values() for _, suffix in roles
    }
    grid_paths.add('/returnsheet/api/loadndvat/lc-grid/footer')
    attempt, total_bytes = None, 0
    for item in bodies:
        envelope, ctx, attempt, event = _corporate_packet(item, selected, scope, attempt, sequences)
        total_bytes += ctx['bytes']
        if len(sequences) > 1024 or total_bytes > 128 * 1024 * 1024:
            raise JsonSafetyError('Masa source response budget exceeded')
        provenance['events'].append(event)
        check_masa_request_identities([ctx], record, scope)
        path = urlparse(ctx['url']).path
        payload = envelope.get('Payload') if isinstance(envelope, dict) else None
        successful = (200 <= ctx['status'] < 300 and isinstance(envelope, dict)
                      and envelope.get('IsSuccessful') is True)
        form = None
        # Repeated grid/footer responses are snapshots too. Check every packet,
        # even if missing/unknown observation metadata will require fallback.
        if path in _PREFILL_PATHS or path.startswith(_GRID_PREFIXES):
            key = (ctx['url'], _corporate_request_key(ctx.get('request_json')))
            old_hash = snapshots.get(key)
            if old_hash is not None and old_hash != ctx['sha256']:
                raise JsonSafetyError('Masa source snapshot changed within one attempt')
            snapshots[key] = ctx['sha256']
            identity_key = 'RecordId' if path in _PREFILL_PATHS else 'ReturnSheetRecordId'
            request = ctx.get('request_json')
            if not isinstance(request, dict) or identity_key not in request:
                reasons.append('missing_masa_request_identity_binding')
        if path in _PREFILL_PATHS:
            primary_seen = True
            source_tax = 'PPN' if path.endswith('/nvat') else 'PPh Unifikasi'
            if tax in ('PPN', 'PPh Unifikasi') and source_tax != tax:
                raise JsonSafetyError('Masa primary source family contradicts selected tax')
            if not successful:
                reasons.append('failed_masa_primary_response')
            form = _check_primary(payload, record, selected, scope, period, source_tax, reasons)
        elif path in grid_paths:
            source_tax = 'PPN' if path.startswith('/returnsheet/api/loadndvat/') else 'PPh Unifikasi'
            if tax in FORMS and source_tax != tax:
                raise JsonSafetyError('Masa grid source family contradicts selected tax')
            if not successful:
                reasons.append('failed_masa_grid_response')
        else:
            reasons.append('unbound_masa_source_response')
        packets[ctx['sequence']] = {'event': event, 'payload': payload, 'form': form, 'successful': successful}
        del item
    if not primary_seen:
        reasons.append('missing_masa_primary_response')
    try:
        projected = project_masa_forms(packets, record=record, observed_forms=observed_forms)
    except _UnsupportedMetadata as exc:
        reasons.append(str(exc))
    else:
        if not reasons:
            provenance['bindings'] = projected['bindings']
            coverage.update({key: projected[key] for key in ('source_root_count', 'evidence_row_count', 'grids')})
            coverage['complete'] = True
            return {'eligible': True, 'reason': '', 'sections': projected['sections'],
                    'coverage': coverage, 'provenance': provenance}
    return {'eligible': False, 'reason': ','.join(dict.fromkeys(reasons)), 'sections': [],
            'coverage': coverage, 'provenance': provenance}
