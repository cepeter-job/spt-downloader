"""Real requested Tk text/bindings; no live portal, credentials or workers."""
from contextlib import contextmanager
import gc
import json
import tkinter as tk
from tkinter import ttk

import pytest

from spt_desktop import app as app_module


EXPECTED_TEXT = {
    'title': 'Coretax SPT downloader : kalau bisa ribet, kenapa dibikin gampang',
    'background': 'jalankan proses sedot di background',
    'results': 'Hasil Sedot berada di folder Downloads Windows',
}


class Controller:
    active = False
    operation = 'export'

    def __init__(self):
        self.starts = []
        self.job_id = None

    def poll(self):
        pass

    def close(self):
        self.active = False

    def start(self, npwp, year, browser, headless):
        self.starts.append((npwp, year, browser, headless))
        self.active = True
        self.job_id = f'synthetic-ui-{len(self.starts)}'
        return self.job_id


def settle(root):
    done = tk.BooleanVar(root)
    root.after(250, lambda: done.set(True))
    root.wait_variable(done)
    root.update_idletasks()


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


def forbidden_credentials(*args, **kwargs):
    raise AssertionError('This synthetic UI contract must not access credentials')


@contextmanager
def window(tmp_path, monkeypatch):
    controller = Controller()
    monkeypatch.setattr(app_module, 'save_login', forbidden_credentials)
    monkeypatch.setattr(app_module, 'delete_login', forbidden_credentials)
    root = tk.Tk()
    root.withdraw()
    application = None
    try:
        application = app_module.App(root, tmp_path, controller=controller)
        yield root, application, controller
    finally:
        controller.close()
        if application is not None and application._settings_close:
            application._settings_close()
        if application is not None:
            application._dispose()
        for callback in root.tk.splitlist(root.tk.call('after', 'info')):
            root.after_cancel(callback)
        root.destroy()
        del application
        gc.collect()


@pytest.mark.parametrize('width,height', [(540, 390), (900, 700), (640, 560), (1120, 800)])
def test_exact_window_title_and_results_label_are_visible_without_clipping(tmp_path, monkeypatch, width, height):
    with window(tmp_path, monkeypatch) as (root, application, controller):
        root.geometry(f'{width}x{height}')
        root.deiconify()
        settle(root)
        assert root.title() == EXPECTED_TEXT['title']
        labels = [widget for widget in descendants(root) if isinstance(widget, ttk.Label)]
        result = [widget for widget in labels if widget.cget('text') == EXPECTED_TEXT['results']]
        assert len(result) == 1, 'The exact requested Downloads label is missing'
        result = result[0]
        assert result.winfo_ismapped()
        left = result.winfo_rootx() - root.winfo_rootx()
        top = result.winfo_rooty() - root.winfo_rooty()
        assert 0 <= left and left + result.winfo_width() <= root.winfo_width()
        assert 0 <= top and top + result.winfo_height() <= root.winfo_height()
        assert result.winfo_width() >= result.winfo_reqwidth()
        assert result.winfo_height() >= result.winfo_reqheight()
        assert not any(widget.cget('text') == 'for personal use : punto ap' for widget in labels)
        assert controller.starts == []


def test_requested_background_checkbox_retains_preference_and_start_binding(tmp_path, monkeypatch):
    with window(tmp_path, monkeypatch) as (root, application, controller):
        dialog = application.settings()
        root.update_idletasks()
        boxes = [widget for widget in descendants(dialog) if isinstance(widget, ttk.Checkbutton)
                 and widget.cget('text') == EXPECTED_TEXT['background']]
        assert len(boxes) == 1, 'The requested real background checkbox is missing'
        checkbox = boxes[0]
        initial = bool(root.getboolean(root.getvar(str(checkbox.cget('variable')))))
        assert initial is application.preferences['headless']
        checkbox.invoke()
        save = next(widget for widget in descendants(dialog) if isinstance(widget, ttk.Button)
                    and widget.cget('text') == 'Simpan')
        save.invoke()
        expected = not initial
        assert application.preferences['headless'] is expected
        assert app_module.load_preferences(tmp_path)['headless'] is expected
        application._settings_close()
        application.npwp.set('0000000000000001')
        application.year.set('2025')
        application.start()
        assert controller.starts == [('0000000000000001', '2025', 'msedge', expected)]


def test_self_test_reports_actual_requested_widget_text_without_accounts(tmp_path, monkeypatch):
    from spt_gui import self_test
    monkeypatch.setattr(app_module, 'JobController', lambda *args, **kwargs: Controller())
    monkeypatch.setattr(app_module, 'save_login', forbidden_credentials)
    monkeypatch.setattr(app_module, 'delete_login', forbidden_credentials)
    report = tmp_path / 'actual-source-selftest.json'
    assert self_test(report) == 0
    data = json.loads(report.read_text(encoding='utf-8'))
    assert data.get('ui_text') == EXPECTED_TEXT
    assert data['live_scrape'] is False and data['credentials_accessed'] is False
    assert data['personal_use_labels'] == ['Coretax → Excel · for personal use only']
    gc.collect()


