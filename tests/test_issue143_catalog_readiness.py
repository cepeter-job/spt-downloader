"""Issue #143: exact original catalog readiness and fail-closed parent binding.

Synthetic fixtures only; do not trigger source GET or render taxpayer values.
"""
import json
from types import SimpleNamespace

import pytest

from coretax_mpn import MpnUnsupported
from coretax_mpn_ui import AccountingUI
from spt_desktop import diagnostics
from test_diagnostics import records
from test_mpn_parent_binding_diagnostics import inspected_binding, COLUMNS, SECRET


@pytest.mark.parametrize('request_seen,accepted,expected', [
    (False, False, 'not_observed'),
    (True, False, 'observed_unbound'),
    (True, True, 'accepted'),
])
def test_freeze_reports_reference_provenance_without_requesting_new_catalog(
        tmp_path, request_seen, accepted, expected):
    ui = AccountingUI.__new__(AccountingUI)
    ui.catalog_frozen = False
    ui.source_pending = {}
    ui.reference_request_seen = request_seen
    ui.reference_raw = b'SYNTHETIC_CATALOG' if accepted else None
    ui._owned = lambda: None
    ui.page = SimpleNamespace(wait_for_timeout=lambda ms: None)
    with diagnostics.session(tmp_path / 'log', 'worker') as log:
        ui._freeze_catalog()
        assert log.flush()
    events = [r for r in records(tmp_path / 'log')
              if r['event'] == 'mpn.catalog_readiness']
    assert len(events) == 1
    assert events[0]['mpn_catalog_state'] == expected
    assert ui.catalog_frozen is True


def test_without_original_reference_only_accounting_type_mismatch_is_unsupported(tmp_path):
    ui, header, row, controls = inspected_binding()
    header['AccountingTypeCode'] = 'SYNTHETIC_CODE'
    ui.list_snapshot['rows'][0] = header.copy()
    ui.catalog_codes = {}
    row[COLUMNS[0]] = SECRET
    with diagnostics.session(tmp_path / 'log', 'worker') as log:
        with pytest.raises(MpnUnsupported):
            ui._bind_header(header)
        assert log.flush()
    assert controls.lookups == []
    events = [r for r in records(tmp_path / 'log')
              if r['event'] == 'mpn.parent_binding_mismatch']
    assert len(events) == 1
    assert events[0]['mpn_accounting_type_projection'] == 'catalog_missing'
    assert SECRET not in json.dumps(events)


def test_catalog_event_drops_untrusted_fields(tmp_path):
    secret = 'SYNTHETIC_PRIVATE_CATALOG'
    with diagnostics.session(tmp_path / 'log', 'worker') as log:
        diagnostics.record('mpn.catalog_readiness',
                           mpn_catalog_state='not_observed', raw=secret, url=secret)
        diagnostics.record('mpn.catalog_readiness', mpn_catalog_state=secret)
        assert log.flush()
    events = [r for r in records(tmp_path / 'log')
              if r['event'] == 'mpn.catalog_readiness']
    assert len(events) == 2
    assert events[0]['mpn_catalog_state'] == 'not_observed'
    assert 'mpn_catalog_state' not in events[1]
    assert secret not in json.dumps(events)
