"""Dialog readiness contracts, exercised only on the synthetic Windows runner."""
import gc
import tkinter as tk

import pytest

from support_gui import ConsentController, consent_event, named_widget


def wait_for_existing_timers(root):
    done = tk.BooleanVar(root)
    root.after(250, lambda: done.set(True))
    root.wait_variable(done)
    root.update_idletasks()


@pytest.fixture
def active_window(tmp_path):
    from spt_desktop.app import App
    root = tk.Tk()
    errors = []
    root.report_callback_exception = lambda *args: errors.append(args)
    controller = ConsentController({})
    app = App(root, tmp_path, controller=controller)
    root.geometry('900x700')
    app.npwp.set('0000000000000001')
    app.year.set('2025')
    app.start()
    wait_for_existing_timers(root)
    root.focus_force()
    try:
        yield root, app, controller
    finally:
        app._close_interaction()
        app._dispose()
        controller.active = False
        for token in root.tk.splitlist(root.tk.call('after', 'info')):
            root.after_cancel(token)
        root.destroy()
        del app
        gc.collect()
        assert not errors, errors


def payload(kind, count):
    if kind == 'selection':
        return {'records': [{'record_id': f'synthetic-{index:04d}', 'meta': {
            'Jenis Pajak': 'PPN', 'Masa Pajak': 'Januari 2025', 'Model SPT': 'Normal'}}
            for index in range(count)]}
    return {'folder': r'C:\SYNTHETIC\Downloads\export',
            'files': [f'SPT Masa PPN/synthetic-{index:04d}.xlsx' for index in range(count)]}


def assert_body_ready(dialog):
    viewport = named_widget(dialog, 'body_viewport')
    item, = viewport.find_all()
    body = viewport.nametowidget(viewport.itemcget(item, 'window'))
    assert int(viewport.itemcget(item, 'width')) == viewport.winfo_width()
    assert int(viewport.itemcget(item, 'height')) >= max(body.winfo_reqheight(), viewport.winfo_height())
    assert viewport.bbox(item)[3] <= float(viewport.cget('scrollregion').split()[3])
    actions = named_widget(dialog, 'actions')
    assert actions.winfo_rooty() >= viewport.winfo_rooty() + viewport.winfo_height()
    assert actions.winfo_rooty() + actions.winfo_height() <= dialog.winfo_rooty() + dialog.winfo_height()


@pytest.mark.parametrize('kind,count', [
    ('selection', 0), ('selection', 3), ('selection', 1000), ('overwrite', 1), ('overwrite', 101),
])
def test_initial_consent_layout_ready_after_idle_without_timer_wait(active_window, kind, count):
    root, app, controller = active_window
    controller.payload = payload(kind, count)
    app.on_event(consent_event(controller, kind))
    interaction = app._interaction
    dialog = interaction['dialog']
    # Idle geometry must be ready without waiting for the resize timer.
    # This is a readiness contract, not a fragile elapsed-time assertion.
    root.update_idletasks()
    assert_body_ready(dialog)
    assert interaction['layout_after'] is None
    tree = named_widget(dialog, 'records' if kind == 'selection' else 'files')
    assert len(tree.get_children()) == count
    assert not tree.selection() and not controller.replies and not controller.stopped
    if kind == 'selection':
        assert named_widget(dialog, 'confirm').instate(['disabled'])
    else:
        assert named_widget(dialog, 'folder').get() == controller.payload['folder']
        assert root.focus_get() is named_widget(dialog, 'decline')


def test_filter_content_reflow_finishes_at_idle_and_keeps_reset_consent(active_window):
    root, app, controller = active_window
    controller.payload = payload('selection', 3)
    app.on_event(consent_event(controller))
    dialog = app._interaction['dialog']
    dialog.geometry('540x390')
    wait_for_existing_timers(root)
    tree = named_widget(dialog, 'records')
    tree.selection_set('record-0')
    root.update()
    named_widget(dialog, 'search').insert(0, 'no-synthetic-match')
    root.update_idletasks()
    assert_body_ready(dialog)
    assert app._interaction['layout_after'] is None
    assert not tree.selection() and not tree.get_children()
    assert named_widget(dialog, 'confirm').instate(['disabled'])
    notice = named_widget(dialog, 'notice')
    text = str(notice.getvar(str(notice.cget('textvariable'))))
    assert 'Pencarian berubah. Pilih lagi SPT yang akan diunduh.' in text
    assert 'Tidak ada SPT yang cocok dengan pencarian.' in text
    assert not controller.replies and not controller.stopped


@pytest.mark.parametrize('kind', ['selection', 'overwrite'])
def test_stop_retires_initial_layout_work_without_late_consent(active_window, kind):
    root, app, controller = active_window
    controller.payload = payload(kind, 3)
    sentinel = root.after(60000, lambda: None)
    app.on_event(consent_event(controller, kind))
    interaction = app._interaction
    dialog = interaction['dialog']
    pending = interaction['layout_after']
    assert pending is not None
    app.stop()
    root.update_idletasks()
    wait_for_existing_timers(root)
    assert app._interaction is None and not dialog.winfo_exists() and root.grab_current() is None
    assert interaction['layout_after'] is None and interaction['bindings'] == []
    remaining = root.tk.splitlist(root.tk.call('after', 'info'))
    assert pending not in remaining and sentinel in remaining
    assert controller.stopped and not controller.replies
    root.after_cancel(sentinel)
