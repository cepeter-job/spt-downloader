"""Literal contact text and real bottom-right geometry; synthetic runner only."""
import gc
import json
import tkinter as tk

import pytest

from spt_desktop.app import App
from support_gui import Controller, widgets
from support_build_reports import report
from build_desktop import validate_report

TEXT = 'bugreport : sharmila@kemenkeu.go.id'


@pytest.mark.parametrize('width,height,scale', [(540, 430, 1.0), (800, 620, 1.0),
                                               (540, 430, 1.5), (800, 620, 1.5)])
def test_contact_is_visible_bottom_right_without_replacing_existing_copy(tmp_path, width, height, scale):
    root = tk.Tk()
    app = None
    original_scale = root.tk.call('tk', 'scaling')
    try:
        root.tk.call('tk', 'scaling', scale * 96 / 72)
        root.geometry(f'{width}x{height}')
        app = App(root, tmp_path, controller=Controller())
        settled = tk.BooleanVar(root)
        root.after(250, lambda: settled.set(True))
        root.wait_variable(settled)
        root.update_idletasks()
        labels = [w for w in widgets(root) if w.winfo_class() == 'TLabel']
        contact = [w for w in labels if str(w.cget('text')) == TEXT]
        assert len(contact) == 1
        label = contact[0]
        assert label.winfo_viewable()
        left = label.winfo_rootx() - root.winfo_rootx()
        top = label.winfo_rooty() - root.winfo_rooty()
        right = left + label.winfo_width()
        bottom = top + label.winfo_height()
        assert 0 <= left < right <= root.winfo_width()
        assert 0 <= top < bottom <= root.winfo_height()
        assert root.winfo_width() - right <= app.view.px(32)
        assert root.winfo_height() - bottom <= app.view.px(32)
        assert label.winfo_rooty() >= app.results_label.winfo_rooty() + app.results_label.winfo_height()
        assert str(app.results_label.cget('text')) == 'Hasil Sedot berada di folder Downloads Windows'
        assert 'Coretax → Excel · for personal use only' in [str(w.cget('text')) for w in labels]
        assert not app.controller.active
    finally:
        if app is not None:
            app._dispose()
        for callback in root.tk.splitlist(root.tk.call('after', 'info')):
            root.after_cancel(callback)
        root.tk.call('tk', 'scaling', original_scale)
        root.destroy()
        del app
        gc.collect()


def test_source_selftest_reports_observed_contact_and_position(tmp_path):
    from spt_gui import self_test
    output = tmp_path / 'contact-selftest.json'
    assert self_test(output) == 0
    data = json.loads(output.read_text(encoding='utf-8'))
    assert data.get('bugreport_footer') == {'text': TEXT, 'bottom_right': True}
    assert data['credentials_accessed'] is False and data['live_scrape'] is False


@pytest.mark.parametrize('bad', [None, {}, {'text': TEXT, 'bottom_right': False},
                               {'text': 'wrong contact', 'bottom_right': True}])
def test_frozen_gate_rejects_missing_wrong_or_misplaced_contact(bad):
    data = report()
    data['bugreport_footer'] = {'text': TEXT, 'bottom_right': True}
    validate_report(data)
    data['bugreport_footer'] = bad
    with pytest.raises(RuntimeError, match='self-test'):
        validate_report(data)
