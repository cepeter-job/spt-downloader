"""Optional original-only observer offers never assert final Induk selection."""
import pytest

import coretax_corporate as observer
import coretax_corporate_l10d as l10d
from coretax_browser import CaptureCancelled
from coretax_build_pins import load_build_pins
from coretax_json import JsonSafetyError
from test_corporate_l10d_native import DETAIL, PROVIDERS


class Page:
    url = DETAIL

    def __init__(self):
        self.reads = []
        self.builds = {url: load_build_pins().get(url) for url in PROVIDERS}
        self.on_read = None

    def evaluate(self, script, url):
        assert 'initiatorType' in script and 'SHA-256' in script
        self.reads.append(url)
        if self.on_read:
            self.on_read()
        return self.builds.get(url)


class Capture:
    def __init__(self):
        self.reads = 0
        self.lifetime = {'synthetic': True}

    def observe_component_lifetime(self, **kwargs):
        self.reads += 1
        return self.lifetime


def observe(page, capture, **kwargs):
    method = getattr(observer, '_observe_l10d_originals', None)
    assert callable(method), 'Original-only producer absent: source-only RED'
    return method(page, object(), object(), capture,
                  load_build_pins().get(PROVIDERS[0]), kwargs.get('check_cancel'))


def test_optional_observer_offer_carries_only_loaded_pins_and_current_owner(monkeypatch):
    page, capture = Page(), Capture()
    calls = []
    monkeypatch.setattr(observer, '_enabled_form_binding', lambda *args: calls.append(args) or True)
    result = observe(page, capture)
    assert result == {'kind': 'corporate-l10d-originals-v1', 'builds': page.builds,
        'route': DETAIL, 'owner_binding': 'observed-enabled-after-induk-v1'}
    assert page.reads == list(PROVIDERS) and capture.reads == 2 and len(calls) == 2
    assert not ({'final_selection', 'native_admission', 'fields', 'projection'} & result.keys())


def test_real_observer_dispatch_and_capture_held_replay_retain_originals_but_use_whole_dom(tmp_path, monkeypatch):
    import coretax_browser as driver
    import coretax_json as adapter
    import json
    from coretax_corporate import FORMS
    from coretax_json import adapt_corporate_detail
    from coretax_json_capture import DetailJsonCapture, checkpoint_bodies
    from support_json_network import Context, exchange
    import support_json_corpus as corpus
    from test_json_capture import Page as NetworkPage
    from test_corporate_component_lifetime import Document, navigate
    from test_corporate_l7_native import REQUEST, selected
    from test_corporate_l10d_native import envelope

    class Tab:
        def __init__(self, name): self.name = name
        def evaluate(self, script): return self.name not in ('Induk', 'L10-D')
        def inner_text(self): return self.name
    class Tabs:
        def __init__(self): self.items = [Tab(name) for name in FORMS]
        def count(self): return len(self.items)
        def nth(self, index): return self.items[index]
    class Form:
        def count(self): return 1
        def is_visible(self): return True
    class Panel:
        def locator(self, selector): return Form()
    context = Context()
    context._spt_financial_route_policy = 'service_workers_blocked'
    page = NetworkPage(context, corpus.LIST_URL)
    page.generation = object()
    page.evaluate_handle = lambda script: Document(page)
    builds = {url: load_build_pins().get(url) for url in PROVIDERS}
    def evaluate(script, url=None):
        if url is not None:
            return builds[url]
        if 'source_owner' in script:
            return {'source_owner': page.url == corpus.LIST_URL, 'detail_owner': page.url == DETAIL}
        return None
    page.evaluate = evaluate
    monkeypatch.setattr(observer, '_tabs', lambda page: (object(), Tabs()))
    monkeypatch.setattr(observer, '_native_panel', lambda *args: Panel())
    monkeypatch.setattr(observer, '_enabled_form_binding', lambda *args: True)
    observed = []
    def collect(*args, **kwargs):
        forms = observer.observe_forms(*args, approved_digest=builds[PROVIDERS[0]], **kwargs)
        observed.append(forms)
        return forms
    monkeypatch.setattr(driver, 'observe_corporate_forms', collect)
    calls = []
    def dom(*args, **kwargs):
        calls.append('whole-record-dom')
        return {'sections': [{'name': 'SYNTHETIC DOM', 'fields': [], 'tables': [], 'text': ''}],
                'capture_complete': True, 'errors': [], 'attachments': []}
    monkeypatch.setattr(driver, 'capture_detail', dom)
    monkeypatch.setattr(driver, 'capture_financial_detail',
                        lambda *args, **kwargs: pytest.fail('Original-only proof must not select native'))
    # Even a caller suppressing the display-oriented dump check cannot turn
    # original custody into final semantic admission. The adapter owns refusal.
    monkeypatch.setattr(adapter, 'has_audit_dump_tables', lambda sections: False)
    record = selected()
    raw = corpus.wire(envelope()).encode()
    with DetailJsonCapture(context, page, record, corpus.SCOPE, tmp_path) as capture:
        capture.begin_readonly_view()
        navigate(page, DETAIL)
        response = exchange(context, page, raw=raw, url=corpus.PRIMARY_URL, post=dict(REQUEST))
        capture.bind_detail_page(page)
        result = driver._hybrid_detail(page, record, corpus.SCOPE, tmp_path, capture, 1000, None)
        assert calls == ['whole-record-dom'] and result['detail_source']['used'] == 'dom'
        assert result['detail_source']['reason'] == 'unverified_corporate_l10d_final_selection_custody'
        candidate, = result['detail_source']['json']['non_display_originals']
        assert candidate['native_admission'] is False and len(candidate['originals']['values']) == 14
        assert observed[0] is not None
        item, = [item for item in observed[0] if item['name'] == 'L10-D']
        assert item['original_custody']['builds'] == builds and 'projection' not in item
        manifest = capture.drain()
        assert manifest['complete'] and 'component_lifetime' in manifest
        bodies = list(capture.iter_bodies())
        assert len(bodies) == 1 and bodies[0]['body'] == raw and response.reads == 1
        record['detail_url'] = DETAIL
        page.evaluate_handle = lambda *args: pytest.fail('Held replay must not use a browser')
        held = checkpoint_bodies(tmp_path, manifest, record, corpus.SCOPE)
        assert held == bodies
        replay = adapt_corporate_detail(held, record, corpus.SCOPE, observed[0])
        assert not replay['eligible'] and replay['provenance']['non_display_originals'] == [candidate]
        assert (tmp_path / manifest['responses'][0]['relative_path']).read_bytes() == raw
        saved = {**record, **result, 'detail_url': DETAIL, 'scope': list(corpus.SCOPE)}
        checkpoint = tmp_path / 'returns' / '0001.json'
        checkpoint.write_text(json.dumps(saved), encoding='utf-8')
        checkpoint_bytes = checkpoint.read_bytes()
        restored = driver.read_detail_checkpoint(checkpoint, record, corpus.SCOPE, detail_source='json-first')
        assert restored['detail_source']['used'] == 'dom'
        assert restored['detail_source']['json']['non_display_originals'] == [candidate]
        assert checkpoint.read_bytes() == checkpoint_bytes


