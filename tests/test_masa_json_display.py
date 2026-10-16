"""Display contracts traced to the pinned public ui-grid implementation."""
import importlib
import importlib.util

import pytest

from coretax_json import _corporate_json, _UnsupportedMetadata


def render(value, kind='number', **options):
    assert importlib.util.find_spec('coretax_masa_bindings'), 'Masa display bindings are not implemented'
    module = importlib.import_module('coretax_masa_bindings')
    return module.render_grid_value(value, kind, **options)


@pytest.mark.parametrize('raw,expected', [
    ('0', '0'), ('1000', '1.000'), ('-1000', '-1.000'),
    ('1234.5', '1.235'), ('-1234.5', '-1.235'), ('-0.1', '0'),
    ('1e3', '1.000'), ('null', '0'), ('"00123"', '00123'),
    ('"1234.5"', '1234.5'), ('""', ''),
])
def test_grid_numeric_body_preserves_string_tokens_but_formats_json_numbers(raw, expected):
    value = _corporate_json(raw)
    assert render(value) == expected


@pytest.mark.parametrize('raw,expected', [('null', ''), ('0', '0'), ('"1000"', '1.000')])
def test_grid_numeric_footer_does_not_use_body_null_default(raw, expected):
    assert render(_corporate_json(raw), footer=True) == expected


@pytest.mark.parametrize('raw,fraction,expected', [
    ('1234.5', 2, '1.234,50'), ('-1.235', 2, '-1,24'),
    ('0', 6, '0,000000'), ('9.999', 2, '10,00'),
])
def test_explicit_numeric_precision_has_source_bound_rounding(raw, fraction, expected):
    assert render(_corporate_json(raw), fraction=fraction) == expected


@pytest.mark.parametrize('raw', ['true', 'false', '{}', '[]', '9007199254740993', '1e1000'])
def test_unsupported_numeric_values_are_not_silently_coerced(raw):
    with pytest.raises(_UnsupportedMetadata):
        render(_corporate_json(raw))


@pytest.mark.parametrize('value,expected', [
    (None, ''), ('', ''), ('00000123', '00000123'), ('  literal  ', '  literal  '),
])
def test_text_values_keep_literal_identity(value, expected):
    assert render(value, 'text') == expected


@pytest.mark.parametrize('value,expected', [
    (None, ''), ('0001-01-01T00:00:00', ''),
    ('2025-01-02', '02-01-2025'), ('2025-01-02T00:00:00', '02-01-2025'),
    ('2025-01-01T18:30:00Z', '02-01-2025'),
    ('2025-01-02T00:30:00+07:00', '02-01-2025'),
])
def test_grid_date_mask_uses_verified_browser_timezone(value, expected):
    assert render(value, 'date', timezone_name='Asia/Jakarta') == expected


@pytest.mark.parametrize('value,zone', [
    ('2025-01-01T18:30:00Z', None), ('2025-01-01T18:30:00Z', 'Europe/Berlin'),
    ('not-a-date', 'Asia/Jakarta'), ('2025-02-30', 'Asia/Jakarta'),
    ('01/02/2025', 'Asia/Jakarta'),
])
def test_unverified_date_shapes_or_timezone_fall_back(value, zone):
    with pytest.raises(_UnsupportedMetadata):
        render(value, 'date', timezone_name=zone)
