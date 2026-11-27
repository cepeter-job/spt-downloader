"""Hosted execution of exact hash-reviewed provider excerpts, not Intl guesses."""
from pathlib import Path
import hashlib

import pytest

from coretax_json import _corporate_json, _UnsupportedMetadata
from test_json_hybrid_native import browser as browser

FIXTURE = Path(__file__).parent / 'fixtures' / 'corporate_l10c_framework.js'


def test_reviewed_provider_excerpt_fixture_has_fixed_pin_and_unchanged_content():
    from coretax_build_pins import load_build_pins
    from coretax_corporate_projection import VENDOR_SOURCE
    assert load_build_pins().get(VENDOR_SOURCE) == '3598ab357518fc6ecf12130803594ef2deb0e4a3adeac40b55bfd7bed487ef11'
    assert hashlib.sha256(FIXTURE.read_text(encoding='utf-8').encode()).hexdigest() == (
        'd38db3f3cef2646e87fc2cb09e1e0ddd4082ed9f68fc4cddb4ead5deee911187')


@pytest.fixture
def framework(browser):
    assert FIXTURE.is_file(), 'Source-only RED: exact provider excerpts not retained'
    context = browser.new_context()
    page = context.new_page()
    page.evaluate(FIXTURE.read_text(encoding='utf-8'))
    try:
        yield page
    finally:
        context.close()


@pytest.mark.parametrize('token,expected', [
    ('null', ''), ('0', '0'), ('0.1', '0,1'), ('4.38', '4,38'),
    ('1234.125', '1.234,125'), ('0.0625', '0,063'), ('-0.0625', '-0,063'),
    ('1.2345', '1,235'), ('-1.2345', '-1,235'), ('0.00049', '0'),
    ('0.0005', '0,001'), ('999999999999999', '999.999.999.999.999')])
def test_l10c_number_matches_actual_default_decimal_pipe_not_integer(framework, token, expected):
    import coretax_corporate_projection as projection
    observed = framework.evaluate('token => window.l10cFramework.number(JSON.parse(token))', token)
    assert ('' if observed is None else observed) == expected
    assert projection._l10c_number(_corporate_json(token), 'id-ID') == expected
    if token == '1234.125':
        assert framework.evaluate('() => window.l10cFramework.number(1234.125,"1.0-0")') == '1.234'


@pytest.mark.parametrize('value,yes,no', [
    (True, True, False), (False, False, True), ('1', True, False), ('0', False, True),
    (1, True, False), (0, False, True), (None, False, True), ('', False, False),
    ('true', False, False), (2, False, False)])
def test_exact_radio_writevalue_is_loose_comparison_and_null_child_patch_is_zero(framework, value, yes, no):
    assert framework.evaluate('value => window.l10cFramework.radio(value)', value) == {'yes': yes, 'no': no}


@pytest.mark.parametrize('first,count', [(0, 10), (10, 10), (20, 5)])
def test_exact_paginator_context_keeps_global_numbering_across_page_boundaries(framework, first, count):
    assert framework.evaluate('args => Array.from({length:args.count},(_,i) => '
        'window.l10cFramework.rowIndex(args.first,i)+1)', {'first': first, 'count': count}) == list(
            range(first + 1, first + count + 1))


@pytest.mark.parametrize('token', ['true', '"4.38"', '-0', '1000000000000000', '0.1234567890123456'])
def test_framework_proof_does_not_remove_typed_source_and_precision_guards(token):
    import coretax_corporate_projection as projection
    with pytest.raises(_UnsupportedMetadata):
        projection._l10c_number(_corporate_json(token), 'id-ID')