@pytest.mark.parametrize('index', [0, 1, 2])
@pytest.mark.parametrize('value', [None, '', 'approved', 'a' * 64])
def test_missing_or_wrong_loaded_pin_cannot_produce_an_offer(monkeypatch, index, value):
    monkeypatch.setattr(observer, '_enabled_form_binding', lambda *args: True)
    page = Page()
    page.builds[PROVIDERS[index]] = value
    assert observe(page, Capture()) is None


@pytest.mark.parametrize('phase', ['start', 'end'])
@pytest.mark.parametrize('defect', ['owner', 'lifetime'])
def test_missing_current_owner_or_lifetime_is_not_inferred(monkeypatch, phase, defect):
    class ChangedCapture(Capture):
        def observe_component_lifetime(self, **kwargs):
            value = super().observe_component_lifetime(**kwargs)
            return None if self.reads == (1 if phase == 'start' else 2) else value
    calls = []
    def enabled(*args):
        calls.append(None)
        return not (defect == 'owner' and len(calls) == (1 if phase == 'start' else 2))
    monkeypatch.setattr(observer, '_enabled_form_binding', enabled)
    assert observe(Page(), ChangedCapture() if defect == 'lifetime' else Capture()) is None


def test_missing_loader_pins_plus_missing_loaded_assets_is_not_positive_equality(monkeypatch):
    monkeypatch.setattr(l10d, 'load_build_pins', lambda: {})
    page = Page()
    page.builds = dict.fromkeys(PROVIDERS)
    assert observe(page, Capture()) is None
    assert page.reads == []


def test_observer_stop_and_explicit_safety_failure_remain_fatal(monkeypatch):
    monkeypatch.setattr(observer, '_enabled_form_binding', lambda *args: True)
    page = Page()
    stopped = False
    def stop():
        if stopped:
            raise CaptureCancelled()
    def on_read():
        nonlocal stopped
        stopped = True
    page.on_read = on_read
    with pytest.raises(CaptureCancelled):
        observe(page, Capture(), check_cancel=stop)
    class UnsafeCapture(Capture):
        def observe_component_lifetime(self, **kwargs):
            raise JsonSafetyError('SYNTHETIC custody failure')
    with pytest.raises(JsonSafetyError):
        observe(Page(), UnsafeCapture())
