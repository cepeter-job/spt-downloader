from conftest import pin_override
"""Source-bound L11-B proof producer; synthetic execution on Actions only."""
from types import SimpleNamespace

import pytest

import coretax_corporate as observer
import coretax_corporate_projection as projection
from test_corporate_l11b_projection import route, selected
import support_json_corpus as corpus


@pytest.mark.parametrize('defect', [None, 'missing-main', 'wrong-main', 'missing-approved-main',
                                    'missing-approved-and-observed-main'])
def test_observer_emits_only_exact_two_pin_proof(monkeypatch, defect):
    class Tab:
        def __init__(self, name):
            self.name = name

        def evaluate(self, script):
            return self.name not in ('Induk', 'L11-B')

        def inner_text(self):
            return self.name

    tabs = [Tab(name) for name in observer.FORMS]
    monkeypatch.setattr(observer, '_tabs', lambda page: (object(), SimpleNamespace(
        count=lambda: len(tabs), nth=lambda index: tabs[index])))
    form = SimpleNamespace(count=lambda: 1, is_visible=lambda: True)
    panel = SimpleNamespace(locator=lambda selector: form)
    monkeypatch.setattr(observer, '_native_panel', lambda *args: panel)
    # The validator resolves cit+main+vendor, so the override must carry all three.
    pins = dict(projection.L11B_HYDRATED_BUILD_DIGESTS)
    assets = dict(pins)
    if defect in ('missing-main', 'missing-approved-and-observed-main'):
        assets.pop(projection.MAIN_SOURCE)
    if defect == 'wrong-main':
        assets[projection.MAIN_SOURCE] = 'a' * 64
    if defect in ('missing-approved-main', 'missing-approved-and-observed-main'):
        pins.pop(projection.MAIN_SOURCE)
    pin_override(monkeypatch, pins)
    probes = []

    def evaluate(script, url=None):
        # The page double must serve both shapes the observer uses: a bare
        # expression (locale) and a script digest probed per URL.
        if url is None:
            return 'id-ID'
        probes.append((script, url))
        return assets.get(url)

    page = SimpleNamespace(url=route(), evaluate=evaluate)
    forms = observer.observe_forms(page, selected(), corpus.SCOPE, object(),
                                   approved_digest=assets[projection.CIT_SOURCE])
    # The v1 L11-B proof verifies the two providers it binds (cit+main); the
    # third (vendor) probe belongs to the hydrated profile, which needs the
    # capture lifetime protocol this double does not provide. Assert the
    # invariant rather than an exact order: a defect may stop the walk early,
    # which is exactly what must keep the binding refused.
    probed = {url for _, url in probes if url is not None}
    assert projection.CIT_SOURCE in probed
    if defect is None:
        assert probed == {projection.CIT_SOURCE, projection.MAIN_SOURCE}
    if defect is not None:
        assert forms is None
    else:
        assert forms is not None
        binding, = [form for form in forms if form['name'] == 'L11-B']
        assert binding['projection'] == {
            'kind': 'corporate-l11b-v1',
            'builds': {projection.CIT_SOURCE: assets[projection.CIT_SOURCE],
                       projection.MAIN_SOURCE: assets[projection.MAIN_SOURCE]},
            'route': route()}
        assert binding['paths'] == [['L11BFormData']]
        assert binding['grids'] == []
