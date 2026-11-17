"""Actual loaded-script providers -> D observer/history -> held originals.

This is a real synthetic SPA, not live acceptance or a native-positive claim:
D final joint capability is deliberately still absent pending shared integration.
"""
import hashlib

import pytest

import coretax_corporate as observer
import coretax_corporate_l10d as owner
from coretax_json import adapt_corporate_detail
from coretax_json_capture import DetailJsonCapture, checkpoint_bodies
from l1d_observer_fixture import Fixture as BaseFixture
from test_corporate_l1d_observer import open_selected
from test_corporate_l10d_native import envelope, DETAIL, PROVIDERS
from test_json_hybrid_native import browser as browser
import support_json_corpus as corpus


class Fixture(BaseFixture):
    def __init__(self, browser, monkeypatch, *, defect=None, large_main=False):
        self.large_main = large_main
        super().__init__(browser, monkeypatch, defect=defect)
        self.raw = corpus.wire(envelope()).encode()
        monkeypatch.setattr(owner, 'load_build_pins', lambda: dict(self.pins))
        monkeypatch.setattr(observer, 'load_build_pins', lambda: dict(self.pins))

    def route(self, route):
        if self.large_main and route.request.url == PROVIDERS[1]:
            self.assets[PROVIDERS[1]] = b'/*' + b' ' * (4 * 1024 * 1024) + b'*/'
            self.pins[PROVIDERS[1]] = hashlib.sha256(self.assets[PROVIDERS[1]]).hexdigest()
        return super().route(route)

    def detail(self):
        tabs, panels = [], []
        for index, (name, _) in enumerate(observer.FORMS.items()):
            enabled = name in ('Induk', 'L10-D')
            tabs.append('<li' + ('' if enabled else ' class="p-disabled"') + '><a role="tab" '
                'aria-controls="panel-' + str(index) + '" href="#" onclick="show(' + str(index)
                + ');return false">' + name + '</a></li>')
            body = ('<rshshr-citr-main-form><label>SYNTHETIC STRUCTURE</label></rshshr-citr-main-form>'
                if name == 'Induk' else '<rshshr-citr-l10d-form><h2>SYNTHETIC D</h2>'
                '<input value="SYNTHETIC BAIT" type="checkbox" checked></rshshr-citr-l10d-form>'
                if name == 'L10-D' else '')
            panels.append('<div class="p-tabview-panel" role="tabpanel" id="panel-' + str(index)
                + '"' + ('' if name == 'Induk' else ' style="display:none"') + '>' + body + '</div>')
        return ('<style>rshshr-citr-l10d-form{display:block}</style>'
            '<rshshr-corporate-income-tax-return><div class="main-content"><div class="p-tabview">'
            '<ul class="p-tabview-nav">' + ''.join(tabs) + '</ul><div class="p-tabview-panels">'
            + ''.join(panels) + '</div></div></div></rshshr-corporate-income-tax-return>')


def observe(fixture, capture):
    return observer.observe_forms(fixture.page, fixture.record, corpus.SCOPE, capture,
                                  approved_digest=fixture.pins[PROVIDERS[0]])


@pytest.mark.parametrize('large_main', [False, True])
def test_loaded_positive_d_providers_and_real_capture_held_originals_are_not_final_proof(
        browser, tmp_path, monkeypatch, large_main):
    fixture = Fixture(browser, monkeypatch, large_main=large_main)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            assert page.url == DETAIL
            forms = observe(fixture, capture)
            assert forms is not None
            binding, = [form for form in forms if form['name'] == 'L10-D']
            assert binding['original_custody']['builds'] == fixture.pins
            assert capture._l10d_history.requested
            state = capture._l10d_history.handle.evaluate('(h) => h.sample()')
            assert state == {'available': True, 'changed': False, 'complete': True}
            # This is an explicit non-final observation. Production drain must
            # not mislabel it as the last joint sample of D and sibling histories.
            page.get_by_role('tab', name='Induk', exact=True).click()
            manifest = capture.drain()
            assert manifest['complete'] and 'corporate_l10d_lifetime' not in manifest
            bodies = list(capture.iter_bodies())
            assert len(bodies) == 1 and bodies[0]['body'] == fixture.raw
            result = adapt_corporate_detail(bodies, fixture.record, corpus.SCOPE, forms)
            assert not result['eligible'] and result['reason'] == owner.FINAL_CUSTODY_BLOCKER
            candidate, = result['provenance']['non_display_originals']
            assert candidate['native_admission'] is False
            assert len(candidate['originals']['values']) == 14
            fixture.record['detail_url'] = DETAIL
            held = checkpoint_bodies(tmp_path, manifest, fixture.record, corpus.SCOPE)
            assert held == bodies
            replay = adapt_corporate_detail(held, fixture.record, corpus.SCOPE, forms)
            assert replay['provenance'] == result['provenance']
            assert page.evaluate('window.businessReads') == page.evaluate('window.forbiddenClicks') == 0
            assert fixture.unexpected == []
            for url in PROVIDERS:
                assert fixture.requests.count((url, 'GET')) >= 2
                assert hashlib.sha256(fixture.assets[url]).hexdigest() == fixture.pins[url]
    finally:
        fixture.close()


@pytest.mark.parametrize('provider', ['corporate', 'main', 'vendor'])
@pytest.mark.parametrize('transport', ['fetch-only', 'preload-only'])
def test_real_non_script_provider_cannot_offer_d_original_custody(
        browser, tmp_path, monkeypatch, provider, transport):
    fixture = Fixture(browser, monkeypatch, defect=provider + '-' + transport)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            open_selected(fixture, capture)
            forms = observe(fixture, capture)
            assert forms is not None
            binding, = [form for form in forms if form['name'] == 'L10-D']
            assert 'original_custody' not in binding
            assert fixture.page.evaluate('window.businessReads') == 0
            assert fixture.unexpected == []
    finally:
        fixture.close()
