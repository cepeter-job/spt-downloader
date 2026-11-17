"""L10-B observer pins and independent capability, synthetic runner-only."""
from copy import deepcopy

import pytest

import coretax_corporate as observer
import coretax_corporate_projection as projection
from coretax_json import JsonSafetyError
from test_corporate_l10b_nondisplay import ROUTE


class Capture:
    def __init__(self):
        self.calls = []
        self.failed = None

    def observe_component_lifetime(self, **kwargs):
        return None if self.failed == 'component' else {'synthetic': True}

    def bind_l10b_structure(self, form, tab, panel, *, phase, **kwargs):
        self.calls.append(phase)
        return self.failed != phase

    def observe_l10b_lifetime(self, **kwargs):
        return None if self.failed == 'final' else {'synthetic': True}


class Page:
    url = ROUTE
    def __init__(self): self.builds = dict(projection.L10B_BUILD_DIGESTS)
    def evaluate(self, script, url):
        assert "initiatorType==='script'" in script
        return self.builds.get(url)


def test_observer_supplies_only_own_source_proven_nondisplay_binding(monkeypatch):
    monkeypatch.setattr(observer, '_enabled_form_binding', lambda *args: True)
    page, capture = Page(), Capture()
    result = observer._observe_l10b(page, object(), object(), object(), capture, None)
    assert result == {'kind': 'corporate-l10b-nondisplay-v1',
                      'builds': dict(projection.L10B_BUILD_DIGESTS), 'route': ROUTE}
    assert capture.calls == ['start', 'end']


@pytest.mark.parametrize('defect', ['component', 'start', 'end', 'final', 'missing-protocol',
                                   'wrong-pin', 'null-pin', 'unloaded', 'disabled'])
def test_missing_proof_or_arbitrary_sha_cannot_get_nondisplay_permission(monkeypatch, defect):
    page, capture = Page(), Capture()
    original = deepcopy(page.builds)
    monkeypatch.setattr(observer, '_enabled_form_binding', lambda *args: defect != 'disabled')
    if defect == 'missing-protocol': capture = object()
    elif defect == 'wrong-pin': page.builds[projection.CIT_SOURCE] = '0' * 64
    elif defect == 'null-pin':
        monkeypatch.setattr(projection, 'load_build_pins', lambda: {})
        page.builds = dict.fromkeys(original)
    elif defect == 'unloaded': page.builds = {}
    else: capture.failed = defect
    assert observer._observe_l10b(page, object(), object(), object(), capture, None) is None


def test_custody_safety_error_is_not_demoted(monkeypatch):
    monkeypatch.setattr(observer, '_enabled_form_binding', lambda *args: True)
    capture = Capture()
    def changed(*args, **kwargs): raise JsonSafetyError('synthetic custody change')
    capture.bind_l10b_structure = changed
    with pytest.raises(JsonSafetyError):
        observer._observe_l10b(Page(), object(), object(), object(), capture, None)


@pytest.mark.parametrize('available', [False, True])
def test_main_observer_dispatches_own_binding_and_refuses_missing_capability(monkeypatch, available):
    from test_issue143_failure_stages import _observe_with_tabs
    calls = []
    proof = {'kind': 'corporate-l10b-nondisplay-v1', 'builds': {}, 'route': 'synthetic'}
    def own(*args):
        calls.append(args)
        return deepcopy(proof) if available else None
    # This test owns only dispatch. The real pin/lifetime helper is tested
    # above; the shared tab harness intentionally has no source authority.
    monkeypatch.setattr(observer, '_observe_l10b', own)
    captions = list(observer.FORMS)
    flags = [name not in ('Induk', 'L10-B') for name in captions]
    forms, inspected = _observe_with_tabs(monkeypatch, flags, captions)
    assert len(calls) == 1 and inspected == ['Induk', 'L10-B']
    if available:
        binding, = [f for f in forms if f['name'] == 'L10-B']
        assert binding['projection'] == proof and binding['paths'] == [['L10bFormData']]
        assert binding['grids'] == []
    else:
        assert forms is None
