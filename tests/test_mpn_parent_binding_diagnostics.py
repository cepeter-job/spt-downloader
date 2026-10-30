"""Synthetic tests for source/DOM parent-identity mismatch diagnostics (#143)."""
import json
from types import SimpleNamespace

import pytest

from coretax_mpn import MpnSafetyError, MpnUnsupported
from coretax_mpn_ui import AccountingUI
from spt_desktop import diagnostics
from test_diagnostics import records


COLUMNS = (3, 4, 5, 13, 15, 16, 17)
FIELDS = ('accounting_type', 'accounting_detail', 'currency',
          'revenue_code', 'payment_code', 'tax_period', 'transaction_number')
EXPECTED = ('SYNTHETIC_ACCOUNTING', 'SYNTHETIC_DETAIL', 'SYNTHETIC_CURRENCY',
            'SYNTHETIC_KAP', 'SYNTHETIC_KJS', 'SYNTHETIC_PERIOD', 'SYNTHETIC_NUMBER')
SECRET = 'SYNTHETIC_PRIVATE_TAXPAYER_AND_TRANSACTION_AMOUNT'


class InspectedControls:
    def __init__(self):
        self.lookups = []

    def locator(self, selector):
        self.lookups.append(selector)
        return self

    def nth(self, index):
        return self

    def count(self):
        return 1

    def is_visible(self):
        return True

    def is_enabled(self):
        return True

    def get_attribute(self, key):
        return {'id': 'ViewButton', 'title': 'Detail Transaksi',
                'aria-label': 'Detail Transaksi'}[key]

    def click(self, **kwargs):
        raise AssertionError('Binding must not click a detail action')


def inspected_binding():
    header = {'RecordId': 'SYNTHETIC_RECORD', 'TaxpayerTIN': SECRET}
    rendered = [''] * 24
    for column, value in zip(COLUMNS, EXPECTED):
        rendered[column] = value
    controls = InspectedControls()
    ui = AccountingUI.__new__(AccountingUI)
    ui.list_snapshot = {'sequence': 7, 'rows': [header.copy()]}
    ui.observer = SimpleNamespace(latest={'list': {'sequence': 7}})
    ui.list_owner = controls
    ui._stop = lambda: None
    ui._freeze_catalog = lambda: None
    ui.catalog_codes = {'ACCOUNTING_TYPE': frozenset({'SYNTHETIC_ACCOUNTING'})}
    ui._owned = lambda: None
    ui._header_projection = lambda _: EXPECTED
    ui._table = lambda owner, headings, count: (None, [rendered])
    return ui, header, rendered, controls


@pytest.mark.parametrize('column,field', list(zip(COLUMNS, FIELDS)))
def test_parent_identity_mismatch_logs_only_first_fixed_field_and_refuses_action(
        tmp_path, column, field):
    ui, header, row, controls = inspected_binding()
    row[column] = SECRET
    root = tmp_path / 'diagnostics'
    with diagnostics.session(root, 'worker') as log:
        with pytest.raises(MpnSafetyError, match='rendered/source identity differs'):
            ui._bind_header(header)
        assert log.flush()
    mismatch = [r for r in records(root) if r['event'] == 'mpn.parent_binding_mismatch']
    assert len(mismatch) == 1
    assert mismatch[0]['mpn_parent_field'] == field
    assert mismatch[0]['level'] == 'WARNING'
    assert controls.lookups == [], 'No detail-control lookup/click is authorized on mismatch'
    assert SECRET not in json.dumps(records(root))
    assert not {'body', 'headers', 'npwp', 'url', 'message'} & mismatch[0].keys()


def test_multiple_mismatched_fields_records_first_only(tmp_path):
    ui, header, row, controls = inspected_binding()
    row[COLUMNS[2]] = SECRET
    row[COLUMNS[6]] = SECRET
    root = tmp_path / 'diagnostics'
    with diagnostics.session(root, 'worker') as log:
        with pytest.raises(MpnSafetyError):
            ui._bind_header(header)
        assert log.flush()
    mismatch = [r for r in records(root) if r['event'] == 'mpn.parent_binding_mismatch']
    assert len(mismatch) == 1 and mismatch[0]['mpn_parent_field'] == 'currency'
    assert controls.lookups == []


def test_matching_parent_identity_preserves_inspected_detail_control(tmp_path):
    ui, header, _, controls = inspected_binding()
    root = tmp_path / 'diagnostics'
    with diagnostics.session(root, 'worker') as log:
        assert ui._bind_header(header) is controls
        assert log.flush()
    assert controls.lookups
    assert not [r for r in records(root) if r['event'] == 'mpn.parent_binding_mismatch']


