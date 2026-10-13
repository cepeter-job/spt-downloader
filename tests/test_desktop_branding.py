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
def test_personal_use_subtitle_and_bottom_right_credit(tmp_path, width, height):
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
        credits = [label for label in labels if str(label['text']) == 'for personal use : punto ap']
        assert len(credits) == 1
        credit = credits[0]
        right_gap = root.winfo_rootx() + root.winfo_width() - credit.winfo_rootx() - credit.winfo_width()
        bottom_gap = root.winfo_rooty() + root.winfo_height() - credit.winfo_rooty() - credit.winfo_height()
        assert 0 <= right_gap <= 25
        assert 0 <= bottom_gap <= 25
        # Scrolled content can extend beyond the viewport; compare the visible shell.
        shell_labels = [label for label in labels if label is not credit and label.winfo_ismapped()
                        and not str(label).startswith(str(window.view.workspace))]
        assert credit.winfo_rooty() >= max(label.winfo_rooty() + label.winfo_height() for label in shell_labels)
        assert credit.winfo_rooty() >= window.view.viewport.winfo_rooty() + window.view.viewport.winfo_height()
    finally:
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
        'for personal use : punto ap',
    ]
    assert data['credentials_accessed'] is False
    assert data['live_scrape'] is False
