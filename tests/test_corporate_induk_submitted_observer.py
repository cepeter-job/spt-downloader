"""Optional submitted Induk observer stage fences, runner-only execution."""
from copy import deepcopy

import pytest

import coretax_browser as driver
import coretax_corporate as observer
import coretax_corporate_projection as projection


class Capture:
    def __init__(self, lost=None):
        self.calls, self.lost = 0, lost

    def observe_component_lifetime(self, **kwargs):
        self.calls += 1
        return None if self.calls == self.lost else {'synthetic': True}


class Form:
    def __init__(self, valid=True):
        self.valid = valid

    def evaluate(self, expression, controls):
        assert 'induk-submitted-controls' in expression
        assert controls == [s[1] for s in projection.INDUK_SUBMITTED_FIELDS]
        return self.valid


class Page:
    url = 'SYNTHETIC ROUTE'

    def __init__(self, defect=None):
        self.defect, self.reads = defect, []

    def evaluate(self, expression, *args):
        if args and type(args[0]) is list:
            self.reads.append('providers')
            assert 'initiatorType' in expression
            return self.defect != 'providers'
        if args and type(args[0]) is str:
            url, = args
            self.reads.append(url)
            return '0' * 64 if self.defect == url else projection.INDUK_SUBMITTED_BUILD_DIGESTS[url]
        assert 'timezone:Intl.DateTimeFormat' in expression
        self.reads.append('environment')
        return {'locale': 'en-US' if self.defect == 'environment' else 'id-ID', 'timezone': 'Asia/Jakarta'}


@pytest.mark.parametrize('defect', ['protocol', 'pins-missing', 'pins-null', 'cit', 'structure',
    'lifetime-start', 'providers', 'main', 'vendor', 'environment', 'lifetime-end'])
def test_optional_amount_proof_is_absent_at_every_unproven_stage(monkeypatch, defect):
    page = Page({'main': projection.MAIN_SOURCE, 'vendor': projection.VENDOR_SOURCE}.get(defect, defect))
    capture = Capture(lost=1 if defect == 'lifetime-start' else 2 if defect == 'lifetime-end' else None)
    if defect == 'protocol': capture = object()
    pins = deepcopy(projection.INDUK_SUBMITTED_BUILD_DIGESTS)
    if defect == 'pins-missing': pins = {}
    if defect == 'pins-null': pins = dict.fromkeys(pins)
    monkeypatch.setattr(projection, 'INDUK_SUBMITTED_BUILD_DIGESTS', pins)
    digest = '0' * 64 if defect == 'cit' else projection.L11C_BUILD_DIGESTS[projection.CIT_SOURCE]
    assert observer._observe_induk_submitted(page, Form(defect != 'structure'), capture, digest, None) is None


def test_optional_amount_proof_stop_after_hash_cannot_run_more_browser_reads():
    page, capture = Page(), Capture()
    calls = 0
    def stop():
        nonlocal calls
        calls += 1
        if calls == 4:
            raise driver.CaptureCancelled('SYNTHETIC STOP')
    with pytest.raises(driver.CaptureCancelled):
        observer._observe_induk_submitted(page, Form(), capture,
            projection.INDUK_SUBMITTED_BUILD_DIGESTS[projection.CIT_SOURCE], stop)
    assert page.reads == ['providers', projection.MAIN_SOURCE]
