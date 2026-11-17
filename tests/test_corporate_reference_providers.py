"""Manifest-only positive loaded-provider custody; all execution on runners."""
from copy import deepcopy
import hashlib
import json

import pytest

import coretax_json as adapter
from coretax_browser import CaptureCancelled
from coretax_json import JsonSafetyError
from coretax_json_capture import DetailJsonCapture, checkpoint_bodies
from support_json_network import exchange
from test_corporate_component_lifetime import setup, selected, begin, navigate, LIST, DETAIL, SCOPE
from test_corporate_l11c_native import L11C_PINS


KEY = 'corporate_reference_providers'


def configured_page(*, defect=None):
    context, page = setup()
    original = page.evaluate
    page.hash_reads = []
    page.loaded = True
    def evaluate(script, args=None):
        if 'Date.now()' in script:
            return {'epoch_ms': 1800000000000, 'timezone': 'Asia/Jakarta'}
        if isinstance(args, list):
            return page.loaded
        if isinstance(args, str):
            page.hash_reads.append(args)
            return None if defect == 'absent' else '0' * 64 if defect == 'wrong' else L11C_PINS[args]
        return original(script)
    page.evaluate = evaluate
    return context, page


def observe(capture):
    method = getattr(capture, 'observe_corporate_reference_providers', None)
    assert callable(method), 'Source-only RED: passive loaded-provider producer absent'
    return method()


def test_provider_fact_is_manifest_owned_uniform_and_held_replay_needs_no_browser(tmp_path):
    context, page = configured_page()
    record = selected()
    with DetailJsonCapture(context, page, record, SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        response = exchange(context, page)
        capture.bind_detail_page(page)
        assert observe(capture) == L11C_PINS
        assert observe(capture) == L11C_PINS
        assert len(page.hash_reads) == 3  # one bounded acquisition, never cache probing
        saved = capture.drain()
        assert saved['complete'] and saved[KEY]['builds'] == L11C_PINS
        assert saved[KEY]['attempt'] == saved['attempt']
        assert KEY not in saved['responses'][0]
        packets = list(capture.iter_bodies())
        assert packets[0]['context'][KEY] == saved[KEY]
        assert packets[0]['body'] == response.raw and response.reads == 1
        record['detail_url'] = DETAIL
        page.evaluate = lambda *args: pytest.fail('Held replay must not inspect the present browser')
        assert checkpoint_bodies(tmp_path, saved, record, SCOPE) == packets
        assert capture.drain() == saved


@pytest.mark.parametrize('defect', ['unloaded', 'absent', 'wrong', 'missing-pin', 'null-pin', 'no-lifetime'])
def test_unavailable_providers_never_mint_permission_or_break_legacy_capture(tmp_path, monkeypatch, defect):
    context, page = configured_page(defect=defect)
    if defect == 'unloaded': page.loaded = False
    if defect in ('missing-pin', 'null-pin'):
        pins = dict(L11C_PINS)
        if defect == 'missing-pin': pins.pop(next(iter(pins)))
        else: pins[next(iter(pins))] = None
        monkeypatch.setattr(adapter, 'load_build_pins', lambda: pins)
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
        if defect != 'no-lifetime': begin(capture)
        navigate(page, DETAIL)
        exchange(context, page)
        capture.bind_detail_page(page)
        assert observe(capture) is None
        saved = capture.drain()
        assert saved['complete'] and KEY not in saved
        assert KEY not in list(capture.iter_bodies())[0]['context']
        if defect in ('unloaded', 'missing-pin', 'null-pin', 'no-lifetime'):
            assert not page.hash_reads


@pytest.mark.parametrize('defect', ['descriptor', 'null', 'component-missing', 'clock-missing',
                                  'cross-attempt', 'pin', 'extra'])
def test_both_held_readers_reject_provider_override_and_malformed_fact(tmp_path, defect):
    context, page = configured_page()
    record = selected()
    with DetailJsonCapture(context, page, record, SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        exchange(context, page)
        capture.bind_detail_page(page)
        assert observe(capture)
        saved = capture.drain()
        path = tmp_path / saved['manifest']
        changed = json.loads(path.read_bytes())
        if defect == 'descriptor': changed['responses'][0][KEY] = deepcopy(changed[KEY])
        elif defect == 'null': changed[KEY] = None
        elif defect == 'component-missing': del changed['component_lifetime']
        elif defect == 'clock-missing': del changed['clock_interval']
        elif defect == 'cross-attempt': changed[KEY]['attempt'] = 'b' * 32
        elif defect == 'pin': changed[KEY]['builds'][next(iter(L11C_PINS))] = '0' * 64
        else: changed[KEY]['SYNTHETIC'] = True
        raw = json.dumps(changed, sort_keys=True).encode()
        path.write_bytes(raw)
        saved = {**changed, 'manifest': saved['manifest'], 'manifest_sha256': hashlib.sha256(raw).hexdigest()}
        capture._manifest_hash, capture._result = saved['manifest_sha256'], deepcopy(saved)
        record['detail_url'] = DETAIL
        with pytest.raises(JsonSafetyError): list(capture.iter_bodies())
        with pytest.raises(JsonSafetyError): checkpoint_bodies(tmp_path, saved, record, SCOPE)


def test_stop_after_provider_hash_is_not_demoted_to_unavailable(tmp_path):
    context, page = configured_page()
    def stop():
        if page.hash_reads: raise CaptureCancelled()
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path, check_cancel=stop) as capture:
        begin(capture)
        navigate(page, DETAIL)
        capture.bind_detail_page(page)
        with pytest.raises(CaptureCancelled): observe(capture)
    assert not list(tmp_path.rglob('manifest.json'))


def test_one_shot_stop_from_hash_rpc_is_never_swallowed(tmp_path):
    context, page = configured_page()
    original = page.evaluate
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        capture.bind_detail_page(page)
        def cancelled(script, args=None):
            if isinstance(args, str): raise CaptureCancelled()
            return original(script, args)
        page.evaluate = cancelled
        with pytest.raises(CaptureCancelled): observe(capture)


@pytest.mark.parametrize('mime', ['application/json', 'text/plain'])
def test_final_document_sample_cannot_hide_late_new_reference_request(tmp_path, mime):
    context, page = configured_page()
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        exchange(context, page)
        capture.bind_detail_page(page)
        assert observe(capture)
        def late():
            page.documents[0].on_read = None
            exchange(context, page, method='GET', content_type=mime,
                url=adapter.ORIGIN + '/referencedata/api/currentreferencedata/id-ID/TRANSACTION_TYPE')
        page.documents[0].on_read = late
        saved = capture.drain()
        assert not saved['complete'] and 'response-after-final-drain' in saved['reasons']


def test_manifest_provider_validator_is_positive_exact_and_attempt_bound():
    method = getattr(adapter, '_capture_corporate_reference_providers', None)
    assert callable(method)
    options = {'attempt': 'a' * 32, 'record_id': 'fixture-record', 'source_url': LIST, 'detail_url': DETAIL}
    value = {'kind': 'corporate-reference-providers-v1', **options, 'builds': dict(L11C_PINS)}
    assert method(value, **options) == value
    for key in value:
        changed = deepcopy(value)
        del changed[key]
        with pytest.raises(JsonSafetyError): method(changed, **options)