@pytest.mark.parametrize('key', ['title', 'background', 'results'])
def test_packaging_rejects_missing_or_old_requested_ui_evidence(key):
    import build_desktop
    from test_desktop_build import report
    valid = {**report(), 'ui_text': dict(EXPECTED_TEXT)}
    build_desktop.validate_report(valid)
    wrong = {**valid, 'ui_text': {**EXPECTED_TEXT, key: 'SYNTHETIC OLD UI TEXT'}}
    with pytest.raises(RuntimeError, match='self-test'):
        build_desktop.validate_report(wrong)
    missing = {**valid, 'ui_text': {name: text for name, text in EXPECTED_TEXT.items() if name != key}}
    with pytest.raises(RuntimeError, match='self-test'):
        build_desktop.validate_report(missing)


@pytest.mark.parametrize('width,height', [(540, 390), (900, 700), (640, 560), (1120, 800)])
def test_requested_header_is_the_real_visible_heading_not_only_the_window_caption(tmp_path, monkeypatch, width, height):
    with window(tmp_path, monkeypatch) as (root, application, controller):
        root.geometry(f'{width}x{height}')
        root.deiconify()
        settle(root)
        headings = [widget for widget in descendants(root) if isinstance(widget, ttk.Label)
                    and str(widget.cget('style')) == 'Title.TLabel']
        assert len(headings) == 1
        heading = headings[0]
        assert heading.cget('text') == EXPECTED_TEXT['title']
        assert root.title() == heading.cget('text')
        assert heading.winfo_ismapped()
        left = heading.winfo_rootx() - root.winfo_rootx()
        top = heading.winfo_rooty() - root.winfo_rooty()
        assert 0 <= left and left + heading.winfo_width() <= root.winfo_width()
        assert 0 <= top and top + heading.winfo_height() <= root.winfo_height()
        assert heading.winfo_width() >= heading.winfo_reqwidth()
        assert heading.winfo_height() >= heading.winfo_reqheight()
        assert controller.starts == []


def test_requested_downloads_description_replaces_the_old_hierarchy_hint(tmp_path, monkeypatch):
    with window(tmp_path, monkeypatch) as (root, application, controller):
        labels = [widget.cget('text') for widget in descendants(root) if isinstance(widget, ttk.Label)]
        assert labels.count(EXPECTED_TEXT['results']) == 1
        obsolete = 'Hasil: Downloads → NPWP - NAMA WP → TAHUN PAJAK → WAKTU EKSPOR.'
        assert not any(obsolete in text for text in labels), 'Replace the old hint; do not display both'
        assert any('Setup Python/uv otomatis saat Mulai.' in text for text in labels)
        assert controller.starts == []


def test_self_test_does_not_report_a_new_caption_over_an_old_real_header(tmp_path, monkeypatch):
    import spt_gui
    original_app = spt_gui.App

    def app_with_changed_real_heading(*args, **kwargs):
        application = original_app(*args, **kwargs)
        heading = next(widget for widget in descendants(application.root)
                       if isinstance(widget, ttk.Label) and str(widget.cget('style')) == 'Title.TLabel')
        heading.configure(text='SYNTHETIC MISMATCHED REAL HEADER')
        return application

    monkeypatch.setattr(app_module, 'JobController', lambda *args, **kwargs: Controller())
    monkeypatch.setattr(app_module, 'save_login', forbidden_credentials)
    monkeypatch.setattr(app_module, 'delete_login', forbidden_credentials)
    monkeypatch.setattr(spt_gui, 'App', app_with_changed_real_heading)
    report = tmp_path / 'must-not-attest-an-old-header.json'
    with pytest.raises(AssertionError):
        spt_gui.self_test(report)
    assert not report.exists()
    gc.collect()


def test_consolidated_native_shell_excludes_removed_owner_footer(tmp_path, monkeypatch):
    with window(tmp_path, monkeypatch) as (root, application, controller):
        labels = [widget.cget('text') for widget in descendants(root) if isinstance(widget, ttk.Label)]
        assert 'for personal use : punto ap' not in labels
        assert 'Coretax → Excel · for personal use only' in labels
        assert controller.starts == []


def test_source_credit_is_an_exact_comment_not_an_extra_visible_label():
    import io
    from pathlib import Path
    import tokenize
    source = Path(app_module.__file__).read_text(encoding='utf-8')
    comments = [token.string for token in tokenize.generate_tokens(io.StringIO(source).readline)
                if token.type == tokenize.COMMENT]
    assert comments.count('#punto ami priyono') == 1
