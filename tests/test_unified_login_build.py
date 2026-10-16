"""Source/frozen acceptance uses observed origin-free controls and account forwarding."""
import json
import pytest
from build_desktop import validate_report
from support_build_reports import report


@pytest.mark.parametrize('value', [None, {}, {'credential_origin': 'coretax'},
    {'origin_selector_present': True, 'credential_origin': 'satu', 'account_forwarded': True},
    {'origin_selector_present': False, 'credential_origin': 'satu', 'account_forwarded': False}])
def test_frozen_gate_requires_real_origin_free_and_account_forwarding_evidence(value):
    data = report()
    validate_report(data)
    data['automatic_login_controls'] = value
    with pytest.raises(RuntimeError, match='self-test'):
        validate_report(data)


def test_source_selftest_observes_removed_origin_and_forwarded_account(tmp_path):
    from spt_gui import self_test
    path = tmp_path / 'automatic-login.json'
    assert self_test(path) == 0
    data = json.loads(path.read_text(encoding='utf-8'))
    assert data.get('automatic_login_controls') == {
        'origin_selector_present': False, 'credential_origin': 'satu', 'account_forwarded': True}
    assert data['credentials_accessed'] is False and data['live_scrape'] is False


def test_selftest_rejects_gui_that_drops_selected_account(tmp_path, monkeypatch):
    from spt_gui import App, self_test
    original = App.start
    def drop_account(app):
        app.preferences['identifier'] = ''
        return original(app)
    monkeypatch.setattr(App, 'start', drop_account)
    with pytest.raises(AssertionError):
        self_test(tmp_path / 'must-not-pass.json')
    assert not (tmp_path / 'must-not-pass.json').exists()
