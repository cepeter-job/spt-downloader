"""Final Induk values, including the child form's later valueChanges writes.

Public 803: calculate at 79448, child setFormData at 57310+, subscription at
55480+, base-header override at 59900+. A stored balance is not the final value.
"""
from copy import deepcopy
import importlib
import importlib.util
import json

import pytest

from coretax_json import _UnsupportedMetadata, _corporate_json


def project(form, control, *, model='NORMAL', migrated=False):
    name = 'coretax_pph21_json_bindings'
    assert importlib.util.find_spec(name) is not None, 'PPh21 source projection is not implemented'
    module = importlib.import_module(name)
    return module.project_pph21_amount(form, control, model=model, migrated=migrated)


def source(**updates):
    form = {
        'Form1A': {'GrossIncomeAndIncomeTaxWithheld': {'IncomeTax': 100.5},
                   'GrossIncomeAndIncomeTaxBorneByGovernment': {'IncomeTax': 2}},
        'Form1B': {'GrossIncomeAndIncomeTaxWithheld': {'IncomeTax': 10},
                   'GrossIncomeAndIncomeTaxBorneByGovernment': {'IncomeTax': 3}},
        'Form3': {'Article21GrossIncomeAndIncomeTaxWithheld': {'IncomeTax': 20},
                  'Article21GrossIncomeAndIncomeTaxBorneByGovernment': {'IncomeTax': 4},
                  'Article26GrossIncomeAndIncomeTaxWithheld': {'IncomeTax': 40.5},
                  'Article26GrossIncomeAndIncomeTaxBorneByGovernment': {'IncomeTax': 5}},
        'A21IncomeTaxWithheld': 999, 'A26IncomeTaxWithheld': 999,
        'A21CarryForward': 10.5, 'A26CarryForward': 2.5,
        'A21PaymentWithSP2D': 2.5, 'A26PaymentWithSP2D': 1.5,
        'A21IncomeTaxUnderpaidOverpaid': 777, 'A26IncomeTaxUnderpaidOverpaid': 888,
        'A21IncomeTaxPaidOnAmended': 5.5, 'A26IncomeTaxPaidOnAmended': 6.5,
        'A21IncomeTaxUnderpaidOverpaidDueToAmendment': -111,
        'A26IncomeTaxUnderpaidOverpaidDueToAmendment': -222,
        'A21IncomeTaxBorneByGovernment': 0, 'A26IncomeTaxBorneByGovernment': 0,
    }
    form.update(updates)
    return _corporate_json(json.dumps(form))


@pytest.mark.parametrize('control,expected', [
    ('A21IncomeTaxWithheld', '131'), ('A26IncomeTaxWithheld', '41'),
    ('A21CarryForward', '11'), ('A26CarryForward', '3'),
    ('A21PaymentWithSP2D', '3'), ('A26PaymentWithSP2D', '2'),
    ('A21IncomeTaxUnderpaidOverpaid', '117'), ('A26IncomeTaxUnderpaidOverpaid', '36'),
    ('A21IncomeTaxPaidOnAmended', '6'), ('A26IncomeTaxPaidOnAmended', '7'),
    ('A21IncomeTaxUnderpaidOverpaidDueToAmendment', '-111'),
    ('A26IncomeTaxUnderpaidOverpaidDueToAmendment', '-222'),
    ('A21IncomeTaxBorneByGovernment', '9'), ('A26IncomeTaxBorneByGovernment', '5'),
])
def test_normal_final_money_after_child_rounding_and_value_changes(control, expected):
    form = source()
    before = deepcopy(form)
    result = project(form, control)
    assert result['value'] == expected
    assert result['provenance'] and result['rule']
    assert all(isinstance(p['path'], list) and p['path'] for p in result['provenance'])
    assert form == before


@pytest.mark.parametrize('control,expected', [
    ('A21IncomeTaxUnderpaidOverpaidDueToAmendment', '111'),
    ('A26IncomeTaxUnderpaidOverpaidDueToAmendment', '29'),
])
def test_amendment_subscription_supersedes_stored_due_after_base_model_patch(control, expected):
    result = project(source(), control, model='AMENDMENT')
    assert result['value'] == expected
    paths = [p['path'] for p in result['provenance']]
    assert [control] not in paths  # Stale stored due is not an active dependency.
    assert [control[:3] + 'IncomeTaxPaidOnAmended'] in paths


