"""Assemble Masa business sections from custody-checked, explicitly bound packets."""
from copy import deepcopy

from coretax_json import ORIGIN, JsonSafetyError, _UnsupportedMetadata, _corporate_request_key
from coretax_masa_bindings import (
    BUILD_DIGESTS, FORMS, MAIN_SOURCE, TAX_SOURCES,
    project_ppn_amount, project_ppn_header, project_ppn_asked_to, project_ppn_footer, project_ppn_grid,
    project_unifikasi_footer, project_unifikasi_grid, project_unifikasi_text,
    project_unifikasi_tree,
)


_PPN_OMITTED_CONTROLS = {
    **dict.fromkeys((
        'TaxableEnterpreneurName', 'Address', 'PhoneNumber', 'Cellphone', 'TIN',
        'BussinessFieldClassification', 'BookkeepingPeriod', 'AccountNo', 'BankName',
        'AccountName', 'MyCheckBox', 'CityOfTaxReturnSigning', 'DeclaratorName', 'Position',
    ), 'INPUT'),
    'DateOfTaxReturnSigning': 'P-CALENDAR',
    'DeadlineSubmission': 'P-CALENDAR',
    'DeclarationBy': 'P-RADIOBUTTON',
    'ReplacementPrevious': 'P-CHECKBOX',
}
# Literal appendix bindings differ from Induk's TaxableEnterpreneurName.
# These repeated identity controls have no slots in the approved clean layout.
_PPN_APPENDIX_OMITTED_CONTROLS = frozenset((
    'TaxableEntrepreneurName', 'TaxPeriodYear', 'TIN', 'ReturnSheetModel',
))


def _source(binding, endpoint, packets, *, pages=False):
    if not isinstance(binding, dict) or binding.get('endpoint') != endpoint:
        raise _UnsupportedMetadata('unbound_masa_source_endpoint')
    requests = binding.get('pages' if pages else 'requests')
    if not isinstance(requests, list) or not requests:
        raise _UnsupportedMetadata('missing_masa_source_requests')
    sources, used = [], set()
    for request in requests:
        if not isinstance(request, dict) or not isinstance(request.get('request_json'), dict):
            raise _UnsupportedMetadata('missing_masa_source_request')
        sequences = request.get('sequences')
        if not isinstance(sequences, list) or not sequences:
            raise _UnsupportedMetadata('missing_masa_source_sequences')
        matched = []
        for sequence in sequences:
            if type(sequence) is not int or sequence <= 0 or sequence in used:
                raise JsonSafetyError('Masa observed source sequence is invalid or duplicated')
            used.add(sequence)
            item = packets.get(sequence)
            if item is None:
                raise _UnsupportedMetadata('missing_masa_bound_packet')
            event = item['event']
            if (event['url'] != endpoint or
                    _corporate_request_key(event.get('request_json')) !=
                    _corporate_request_key(request['request_json'])):
                raise JsonSafetyError('Masa source sequence contradicts its observed request')
            if not item['successful']:
                raise _UnsupportedMetadata('failed_masa_bound_response')
            matched.append(item)
        if len({item['event']['sha256'] for item in matched}) != 1:
            raise JsonSafetyError('Masa bound response snapshot changed')
        if pages and (type(request.get('offset')) is not int or
                      request['offset'] != request['request_json'].get('First')):
            raise JsonSafetyError('Masa observed page offset contradicts its request')
        sources.append(matched[0])
    if not pages and len({item['event']['sha256'] for item in sources}) != 1:
        raise JsonSafetyError('Masa bound primary or footer snapshot changed')
    return sources if pages else sources[0]


def _evidence(entries, source, container, destination, *, rule=None):
    return [{**deepcopy(entry), **({'projection_rule': rule} if rule is not None else {}), 'sequence': entry.get('sequence', source['event']['sequence']),
             'container_path': list(container), 'destination': dict(destination)} for entry in entries]


