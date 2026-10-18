"""Reported PPh21 footer source totals and physical spans, never body sums."""
from copy import deepcopy
import importlib
import importlib.util
import json

import pytest

from coretax_json import _corporate_json, _UnsupportedMetadata

BORNE = 'JUMLAH PENGHASILAN BRUTO DAN PAJAK PENGHASILAN YANG DITANGGUNG OLEH PEMERINTAH'
WITHHELD = 'JUMLAH PENGHASILAN BRUTO DAN PAJAK PENGHASILAN YANG DIPOTONG'
TOTAL = 'JUMLAH TOTAL PENGHASILAN BRUTO DAN PAJAK PENGHASILAN YANG DITANGGUNG OLEH PEMERINTAH SERTA PAJAK PENGHASILAN YANG DIPOTONG'
KEYS = ('GrossIncomeAndIncomeTaxBorneByGovernment', 'GrossIncomeAndIncomeTaxWithheld',
        'TotalGrossIncomeAndIncomeTaxBorneByGovernmentAndIncomeTaxWithheld')
SPECS = {
    'l1a': ('Form1A', KEYS, [BORNE, WITHHELD, TOTAL], [5, 3, 1, 1, 1, 5]),
    'l1b-bpa2': ('Form1B', KEYS, [BORNE, WITHHELD, TOTAL], [5, 3, 1, 1, 5]),
    'l2-bpa2': ('Form2', (None,), ['TOTAL'], [5, 5, 1, 1, 4]),
    'l3-bp21': ('Form3', ('Article21' + KEYS[0], 'Article21' + KEYS[1]), [
        'JUMLAH PENGHASILAN BRUTO UNTUK PASAL 21 DAN PAJAK PENGHASILAN PASAL 21 YANG DITANGGUNG OLEH PEMERINTAH',
        'JUMLAH UNTUK PASAL 21 DAN PENGHASILAN BRUTO PASAL 21 SERTA PAJAK PENGHASILAN YANG DIPOTONG'], [4, 4, 1, 1, 4]),
    'l3-bp26': ('Form3', ('Article26' + KEYS[0], 'Article26' + KEYS[1], KEYS[2]), [
        'JUMLAH PENGHASILAN BRUTO UNTUK PASAL 26 DAN PAJAK PENGHASILAN PASAL 26 YANG DITANGGUNG OLEH PEMERINTAH',
        'JUMLAH UNTUK PASAL 26 DAN PENGHASILAN BRUTO PASAL 26 SERTA PAJAK PENGHASILAN YANG DIPOTONG', TOTAL], [5, 7, 1, 1, 4]),
}


def project(grid, form):
    name = 'coretax_pph21_json_bindings'
    assert importlib.util.find_spec(name) is not None, 'PPh21 footer projection is not implemented'
    return importlib.import_module(name).project_pph21_footer(grid, form)


def fixture(grid, *, nulls=False):
    root, keys, labels, spans = SPECS[grid]
    part, paths, rows = {}, [], [[]]
    # The reported third total deliberately differs from the first two summed.
    amounts = [(1200, 120), (400, 40), (9000, 900)]
    texts = [('1.200', '120'), ('400', '40'), ('9.000', '900')]
    for index, key in enumerate(keys):
        values = (None, None) if nulls else amounts[index]
        fields = ('TotalGrossIncome', 'TotalIncomeTax') if key is None else ('GrossIncome', 'IncomeTax')
        target = part if key is None else part.setdefault(key, {})
        for field, value in zip(fields, values):
            target[field] = value
            paths.append([root] + ([] if key is None else [key]) + [field])
        gross, tax = ('0', '0') if nulls else texts[index]
        rows.append(['', labels[index], gross, '', tax, ''] if grid == 'l1a'
                    else ['', labels[index], gross, tax, ''])
    return _corporate_json(json.dumps({root: part})), rows, paths, [[]] + [spans] * len(keys)


@pytest.mark.parametrize('grid', SPECS)
def test_reported_footer_rows_spans_provenance_and_original_source(grid):
    form, rows, paths, spans = fixture(grid)
    before = deepcopy(form)
    result = project(grid, form)
    assert result['footer'] == rows and result['footer_spans'] == spans
    assert [p['path'] for p in result['provenance']] == paths
    assert all(p['type'] == 'number' for p in result['provenance'])
    assert form == before


@pytest.mark.parametrize('grid', ['l1b-bpa1', 'l2-bpa1'])
def test_first_bpa_grid_has_no_footer_not_a_duplicate_of_second_grid(grid):
    form, _, _, _ = fixture(grid.replace('bpa1', 'bpa2'))
    assert project(grid, form) == {'footer': [], 'footer_spans': [], 'provenance': []}


@pytest.mark.parametrize('grid', SPECS)
def test_null_and_missing_leaf_have_distinct_evidence_but_same_nullish_zero(grid):
    form, rows, paths, spans = fixture(grid, nulls=True)
    result = project(grid, form)
    assert result['footer'] == rows and result['footer_spans'] == spans
    assert [p['path'] for p in result['provenance']] == paths
    assert all(p['type'] == 'null' for p in result['provenance'])
    root, keys, _, _ = SPECS[grid]
    for key in keys:
        if key is None:
            form[root].clear()
        else:
            form[root][key].clear()
    missing = project(grid, form)
    assert missing['footer'] == rows
    assert all(p['type'] == 'missing' for p in missing['provenance'])


def test_null_parent_is_not_misattributed_to_nonexistent_json_children():
    form, _, _, _ = fixture('l1a')
    form['Form1A'][KEYS[0]] = None
    result = project('l1a', form)
    for p, field in zip(result['provenance'][:2], ('GrossIncome', 'IncomeTax')):
        assert p['path'] == ['Form1A', KEYS[0]] and p['type'] == 'null'
        assert p['requested_path'] == ['Form1A', KEYS[0], field]


def test_negative_zero_and_other_form_totals_stay_independent():
    form, _, _, _ = fixture('l1a')
    form['Form1A'][KEYS[0]] = _corporate_json('{"GrossIncome":-3000,"IncomeTax":0}')
    form['Form1B'] = _corporate_json('{"GrossIncomeAndIncomeTaxBorneByGovernment":{"GrossIncome":999,"IncomeTax":999}}')
    result = project('l1a', form)
    assert result['footer'][1] == ['', BORNE, '-3.000', '', '0', '']
    assert len(result['footer']) == 4
    assert all(p['path'][0] == 'Form1A' for p in result['provenance'])


@pytest.mark.parametrize('bad', ['not-a-number', True, [], {}])
def test_invalid_amount_shapes_are_unsupported_not_guessed(bad):
    form, _, _, _ = fixture('l1a')
    form['Form1A'][KEYS[0]]['GrossIncome'] = bad
    with pytest.raises(_UnsupportedMetadata):
        project('l1a', form)


@pytest.mark.parametrize('grid,form', [('unknown-grid', {}), ('l1a', None),
                                      ('l1a', []), ('l1a', {'Form1A': 'bad'})])
def test_unknown_grid_or_container_cannot_claim_footer_coverage(grid, form):
    with pytest.raises(_UnsupportedMetadata):
        project(grid, form)

