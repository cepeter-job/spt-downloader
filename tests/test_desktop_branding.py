"""Personal-use labels are real UI controls; no accounts or workers are used."""
import gc
import tkinter as tk
from tkinter import ttk

import pytest

from spt_desktop.app import App


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


@pytest.mark.parametrize('width,height', [(540, 430), (800, 620)])
def test_personal_use_subtitle_is_visible_without_the_removed_punto_footer(tmp_path, width, height):
    root = tk.Tk()
    window = None
    try:
        root.geometry(f'{width}x{height}')
        window = App(root, tmp_path)
        done = tk.BooleanVar(root)
        root.after(250, lambda: done.set(True))
        root.wait_variable(done)
        root.update_idletasks()
        body = root.winfo_children()[0]
        labels = [child for child in descendants(body) if isinstance(child, ttk.Label)]
        texts = [str(label['text']) for label in labels]
        assert 'Coretax → Excel · for personal use only' in texts
        assert not any('read-only' in text or 'data perpajakan rahasia' in text for text in texts)
        assert 'for personal use : punto ap' not in texts
        subtitle = next(label for label in labels
                        if str(label['text']) == 'Coretax → Excel · for personal use only')
        assert subtitle.winfo_ismapped()
        left = subtitle.winfo_rootx() - root.winfo_rootx()
        top = subtitle.winfo_rooty() - root.winfo_rooty()
        assert 0 <= left and left + subtitle.winfo_width() <= root.winfo_width()
        assert 0 <= top and top + subtitle.winfo_height() <= root.winfo_height()
        # Exercise teardown with an owned view callback still queued.
        window.view.request_reflow()
    finally:
        if window is not None:
            window._dispose()
        for callback in root.tk.splitlist(root.tk.call('after', 'info')):
            root.after_cancel(callback)
        root.destroy()
        del window
        gc.collect()


def test_self_test_reports_the_actual_personal_use_labels(tmp_path):
    import json
    from spt_gui import self_test

    report = tmp_path / 'selftest.json'
    assert self_test(report) == 0
    data = json.loads(report.read_text(encoding='utf-8'))
    assert data.get('personal_use_labels') == [
        'Coretax → Excel · for personal use only',
    ]
    assert data['credentials_accessed'] is False
    assert data['live_scrape'] is False
