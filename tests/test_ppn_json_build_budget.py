"""Synthetic browser contracts for the reviewed PPN main bundle size."""
import hashlib

import pytest

from masa_json_fixtures import SCOPE
from masa_observer_fixture import ASSETS, FORMS, MAIN, Fixture
from support_masa_native import browser, observed


@pytest.mark.parametrize(
    ('tax', 'asset_kind', 'size', 'matching_digest', 'loaded', 'accepted'),
    [
        ('PPN', 'main', 4_357_138, True, True, True),
        ('PPN', 'main', 5 * 1024 * 1024, True, True, True),
        ('PPN', 'main', 5 * 1024 * 1024 + 1, True, True, False),
        ('PPh Unifikasi', 'main', 4_357_138, True, True, True),
        ('PPh Unifikasi', 'main', 5 * 1024 * 1024, True, True, True),
        ('PPh Unifikasi', 'main', 5 * 1024 * 1024 + 1, True, True, False),
        ('PPh Unifikasi', 'tax', 4_357_138, True, True, False),
        ('PPh Unifikasi', 'main', 4_357_138, False, True, False),
        ('PPh Unifikasi', 'main', 4_357_138, True, False, False),
        ('PPN', 'tax', 4_357_138, True, True, False),
        ('PPN', 'main', 4_357_138, False, True, False),
        ('PPN', 'main', 4_357_138, True, False, False),
    ],
    ids=['reviewed-size', 'ppn-main-ceiling', 'over-ceiling',
         'unifikasi-reviewed-size', 'unifikasi-main-ceiling', 'unifikasi-over-ceiling',
         'unifikasi-tax-chunk-bounded', 'unifikasi-changed-digest', 'unifikasi-not-loaded',
         'tax-chunk-unchanged', 'changed-digest', 'not-loaded'],
)
def test_ppn_main_build_budget_is_bounded_and_scope_specific(
    browser, tmp_path, monkeypatch, tax, asset_kind, size,
    matching_digest, loaded, accepted,
):
    # Reproduce only the public bundle's byte length, never its actual code.
    body = b'/*' + b'x' * (size - 4) + b'*/'
    asset = MAIN if asset_kind == 'main' else ASSETS[tax]
    original_route = Fixture.route
    original_document = Fixture.document

    def route_large_asset(self, route):
        if route.request.url == asset:
            route.fulfill(content_type='application/javascript', body=body)
        else:
            original_route(self, route)

    def document_without_asset(self):
        return original_document(self).replace('<script src="' + asset + '"></script>', '')

    monkeypatch.setattr(Fixture, 'route', route_large_asset)
    if not loaded:
        monkeypatch.setattr(Fixture, 'document', document_without_asset)
    with observed(browser, tmp_path, monkeypatch, tax) as (module, fixture, capture):
        reviewed_body = body if matching_digest else body + b'/* different review */'
        digest = hashlib.sha256(reviewed_body).hexdigest()
        monkeypatch.setitem(module.BUILD_DIGESTS, asset, digest)
        forms = module.observe_masa_forms(fixture.page, fixture.record, SCOPE, capture, max_pages=5)
        if accepted:
            assert forms is not None
            assert [form['name'] for form in forms] == [form[0] for form in FORMS[tax]]
            assert all(form['builds'][asset] == digest for form in forms)
            assert capture.drain()['complete']
        else:
            assert forms is None
        assert fixture.page.evaluate('window.valueReads') == 0
        assert fixture.page.evaluate('window.forbiddenClicks') == 0
        assert not fixture.unexpected
