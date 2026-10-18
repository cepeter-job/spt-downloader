"""Assemble the five approved PPh21 forms from custody-checked JSON only."""
from copy import deepcopy
import re

from coretax_json import (ORIGIN, PPH21_REFERENCE_URL, PPH21_MODEL_REFERENCE_URL,
                          JsonSafetyError, _UnsupportedMetadata)
from coretax_masa_projection import _source, _evidence
from coretax_pph21_observer import BUILD_DIGESTS, FORMS
from coretax_pph21_json_bindings import (AMOUNT_CONTROLS, REFERENCE_TYPES, project_pph21_amount,
    project_pph21_footer, project_pph21_grid, project_pph21_header,
    project_pph21_references, project_pph21_model_references)

_HEADERS = ['NO.', 'URAIAN', 'KAP-KJS', 'JUMLAH (Rp)']
_HEADER_CONTROLS = {'TaxPeriodMonth': ('Masa Pajak', 'INPUT'), 'TaxPeriodYear': ('Tahun Pajak', 'INPUT'),
                   'Status': ('Status SPT', 'UI-DROPDOWN'), 'SubmitInProgressStatus': ('Status Penyampaian', 'INPUT')}


def _label(value):
    return re.sub(r'[^a-z0-9]', '', value.casefold()) if type(value) is str else None


def _induk_specs():
    specs = []
    for article, code in [('21', '411121-100'), ('26', '411127-100')]:
        prefix = 'A' + article
        controls = tuple(name for name in AMOUNT_CONTROLS if name.startswith(prefix))
        labels = [
            ('PPH' if article == '21' else 'PAJAK PENGHASILAN') + ' PASAL ' + article + ' YANG DIPOTONG',
            f'KELEBIHAN PENYETORAN PPH PASAL {article} DARI MASA PAJAK SEBELUMNYA',
            f'PEMBAYARAN PAJAK PENGHASILAN PASAL {article} DENGAN SP2D (HANYA UNTUK INSTANSI PEMERINTAH)',
            f'PPH PASAL {article} YANG KURANG (LEBIH) DISETOR (1-2-3) (Apabila ada lebih setor akan dikompensasikan)',
            f'PPH PASAL {article} YANG KURANG (LEBIH) DISETOR PADA SPT YANG DIBETULKAN',
            f'PPH PASAL {article} YANG KURANG (LEBIH) DISETOR KARENA PEMBETULAN (4-5) (Apabila ada Lebih Setor akan dikompensasikan)',
        ]
        specs.append((f'I. PAJAK PENGHASILAN PASAL {article} YANG DIPOTONG', controls[:-1], labels, code))
        specs.append((f'II. PAJAK PENGHASILAN PASAL {article} YANG DITANGGUNG OLEH PEMERINTAH', controls[-1:],
                      [f'PAJAK PENGHASILAN PASAL {article} DITANGGUNG PEMERINTAH'], code))
    return specs


def _reference(binding, endpoint, packets):
    if (not isinstance(binding, dict) or set(binding) != {'endpoint', 'method', 'sequences'}
            or binding['endpoint'] != endpoint or binding['method'] != 'GET'
            or not isinstance(binding['sequences'], list) or not binding['sequences']):
        raise _UnsupportedMetadata('unbound_pph21_reference_request')
    sources, seen = [], set()
    for sequence in binding['sequences']:
        if type(sequence) is not int or sequence <= 0 or sequence in seen:
            raise JsonSafetyError('PPh21 reference sequence is invalid or repeated')
        seen.add(sequence)
        source = packets.get(sequence)
        if source is None:
            raise _UnsupportedMetadata('missing_pph21_reference_response')
        event = source['event']
        if event['url'] != endpoint or event['method'] != 'GET' or event.get('request_json') is not None:
            raise JsonSafetyError('PPh21 reference sequence contradicts its observed GET')
        if not source['successful']:
            raise _UnsupportedMetadata('failed_pph21_reference_response')
        sources.append(source)
    if len({source['event']['sha256'] for source in sources}) != 1:
        raise JsonSafetyError('PPh21 reference snapshot changed')
    return sources[0]


