"""Unifikasi footer visibility, shared totals and physical column spans."""
from copy import deepcopy
import importlib

import pytest

from coretax_json import _corporate_json, _UnsupportedMetadata
from coretax_masa_bindings import render_grid_value


def project(grid, form):
    implementation = getattr(importlib.import_module('coretax_masa_bindings'), 'project_unifikasi_footer', None)
    assert callable(implementation), 'Unifikasi footer projection is not implemented'
    return implementation(grid, form)


CASES = [
    ('list-i-bpnr', [
        ('TotalIncomeTaxWithDirectPaymentBPUBPNR', 'JUMLAH PAJAK PENGHASILAN DITANGGUNG PEMERINTAH DENGAN MENGGUNAKAN METODE PEMBAYARAN LANGSUNG'),
        ('TotalIncomeTaxBPUBPNR', 'JUMLAH PAJAK PENGHASILAN DITANGGUNG PEMERINTAH'),
        ('TotalIncomeTaxPaidWithDirectPaymentBPUBPNR', 'JUMLAH PAJAK PENGHASILAN DIBAYAR DENGAN MENGGUNAKAN METODE PEMBAYARAN LANGSUNG'),
        ('TotalIncomeTaxToBePaidBPUBPNR', 'JUMLAH PAJAK PENGHASILAN YANG HARUS DIBAYAR'),
    ], [10, 1, 5]),
    ('list-ii-sp', [
        ('TotalIncomeTaxSP', 'JUMLAH PPh YANG DITANGGUNG PEMERINTAH'),
        ('TotalIncomeTaxToBePaidSP', 'JUMLAH PPh YANG HARUS DIBAYAR'),
    ], [6, 1, 4]),
    ('list-ii-cy', [('TotalIncomeTaxToBePaidCY', 'JUMLAH PPh YANG HARUS DIBAYAR')], [6, 1, 4]),
    # Preserve the pinned component's literal label, including PAX.
    ('attachment-i', [('TotalIncomeTaxAttachment', 'TOTAL INCOME PAX TO BE PAID')], [12, 1, 4]),
]


def test_bpu_footer_remains_hidden_even_when_shared_totals_are_nonzero():
    result = project('list-i-bpu', _corporate_json('{"TotalIncomeTaxBPUBPNR":999}'))
    assert result == {'footer': [], 'footer_spans': [], 'provenance': []}


@pytest.mark.parametrize('grid,bindings,spans', CASES)
def test_visible_footer_uses_named_prefill_total_not_row_column_or_page_sum(grid, bindings, spans):
    values = ['1234.5', '-2.5', '0', '9']
    displayed = ['1.235', '-3', '0', '9']
    form = {'TaxBase': _corporate_json('901'), 'IncomeTax': _corporate_json('902')}
    for index, (key, _) in enumerate(bindings):
        form[key] = _corporate_json(values[index])
    before = deepcopy(form)
    result = project(grid, form)
    assert result['footer'] == [[label, displayed[i], ''] for i, (_, label) in enumerate(bindings)]
    assert result['footer_spans'] == [spans] * len(bindings)
    assert result['provenance'] == [
        {'path': [key], 'source': 'prefill_form', 'type': 'number', 'value': values[i]}
        for i, (key, _) in enumerate(bindings)]
    assert form == before


@pytest.mark.parametrize('grid,bindings,spans', CASES)
@pytest.mark.parametrize('shape', ['missing', 'null'])
def test_footer_zero_display_does_not_replace_null_or_missing_source_evidence(grid, bindings, spans, shape):
    form = {key: None for key, _ in bindings} if shape == 'null' else {}
    result = project(grid, form)
    assert result['footer'] == [[label, '0', ''] for _, label in bindings]
    assert all(p['type'] == shape and p['value'] is None for p in result['provenance'])


@pytest.mark.parametrize('raw,displayed', [('"001234.50"', '1.235'), ('""', '')])
def test_footer_decimal_strings_are_formatted_but_raw_lexemes_are_preserved(raw, displayed):
    result = project('attachment-i', {'TotalIncomeTaxAttachment': _corporate_json(raw)})
    assert result['footer'][0][1] == displayed
    assert result['provenance'][0]['type'] == 'string'
    assert result['provenance'][0]['value'] == _corporate_json(raw)


@pytest.mark.parametrize('raw', ['true', '[]', '{}', '"1_000"', '"NaN"'])
def test_invalid_footer_amount_cannot_be_silently_coerced(raw):
    with pytest.raises(_UnsupportedMetadata):
        project('attachment-i', {'TotalIncomeTaxAttachment': _corporate_json(raw)})


def test_decimal_underscore_is_not_accepted_by_footer_pipe_but_body_stays_literal():
    assert render_grid_value('1_000', 'number') == '1_000'
    with pytest.raises(_UnsupportedMetadata):
        render_grid_value('1_000', 'number', footer=True)


@pytest.mark.parametrize('grid,form', [('unknown', {}), ('list-ii-sp', []), ('list-i-bpnr', None)])
def test_unknown_footer_scope_is_not_a_blank_complete_result(grid, form):
    with pytest.raises(_UnsupportedMetadata):
        project(grid, form)
