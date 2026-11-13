"""Fixed-enum gate diagnostics for the optional L7 raw-negative proof.

Hosted-CI only: the observer must name the exact predicate
that dropped `raw_negative_projection` without recording payloads, digests,
routes, identifiers or values.
"""
import pytest

import coretax_corporate as observer
import coretax_corporate_projection as projection
from spt_desktop import diagnostics
from test_diagnostics import records

EVENT = 'corporate.l7_negative_gate'


class Table:
    def __init__(self, samples):
        self._samples = list(samples)
        self._calls = 0

    def evaluate(self, _script):
        sample = self._samples[min(self._calls, len(self._samples) - 1)]
        self._calls += 1
        return sample


class Grid:
    def __init__(self, table):
        self._table = table

    def locator(self, _selector):
        return self._table


_UNSET = object()


class Page:
    def __init__(self, pins, environment=None, url='https://synthetic.invalid/detail?view=true',
                 digest_override=_UNSET):
        self._pins = pins
        self._environment = environment or {'locale': 'id-ID', 'timezone': 'Asia/Jakarta'}
        self.url = url
        self._digest_override = digest_override

    def evaluate(self, script, url=None):
        if 'Intl.DateTimeFormat' in script:
            return self._environment
        if self._digest_override is not _UNSET:
            return self._digest_override
        return self._pins.get(url)


class Capture:
    def __init__(self, binds=(True, True), lifetime=True):
        self._binds = list(binds)
        self._lifetime = lifetime

    def observe_component_lifetime(self, **_kwargs):
        return {}

    def bind_l7_structure(self, *_args, **_kwargs):
        return self._binds.pop(0) if self._binds else True

    def observe_l7_lifetime(self, **_kwargs):
        return {} if self._lifetime else None


def legacy(environment=None):
    return {'route': 'https://synthetic.invalid/detail?view=true',
            'locale': (environment or {}).get('locale', 'id-ID'),
            'timezone': (environment or {}).get('timezone', 'Asia/Jakarta'),
            'tables': [{'headers': ['H1', 'H2'], 'footer_spans': ['2']}]}


def pins():
    return dict(projection.L7_NEGATIVE_BUILD_DIGESTS)


def run(tmp_path, monkeypatch, capture=None, page=None, enabled=(True,)):
    """Drive the optional proof once inside a real diagnostics session."""
    states = list(enabled)

    def enabled_binding(*_args):
        return states.pop(0) if states else True

    monkeypatch.setattr(observer, '_enabled_form_binding', enabled_binding)
    with diagnostics.session(tmp_path, 'worker'):
        return observer._observe_l7_negative(
            page, object(), Grid(Table([{'headers': ['H1', 'H2'], 'footer_spans': ['2']}])),
            object(), object(), capture, legacy(), lambda: None)


def gates(tmp_path):
    return [row['corporate_l7_negative_gate'] for row in records(tmp_path)
            if row['event'] == EVENT]


def test_strong_proof_records_no_gate(tmp_path, monkeypatch):
    proof = run(tmp_path, monkeypatch, Capture(), Page(pins()))
    assert proof['kind'] == 'corporate-l7-stable-negative-v1'
    assert proof['builds'] == pins()
    assert gates(tmp_path) == []


def test_missing_capture_protocol_is_named(tmp_path, monkeypatch):
    capture = Capture()
    capture.bind_l7_structure = None
    assert run(tmp_path, monkeypatch, capture, Page(pins())) is None
    assert gates(tmp_path) == ['protocol']


def test_invalid_pins_are_named(tmp_path, monkeypatch):
    monkeypatch.setattr(projection, 'L7_NEGATIVE_BUILD_DIGESTS', {projection.MAIN_SOURCE: 'x'})
    assert run(tmp_path, monkeypatch, Capture(), Page(pins())) is None
    assert gates(tmp_path) == ['pins']


def test_disabled_l7_binding_is_named(tmp_path, monkeypatch):
    assert run(tmp_path, monkeypatch, Capture(), Page(pins()), enabled=(False,)) is None
    assert gates(tmp_path) == ['enabled']


def test_structure_start_refusal_is_named(tmp_path, monkeypatch):
    assert run(tmp_path, monkeypatch, Capture(binds=(False,)), Page(pins())) is None
    assert gates(tmp_path) == ['structure_start']


def test_foreign_environment_is_named(tmp_path, monkeypatch):
    page = Page(pins(), environment={'locale': 'en-US', 'timezone': 'Asia/Jakarta'})
    assert run(tmp_path, monkeypatch, Capture(), page) is None
    assert gates(tmp_path) == ['environment']


@pytest.mark.parametrize('digest', ['0' * 64, 'short', None])
def test_unproved_build_digest_is_named(tmp_path, monkeypatch, digest):
    assert run(tmp_path, monkeypatch, Capture(), Page(pins(), digest_override=digest)) is None
    assert gates(tmp_path) == ['builds']


def test_unstable_table_shape_is_named(tmp_path, monkeypatch):
    table = Table([{'headers': ['H1', 'H2'], 'footer_spans': ['2']},
                   {'headers': ['H1', 'H2', 'H3'], 'footer_spans': ['2']}])
    monkeypatch.setattr(observer, '_enabled_form_binding', lambda *a: True)
    with diagnostics.session(tmp_path, 'worker'):
        proof = observer._observe_l7_negative(Page(pins()), object(), Grid(table), object(),
                                              object(), Capture(), legacy(), lambda: None)
    assert proof is None
    assert gates(tmp_path) == ['table']


def test_route_detour_is_named(tmp_path, monkeypatch):
    page = Page(pins(), url='https://synthetic.invalid/detail?view=true&synthetic=detour')
    assert run(tmp_path, monkeypatch, Capture(), page) is None
    assert gates(tmp_path) == ['route']


def test_late_disabled_binding_is_named(tmp_path, monkeypatch):
    assert run(tmp_path, monkeypatch, Capture(), Page(pins()), enabled=(True, False)) is None
    assert gates(tmp_path) == ['enabled_end']


def test_structure_end_refusal_is_named(tmp_path, monkeypatch):
    assert run(tmp_path, monkeypatch, Capture(binds=(True, False)), Page(pins())) is None
    assert gates(tmp_path) == ['structure_end']


def test_unavailable_lifetime_is_named(tmp_path, monkeypatch):
    assert run(tmp_path, monkeypatch, Capture(lifetime=False), Page(pins())) is None
    assert gates(tmp_path) == ['lifetime']


def test_gate_categories_registered_and_value_free(tmp_path, monkeypatch):
    row = None
    run(tmp_path, monkeypatch, Capture(binds=(False,)), Page(pins()))
    row, = [r for r in records(tmp_path) if r['event'] == EVENT]
    assert set(row) <= {'schema', 'timestamp', 'level', 'event', 'role', 'sequence',
                        'elapsed_ms', 'python', 'frozen', 'job_ref', 'session_id',
                        'corporate_l7_negative_gate'}
    assert row['level'] == 'INFO'
    assert observer.__name__ in diagnostics.MODULES