def _forms(observed):
    if not isinstance(observed, list) or [f.get('name') if isinstance(f, dict) else None for f in observed] != list(FORMS):
        raise _UnsupportedMetadata('incomplete_pph21_form_catalog')
    for form in observed:
        allowed = {'name', 'fields', 'tables', 'builds', 'locale', 'timezone'}
        if form['name'] == 'Induk':
            allowed |= {'primary', 'references'}
        if (set(form) - allowed or form.get('builds') != BUILD_DIGESTS or form.get('locale') != 'id-ID'
                or form.get('timezone') != 'Asia/Jakarta' or not isinstance(form.get('fields'), list)
                or not isinstance(form.get('tables'), list)):
            raise _UnsupportedMetadata('unverified_pph21_form_metadata')
        expected = (['Tabel ' + str(i + 1) for i in range(4)] if form['name'] == 'Induk' else
                    [suffix for suffix, _ in FORMS[form['name']][2]])
        if [t.get('name') if isinstance(t, dict) else None for t in form['tables']] != expected:
            raise _UnsupportedMetadata('incomplete_pph21_table_catalog')
    return {form['name']: form for form in observed}


def _omission(name, field):
    control, tag, group = field['field'], field['tag'], _label(field['group'])
    if name != 'Induk':
        return control in ('Tin', 'TaxPeriod') and tag == 'INPUT' and group == 'header'
    if group == _label('A. IDENTITAS PEMOTONG'):
        return control in ('Tin', 'Name', 'Address', 'PhoneNumber') and tag == 'INPUT'
    if group == _label('D. PERNYATAAN DAN TANDA TANGAN'):
        return ((control in ('MyCheckBox', 'DeclaratorName') and tag == 'INPUT')
                or (control == 'DeclarationBy' and tag == 'P-RADIOBUTTON'))
    return False


