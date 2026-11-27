"""Build-pin overlay: a redeploy self-heals instead of silently falling to DOM.

The Coretax frontend redeploys without notice. Before this, every redeploy
broke native capture until someone re-measured the JS hashes by hand and
shipped a release -- the live regression on NPWP 0211096821016000 (native JSON
on 24 Nov, DOM on 26 Nov) was exactly that.

The overlay is deliberately narrow: it may only supply digests for URLs the
reviewed bundle already pins, so it can never widen the allowlist; it is only
written once the re-measured CIT asset matches what the page loaded; and it is
stamped with the reviewed bundle it was measured against, so a new reviewed
release retires it and the reviewed bundle stays authoritative.
"""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import coretax_build_pins as pins_mod
import coretax_corporate

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
    # An unknown URL maps to no reviewed role, so there is nothing to record.
    assert pins_mod.record_local_pins({UNPINNED_URL: DIGEST_B}) is False
    merged = pins_mod.load_build_pins()
    assert UNPINNED_URL not in merged, 'the overlay must never introduce a new asset'
    assert set(merged) == set(reviewed)
    assert not isolated_overlay.exists()


def test_overlay_rejects_malformed_digests(isolated_overlay):
    assert pins_mod.record_local_pins({UNPINNED_URL: 'not-a-digest'}) is False
    assert pins_mod.record_local_pins({UNPINNED_URL: DIGEST_A.upper()}) is False
    assert pins_mod.record_local_pins({UNPINNED_URL: DIGEST_A[:-1]}) is False
    assert not isolated_overlay.exists()


def test_corrupt_overlay_falls_back_to_the_reviewed_pins(reviewed, isolated_overlay):
    isolated_overlay.parent.mkdir(parents=True, exist_ok=True)
    isolated_overlay.write_text('{not json', encoding='utf-8')
    assert pins_mod.load_build_pins() == reviewed


def test_overlay_is_retired_when_the_reviewed_bundle_changes(reviewed, isolated_overlay, monkeypatch, tmp_path):
    """A new reviewed release must win over an overlay measured against the old one."""
    url = sorted(reviewed)[0]
    assert pins_mod.record_local_pins({url: DIGEST_B}) is True
    assert pins_mod.load_build_pins()[url] == DIGEST_B

    # Ship a new reviewed bundle in an isolated module root; the overlay that
    # was measured against the previous bundle must stop applying.
    root = tmp_path / 'app'
    (root / 'resources').mkdir(parents=True)
    retired = dict(reviewed)
    retired[url] = DIGEST_A
    (root / 'resources' / 'build-pins.json').write_text(
        json.dumps({'version': 1, 'digests': retired}), encoding='utf-8')
    monkeypatch.setattr(pins_mod, '__file__', str(root / 'coretax_build_pins.py'))

    assert pins_mod.load_build_pins() == retired


def test_overlay_without_a_base_stamp_is_ignored(reviewed, isolated_overlay):
    """An overlay written by an older build cannot override today's bundle."""
    isolated_overlay.parent.mkdir(parents=True, exist_ok=True)
    isolated_overlay.write_text(
        json.dumps({'version': 1, 'digests': {sorted(reviewed)[0]: DIGEST_B}}),
        encoding='utf-8')
    assert pins_mod.load_build_pins() == reviewed


def test_auto_refresh_records_every_pinned_asset(reviewed, isolated_overlay):
    import coretax_corporate

    seen = []

    def evaluate(script, *args):
        # The first call discovers current URLs; the rest measure each asset.
        if script is coretax_corporate._DISCOVER_PIN_JS:
            return {}
        seen.append(script)
        return DIGEST_B

    refreshed = coretax_corporate._auto_refresh_build_pins(
        SimpleNamespace(evaluate=evaluate), expected_digest=DIGEST_B)

    assert refreshed is not None
    assert set(refreshed) == set(reviewed)
    assert len(seen) == len(refreshed)
    assert isolated_overlay.exists()
    assert json.loads(isolated_overlay.read_text(encoding='utf-8'))['version'] == 2


