"""Synthetic original-number proof for the narrow parent identity fallback."""
import pytest

import coretax_mpn as mpn


def source():
    return {name:mpn.MpnNumber(value) for name,value in (
        ('CurrencyAmount','1250'),('CurrencyAmountLeft','0'),('ExchangeRate','1'),
        ('Amount','-1250'),('AmountLeft','0'))}


def rendered():
    row=['']*24
    row[7:12]=['1.250,00','0,00','1,00','-1.250,00','0,00']
    return row


def test_bounded_parent_identity_preserves_exact_five_original_integer_values():
    values=mpn.parent_numeric_binding(rendered(),source())
    assert values==(1250,0,1,-1250,0)


@pytest.mark.parametrize('value', [None, '1250', mpn.MpnNumber('1250.01'),
    mpn.MpnNumber('1000000000000000'), mpn.MpnNumber('-1000000000000000')])
def test_unproved_parent_original_number_cannot_authorize_identity(value):
    data=source();data['Amount']=value
    assert mpn.parent_numeric_binding(rendered(),data) is None


@pytest.mark.parametrize('value', ['', '1 250,00', '1,250.00', 'NaN', '1.25,00'])
def test_unreviewed_parent_numeric_display_remains_unsupported(value):
    row=rendered();row[10]=value
    assert mpn.parent_numeric_binding(row,source()) is None


@pytest.mark.parametrize('column', [7,8,9,10,11])
def test_changed_known_parent_number_is_a_fatal_identity_contradiction(column):
    row=rendered();row[column]='999,00'
    with pytest.raises(mpn.MpnSafetyError):
        mpn.parent_numeric_binding(row,source())


def test_equivalent_original_lexemes_cannot_manufacture_numeric_uniqueness():
    first=source();second=source()
    second['CurrencyAmount']=mpn.MpnNumber('1250.000')
    second['AmountLeft']=mpn.MpnNumber('-0')
    assert mpn.parent_numeric_binding(rendered(),first)==mpn.parent_numeric_binding(rendered(),second)


@pytest.mark.parametrize(('bad_column','changed_column','kind'), [
    (7,10,'source'),(7,10,'display'),(11,7,'source'),(11,7,'display')])
def test_unproved_field_cannot_hide_an_independently_known_number_contradiction(bad_column,changed_column,kind):
    row=rendered();data=source()
    fields={7:'CurrencyAmount',8:'CurrencyAmountLeft',9:'ExchangeRate',10:'Amount',11:'AmountLeft'}
    if kind=='source':
        data[fields[bad_column]]=None
    else:
        row[bad_column]='SYNTHETIC_UNSUPPORTED_NUMBER'
    row[changed_column]='999,00'
    with pytest.raises(mpn.MpnSafetyError):
        mpn.parent_numeric_binding(row,data)
