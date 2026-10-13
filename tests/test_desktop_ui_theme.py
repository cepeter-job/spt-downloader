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
