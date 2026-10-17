"""Synthetic Unifikasi tree mappings from the reviewed native component."""
from copy import deepcopy
import importlib
import importlib.util

import pytest

from coretax_json import _corporate_json, _UnsupportedMetadata

HEADERS = ['NO', 'DETIL', 'SETOR SENDIRI', 'PEMOTONGAN / PEMUNGUTAN',
           'PPh DITANGGUNG PEMERINTAH', 'JUMLAH PPh DIBAYAR',
           'JUMLAH PPh DIBAYAR DARI SPT YANG DIBETULKAN',
           'PPh KURANG BAYAR / LEBIH BAYAR KARENA PEMBETULAN']


def project(form, **kwargs):
    assert importlib.util.find_spec('coretax_masa_bindings'), 'Masa tree bindings are not implemented'
    return importlib.import_module('coretax_masa_bindings').project_unifikasi_tree(form, HEADERS, **kwargs)


def fixture():
    return _corporate_json('''{
      "IncomeTaxes":[{"data":{"No":"01","Name":"Article 4 Section 2",
        "TotalSelfPayment":1000,"TotalWithholding":0,"TotalIncomeTaxByGovernment":17,
        "TotalIncomeTaxPaid":1017,"TotalIncomeTaxPaidPreviousReturn":null,
        "TotalIncomeTaxAmendment":-2},"expanded":true,"children":[
          {"data":{"No":"01.1","Name":"Article child unchanged","TotalSelfPayment":3},
           "expanded":true,"children":null}]}],
      "TotalSelfPayment":1000,"TotalWithholding":0,"TotalIncomeTaxByGoverment":29,
      "TotalIncomeTaxPaid":1029,"TotalIncomeTaxPaidPreviousReturn":null,
      "TotalIncomeTaxAmendment":999
    }''')


def test_unifikasi_tree_and_footer_have_independent_government_keys():
    form = fixture(); before = deepcopy(form)
    result = project(form, locale='en-US')
    table = result['table']
    assert table['rows'] == [
        ['01', 'Pasal 4 Ayat 2', '1,000', '0', '17', '1,017', '', '-2'],
        ['01.1', 'Article child unchanged', '3', '', '', '', '', '']]
    assert table['footer'] == [['TOTAL OF INCOME TAX', '1,000', '0', '29', '1,029', '', '']]
    assert table['footer_spans'] == [[2, 1, 1, 1, 1, 1, 1]]
    assert table['body_row_count'] == 2 and table['source_total'] == 2
    assert table['complete'] is True and form == before
    paths = [item['path'] for item in result['provenance']]
    assert ['IncomeTaxes', 0, 'data', 'TotalIncomeTaxByGovernment'] in paths
    assert ['TotalIncomeTaxByGoverment'] in paths
    assert ['TotalIncomeTaxAmendment'] not in paths


def test_duplicate_tree_rows_are_not_deduplicated():
    form = fixture()
    form['IncomeTaxes'].append(deepcopy(form['IncomeTaxes'][0]))
    table = project(form, locale='en-US')['table']
    assert table['body_row_count'] == 4
    assert table['rows'][:2] == table['rows'][2:]


@pytest.mark.parametrize('kind', ['collapsed', 'invalid_children', 'missing_data', 'unknown_locale'])
def test_unverified_tree_shapes_or_locale_are_explicitly_unsupported(kind):
    form = fixture()
    if kind == 'collapsed': form['IncomeTaxes'][0]['expanded'] = False
    elif kind == 'invalid_children': form['IncomeTaxes'][0]['children'] = {}
    elif kind == 'missing_data': form['IncomeTaxes'][0].pop('data')
    with pytest.raises(_UnsupportedMetadata):
        project(form, locale='unknown' if kind == 'unknown_locale' else 'en-US')


def test_empty_tree_remains_empty_and_retains_explicit_totals():
    form = fixture(); form['IncomeTaxes'] = []
    table = project(form, locale='en-US')['table']
    assert table['rows'] == [] and table['body_row_count'] == 0
    assert table['footer'][0][3] == '29'
