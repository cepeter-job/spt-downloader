"""Reviewed Unifikasi catalogs and submitted controls, separate from PPN/PPh21."""
from coretax_json import JsonSafetyError, _UnsupportedMetadata, _select_reference_version
from coretax_masa_bindings import _source_scalar, project_unifikasi_text

REFERENCE_TYPES = ('EBUPOT_TAX_CERTIFICATE', 'EBUPOT_PAYMENT_METHOD',
                   'EBUPOTSP_TAX_OBJECT', 'EBUPOTCY_TAX_OBJECT', 'PERIOD')


def project_references(payload, *, clock_interval=None):
    if not isinstance(payload, list) or len(payload) != len(REFERENCE_TYPES):
        raise _UnsupportedMetadata('incomplete_unifikasi_reference_catalogs')
    lookups, evidence = {}, []
    for index, catalog in enumerate(payload):
        if not isinstance(catalog, dict):
            raise _UnsupportedMetadata('unsupported_unifikasi_reference_catalog')
        kind = catalog.get('ReferenceDataType')
        if type(kind) is not str or kind not in REFERENCE_TYPES or kind in lookups:
            raise _UnsupportedMetadata('unbound_unifikasi_reference_type')
        if 'language' in catalog and catalog['language'] != 'id-ID':
            raise JsonSafetyError('Unifikasi reference locale contradicts reviewed display')
        details = catalog.get('Details')
        if not isinstance(details, list):
            raise _UnsupportedMetadata('missing_unifikasi_reference_details')
        evidence.append({'path': [index, 'ReferenceDataType'], 'value': kind, 'type': 'string'})
        groups, descriptions = {}, {}
        for ordinal, entry in enumerate(details):
            if not isinstance(entry, dict) or any(type(entry.get(k)) is not str for k in ('Code', 'CodeDescription')):
                raise _UnsupportedMetadata('unsupported_unifikasi_reference_scalar')
            if 'language' in entry and entry['language'] != 'id-ID':
                raise JsonSafetyError('Unifikasi detail locale contradicts reviewed display')
            for key in ('ValidTo', 'ValidFrom'):
                if key in entry and entry[key] is not None and type(entry[key]) is not str:
                    raise _UnsupportedMetadata('unsupported_unifikasi_reference_validity')
            groups.setdefault(entry['Code'], []).append((ordinal, entry))
            for key in ('Code', 'CodeDescription', 'ValidTo', 'ValidFrom'):
                value = entry.get(key)
                item = {'path': [index, 'Details', ordinal, key], 'value': value,
                        'type': 'missing' if key not in entry else 'null' if value is None else 'string'}
                evidence.append(item)
                if key == 'CodeDescription':
                    descriptions[ordinal] = item
        lookup = {}
        for code, versions in groups.items():
            if kind == 'PERIOD' and len(versions) != 1:
                raise _UnsupportedMetadata('ambiguous_unifikasi_period_description')
            ordinal, chosen, rule = _select_reference_version(versions, clock_interval)
            lookup[code] = chosen['CodeDescription']
            selected = descriptions[ordinal]
            selected['projection_rule'] = 'reviewed-grid-active-version:' + rule
            if clock_interval is not None and rule not in ('first-open-ended', 'only-version'):
                selected['clock_interval'] = dict(clock_interval)
        lookups[kind] = lookup
    return {'lookups': lookups, 'provenance': evidence}


def project_field(form, outer, control, lookups):
    if not isinstance(form, dict) or not isinstance(outer, dict):
        raise _UnsupportedMetadata('unsupported_unifikasi_field_source')
    evidence = []
    container = ['Payload', 'FormData']
    if control == 'TaxPeriodCode':
        code = _source_scalar(form, ('TaxPeriodCode',), evidence)
        choices = lookups.get('PERIOD', {}) if isinstance(lookups, dict) else {}
        if type(code) is not str or code not in choices:
            raise _UnsupportedMetadata('unbound_unifikasi_period_description')
        value = choices[code]
    elif control == 'StatementSignature':
        signature = _source_scalar(form, ('StatementSignature',), evidence)
        if signature is not None and type(signature) is not str:
            raise _UnsupportedMetadata('unsupported_unifikasi_signature_type')
        value = '' if signature is None else signature
    elif control == 'SubmitInProgressStatus':
        flag = form.get('SubmitInProgressStatus')
        if flag is not None and type(flag) is not bool:
            raise _UnsupportedMetadata('unsupported_unifikasi_progress_flag')
        evidence.append({'path': ['SubmitInProgressStatus'], 'value': flag,
                         'type': 'missing' if 'SubmitInProgressStatus' not in form else
                                 'null' if flag is None else 'boolean'})
        status = _source_scalar(form, ('ReturnSheetStatusCode',), evidence)
        value = 'In Progress' if flag else 'Submitted' if status == 'SUBMITTED' else '-'
    elif control in ('MyCheckBox', 'DeclarationBy'):
        status = _source_scalar(outer, ('ReturnSheetStatusCode',), evidence)
        if status != 'SUBMITTED':
            raise _UnsupportedMetadata('unverified_unifikasi_control_lifecycle')
        # The pinned child getter returns undefined: null != undefined is false,
        # so its guarded MyCheckBox=true patch never runs. ngModel starts false.
        value = 'false' if control == 'MyCheckBox' else '0'
        container = ['Payload']
    else:
        result = project_unifikasi_text(form, control)
        return {**result, 'container_path': container}
    return {'value': value, 'provenance': evidence, 'container_path': container,
            'projection_rule': 'reviewed-unifikasi-submitted-control:' + control}


def grid_lookups(name, catalogs):
    if not catalogs:
        return None
    lookups = {'TaxCertificate': catalogs['EBUPOT_TAX_CERTIFICATE'],
               'PaymentMethod': catalogs['EBUPOT_PAYMENT_METHOD']}
    if name == 'list-ii-sp':
        lookups['TaxObject'] = catalogs['EBUPOTSP_TAX_OBJECT']
    elif name == 'list-ii-cy':
        lookups['TaxObject'] = catalogs['EBUPOTCY_TAX_OBJECT']
    return lookups


def reference_projection(observed_forms, packets):
    from coretax_json import UNIFIKASI_REFERENCE_URL
    from coretax_pph21_projection import _reference
    bindings = [form.get('references') for form in observed_forms]
    has_packet = any(item['event']['url'] == UNIFIKASI_REFERENCE_URL for item in packets.values())
    if not any(binding is not None for binding in bindings) and not has_packet:
        return {}, [], None
    first = bindings[0]
    if (not isinstance(first, list) or len(first) != 1
            or any(binding != first for binding in bindings)):
        raise _UnsupportedMetadata('incomplete_unifikasi_reference_binding')
    source = _reference(first[0], UNIFIKASI_REFERENCE_URL, packets)
    projected = project_references(source['payload'], clock_interval=source['event'].get('clock_interval'))
    return projected['lookups'], projected['provenance'], source
