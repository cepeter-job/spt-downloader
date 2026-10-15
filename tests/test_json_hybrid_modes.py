"""Synthetic mode contracts. Run product tests on GitHub Windows only."""
import inspect
import json

import pytest


def test_cli_omitted_mode_keeps_dom():
    import coretax
    args = coretax.parser().parse_args([])
    assert getattr(args, 'detail_source', None) == 'dom'


@pytest.mark.parametrize('mode', ['dom', 'json-first'])
def test_cli_preserves_literal_supported_mode(mode):
    import coretax
    args = coretax.parser().parse_args(['--detail-source', mode])
    assert args.detail_source == mode
    assert args.year_basis == 'period'


@pytest.mark.parametrize('mode', ['JSON-FIRST', 'json-hybrid', ' DOM ', '', 'json'])
def test_invalid_cli_mode_is_rejected_as_a_choice(mode, capsys):
    import coretax
    with pytest.raises(SystemExit) as error:
        coretax.parser().parse_args(['--detail-source', mode])
    assert error.value.code == 2
    assert 'invalid choice' in capsys.readouterr().err


@pytest.mark.parametrize('saved', [{}, {'detail_source': 'JSON-FIRST'},
    {'detail_source': 'json-hybrid'}, {'detail_source': True},
    {'detail_source': 1}, {'detail_source': None}, {'detail_source': {}}])
def test_legacy_or_invalid_saved_mode_defaults_to_dom(tmp_path, saved):
    from spt_desktop.app import load_preferences
    (tmp_path / 'preferences.json').write_text(json.dumps(saved), encoding='utf-8')
    assert load_preferences(tmp_path).get('detail_source') == 'dom'


@pytest.mark.parametrize('mode', ['dom', 'json-first'])
def test_saved_mode_round_trip_preserves_nonsecret_preferences(tmp_path, mode):
    from spt_desktop.app import DEFAULTS, load_preferences, save_preferences
    expected = {**DEFAULTS, 'browser': 'chrome', 'headless': False,
                'identifier': 'SYNTHETIC ACCOUNT', 'detail_source': mode}
    save_preferences(tmp_path, expected)
    assert load_preferences(tmp_path) == expected
    assert json.loads((tmp_path / 'preferences.json').read_text(encoding='utf-8')) == expected


@pytest.mark.parametrize('mode', ['JSON-FIRST', 'json-hybrid', '', True, 1, None, {}])
def test_invalid_new_mode_does_not_replace_saved_preferences(tmp_path, mode):
    from spt_desktop.app import DEFAULTS, save_preferences
    previous = {**DEFAULTS, 'detail_source': 'dom'}
    save_preferences(tmp_path, previous)
    original = (tmp_path / 'preferences.json').read_bytes()
    with pytest.raises(ValueError):
        save_preferences(tmp_path, {**previous, 'detail_source': mode})
    assert (tmp_path / 'preferences.json').read_bytes() == original
    assert not (tmp_path / 'preferences.tmp').exists()


@pytest.mark.parametrize('mode', ['dom', 'json-first'])
def test_controller_propagates_mode_to_worker_launch(tmp_path, monkeypatch, mode):
    from spt_desktop.controller import JobController
    parameter = inspect.signature(JobController.start).parameters.get('detail_source')
    assert parameter is not None, 'Optional detail-source mode is missing'
    assert parameter.default == 'dom'
    controller = JobController(tmp_path, lambda event: None)
    launched = []
    def acquire(arguments, browser, headless, operation):
        launched.append((arguments, browser, headless, operation))
        return 'synthetic-job'
    monkeypatch.setattr(controller, '_start_worker', acquire)
    assert controller.start('0000000000000001', '2025', 'chrome', False,
                            detail_source=mode) == 'synthetic-job'
    assert launched == [(['--npwp', '0000000000000001', '--year', '2025',
                         '--detail-source', mode], 'chrome', False, 'export')]
