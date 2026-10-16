"""Final AskedTo selection is response-backed, not a DOM checked-state read."""
import importlib

import pytest

from coretax_json import _UnsupportedMetadata, _corporate_json


def project(text):
    helper = getattr(importlib.import_module('coretax_masa_bindings'), 'project_ppn_asked_to', None)
    assert callable(helper), 'PPN final AskedTo projection is absent'
    return helper(_corporate_json(text), model='AMENDMENT')


def test_nonnegative_submitted_amendment_clears_stale_refund_selection():
    result = project('{"VATUnderOrOverPaidDueToAmendment":{"VAT":1},"AskedTo":"FAST_REFUND"}')
    assert result['value'] is None
    assert result['rule'] == 'not_overpaid_clear'
    assert any(x['path']==['VATUnderOrOverPaidDueToAmendment','VAT'] for x in result['provenance'])


def test_null_choice_with_nonnegative_submitted_amendment_is_proven_not_missing_capture():
    result = project('{"VATUnderOrOverPaidDueToAmendment":{"VAT":0},"AskedTo":null}')
    assert result['value'] is None
    assert any(x['path']==['AskedTo'] and x['type']=='null' for x in result['provenance'])


@pytest.mark.parametrize('choice', ['CARRY_FORWARD','FAST_REFUND','FORWARD_REFUND'])
def test_negative_amendment_with_export_preserves_source_choice_without_clock_dependency(choice):
    result = project('{"VATUnderOrOverPaidDueToAmendment":{"VAT":-1},"A1FormListOfExportTaxableGoodsOrServices":{"Total":1},"AskedTo":"'+choice+'"}')
    assert result['value'] == choice
    assert any(x['path']==['A1FormListOfExportTaxableGoodsOrServices','Total'] for x in result['provenance'])


def test_carry_forward_override_cannot_be_guessed_without_calendar_and_bookkeeping_binding():
    with pytest.raises(_UnsupportedMetadata):
        project('{"VATUnderOrOverPaidDueToAmendment":{"VAT":-1},"A1FormListOfExportTaxableGoodsOrServices":{"Total":0},"AskedTo":"FAST_REFUND"}')