@pytest.mark.parametrize('control,expected', [
    ('A21IncomeTaxUnderpaidOverpaid', '777'),
    ('A21IncomeTaxUnderpaidOverpaidDueToAmendment', '-111'),
    ('A26IncomeTaxUnderpaidOverpaid', '36'),
    ('A26IncomeTaxUnderpaidOverpaidDueToAmendment', '29'),
])
def test_migration_preserves_only_article21_raw_balances_not_article26(control, expected):
    assert project(source(), control, model='AMENDMENT', migrated=True)['value'] == expected


@pytest.mark.parametrize('article', ['A21', 'A26'])
@pytest.mark.parametrize('stored,expected', [(1700, '1.700'), (-1.5, '-1'), (None, None)])
def test_borne_by_government_preserves_nonzero_and_uses_js_negative_tie_rounding(article, stored, expected):
    control = article + 'IncomeTaxBorneByGovernment'
    result = project(source(**{control: stored}), control)
    assert result['value'] == (expected if expected is not None else {'A21': '9', 'A26': '5'}[article])
    if stored is not None:
        assert [p['path'] for p in result['provenance']] == [[control]]


def test_withheld_tracks_final_source_contributions_not_stale_scalar():
    result = project(source(), 'A21IncomeTaxWithheld')
    paths = [p['path'] for p in result['provenance']]
    assert paths == [
        ['Form1A', 'GrossIncomeAndIncomeTaxWithheld', 'IncomeTax'],
        ['Form1B', 'GrossIncomeAndIncomeTaxWithheld', 'IncomeTax'],
        ['Form3', 'Article21GrossIncomeAndIncomeTaxWithheld', 'IncomeTax'],
    ]


def test_optional_sum_paths_distinguish_missing_from_json_null():
    form = source(Form1A={}, Form1B={'GrossIncomeAndIncomeTaxWithheld': {'IncomeTax': None}})
    result = project(form, 'A21IncomeTaxWithheld')
    assert result['value'] == '20'
    types = [p['type'] for p in result['provenance']]
    assert types[0] == 'missing' and types[1] == 'null'


@pytest.mark.parametrize('bad', ['123', '1.234,50', True, [], {}, 9007199254740992])
def test_ambiguous_source_types_and_unsafe_precision_do_not_become_guessed_money(bad):
    form = source()
    form['Form1A']['GrossIncomeAndIncomeTaxWithheld']['IncomeTax'] = _corporate_json(json.dumps(bad))
    with pytest.raises(_UnsupportedMetadata):
        project(form, 'A21IncomeTaxWithheld')


def test_missing_direct_math_round_input_is_not_fabricated_zero():
    form = source()
    del form['A21CarryForward']
    with pytest.raises(_UnsupportedMetadata):
        project(form, 'A21CarryForward')
    form['A21CarryForward'] = None
    assert project(form, 'A21CarryForward')['value'] == '0'


@pytest.mark.parametrize('kwargs', [{'model': 'unknown'}, {'migrated': 'false'}])
def test_unverified_lifecycle_branch_is_unsupported(kwargs):
    with pytest.raises(_UnsupportedMetadata):
        project(source(), 'A21IncomeTaxWithheld', **kwargs)


def test_binary_accumulation_noise_remains_unsupported_without_tolerance_rounding():
    form = source()
    for root, amount in [('Form1A', '0.1'), ('Form1B', '0.2')]:
        form[root]['GrossIncomeAndIncomeTaxWithheld']['IncomeTax'] = _corporate_json(amount)
    form['Form3']['Article21GrossIncomeAndIncomeTaxWithheld']['IncomeTax'] = _corporate_json('0')
    # Conservative coverage loss is preferable to silently inventing a tolerance
    # that might change a later JS rounding boundary. The adapter must use DOM.
    with pytest.raises(_UnsupportedMetadata, match='unverified_pph21_numeric_precision'):
        project(form, 'A21IncomeTaxWithheld')


def test_unknown_money_control_is_not_guessed_from_similar_name():
    with pytest.raises(_UnsupportedMetadata):
        project(source(), 'A21IncomeTaxWithheldTotal')
