"""Optional browser-clock evidence belongs to the same private capture attempt."""
from copy import deepcopy
import hashlib
import json

import pytest

from coretax_json import JsonSafetyError
from coretax_json_capture import DetailJsonCapture, checkpoint_bodies
from coretax_masa_json import adapt_masa_detail
from support_json_network import Context
from test_json_capture import Page, DETAIL_URL, SCOPE
from test_pph21_reference_capture import selected, exchange, RAW
from test_pph21_reference_packets import reference_packet
from test_pph21_json_primary import case, source
from test_dated_reference_catalogs import CLOCK, START


def test_clock_is_sampled_before_view_and_after_final_body_then_replayed_without_clock(tmp_path):
    context = Context()
    page = Page(context)
    phases = []

    def sample(script):
        phases.append(page.url)
        assert 'Date.now()' in script and 'timeZone' in script
        return {'epoch_ms': START + (1000 if len(phases) == 2 else 0), 'timezone': 'Asia/Jakarta'}

    page.evaluate = sample
    record = selected()
    with DetailJsonCapture(context, page, record, SCOPE, tmp_path) as capture:
        page.url = DETAIL_URL
        response = exchange(context, page)
        capture.bind_detail_page(page)
        result = capture.drain()
        clock = {**CLOCK, 'attempt': result['attempt']}
        assert result.get('clock_interval') == clock
        assert phases == [record['list_url'], DETAIL_URL]
        assert response.reads == 1
        assert 'clock_interval' not in result['responses'][0]
        packets = list(capture.iter_bodies())
        assert packets[0]['context']['clock_interval'] == clock
        assert packets[0]['body'] == RAW
        # Repeated drain and offline replay must not sample the present clock.
        page.evaluate = lambda _: pytest.fail('Replay must use recorded clock evidence')
        assert capture.drain() == result
        assert checkpoint_bodies(tmp_path, result, record, SCOPE) == packets


@pytest.mark.parametrize('sample', [None, {'epoch_ms': True, 'timezone': 'Asia/Jakarta'},
    {'epoch_ms': START, 'timezone': 'unknown'}, {'epoch_ms': float('inf'), 'timezone': 'Asia/Jakarta'}])
def test_unavailable_or_invalid_browser_clock_does_not_invent_interval(tmp_path, sample):
    context = Context()
    page = Page(context, DETAIL_URL)
    page.evaluate = lambda _: deepcopy(sample)
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
        exchange(context, page)
        capture.bind_detail_page(page)
        result = capture.drain()
        assert result['complete'] and 'clock_interval' not in result
        assert 'clock_interval' not in list(capture.iter_bodies())[0]['context']


def test_backwards_browser_clock_does_not_create_evidence(tmp_path):
    context = Context()
    page = Page(context, DETAIL_URL)
    samples = iter([START + 1000, START])
    page.evaluate = lambda _: {'epoch_ms': next(samples), 'timezone': 'Asia/Jakarta'}
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
        exchange(context, page)
        capture.bind_detail_page(page)
        assert 'clock_interval' not in capture.drain()


@pytest.mark.parametrize('defect', ['bool', 'float', 'string', 'missing', 'extra', 'reversed',
    'negative', 'unsafe', 'timezone', 'attempt', 'mixed', 'absent-one'])
def test_clock_contradictions_are_fatal_before_metadata_fallback(defect):
    record, outer, _ = case()
    bodies = [source(outer), reference_packet()]
    attempt = bodies[0]['context']['attempt']
    clock = {**CLOCK, 'attempt': attempt}
    for item in bodies:
        item['context']['clock_interval'] = deepcopy(clock)
    broken = bodies[-1]['context']['clock_interval']
    if defect == 'bool': broken['start_ms'] = True
    elif defect == 'float': broken['start_ms'] = float(START)
    elif defect == 'string': broken['end_ms'] = str(START)
    elif defect == 'missing': del broken['end_ms']
    elif defect == 'extra': broken['unbound'] = 1
    elif defect == 'reversed': broken['start_ms'] = START + 2000
    elif defect == 'negative': broken['start_ms'] = -1
    elif defect == 'unsafe': broken['end_ms'] = 8640000000000001
    elif defect == 'timezone': broken['timezone'] = 'UTC'
    elif defect == 'attempt': broken['attempt'] = 'f' * 32
    elif defect == 'mixed': broken['end_ms'] += 1
    else: del bodies[-1]['context']['clock_interval']
    with pytest.raises(JsonSafetyError):
        adapt_masa_detail(bodies, record=record, scope=SCOPE, observed_forms=[])


def test_valid_clock_is_preserved_in_every_packet_event_without_mutating_original():
    record, outer, _ = case()
    bodies = [source(outer), reference_packet()]
    for item in bodies:
        item['context']['clock_interval'] = {**CLOCK, 'attempt': item['context']['attempt']}
    before = deepcopy(bodies)
    result = adapt_masa_detail(bodies, record=record, scope=SCOPE, observed_forms=[])
    assert not result['eligible']
    assert all(event.get('clock_interval') == bodies[0]['context']['clock_interval']
               for event in result['provenance']['events'])
    assert bodies == before


def test_tampered_clock_manifest_cannot_be_replayed_even_with_rehashed_bytes(tmp_path):
    context = Context()
    page = Page(context, DETAIL_URL)
    page.evaluate = lambda _: {'epoch_ms': START, 'timezone': 'Asia/Jakarta'}
    record = selected()
    with DetailJsonCapture(context, page, record, SCOPE, tmp_path) as capture:
        exchange(context, page)
        capture.bind_detail_page(page)
        result = capture.drain()
    path = tmp_path / result['manifest']
    saved = json.loads(path.read_bytes())
    saved['clock_interval'] = {**CLOCK, 'attempt': 'f' * 32}
    raw = json.dumps(saved).encode()
    path.write_bytes(raw)
    result.update(clock_interval=saved['clock_interval'], manifest_sha256=hashlib.sha256(raw).hexdigest())
    with pytest.raises(JsonSafetyError):
        checkpoint_bodies(tmp_path, result, record, SCOPE)