def _forms(tax, observed):
    if not isinstance(observed, list) or not observed or tax not in FORMS:
        raise _UnsupportedMetadata('unverified_masa_form_projection')
    names = [form.get('name') if isinstance(form, dict) else None for form in observed]
    if any(type(name) is not str for name in names) or len(names) != len(set(names)) or set(names) != set(FORMS[tax]):
        raise _UnsupportedMetadata('incomplete_masa_form_catalog')
    expected_builds = {url: BUILD_DIGESTS[url] for url in (MAIN_SOURCE, TAX_SOURCES[tax])}
    for form in observed:
        if form.get('builds') != expected_builds:
            raise _UnsupportedMetadata('unverified_masa_public_build')
        if form.get('locale') not in ('id-ID', 'en-US') or form.get('timezone') != 'Asia/Jakarta':
            raise _UnsupportedMetadata('unverified_masa_display_environment')
        if not isinstance(form.get('fields'), list) or not isinstance(form.get('tables'), list):
            raise _UnsupportedMetadata('missing_masa_form_structure')
        expected = [name for _, name in FORMS[tax][form['name']][1]]
        if tax == 'PPh Unifikasi' and form['name'] == 'INDUK':
            expected = ['income-taxes']
        actual = [table.get('name') if isinstance(table, dict) else None for table in form['tables']]
        if actual != expected:
            raise _UnsupportedMetadata('incomplete_masa_table_catalog')
    return {form['name']: form for form in observed}


