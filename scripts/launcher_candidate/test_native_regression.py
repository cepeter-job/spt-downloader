"""Mandatory candidate-only Windows/Tk behavioral qualification; invoke explicitly."""

def test_finite_regression_scenario_exercises_real_app_and_owned_cleanup(tmp_path):
    import json
    from scripts.launcher_candidate.reader_host import run
    directory = tmp_path / 'regression'
    assert run('regression', directory) == 0
    report = json.loads((directory / 'regression.json').read_text(encoding='utf-8'))
    assert report['checks'] == {
        'settings_return_discard_save_clear': True,
        'selection_explicit_consent': True,
        'overwrite_preserve_and_explicit_consent': True,
        'stale_and_stop_precedence': True,
        'complete_partial_eligibility': True,
        'owned_cleanup': True,
    }
    assert report['credentials_accessed'] is False
    assert report['live_scrape'] is False
    assert report['accessibility_acceptance'] is False
