"""Runner-only layout policy and real Windows work-area contracts."""
import gc
import pytest


def test_layout_thresholds_do_not_shrink_typography():
    from spt_desktop.ui_theme import layout_policy
    assert layout_policy(959, 600).compact is True
    assert layout_policy(960, 600).compact is False
    assert layout_policy(960, 559).form_stacked is True
    assert layout_policy(960, 560).form_stacked is False
    assert layout_policy(640, 540).stage_columns == 2
    assert layout_policy(1120, 700).stage_columns == 4
    assert layout_policy(1120, 700).summary_width_dip == 244
    assert layout_policy(1120, 700).gap_dip == 24


def test_dip_conversion_is_applied_once():
    from spt_desktop.ui_theme import dip_to_px
    assert dip_to_px(24, 1.0) == 24
    assert dip_to_px(24, 1.5) == 36
    assert dip_to_px(24, 2.0) == 48


def test_native_work_area_is_measured_and_effective_scale_is_tk_scale():
    from spt_desktop.ui_theme import client_work_area, effective_scale
    import tkinter as tk
    root = tk.Tk()
    try:
        root.update_idletasks()
        width, height = client_work_area(root)
        assert width > 0 and height > 0
        assert effective_scale(root) == pytest.approx(root.winfo_fpixels('1i') / 96)
    finally:
        root.destroy()
        gc.collect()


def test_window_geometry_never_exceeds_measured_client_work_area(monkeypatch):
    from spt_desktop import ui_theme
    import tkinter as tk
    root = tk.Tk()
    try:
        monkeypatch.setattr(ui_theme, 'client_work_area', lambda root: (800, 600))
        ui_theme.configure_theme(root)
        root.update_idletasks()
        assert root.winfo_width() <= 800 and root.winfo_height() <= 600
        assert root.minsize()[0] <= 800 and root.minsize()[1] <= 600
        names = set(root.tk.splitlist(root.tk.call('font', 'names')))
        ui_theme.configure_theme(root)
        assert set(root.tk.splitlist(root.tk.call('font', 'names'))) == names
    finally:
        root.destroy()
        gc.collect()


def test_work_area_failure_preserves_window_manager_geometry(monkeypatch):
    from spt_desktop import ui_theme
    import tkinter as tk
    root = tk.Tk()
    try:
        root.geometry('400x300')
        root.update_idletasks()
        old = (root.winfo_width(), root.winfo_height(), root.minsize())
        def failed(root):
            raise OSError('Synthetic unavailable monitor information')
        monkeypatch.setattr(ui_theme, 'client_work_area', failed)
        ui_theme.configure_theme(root)
        root.update_idletasks()
        assert (root.winfo_width(), root.winfo_height(), root.minsize()) == old
    finally:
        root.destroy()
        gc.collect()


def test_dialog_sizes_leave_parent_unchanged():
    from spt_desktop import ui_theme
    import tkinter as tk
    from tkinter import ttk
    root = tk.Tk()
    try:
        ui_theme.configure_theme(root)
        root.geometry('800x620+12+12')
        root.update_idletasks()
        before = (root.geometry(), root.minsize(), root.tk.call('tk', 'scaling'),
                  root.tk.call('font', 'actual', 'SPTBody'))
        dialog = tk.Toplevel(root)
        dialog.transient(root)
        scale = ui_theme.configure_dialog(dialog, root, size_dip=(920, 600))
        root.update_idletasks()
        available = ui_theme.client_work_area(dialog, monitor_window=root)
        assert 0 < dialog.winfo_width() <= available[0]
        assert 0 < dialog.winfo_height() <= available[1]
        assert dialog.minsize()[0] <= available[0] and dialog.minsize()[1] <= available[1]
        assert scale == pytest.approx(ui_theme.effective_scale(root))
        assert (root.geometry(), root.minsize(), root.tk.call('tk', 'scaling'),
                root.tk.call('font', 'actual', 'SPTBody')) == before
        assert int(ttk.Style(dialog).lookup('SPT.Dialog.Treeview', 'rowheight')) == (
            int(root.tk.call('font', 'metrics', 'SPTBody', '-linespace')) + ui_theme.dip_to_px(8, scale))
    finally:
        root.destroy()
        gc.collect()


def test_dialog_work_area_failure_preserves_window_manager_choice(monkeypatch):
    from spt_desktop import ui_theme
    import tkinter as tk
    root = tk.Tk()
    try:
        ui_theme.configure_theme(root)
        dialog = tk.Toplevel(root)
        dialog.geometry('320x210+16+16')
        root.update_idletasks()
        before = (dialog.geometry(), dialog.minsize(), root.geometry())
        calls = []
        def unavailable(window, *, monitor_window=None):
            calls.append((window, monitor_window))
            raise OSError('Synthetic missing work area')
        monkeypatch.setattr(ui_theme, 'client_work_area', unavailable)
        ui_theme.configure_dialog(dialog, root, size_dip=(920, 600))
        root.update_idletasks()
        assert calls == [(dialog, root)]
        assert (dialog.geometry(), dialog.minsize(), root.geometry()) == before
    finally:
        root.destroy()
        gc.collect()


def test_dialog_small_work_area_does_not_force_an_unreachable_minimum(monkeypatch):
    from spt_desktop import ui_theme
    import tkinter as tk
    root = tk.Tk()
    try:
        ui_theme.configure_theme(root)
        dialog = tk.Toplevel(root)
        root.update_idletasks()
        calls = []
        def small(window, *, monitor_window=None):
            calls.append((window, monitor_window))
            return 420, 280
        monkeypatch.setattr(ui_theme, 'client_work_area', small)
        ui_theme.configure_dialog(dialog, root, size_dip=(920, 600))
        root.update_idletasks()
        assert calls == [(dialog, root)]
        assert dialog.winfo_width() <= 420 and dialog.winfo_height() <= 280
        assert dialog.minsize()[0] <= 420 and dialog.minsize()[1] <= 280
    finally:
        root.destroy()
        gc.collect()
