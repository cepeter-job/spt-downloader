"""Ordering cannot downgrade locale contradictions or invent vendor custody."""
from copy import deepcopy
import hashlib
import json

import pytest

from coretax_json import JsonSafetyError, adapt_corporate_detail
from coretax_masa_json import adapt_masa_detail
from coretax_corporate_projection import project_countries
from coretax_pph21_json_bindings import project_pph21_references
from coretax_unifikasi_json import project_references
from test_pph21_json_references import source, TYPES
from test_unifikasi_json_references import catalogs


VENDOR_SHA = '1de6335b41d5431fd302ab7b7d00b6c593dfa6640c43ab8a88fbfbdb1b0f4b68'
FAMILIES = ('pph21', 'unifikasi', 'country')


def mixed(payload, location, parameter):
    payload[0]['Details'][0]['ParameterData'] = parameter
    if location == 'same-row':
        target = payload[0]['Details'][0]
    elif location == 'later-row':
        target = {'Code': 'SYN_OTHER', 'CodeDescription': 'SYNTHETIC OTHER', 'ValidTo': None}
        payload[0]['Details'].append(target)
    else:
        target = payload[-1]
    target['language'] = 'en-US'


@pytest.mark.parametrize('family', FAMILIES)
@pytest.mark.parametrize('location', ['same-row', 'later-row', 'later-catalog'])
@pytest.mark.parametrize('parameter', [1, '{"DisplayIndex":null}'])
def test_pure_catalog_locale_contradiction_precedes_unsupported_ordering(family, location, parameter):
    payload = (source() if family == 'pph21' else catalogs() if family == 'unifikasi' else
               [{'ReferenceDataType': 'COUNTRY_CODE', 'Details': [
                   {'Code': 'SYN', 'CodeDescription': 'SYNTHETIC COUNTRY', 'ValidTo': None}]}])
    mixed(payload, location, parameter)
    before = deepcopy(payload)
    with pytest.raises(JsonSafetyError):
        if family == 'pph21':
            project_pph21_references(payload, requested_types=TYPES, locale='id-ID')
        elif family == 'unifikasi':
            project_references(payload)
        else:
            project_countries(payload)
    assert payload == before


def case(family):
    if family == 'country':
        from test_corporate_l11c_native import packets, selected, bindings, COUNTRY, corpus
        return selected(), packets(), bindings(), corpus.SCOPE, COUNTRY
    if family == 'pph21':
        from pph21_projection_fixture import case as create, REFERENCE
        from masa_json_fixtures import SCOPE
        record, packets, forms = create()
        return record, packets, forms, SCOPE, REFERENCE
    from unifikasi_projection_fixture import case as create, URL
    value = create()
    return value['record'], value['packets'], value['forms'], value['scope'], URL


def rewrite(packets, endpoint, operation):
    packet, = [p for p in packets if p['context']['url'] == endpoint]
    envelope = json.loads(packet['body'])
    operation(envelope['Payload'])
    packet['body'] = json.dumps(envelope).encode()
    packet['context'].update(bytes=len(packet['body']), sha256=hashlib.sha256(packet['body']).hexdigest())


@pytest.mark.parametrize('family', FAMILIES)
@pytest.mark.parametrize('observed', [False, True])
@pytest.mark.parametrize('location', ['same-row', 'later-row', 'later-catalog'])
@pytest.mark.parametrize('parameter', [1, '{"DisplayIndex":null}'])
def test_exact_packet_locale_contradiction_is_fatal_before_form_fallback(family, observed, location, parameter):
    record, packets, forms, scope, endpoint = case(family)
    rewrite(packets, endpoint, lambda payload: mixed(payload, location, parameter))
    before = deepcopy((record, packets, forms))
    with pytest.raises(JsonSafetyError):
        if family == 'country':
            adapt_corporate_detail(packets, record, scope, forms if observed else [])
        else:
            adapt_masa_detail(packets, record=record, scope=scope, observed_forms=forms if observed else [])
    assert (record, packets, forms) == before


def duplicate(payload):
    for catalog in payload:
        if catalog['ReferenceDataType'] == 'PERIOD':
            continue
        catalog['Details'] = [version for row in catalog['Details'] for version in (
            {**row, 'CodeDescription': 'ZULU', 'ValidTo': None},
            {**row, 'CodeDescription': 'ALPHA', 'ValidTo': None})]


@pytest.mark.parametrize('family', FAMILIES)
@pytest.mark.parametrize('duplicates', [False, True])
def test_pure_catalog_declares_duplicate_dependency_without_claiming_loaded_proof(family, duplicates):
    payload = (source() if family == 'pph21' else catalogs() if family == 'unifikasi' else
               [{'ReferenceDataType': 'COUNTRY_CODE', 'Details': [
                   {'Code': 'SYN', 'CodeDescription': 'SYNTHETIC COUNTRY', 'ValidTo': None}]}])
    if duplicates:
        duplicate(payload)
    before = deepcopy(payload)
    if family == 'pph21':
        result = project_pph21_references(payload, requested_types=TYPES, locale='id-ID')
    elif family == 'unifikasi':
        result = project_references(payload)
    else:
        result = project_countries(payload)
    assert result.get('requires_vendor') is duplicates
    assert payload == before


@pytest.mark.parametrize('family', ['pph21', 'unifikasi'])
@pytest.mark.parametrize('duplicates', [False, True])
@pytest.mark.parametrize('proof', ['missing', 'wrong', 'verified'])
def test_native_duplicate_catalog_requires_positive_vendor_proof_but_unique_legacy_survives(
        family, duplicates, proof):
    record, packets, forms, scope, endpoint = case(family)
    if duplicates:
        rewrite(packets, endpoint, duplicate)
    induk, = [form for form in forms if form['name'] in ('Induk', 'INDUK')]
    if proof != 'missing':
        induk['reference_order_build'] = VENDOR_SHA if proof == 'verified' else '0' * 64
    before = deepcopy((record, packets, forms))
    result = adapt_masa_detail(packets, record=record, scope=scope, observed_forms=forms)
    eligible = proof == 'verified' or proof == 'missing' and not duplicates
    assert result['eligible'] is eligible, result['reason']
    if not eligible:
        assert result['sections'] == [] and not result['coverage']['complete']
    elif duplicates:
        assert any(e.get('reference_order_build') == VENDOR_SHA
                   and e.get('catalog_order_rule') for e in result['provenance']['bindings'])
        values = {v for section in result['sections'] for table in section['tables']
                  for row in table['rows'] for v in row if isinstance(v, str)}
        assert 'ALPHA' in values and 'ZULU' not in values
    assert (record, packets, forms) == before


@pytest.mark.parametrize('family', ['pph21', 'unifikasi'])
def test_vendor_proof_never_relaxes_period_or_model_dropdown_uniqueness(family):
    record, packets, forms, scope, endpoint = case(family)
    induk, = [form for form in forms if form['name'] in ('Induk', 'INDUK')]
    induk['reference_order_build'] = VENDOR_SHA
    if family == 'pph21':
        from pph21_projection_fixture import MODEL_REFERENCE
        endpoint = MODEL_REFERENCE
    def mutate(payload):
        target = payload[-1] if family == 'unifikasi' else payload[0]
        target['Details'] *= 2
    rewrite(packets, endpoint, mutate)
    result = adapt_masa_detail(packets, record=record, scope=scope, observed_forms=forms)
    assert not result['eligible'] and result['sections'] == []
