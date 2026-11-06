"""Build-pin allowlist: reviewed file wins, failures fail closed."""
import json
from pathlib import Path

from coretax_build_pins import load_build_pins

GOOD = {'version': 1, 'digests': {'https://example.invalid/a.js': 'a' * 64}}


def test_valid_file_returns_digests(tmp_path):
    path = tmp_path / 'pins.json'
    path.write_text(json.dumps(GOOD), encoding='utf-8')
    assert load_build_pins(path) == GOOD['digests']


def test_missing_file_fails_closed(tmp_path):
    assert load_build_pins(tmp_path / 'absent.json') == {}


def test_corrupt_file_fails_closed(tmp_path):
    path = tmp_path / 'pins.json'
    path.write_text('{not json', encoding='utf-8')
    assert load_build_pins(path) == {}


def test_wrong_shape_fails_closed(tmp_path):
    for payload in ({'version': 2, 'digests': GOOD['digests']},
                    {'version': 1, 'digests': {}},
                    {'version': 1, 'digests': {'http://x/a.js': 'a' * 64}},
                    {'version': 1, 'digests': {'https://x/a.js': 'xyz'}},
                    {'version': 1}):
        path = tmp_path / 'pins.json'
        path.write_text(json.dumps(payload), encoding='utf-8')
        assert load_build_pins(path) == {}


def test_checked_in_pins_cover_all_observer_sources():
    """The shipped pin file must pin every URL an observer hashes."""
    pins = load_build_pins()
    assert len(pins) == 6
    assert all(digest and len(digest) == 64 for digest in pins.values())
