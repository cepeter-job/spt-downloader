"""Uncovered PPh21 observer gates, exercised with fake pages (no browser).

The browser defect fixtures pin the common gates; these fakes cover the
remaining fixed categories so the observer-gate diagnostic is fully
exercised without trusting new DOM shapes.
"""
import hashlib
import importlib

from masa_json_fixtures import SCOPE, TAXPAYER, selected
from pph21_observer_fixture import MAIN, ARTICLE, BUILD, browser  # noqa: F401  (browser unused; kept for parity)
from spt_desktop import diagnostics
from test_diagnostics import records

ORIGIN = 'https://coretax.intranet.pajak.go.id'
DETAIL_URL = ORIGIN + '/returnsheets/id-ID/synthetic/' + TAXPAYER + '/' + '00000000-0000-4000-8000-000000000001'


def module(monkeypatch):
    mod = importlib.import_module('coretax_pph21_observer')
    digest = hashlib.sha256(BUILD).hexdigest()
    monkeypatch.setattr(mod, 'BUILD_DIGESTS', {MAIN: digest, ARTICLE: digest})
    return mod


class FakeCapture:
    def __init__(self, events=()):
        self._events = list(events)

    def request_observations(self):
        return list(self._events)

    def drain(self):
        return {'complete': True, 'reasons': []}


class FakePage:
    def __init__(self, mod, *, env=None, fail_enabled=False, marker='Page 1 of 1'):
        self.url = DETAIL_URL
        self._mod = mod
        self._env = env or {'locale': 'id-ID', 'timezone': 'Asia/Jakarta'}
        self._fail = fail_enabled
        self._marker = marker

    def evaluate(self, expr, *args):
        if self._fail:
            raise RuntimeError('synthetic evaluate failure')
        if args and isinstance(args[0], str):
            return self._mod.BUILD_DIGESTS[args[0]]
        if 'locale' in expr:
            return dict(self._env)
        raise AssertionError('unexpected page.evaluate: ' + str(expr)[:60])


class FakeTab:
    def __init__(self, caption, *, disabled=False):
        self._caption = caption
        self._disabled = disabled

    def inner_text(self):
        return self._caption

    def evaluate(self, expr):
        return self._disabled


class FakeTabs:
    def __init__(self, captions, *, disabled_first=False):
        self._tabs = [FakeTab(c) for c in captions]
        if disabled_first and self._tabs:
            self._tabs[0]._disabled = True

    def count(self):
        return len(self._tabs)

    def nth(self, i):
        return self._tabs[i]


class FakeLocator:
    def __init__(self, page, *, count=1, visible=True, fields=(), grids=0,
                 marker='', metadata=None, inner='', tables=1):
        self._page = page
        self._count = count
        self._visible = visible
        self._fields = fields
        self._grids = grids
        self._marker = marker
        self._metadata = metadata or {}
        self._inner = inner
        self._tables = tables

    def count(self):
        return self._count

    def nth(self, index):
        return self

    def is_visible(self):
        return self._visible

    def inner_text(self):
        return self._inner

    def locator(self, selector):
        if selector == 'ui-grid':
            return FakeLocator(self._page, count=self._grids, marker=self._marker,
                               metadata=self._metadata)
        if selector == 'table:visible':
            return FakeLocator(self._page, count=self._tables, metadata=self._metadata,
                               marker=self._marker)
        if selector == '.p-paginator-current':
            return FakeLocator(self._page, count=1, inner=self._marker)
        if selector == 'p-table':
            return FakeLocator(self._page, count=1, marker=self._marker,
                               metadata=self._metadata)
        return FakeLocator(self._page, count=self._grid_count(selector),
                           grids=self._grids, marker=self._marker,
                           metadata=self._metadata, tables=self._tables)

    def _grid_count(self, selector):
        return self._count

    def evaluate(self, expr):
        if 'seen=new Set' in expr:
            return list(self._fields) if self._fields else []
        return dict(self._metadata)