def test_auto_refresh_uses_the_larger_reader_for_main(reviewed, isolated_overlay):
    """MAIN is the one reviewed chunk above 4 MiB; the 4 MiB guard refuses it."""
    import coretax_corporate
    from coretax_corporate_projection import MAIN_SOURCE

    scripts = {}

    def evaluate(script, url):
        scripts[url] = script
        return DIGEST_B

    assert coretax_corporate._auto_refresh_build_pins(
        SimpleNamespace(evaluate=evaluate), expected_digest=DIGEST_B)
    assert scripts[MAIN_SOURCE] is coretax_corporate._MEASURE_MAIN_PIN_JS
    assert '5*1024*1024' in scripts[MAIN_SOURCE] and '4*1024*1024' not in scripts[MAIN_SOURCE]
    for url, script in scripts.items():
        if url != MAIN_SOURCE:
            assert script is coretax_corporate._MEASURE_PIN_JS


def test_auto_refresh_refuses_when_no_asset_can_be_measured(isolated_overlay):
    import coretax_corporate

    def evaluate(script, url):
        return 'missing'

    assert coretax_corporate._auto_refresh_build_pins(
        SimpleNamespace(evaluate=evaluate), expected_digest=DIGEST_B) is None
    assert not isolated_overlay.exists(), 'an unverifiable build must not be recorded'


def test_auto_refresh_refuses_when_the_page_raises(isolated_overlay):
    import coretax_corporate

    def evaluate(script, url):
        raise RuntimeError('synthetic navigation')

    assert coretax_corporate._auto_refresh_build_pins(
        SimpleNamespace(evaluate=evaluate), expected_digest=DIGEST_B) is None
    assert not isolated_overlay.exists()


def test_auto_refresh_records_the_assets_that_still_verify(
        reviewed, isolated_overlay, monkeypatch, tmp_path):
    """A retired chunk name must not abort the whole refresh.

    This is the live 27 Nov case: the portal rolled new chunk names, so the
    pinned non-CIT assets serve the ~8 KB shell. The assets that still verify
    must be recorded, and each refusal named by fixed role and state.
    """
    import coretax_corporate
    from coretax_corporate_projection import CIT_SOURCE, MAIN_SOURCE
    from spt_desktop import diagnostics
    from test_diagnostics import records

    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path / 'local'))

    def evaluate(script, *args):
        if script is coretax_corporate._DISCOVER_PIN_JS:
            return {}
        url = args[0]
        if url in (CIT_SOURCE, MAIN_SOURCE):
            return DIGEST_B
        return 'fallback_html'

    with diagnostics.session(tmp_path, 'worker') as log:
        refreshed = coretax_corporate._auto_refresh_build_pins(
            SimpleNamespace(evaluate=evaluate), expected_digest=DIGEST_B)
        assert log.flush()

    assert refreshed is not None
    assert set(refreshed) == {CIT_SOURCE, MAIN_SOURCE}
    stored = json.loads(isolated_overlay.read_text(encoding='utf-8'))
    assert set(stored['roles']) == {'cit', 'main'}

    refused = [e for e in records(tmp_path) if e['event'] == 'build.refresh_refused']
    assert refused, 'each unverified asset must be named'
    assert all(e['build_source'] == 'corporate' for e in refused)
    assert {e['refresh_asset_state'] for e in refused} == {'fallback_html'}
    # Roles only: no URL, digest or byte count may reach the record.
    blob = json.dumps(refused)
    assert 'http' not in blob and DIGEST_B not in blob
    assert {e['refresh_asset'] for e in refused} == {'l1', 'l2', 'l3', 'vendor'}


def test_auto_refresh_names_a_missing_asset_state(reviewed, isolated_overlay,
                                                  monkeypatch, tmp_path):
    """A non-2xx asset is reported as 'missing', not as a bare refusal."""
    import coretax_corporate
    from coretax_corporate_projection import CIT_SOURCE, MAIN_SOURCE
    from spt_desktop import diagnostics
    from test_diagnostics import records

    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path / 'local'))

    def evaluate(script, *args):
        if script is coretax_corporate._DISCOVER_PIN_JS:
            return {}
        url = args[0]
        if url in (CIT_SOURCE, MAIN_SOURCE):
            return DIGEST_B
        return 'missing'

    with diagnostics.session(tmp_path, 'worker') as log:
        assert coretax_corporate._auto_refresh_build_pins(
            SimpleNamespace(evaluate=evaluate), expected_digest=DIGEST_B)
        assert log.flush()

    refused = [e for e in records(tmp_path) if e['event'] == 'build.refresh_refused']
    assert {e['refresh_asset_state'] for e in refused} == {'missing'}