def test_mismatch_schema_rejects_untrusted_values_without_conversion(tmp_path):
    class Untrusted:
        def __str__(self):
            raise AssertionError('Untrusted field values must not be stringified')

    root = tmp_path / 'diagnostics'
    with diagnostics.session(root, 'worker') as log:
        for candidate in (SECRET, None, True, Untrusted(), {}, [], 3):
            diagnostics.record('mpn.parent_binding_mismatch', mpn_parent_field=candidate,
                               body=SECRET, npwp=SECRET, message=SECRET)
        assert log.flush()
    mismatch = [r for r in records(root) if r['event'] == 'mpn.parent_binding_mismatch']
    assert len(mismatch) == 7
    assert all('mpn_parent_field' not in row for row in mismatch)
    assert SECRET not in json.dumps(mismatch)


@pytest.mark.parametrize('source_case,expected_reason', [
    ('label', 'catalog_label'),
    ('fallback', 'raw_code_fallback'),
    ('missing_catalog', 'catalog_missing'),
    ('unreviewed', 'code_not_in_catalog'),
    ('blank', 'source_code_missing'),
])
def test_accounting_type_mismatch_captures_only_catalog_provenance(
        tmp_path, source_case, expected_reason):
    ui, header, row, controls = inspected_binding()
    header['AccountingTypeCode'] = 'SYNTHETIC_CATEGORY_CODE'
    ui.catalogs = {'ACCOUNTING_TYPE': {
        'SYNTHETIC_CATEGORY_CODE': 'SYNTHETIC_CATEGORY_LABEL'}}
    ui.catalog_codes = {'ACCOUNTING_TYPE': frozenset({'SYNTHETIC_CATEGORY_CODE'})}
    if source_case == 'fallback':
        ui.catalogs = {'ACCOUNTING_TYPE': {}}
    elif source_case == 'missing_catalog':
        ui.catalog_codes = {'ACCOUNTING_TYPE': None}
    elif source_case == 'unreviewed':
        ui.catalog_codes = {'ACCOUNTING_TYPE': frozenset({'ANOTHER_SYNTHETIC_CODE'})}
    elif source_case == 'blank':
        header['AccountingTypeCode'] = None
    # The source list snapshot must carry the exact selected source header;
    # otherwise the pre-existing RecordId/digest guard rejects before this
    # targeted rendered-vs-source mismatch is actually exercised.
    ui.list_snapshot['rows'][0] = header.copy()
    row[COLUMNS[0]] = SECRET
    root = tmp_path / 'diagnostics'
    with diagnostics.session(root, 'worker') as log:
        with pytest.raises(MpnUnsupported if source_case == 'missing_catalog'
                           else MpnSafetyError):
            ui._bind_header(header)
        assert log.flush()
    mismatch = [event for event in records(root)
                if event['event'] == 'mpn.parent_binding_mismatch']
    assert len(mismatch) == 1
    assert mismatch[0]['mpn_parent_field'] == 'accounting_type'
    assert mismatch[0]['mpn_accounting_type_projection'] == expected_reason
    assert controls.lookups == []
    assert SECRET not in json.dumps(records(root))
    assert 'SYNTHETIC_CATEGORY_CODE' not in json.dumps(records(root))


def test_accounting_projection_enum_rejects_untrusted_values(tmp_path):
    root = tmp_path / 'logs'
    with diagnostics.session(root, 'worker') as log:
        diagnostics.record('mpn.parent_binding_mismatch',
                           mpn_parent_field='accounting_type',
                           mpn_accounting_type_projection=SECRET)
        diagnostics.record('mpn.parent_binding_mismatch',
                           mpn_parent_field='accounting_type',
                           mpn_accounting_type_projection='catalog_label')
        assert log.flush()
    events = [r for r in records(root) if r['event'] == 'mpn.parent_binding_mismatch']
    assert len(events) == 2
    assert 'mpn_accounting_type_projection' not in events[0]
    assert events[1]['mpn_accounting_type_projection'] == 'catalog_label'
    assert SECRET not in json.dumps(events)


def test_missing_catalog_never_downgrades_an_independent_currency_contradiction(tmp_path):
    ui, header, rendered, controls = inspected_binding()
    header['AccountingTypeCode'] = 'SYNTHETIC_ACCOUNTING'
    ui.list_snapshot['rows'][0] = header.copy()
    ui.catalog_codes['ACCOUNTING_TYPE'] = None
    rendered[COLUMNS[0]] = SECRET
    rendered[COLUMNS[2]] = SECRET
    with diagnostics.session(tmp_path / 'log', 'worker') as log:
        with pytest.raises(MpnSafetyError):
            ui._bind_header(header)
        assert log.flush()
    assert controls.lookups == []
