"""Build-pin overlay: a redeploy self-heals instead of silently falling to DOM.

The Coretax frontend redeploys without notice. Before this, every redeploy
broke native capture until someone re-measured the JS hashes by hand and
shipped a release -- the live regression on NPWP 0211096821016000 (native JSON
on 24 Nov, DOM on 26 Nov) was exactly that.

The overlay is deliberately narrow: it may only supply digests for URLs the
reviewed bundle already pins, so it can never widen the allowlist, and the
reviewed bundle stays authoritative whenever it matches.
"""
import json
from types import SimpleNamespace

import pytest

import coretax_build_pins as pins_mod

DIGEST_A = 'a' * 64
DIGEST_B = 'b' * 64
UNPINNED_URL = 'https://synthetic.invalid/not-pinned.js'


@pytest.fixture
def isolated_overlay(monkeypatch, tmp_path):
    """Point the user-scoped overlay at a temp dir, never the real profile."""
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path / 'local'))
    return tmp_path / 'local' / 'SPTDownloader' / 'build-pins.local.json'


@pytest.fixture
def reviewed():
    """The reviewed bundle read verbatim, so a stray overlay cannot skew it."""
    from pathlib import Path
    target = Path(pins_mod.__file__).resolve().parent / 'resources' / 'build-pins.json'
    pins = pins_mod.load_build_pins(target)
    assert pins, 'the reviewed pin bundle must be present'
    return pins


def test_overlay_overrides_a_pinned_digest(reviewed, isolated_overlay):
    url = sorted(reviewed)[0]
    assert pins_mod.record_local_pins({url: DIGEST_B}) is True
    merged = pins_mod.load_build_pins()
    assert merged[url] == DIGEST_B
    for other, digest in reviewed.items():
        if other != url:
            assert merged[other] == digest


def test_explicit_path_is_never_merged_with_the_overlay(tmp_path, reviewed, isolated_overlay):
    url = sorted(reviewed)[0]
    target = tmp_path / 'build-pins.json'
    target.write_text(json.dumps({'version': 1, 'digests': {url: DIGEST_A}}), encoding='utf-8')
    assert pins_mod.record_local_pins({url: DIGEST_B}) is True
    assert pins_mod.load_build_pins(target)[url] == DIGEST_A


def test_overlay_cannot_widen_the_allowlist(reviewed, isolated_overlay):
    assert pins_mod.record_local_pins({UNPINNED_URL: DIGEST_B}) is True
    merged = pins_mod.load_build_pins()
    assert UNPINNED_URL not in merged, 'the overlay must never introduce a new asset'
    assert set(merged) == set(reviewed)


def test_overlay_rejects_malformed_digests(isolated_overlay):
    assert pins_mod.record_local_pins({UNPINNED_URL: 'not-a-digest'}) is False
    assert pins_mod.record_local_pins({UNPINNED_URL: DIGEST_A.upper()}) is False
    assert pins_mod.record_local_pins({UNPINNED_URL: DIGEST_A[:-1]}) is False
    assert not isolated_overlay.exists()


def test_corrupt_overlay_falls_back_to_the_reviewed_pins(reviewed, isolated_overlay):
    isolated_overlay.parent.mkdir(parents=True, exist_ok=True)
    isolated_overlay.write_text('{not json', encoding='utf-8')
    assert pins_mod.load_build_pins() == reviewed


def test_auto_refresh_records_every_pinned_asset(reviewed, isolated_overlay):
    import coretax_corporate

    seen = []

    def evaluate(script, url):
        seen.append(url)
        return DIGEST_B

    refreshed = coretax_corporate._auto_refresh_build_pins(SimpleNamespace(evaluate=evaluate))

    assert refreshed is not None
    assert set(refreshed) == set(reviewed)
    assert len(seen) == len(refreshed)
    assert isolated_overlay.exists()
    assert json.loads(isolated_overlay.read_text(encoding='utf-8'))['version'] == 1


def test_auto_refresh_refuses_when_any_asset_cannot_be_measured(isolated_overlay):
    import coretax_corporate

    def evaluate(script, url):
        return None

    assert coretax_corporate._auto_refresh_build_pins(SimpleNamespace(evaluate=evaluate)) is None
    assert not isolated_overlay.exists(), 'an unverifiable build must not be recorded'


def test_auto_refresh_refuses_when_the_page_raises(isolated_overlay):
    import coretax_corporate

    def evaluate(script, url):
        raise RuntimeError('synthetic navigation')

    assert coretax_corporate._auto_refresh_build_pins(SimpleNamespace(evaluate=evaluate)) is None
    assert not isolated_overlay.exists()


def test_gate_auto_admits_on_drift_and_emits_diagnostic(
        monkeypatch, tmp_path, isolated_overlay):
    """A redeploy is admitted only after every pinned asset re-measures.

    This is the live regression: NPWP 0211096821016000 captured native JSON on
    24 Nov and fell to DOM on 26 Nov purely because the portal redeployed. The
    gate must now re-verify and admit instead of silently degrading.
    """
    import coretax_browser
    import coretax_corporate
    import coretax_json
    from spt_desktop import diagnostics
    from test_diagnostics import records

    monkeypatch.setattr(coretax_browser, 'verify_detail_url', lambda *a: None)
    monkeypatch.setattr(coretax_browser, 'list_taxpayer_id', lambda url: 'SYNTHETIC-ID')
    monkeypatch.setattr(coretax_json, '_corporate_selected', lambda *a: {})
    monkeypatch.setattr(coretax_json, '_check_corporate_route', lambda *a: None)
    monkeypatch.setattr(coretax_corporate, '_tabs',
                        lambda page: (object(), SimpleNamespace(count=lambda: 0)))

    def evaluate(script, *args):
        return DIGEST_B  # the redeployed build

    page = SimpleNamespace(url='https://synthetic.invalid/view', evaluate=evaluate)
    record = {'list_url': 'https://synthetic.invalid/list', 'record_id': 'SYNTHETIC-ID'}
    with diagnostics.session(tmp_path, 'worker') as log:
        forms = coretax_corporate.observe_forms(
            page, record, ('synthetic', 2025, 'period'), object(),
            approved_digest=DIGEST_A)
        assert log.flush()

    assert forms is None, 'the stubbed tab list is empty, so observation stops'
    events = records(tmp_path)
    admitted = [e for e in events if e['event'] == 'build.auto_admitted']
    assert len(admitted) == 1 and admitted[0]['build_source'] == 'corporate'
    assert not [e for e in events if e['event'] == 'build.unfamiliar_build']
    assert isolated_overlay.exists(), 'the admitted build must be recorded'