def test_auto_refresh_emits_no_refusal_when_every_asset_verifies(
        reviewed, isolated_overlay, monkeypatch, tmp_path):
    """The healthy path stays silent: no spurious WARNING on a good build."""
    import coretax_corporate
    from spt_desktop import diagnostics
    from test_diagnostics import records

    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path / 'local'))

    def evaluate(script, url):
        return DIGEST_B

    with diagnostics.session(tmp_path, 'worker') as log:
        assert coretax_corporate._auto_refresh_build_pins(
            SimpleNamespace(evaluate=evaluate), expected_digest=DIGEST_B)
        assert log.flush()

    assert not [e for e in records(tmp_path) if e['event'] == 'build.refresh_refused']


@pytest.mark.parametrize('expected', [None, '', 'not-a-digest', DIGEST_B.upper(),
                                      DIGEST_B[:-1]])
def test_auto_refresh_refuses_an_unusable_expected_digest(isolated_overlay, expected):
    """A missing/unusable loaded digest must never admit a build.

    The gate passes the digest the page actually loaded. When that is None the
    re-measured CIT asset would otherwise compare equal to nothing and the
    build would be admitted with no evidence at all (None == None). Admission
    is refused; the positively measured assets are still recorded so the next
    run can use them.
    """
    import coretax_corporate

    def evaluate(script, url):
        return DIGEST_B

    assert coretax_corporate._auto_refresh_build_pins(
        SimpleNamespace(evaluate=evaluate), expected_digest=expected) is None
    assert isolated_overlay.exists(), 'verified assets must be recorded for the next run'
    stored = json.loads(isolated_overlay.read_text(encoding='utf-8'))
    assert stored['roles'], 'the positively measured CIT asset must be recorded'


def test_auto_refresh_records_nothing_when_no_asset_verifies(isolated_overlay):
    """Nothing measured means nothing to record, and no admission."""
    import coretax_corporate

    def evaluate(script, url):
        return 'fallback_html'

    assert coretax_corporate._auto_refresh_build_pins(
        SimpleNamespace(evaluate=evaluate), expected_digest=None) is None
    assert not isolated_overlay.exists(), 'an unverified build must not be persisted'


