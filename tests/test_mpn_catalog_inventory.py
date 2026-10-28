"""Synthetic original-catalog absence proof, independent of browser state."""
from copy import deepcopy

import pytest

from coretax_mpn import captured_catalogs


def original_catalog(details):
    groups=[]
    for name in ('ACCOUNTING_TYPE','ACCOUNTING_TYPE_DETAIL',
                 'REVENUE_CHART_OF_ACCOUNTS_6_DIGITS_SEGMENT','PERIOD'):
        entries=deepcopy(details) if name=='ACCOUNTING_TYPE_DETAIL' else []
        if name=='ACCOUNTING_TYPE':
            entries=[{'Code':'OtherTaxReturn','CodeDescription':'OtherTaxReturn',
                      'AppLanguageId':'id-ID','ValidTo':None}]
        groups.append({'ReferenceDataType':name,'Checksum':'SYNTHETIC-CATALOG-V1','Details':entries})
    return {'IsSuccessful':True,'Payload':groups}


@pytest.mark.parametrize('details,expected', [
    ([],frozenset()),
    ([{'Code':'01'}],frozenset({'01'})),
    ([{'Code':'01'},{'Code':'1'}],frozenset({'01','1'})),
    ([{'Code':'01'},{'Code':'01'}],frozenset({'01'})),
    ([{'Code':'01','CodeDescription':'Expired','ValidTo':'2020-01-01'}],frozenset({'01'})),
    ([{}],None),
    ([{'Code':1}],None),
    ([{'Code':'01'},None],None),
])
def test_original_code_inventory_distinguishes_absence_from_ineligible_labels(details,expected):
    body=original_catalog(details)
    original=deepcopy(body)
    default=captured_catalogs(body)
    labels,codes=captured_catalogs(body,include_codes=True)
    assert labels==default
    assert codes['ACCOUNTING_TYPE_DETAIL']==expected
    assert body==original