def project_masa_forms(packets, *, record, observed_forms):
    """No DOM value, unbound lookup, or corporate leaf-table projection is accepted."""
    tax = record['meta']['Jenis Pajak']
    forms = _forms(tax, observed_forms)
    prefill = ORIGIN + '/returnsheet/api/prefillreturnsheet/' + ('nvat' if tax == 'PPN' else 'withholding-tax')
    primary = _source(forms['INDUK'].get('primary'), prefill, packets)
    source_form = primary.get('form')
    if not isinstance(source_form, dict):
        raise _UnsupportedMetadata('missing_masa_projectable_form')
    lc_source, lc_projection = None, None
    if tax == 'PPN':
        lc_source = _source(forms['C']['tables'][0].get('footer_source'),
                            ORIGIN + '/returnsheet/api/loadndvat/lc-grid/footer', packets)
        request = lc_source['event'].get('request_json', {})
        if request.get('IsNormalVAT') is not True:
            raise _UnsupportedMetadata('unverified_masa_lc_kind')
        lc_projection = project_ppn_footer('C', source_form, lc_footer=lc_source['payload'])
    sections, bindings, grids, omissions = [], [], [], []
    unifikasi_lookups = {}
    if tax == 'PPh Unifikasi':
        from coretax_unifikasi_json import reference_projection, project_field, grid_lookups
        unifikasi_lookups, reference_evidence, reference_source = reference_projection(observed_forms, packets)
        if reference_source is not None:
            bindings.extend(_evidence(reference_evidence, reference_source, ['Payload'],
                                      {'form': 'INDUK', 'field': 'reference catalogs'}))
    for observed in observed_forms:
        name = observed['name']
        section = {'name': name, 'fields': [], 'tables': []}
        choice = None
        choice_bound = False
        if tax == 'PPh Unifikasi':
            declarations = [f for f in observed['fields'] if isinstance(f, dict)
                            and f.get('field') == 'DeclarationBy']
            expected = [('0', 'Wajib Pajak', 'P-RADIOBUTTON'), ('1', 'Kuasa Wajib Pajak', 'P-RADIOBUTTON')]
            if declarations and (name != 'INDUK' or
                    [(f.get('option'), f.get('label'), f.get('tag')) for f in declarations] != expected):
                raise _UnsupportedMetadata('incomplete_unifikasi_declaration_options')
        if tax == 'PPN' and name == 'INDUK':
            options = [f for f in observed['fields'] if isinstance(f, dict) and f.get('field') == 'AskedTo']
            if options:
                expected = [
                    ('CARRY_FORWARD', '1. dikompensasikan', 'P-RADIOBUTTON'),
                    ('FAST_REFUND', '2. dikembalikan melalui pengembalian pendahuluan', 'P-RADIOBUTTON'),
                    ('FORWARD_REFUND', '3. dikembalikan melalui pemeriksaan', 'P-RADIOBUTTON'),
                ]
                if [(f.get('option'), f.get('label'), f.get('tag')) for f in options] != expected:
                    raise _UnsupportedMetadata('unverified_ppn_requested_options')
                choice = project_ppn_asked_to(source_form, model=source_form.get('ReturnSheetModel'))
        for field in observed['fields']:
            if (not isinstance(field, dict) or set(field) - {'field', 'label', 'group', 'column_label', 'tag', 'option'}
                    or any(type(field.get(key)) is not str for key in ('field', 'label', 'group', 'column_label', 'tag'))
                    or not field['field'] or not field['label']):
                raise _UnsupportedMetadata('unverified_masa_field_metadata')
            if (tax == 'PPN' and name in ('A-1', 'A-2', 'B-1', 'B-2', 'B-3', 'C')
                    and field['field'] in _PPN_APPENDIX_OMITTED_CONTROLS):
                if field['tag'] != 'INPUT' or 'option' in field:
                    raise _UnsupportedMetadata('unverified_ppn_omitted_control_shape')
                omissions.append({'form': name, 'field': field['field'], 'tag': field['tag'],
                                  'reason': 'approved_ppn_template_omission'})
                continue
            if tax == 'PPN' and name == 'INDUK' and field['field'] in _PPN_OMITTED_CONTROLS:
                if field['tag'] != _PPN_OMITTED_CONTROLS[field['field']]:
                    raise _UnsupportedMetadata('unverified_ppn_omitted_control_shape')
                if field['field'] == 'ReplacementPrevious':
                    if (field['label'] != 'Ganti SPT sebelumnya'
                            or field['group'] != 'III. PENGHITUNGAN PPN KURANG BAYAR / LEBIH BAYAR'):
                        raise _UnsupportedMetadata('unverified_ppn_omitted_control_shape')
                if field['field'] == 'DeclarationBy':
                    if (field.get('option'), field['label']) not in (('0', 'PKP'), ('1', 'Kuasa Wajib Pajak')):
                        raise _UnsupportedMetadata('unverified_ppn_omitted_option')
                elif 'option' in field:
                    raise _UnsupportedMetadata('unverified_ppn_omitted_option')
                omissions.append({'form': name, 'field': field['field'], 'tag': field['tag'],
                                  'reason': 'approved_ppn_template_omission'})
                continue
            if tax == 'PPN' and name == 'INDUK' and field['field'] == 'AskedTo':
                if choice is None:
                    raise _UnsupportedMetadata('unverified_ppn_requested_choice')
                if not choice_bound:
                    bindings.extend(_evidence(choice['provenance'], primary, ['Payload', 'FormData'],
                                              {'form': name, 'field': 'AskedTo'}, rule=choice['rule']))
                    choice_bound = True
                if choice['value'] is not None and field['option'] == choice['value']:
                    section['fields'].append({**deepcopy(field), 'value': choice['value']})
                continue
            if tax == 'PPh Unifikasi' and field['field'] == 'DeclarationBy':
                if (name != 'INDUK' or field['tag'] != 'P-RADIOBUTTON'
                        or (field.get('option'), field['label']) not in
                        (('0', 'Wajib Pajak'), ('1', 'Kuasa Wajib Pajak'))):
                    raise _UnsupportedMetadata('unverified_unifikasi_declaration_option')
                projected = project_field(source_form, primary['payload'], 'DeclarationBy', unifikasi_lookups)
                if field['option'] == projected['value']:
                    section['fields'].append({**deepcopy(field), 'value': projected['value']})
                    bindings.extend(_evidence(projected['provenance'], primary, projected['container_path'],
                        {'form': name, 'field': 'DeclarationBy'}, rule=projected.get('projection_rule')))
                continue
            # Known option metadata is not itself a verified final selected value.
            if 'option' in field:
                raise _UnsupportedMetadata('unverified_masa_choice_value')
            control = field['field']
            event_source, container = primary, ['Payload', 'FormData']
            if tax == 'PPN':
                if name != 'INDUK':
                    raise _UnsupportedMetadata('unverified_ppn_appendix_control')
                if control in ('Period', 'Model'):
                    projected = project_ppn_header(primary['payload'], control)
                    container = ['Payload']
                elif control in lc_projection['induk_values']:
                    projected = {'value': lc_projection['induk_values'][control],
                                 'provenance': lc_projection['provenance']}
                    event_source, container = lc_source, ['Payload']
                else:
                    if control.startswith('VATandSTLGCollectedByOtherPartiesUnderOverpaidDueAmmendment'):
                        primary_sequences = [sequence for request in forms['INDUK']['primary']['requests']
                                             for sequence in request['sequences']]
                        footer_sequences = [sequence for request in forms['C']['tables'][0]['footer_source']['requests']
                                            for sequence in request['sequences']]
                        if min(footer_sequences) <= max(primary_sequences):
                            raise _UnsupportedMetadata('unverified_ppn_footer_lifecycle')
                    projected = project_ppn_amount(source_form, control, model=source_form.get('ReturnSheetModel'),
                                                   lc_footer=lc_source['payload'])
            else:
                expected_tag = 'UI-DROPDOWN' if control == 'TaxPeriodCode' else 'INPUT'
                if field['tag'] != expected_tag:
                    raise _UnsupportedMetadata('unverified_unifikasi_control_tag')
                projected = project_field(source_form, primary['payload'], control, unifikasi_lookups)
                container = projected['container_path']
            section['fields'].append({**deepcopy(field), 'value': projected['value']})
            for entry in projected['provenance']:
                source = lc_source if tax == 'PPN' and entry.get('source') == 'lc_footer' else event_source
                path = ['Payload'] if source is lc_source else container
                bindings.extend(_evidence([entry], source, path, {'form': name, 'field': control},
                                          rule=projected.get('rule', projected.get('projection_rule'))))
        for table in observed['tables']:
            if (not isinstance(table.get('headers'), list) or not isinstance(table.get('footer_spans'), list)
                    or type(table.get('group')) is not str
                    or set(table) - {'name', 'headers', 'group', 'footer_spans', 'endpoint', 'pages', 'source_total', 'footer_source'}):
                raise _UnsupportedMetadata('unverified_masa_table_metadata')
            grid_name = table['name']
            destination = {'form': name, 'table': grid_name}
            if grid_name == 'income-taxes':
                projected = project_unifikasi_tree(source_form, table['headers'], locale=observed['locale'])
                result = projected['table']
                bindings.extend(_evidence(projected['provenance'], primary, ['Payload', 'FormData'], destination))
            else:
                prefix = 'loadndvat/' if tax == 'PPN' else 'loadwtr/'
                endpoint = ORIGIN + '/returnsheet/api/' + prefix + grid_name + '-grid'
                sources = _source(table, endpoint, packets, pages=True)
                pages = [{'request': item['event']['request_json'], 'payload': item['payload'],
                          'sequence': item['event']['sequence']} for item in sources]
                if tax == 'PPN':
                    projected = project_ppn_grid(name, pages, table['headers'],
                        record_id=record['record_id'], timezone_name=observed['timezone'])
                    footer = lc_projection if name == 'C' else project_ppn_footer(name, source_form)
                else:
                    projected = project_unifikasi_grid(grid_name, pages, table['headers'],
                        record_id=record['record_id'], timezone_name=observed['timezone'],
                        lookups=grid_lookups(grid_name, unifikasi_lookups))
                    footer = project_unifikasi_footer(grid_name, source_form)
                result = projected['table']
                if type(table.get('source_total')) is not int or table['source_total'] != result['source_total']:
                    raise JsonSafetyError('Masa observed grid count contradicts source response count')
                result.update(footer=footer['footer'], footer_spans=footer['footer_spans'])
                bindings.extend(_evidence(projected['provenance'], sources[0], ['Payload'], destination))
                footer_source = lc_source if tax == 'PPN' and name == 'C' else primary
                container = ['Payload'] if footer_source is lc_source else ['Payload', 'FormData']
                bindings.extend(_evidence(footer['provenance'], footer_source, container, destination))
                grids.append({'form': name, 'name': grid_name, 'source_total': result['source_total'],
                              'complete': True, 'sequences': [item['event']['sequence'] for item in sources]})
            if table['footer_spans'] != result['footer_spans']:
                raise _UnsupportedMetadata('unverified_masa_footer_layout')
            result.update(name=grid_name, group=table['group'])
            # Exporters locate the footer boundary by body_row_count. Keep both
            # the explicit footer and physical rows without counting it as body.
            result['rows'] = result['rows'] + deepcopy(result['footer'])
            section['tables'].append(result)
        sections.append(section)
    return {'sections': sections, 'bindings': bindings, 'grids': grids, 'omitted_fields': omissions,
            'source_root_count': len(source_form),
            'evidence_row_count': sum(len(section['fields']) + sum(len(table['rows']) for table in section['tables'])
                                      for section in sections)}