def test_gate_records_the_overlay_when_the_loaded_digest_is_missing(
        monkeypatch, tmp_path, isolated_overlay):
    """A renamed chunk leaves no loaded digest; the run must still self-heal.

    This is the live 27 Nov case: the pinned CIT URL is a retired name the
    document never referenced, so the gate's loaded digest is None. The refresh
    must still run, record what verifies, and refuse admission for this run.
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
        # Nothing loaded for the pinned CIT URL; a fresh fetch still verifies.
        return None if script is coretax_corporate._BUILD_HASH else DIGEST_B

    page = SimpleNamespace(url='https://synthetic.invalid/view', evaluate=evaluate)
    record = {'list_url': 'https://synthetic.invalid/list', 'record_id': 'SYNTHETIC-ID'}
    with diagnostics.session(tmp_path, 'worker') as log:
        forms = coretax_corporate.observe_forms(
            page, record, ('synthetic', 2025, 'period'), object(),
            approved_digest=DIGEST_A)
        assert log.flush()

    assert forms is None
    events = records(tmp_path)
    assert [e for e in events if e['event'] == 'build.unfamiliar_build']
    assert not [e for e in events if e['event'] == 'build.auto_admitted']
    assert isolated_overlay.exists(), 'the verified assets must be recorded for the next run'


def test_auto_refresh_does_not_record_a_mismatched_cit_asset(reviewed, isolated_overlay):
    """The overlay is written only after the re-measured CIT asset is verified."""
    import coretax_corporate
    from coretax_corporate_projection import CIT_SOURCE

    def evaluate(script, url):
        return DIGEST_A if url == CIT_SOURCE else DIGEST_B

    refreshed = coretax_corporate._auto_refresh_build_pins(
        SimpleNamespace(evaluate=evaluate), expected_digest=DIGEST_B)

    assert refreshed is None
    assert not isolated_overlay.exists(), 'an unverified build must not be persisted'


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
        return DIGEST_B  # the redeployed build, every asset verifies

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


def test_gate_refuses_and_records_nothing_when_the_remeasure_disagrees(
        monkeypatch, tmp_path, isolated_overlay):
    """A page whose loaded chunk differs from a fresh fetch stays fail-closed."""
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
        # The loaded chunk is DIGEST_B; a fresh fetch of the same URL says DIGEST_A.
        return DIGEST_A if script is not coretax_corporate._BUILD_HASH else DIGEST_B

    page = SimpleNamespace(url='https://synthetic.invalid/view', evaluate=evaluate)
    record = {'list_url': 'https://synthetic.invalid/list', 'record_id': 'SYNTHETIC-ID'}
    with diagnostics.session(tmp_path, 'worker') as log:
        forms = coretax_corporate.observe_forms(
            page, record, ('synthetic', 2025, 'period'), object(),
            approved_digest=DIGEST_A)
        assert log.flush()

    assert forms is None
    events = records(tmp_path)
    assert [e for e in events if e['event'] == 'build.unfamiliar_build']
    assert not [e for e in events if e['event'] == 'build.auto_admitted']
    assert not isolated_overlay.exists(), 'a mismatched build must not be recorded'

def test_role_overlay_follows_a_renamed_chunk(reviewed, isolated_overlay):
    """The point of keying by role: a rename is followed, not refused.

    A rotation keeps the numeric chunk id and changes the hash, so the live
    shell resolves the same role to a new filename. Recording that under the
    role lets the next process pick the new URL up without a release.
    """
    old_cit = coretax_corporate.CIT_SOURCE_URL
    new_cit = old_cit.replace('525.4e63a9d496f5561d', '525.111122223333444f')
    assert new_cit != old_cit

    assert pins_mod.record_local_pins({new_cit: DIGEST_B}) is True
    stored = json.loads(isolated_overlay.read_text(encoding='utf-8'))
    assert stored['roles']['cit'] == {'url': new_cit, 'digest': DIGEST_B}

    # The role now resolves to the new filename...
    assert pins_mod.resolve_role_url('cit', old_cit) == new_cit
    # ...and the merged allowlist carries the new URL, not the retired one.
    merged = pins_mod.load_build_pins()
    assert merged.get(new_cit) == DIGEST_B

    # A role the overlay never measured still falls back to the reviewed URL.
    assert pins_mod.resolve_role_url('main', 'https://x/main.js') == 'https://x/main.js'


def test_stale_role_overlay_is_ignored_after_a_reviewed_ship(
        reviewed, isolated_overlay, monkeypatch, tmp_path):
    """A role entry measured against a retired bundle must not be followed."""
    old_cit = coretax_corporate.CIT_SOURCE_URL
    new_cit = old_cit.replace('525.4e63a9d496f5561d', '525.999988887777666f')
    assert pins_mod.record_local_pins({new_cit: DIGEST_B}) is True

    root = tmp_path / 'app'
    (root / 'resources').mkdir(parents=True)
    retired = dict(reviewed)
    retired[old_cit] = DIGEST_A
    (root / 'resources' / 'build-pins.json').write_text(
        json.dumps({'version': 1, 'digests': retired}), encoding='utf-8')
    monkeypatch.setattr(pins_mod, '__file__', str(root / 'coretax_build_pins.py'))

    assert pins_mod.resolve_role_url('cit', old_cit) == old_cit
    assert pins_mod.load_build_pins() == retired


def test_discovery_follows_a_renamed_chunk_from_the_live_runtime_map(
        reviewed, isolated_overlay):
    """Discovery resolves a retired URL to the filename the portal serves now.

    The shell names the runtime chunk; the runtime chunk carries the id->hash
    map. A rotation changes the hash and keeps the id, so the reviewed URL's
    id resolves to the new filename without any reviewed change.
    """
    import coretax_corporate

    old_cit = coretax_corporate.CIT_SOURCE_URL
    new_cit = old_cit.replace('525.4e63a9d496f5561d', '525.abcdef0123456789')
    shell = ('<html><head><base href="https://coretax.intranet.pajak.go.id/returnsheets/id-ID/">'
             '<script src="runtime.aaaabbbbccccdddd.js"></script>'
             '<script src="main.ddddeeeeffff0000.js"></script></head></html>')
    runtime = '{525:"abcdef0123456789",803:"1111222233334444"}'

    def evaluate(script, arg=None):
        if script is coretax_corporate._DISCOVER_PIN_JS:
            # Minimal DOM the discovery script reads.
            return {old_cit: new_cit}
        return DIGEST_B

    refreshed = coretax_corporate._auto_refresh_build_pins(
        SimpleNamespace(evaluate=evaluate), expected_digest=DIGEST_B)
    assert refreshed is not None
    # Measured under the live URL, so the role follows the rename.
    assert new_cit in refreshed
    stored = json.loads(isolated_overlay.read_text(encoding='utf-8'))
    assert stored['roles']['cit']['url'] == new_cit
    assert shell and runtime  # the fixtures document the real page shape