class FakePanel:
    def __init__(self, page, *, root_count=1, fields=(), induk_grids=0,
                 root_grids=None, root_tables=1, first_grids=0,
                 marker='Page 1 of 1', metadata=None):
        self._page = page
        self._root_count = root_count
        self._fields = fields
        self._grids = root_grids if root_grids is not None else induk_grids
        self._marker = marker
        self._metadata = metadata or {'group': 'LIST-IA', 'headers': ['H']}
        self._root_tables = root_tables
        self._first_grids = first_grids
        self._calls = 0

    def locator(self, selector):
        # First root is Induk (no ui-grid expected); later roots are grid forms.
        self._calls += 1
        grids = self._first_grids if self._calls == 1 else self._grids
        return FakeLocator(self._page, count=self._root_count,
                           fields=self._fields, grids=grids,
                           marker=self._marker, metadata=self._metadata,
                           tables=self._root_tables)


def base_fakes(mod, monkeypatch, *, captions=None, panel=None, page=None, disabled_first=False):
    monkeypatch.setattr(mod, '_reference_order_build', lambda p, c: None)
    monkeypatch.setattr(mod, '_turn_grid', lambda p, t, m, c: True)
    monkeypatch.setattr(mod, '_pages', lambda *a, **k: [])
    captions = captions or ['Induk', 'L-IA', 'L-IB', 'L-II', 'L-III']
    monkeypatch.setattr(mod, '_tabs', lambda p: (None, FakeTabs(captions, disabled_first=disabled_first)))
    panel = panel or FakePanel(page if page is not None else object())
    return panel


def run(mod, monkeypatch, page, record, *, panel=None, captions=None,
        requests=(), observations=(), reference_bindings='skip', disabled_first=False):
    if reference_bindings != 'skip':
        monkeypatch.setattr(mod, '_reference_bindings',
                            lambda *a, **k: reference_bindings)
    else:
        monkeypatch.setattr(mod, '_reference_bindings', lambda *a, **k: [{}])
    monkeypatch.setattr(mod, '_requests', lambda *a, **k: list(requests))
    monkeypatch.setattr(mod, '_observations', lambda c, r, s: list(observations))
    panel_obj = panel if panel is not None else FakePanel(page)
    monkeypatch.setattr(mod, '_native_panel', lambda *a, **k: panel_obj)
    base_fakes(mod, monkeypatch, captions=captions, panel=panel_obj, page=page,
               disabled_first=disabled_first)
    return mod.observe_pph21_forms(page, record, SCOPE, FakeCapture(observations), max_pages=5)


def gates_in(root):
    return [row['pph21_observer_gate'] for row in records(root)
            if row['event'] == 'pph21.observer_gate']


def test_unsupported_tax_gate(monkeypatch, tmp_path):
    mod = module(monkeypatch)
    record = selected('PPN')
    root = tmp_path / 'd'
    with diagnostics.session(root, 'worker') as log:
        assert run(mod, monkeypatch, FakePage(mod), record) is None
        assert log.flush()
    assert gates_in(root) == ['unsupported_tax']


def test_environment_gate(monkeypatch, tmp_path):
    mod = module(monkeypatch)
    page = FakePage(mod, env={'locale': 'en-US', 'timezone': 'Asia/Jakarta'})
    root = tmp_path / 'd'
    with diagnostics.session(root, 'worker') as log:
        assert run(mod, monkeypatch, page, selected('PPh Pasal 21/26')) is None
        assert log.flush()
    assert gates_in(root) == ['environment']


def test_evaluation_error_gate(monkeypatch, tmp_path):
    mod = module(monkeypatch)
    page = FakePage(mod, fail_enabled=True)
    root = tmp_path / 'd'
    with diagnostics.session(root, 'worker') as log:
        assert run(mod, monkeypatch, page, selected('PPh Pasal 21/26')) is None
        assert log.flush()
    assert gates_in(root) == ['evaluation_error']


def test_form_root_gate(monkeypatch, tmp_path):
    mod = module(monkeypatch)
    page = FakePage(mod)
    panel = FakePanel(page, root_count=0)
    root = tmp_path / 'd'
    with diagnostics.session(root, 'worker') as log:
        assert run(mod, monkeypatch, page, selected('PPh Pasal 21/26'), panel=panel) is None
        assert log.flush()
    assert gates_in(root) == ['form_root']


