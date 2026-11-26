"""The explicit build-pin reset is operator-visible and never implicit."""
import coretax
import coretax_build_pins as pins_mod


def test_reset_build_pins_removes_the_overlay(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path / 'local'))
    url = sorted(pins_mod.load_build_pins())[0]
    assert pins_mod.record_local_pins({url: 'b' * 64}) is True
    assert pins_mod.local_pins_path().exists()

    assert coretax._main(['--reset-build-pins']) == 0

    assert not pins_mod.local_pins_path().exists()
    out = capsys.readouterr().out
    assert 'overlay removed' in out


def test_reset_build_pins_without_an_overlay_succeeds(tmp_path, monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path / 'local'))
    assert coretax._main(['--reset-build-pins']) == 0
    assert not pins_mod.local_pins_path().exists()