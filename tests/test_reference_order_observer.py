"""A loaded synthetic vendor is hashed; missing assets are never forced."""
import hashlib

import pytest

import coretax_json
from masa_json_fixtures import SCOPE
from pph21_observer_fixture import browser

VENDOR_BUILD = b'/* SYNTHETIC ORDER VENDOR -- no portal code */'


@pytest.mark.parametrize('family', ['pph21', 'unifikasi'])
@pytest.mark.parametrize('vendor', ['verified', 'changed', 'missing'])
def test_optional_induk_proof_requires_loaded_digest_without_business_reads(
        browser, tmp_path, monkeypatch, family, vendor):
    digest = hashlib.sha256(VENDOR_BUILD).hexdigest()
    monkeypatch.setattr(coretax_json, 'REFERENCE_ORDER_SHA256', digest, raising=False)
    raw = None if vendor == 'missing' else VENDOR_BUILD + (b'/* CHANGED */' if vendor == 'changed' else b'')
    if family == 'pph21':
        from pph21_observer_fixture import observed
        from test_pph21_json_observer import feature, assert_no_values_or_actions
        observer = feature(monkeypatch)
        with observed(browser, tmp_path, native=True, vendor=raw) as (fixture, capture):
            forms = observer(fixture.page, fixture.record, SCOPE, capture, max_pages=5)
            assert forms is not None
            induk, = [form for form in forms if form['name'] == 'Induk']
            assert_no_values_or_actions(fixture)
            assert len(fixture.vendor_requests) == (0 if vendor == 'missing' else 2)
    else:
        from support_masa_native import observed
        with observed(browser, tmp_path, monkeypatch, 'PPh Unifikasi', vendor=raw) as (module, fixture, capture):
            forms = module.observe_masa_forms(fixture.page, fixture.record, SCOPE, capture, max_pages=5)
            assert forms is not None
            induk, = [form for form in forms if form['name'] == 'INDUK']
            assert fixture.unexpected == []
            assert len(fixture.vendor_requests) == (0 if vendor == 'missing' else 2)
    if vendor == 'verified':
        assert induk.get('reference_order_build') == digest
    else:
        assert 'reference_order_build' not in induk