def project_pph21_forms(packets, *, record, observed_forms):
    """Value catalogs and table geometry cross-reference; amounts are emitted once."""
    forms = _forms(observed_forms)
    primary = _source(forms['Induk'].get('primary'), ORIGIN + '/returnsheet/api/prefillreturnsheet/article-2126', packets)
    request = primary['event']['request_json']
    if set(request) != {'RecordId', 'onManualClick'} or request['onManualClick'] is not False:
        raise _UnsupportedMetadata('unverified_pph21_prefill_lifecycle')
    source_form, outer = primary.get('form'), primary['payload']
    if (not isinstance(source_form, dict) or not isinstance(outer, dict)
            or outer.get('ReturnSheetStatusCode') != 'SUBMITTED' or type(outer.get('IsMigrated')) is not bool):
        raise _UnsupportedMetadata('unverified_pph21_primary_lifecycle')
    references = forms['Induk'].get('references')
    if (not isinstance(references, list) or len(references) != 2
            or [r.get('endpoint') if isinstance(r, dict) else None for r in references]
                != [PPH21_REFERENCE_URL, PPH21_MODEL_REFERENCE_URL]):
        raise _UnsupportedMetadata('missing_pph21_reference_catalog_binding')
    grid_reference = _reference(references[0], PPH21_REFERENCE_URL, packets)
    model_reference = _reference(references[1], PPH21_MODEL_REFERENCE_URL, packets)
    grid_labels = project_pph21_references(grid_reference['payload'], requested_types=REFERENCE_TYPES, locale='id-ID')
    model_labels = project_pph21_model_references(model_reference['payload'], locale='id-ID')
    bindings = _evidence(grid_labels['provenance'], grid_reference, ['Payload'], {'reference_catalog': 'grid'})
    bindings += _evidence(model_labels['provenance'], model_reference, ['Payload'], {'reference_catalog': 'model'})
    sections, grids, omissions = [], [], []
    for name, observed in forms.items():
        section = {'name': name, 'fields': [], 'tables': []}
        seen, amounts = set(), {}
        for field in observed['fields']:
            if (not isinstance(field, dict) or set(field) != {'field', 'label', 'group', 'column_label', 'tag'}
                    or any(type(value) is not str for value in field.values())):
                raise _UnsupportedMetadata('unverified_pph21_field_metadata')
            control = field['field']
            if _omission(name, field):
                omissions.append({'form': name, 'control': control, 'reason': 'outside_approved_clean_layout'})
                continue
            if name != 'Induk' or control in seen:
                raise _UnsupportedMetadata('unverified_pph21_control_binding')
            seen.add(control)
            if control in AMOUNT_CONTROLS:
                if field['tag'] != 'P-INPUTNUMBER':
                    raise _UnsupportedMetadata('unverified_pph21_amount_host')
                amounts[control] = field
                continue
            if control not in _HEADER_CONTROLS or _label(field['group']) != 'header':
                raise _UnsupportedMetadata('unverified_pph21_header_binding')
            label, tag = _HEADER_CONTROLS[control]
            if field['tag'] != tag or field['label'] not in (label, control):
                raise _UnsupportedMetadata('unverified_pph21_header_binding')
            projected = project_pph21_header(outer, control, model_labels=model_labels['lookups']['ReturnSheetModel'])
            section['fields'].append({**field, 'label': label, 'value': projected['value']})
            entries = projected['provenance']
            if control == 'Status':
                entries = [{**entry, 'lookup': 'ReturnSheetModel'} for entry in entries]
            bindings.extend(_evidence(entries, primary, ['Payload'], {'form': name, 'field': control}, rule=projected['rule']))
        if name == 'Induk':
            if seen != set(AMOUNT_CONTROLS) | set(_HEADER_CONTROLS):
                raise _UnsupportedMetadata('incomplete_pph21_induk_controls')
            for table, (caption, controls, labels, code) in zip(observed['tables'], _induk_specs()):
                if (set(table) != {'name', 'headers', 'group', 'footer_spans', 'row_spans', 'row_fields'}
                        or not isinstance(table['headers'], list) or [_label(h) for h in table['headers']] != [_label(h) for h in _HEADERS]
                        or _label(table['group']) != _label(caption) or table['footer_spans'] != []
                        or table['row_fields'] != [[]] + [[control] for control in controls]):
                    raise _UnsupportedMetadata('unverified_pph21_induk_geometry')
                spans = table['row_spans']
                if (not isinstance(spans, list) or len(spans) != len(controls) + 1
                        or any(not isinstance(row, list) or len(row) != 4 or any(type(n) is not int or n != 1 for n in row) for row in spans)):
                    raise _UnsupportedMetadata('unverified_pph21_induk_spans')
                rows = []
                for index, (control, label) in enumerate(zip(controls, labels)):
                    if _label(amounts[control]['group']) != _label(caption):
                        raise _UnsupportedMetadata('unverified_pph21_amount_group')
                    projected = project_pph21_amount(source_form, control, model=outer['ReturnSheetModel'], migrated=outer['IsMigrated'])
                    rows.append([str(index + 1) + '.', label, code if index == 0 else '', projected['value']])
                    bindings.extend(_evidence(projected['provenance'], primary, ['Payload', 'FormData'],
                        {'form': name, 'table': table['name'], 'field': control}, rule=projected['rule']))
                section['tables'].append({'name': table['name'], 'group': caption, 'headers': list(_HEADERS),
                    'rows': rows, 'body_row_count': len(rows), 'footer': [], 'footer_spans': [], 'complete': True})
        else:
            for table, (suffix, group) in zip(observed['tables'], FORMS[name][2]):
                if (set(table) != {'name', 'headers', 'group', 'footer_spans', 'endpoint', 'pages', 'source_total'}
                        or table['group'] != group):
                    raise _UnsupportedMetadata('unverified_pph21_grid_metadata')
                endpoint = ORIGIN + '/returnsheet/api/loadarticle2126/' + suffix + '-grid'
                sources = _source(table, endpoint, packets, pages=True)
                pages = [{'request': item['event']['request_json'], 'payload': item['payload'], 'sequence': item['event']['sequence']} for item in sources]
                projected = project_pph21_grid(suffix, pages, table['headers'], record_id=record['record_id'],
                    timezone_name=observed['timezone'], lookups=grid_labels['lookups'])
                result = projected['table']
                if type(table['source_total']) is not int or table['source_total'] != result['source_total']:
                    raise JsonSafetyError('PPh21 observed total contradicts response count')
                footer = project_pph21_footer(suffix, source_form)
                if table['footer_spans'] != footer['footer_spans']:
                    raise _UnsupportedMetadata('unverified_pph21_footer_layout')
                result.update(name=suffix, group=group, footer=footer['footer'], footer_spans=footer['footer_spans'])
                result['rows'] += deepcopy(result['footer'])
                section['tables'].append(result)
                bindings.extend(_evidence(projected['provenance'], sources[0], ['Payload'], {'form': name, 'table': suffix}))
                bindings.extend(_evidence(footer['provenance'], primary, ['Payload', 'FormData'], {'form': name, 'table': suffix}))
                grids.append({'form': name, 'name': suffix, 'source_total': result['source_total'], 'complete': True,
                              'sequences': [item['event']['sequence'] for item in sources]})
        sections.append(section)
    return {'sections': sections, 'bindings': bindings, 'grids': grids, 'omitted_fields': omissions,
            'source_root_count': len(source_form),
            'evidence_row_count': sum(len(s['fields']) + sum(len(t['rows']) for t in s['tables']) for s in sections)}