def test_induk_grid_structure_gate(monkeypatch, tmp_path):
    mod = module(monkeypatch)
    page = FakePage(mod)
    panel = FakePanel(page, first_grids=1)
    root = tmp_path / 'd'
    with diagnostics.session(root, 'worker') as log:
        assert run(mod, monkeypatch, page, selected('PPh Pasal 21/26'), panel=panel) is None
        assert log.flush()
    assert gates_in(root) == ['grid_structure']


def test_reference_gate_from_manual_click(monkeypatch, tmp_path):
    mod = module(monkeypatch)
    page = FakePage(mod)
    panel = FakePanel(page)
    root = tmp_path / 'd'
    with diagnostics.session(root, 'worker') as log:
        assert run(mod, monkeypatch, page, selected('PPh Pasal 21/26'), panel=panel,
                   requests=[{'request_json': {'onManualClick': True}}]) is None
        assert log.flush()
    assert gates_in(root) == ['reference']


def test_reference_bindings_gate(monkeypatch, tmp_path):
    mod = module(monkeypatch)
    page = FakePage(mod)
    panel = FakePanel(page)
    flat = {name: (selector, None, ()) for name, (selector, _, _) in mod.FORMS.items()}
    monkeypatch.setattr(mod, 'FORMS', flat)
    root = tmp_path / 'd'
    with diagnostics.session(root, 'worker') as log:
        assert run(mod, monkeypatch, page, selected('PPh Pasal 21/26'), panel=panel,
                   reference_bindings=None) is None
        assert log.flush()
    assert gates_in(root) == ['reference_bindings']


def test_tab_disabled_gate(monkeypatch, tmp_path):
    mod = module(monkeypatch)
    page = FakePage(mod)
    root = tmp_path / 'd'
    with diagnostics.session(root, 'worker') as log:
        assert run(mod, monkeypatch, page, selected('PPh Pasal 21/26'), disabled_first=True) is None
        assert log.flush()
    assert gates_in(root) == ['tab_disabled']


def test_tab_caption_gate(monkeypatch, tmp_path):
    mod = module(monkeypatch)
    page = FakePage(mod)
    root = tmp_path / 'd'
    with diagnostics.session(root, 'worker') as log:
        assert run(mod, monkeypatch, page, selected('PPh Pasal 21/26'),
                   captions=['Induk', 'Unknown', 'L-IB', 'L-II', 'L-III']) is None
        assert log.flush()
    assert gates_in(root) in (['tab_set'], ['tab_caption'])


def test_roles_grid_mismatch_gate(monkeypatch, tmp_path):
    mod = module(monkeypatch)
    page = FakePage(mod)
    panel = FakePanel(page, root_grids=0, root_tables=1)
    root = tmp_path / 'd'
    with diagnostics.session(root, 'worker') as log:
        assert run(mod, monkeypatch, page, selected('PPh Pasal 21/26'), panel=panel) is None
        assert log.flush()
    assert gates_in(root) == ['grid_structure']


def test_total_gate(monkeypatch, tmp_path):
    mod = module(monkeypatch)
    page = FakePage(mod)
    panel = FakePanel(page, root_grids=1, root_tables=1, marker='No records')
    root = tmp_path / 'd'
    with diagnostics.session(root, 'worker') as log:
        assert run(mod, monkeypatch, page, selected('PPh Pasal 21/26'), panel=panel) is None
        assert log.flush()
    assert gates_in(root) == ['total']


def test_reference_bindings_internal_gate(monkeypatch, tmp_path):
    """A failing reference GET records 'reference' from inside _reference_bindings."""
    mod = module(monkeypatch)
    page = FakePage(mod)
    panel = FakePanel(page)
    root = tmp_path / 'd'
    with diagnostics.session(root, 'worker') as log:
        # Call the real _reference_bindings with a failing GET result.
        page.evaluate = lambda expr, *a: {'ok': False, 'status': 0}
        assert mod._reference_bindings(page, selected('PPh Pasal 21/26'), SCOPE,
                                       FakeCapture(), None) is None
        assert log.flush()
    assert gates_in(root) == ['reference']
