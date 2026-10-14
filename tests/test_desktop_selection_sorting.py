"""Real Tk header sorting contracts. GitHub Windows execution only."""
from copy import deepcopy
import pytest
from test_desktop_selection_gui import window, widgets, button


def inventory():
    return {'records': [
        {'record_id': '::synthetic {return}; [literal] / id',
         'meta': {'Jenis Pajak': 'PPN', 'Masa Pajak': 'Januari 2025', 'Model SPT': 'Normal'}},
        {'record_id': 'badan-one', 'meta': {'Jenis Pajak': 'PPh Badan',
         'Masa Pajak': 'Januari - Desember 2025', 'Model SPT': 'Amendment 001'}},
        {'record_id': '21-one', 'meta': {'Jenis Pajak': 'PPh Pasal 21/26',
         'Masa Pajak': 'Februari 2025', 'Model SPT': 'Normal'}},
        {'record_id': 'badan-two', 'meta': {'Jenis Pajak': 'pph badan',
         'Masa Pajak': 'Januari - Desember 2025', 'Model SPT': 'Amendment 0002'}},
    ]}


def tree_in(dialog):
    return next(widget for widget in widgets(dialog) if widget.winfo_class() == 'Treeview')


def search_in(dialog):
    return next(widget for widget in widgets(dialog) if widget.winfo_class() == 'TEntry')


def click_type_heading(root, tree):
    command = tree.heading('type', 'command')
    assert command, 'Jenis pajak header has no sorting action'
    root.tk.call(command)
    root.update()


def source_rows(payload):
    return {f'record-{ordinal}': tuple(str(record['meta'].get(key, '')) for key in
             ('Jenis Pajak', 'Masa Pajak', 'Model SPT')) + (record['record_id'],)
            for ordinal, record in enumerate(payload['records'])}


@pytest.mark.parametrize('clicks', [1, 2, 3])
def test_header_toggles_two_directions_and_preserves_source_rows(tmp_path, clicks):
    payload = inventory()
    original = deepcopy(payload)
    rows = source_rows(payload)
    with window(tmp_path, payload) as (root, app, controller, dialog):
        tree = tree_in(dialog)
        assert tree.heading('type', 'text') == 'Jenis pajak'
        assert tuple(tree.get_children()) == tuple(rows)
        assert not tree.selection()
        for _ in range(clicks):
            click_type_heading(root, tree)
        descending = clicks % 2 == 0
        expected = sorted(rows, key=lambda iid: rows[iid][0].casefold(), reverse=descending)
        assert list(tree.get_children()) == expected
        assert tree.heading('type', 'text') == ('Jenis pajak ▼' if descending else 'Jenis pajak ▲')
        assert {iid: tuple(tree.item(iid, 'values')) for iid in tree.get_children()} == rows
        assert payload == original and not controller.replies and not controller.stopped
        assert not tree.selection()
        assert button(dialog, 'Sedot SPT terpilih').instate(['disabled'])


@pytest.mark.parametrize('clicks', [1, 2])
def test_sorting_keeps_exact_selected_identifiers_and_inventory_order_in_reply(tmp_path, clicks):
    payload = inventory()
    with window(tmp_path, payload) as (root, app, controller, dialog):
        tree = tree_in(dialog)
        chosen = ('record-0', 'record-3')
        tree.selection_set(chosen)
        tree.event_generate('<<TreeviewSelect>>')
        root.update()
        for _ in range(clicks):
            click_type_heading(root, tree)
            assert set(tree.selection()) == set(chosen)
            assert not button(dialog, 'Sedot SPT terpilih').instate(['disabled'])
            assert not controller.replies
        button(dialog, 'Sedot SPT terpilih').invoke()
        root.update()
        expected_ids = [payload['records'][ordinal]['record_id'] for ordinal in (0, 3)]
        assert controller.replies == [('selection', 'a' * 32, {'selected_ids': expected_ids})]
        assert app._ui_state.selected_count == len(expected_ids)
        assert not controller.stopped and not dialog.winfo_exists()


def test_sorting_keeps_active_search_and_visible_selection_with_stable_ties(tmp_path):
    payload = inventory()
    with window(tmp_path, payload) as (root, app, controller, dialog):
        tree = tree_in(dialog)
        entry = search_in(dialog)
        entry.insert(0, 'Badan')
        root.update()
        assert list(tree.get_children()) == ['record-1', 'record-3']
        tree.selection_set('record-3')
        tree.event_generate('<<TreeviewSelect>>')
        root.update()
        for _ in range(2):
            click_type_heading(root, tree)
            assert entry.get() == 'Badan'
            assert list(tree.get_children()) == ['record-1', 'record-3']
            assert tuple(tree.selection()) == ('record-3',)
            assert not button(dialog, 'Sedot SPT terpilih').instate(['disabled'])
            assert any(widget.winfo_class() == 'TLabel' and
                       str(widget.cget('text')).startswith('1 SPT dipilih')
                       for widget in widgets(dialog))
        button(dialog, 'Sedot SPT terpilih').invoke()
        assert controller.replies == [('selection', 'a' * 32, {'selected_ids': ['badan-two']})]


def test_search_change_preserves_sort_mode_but_clears_consent_as_before(tmp_path):
    payload = inventory()
    rows = source_rows(payload)
    with window(tmp_path, payload) as (root, app, controller, dialog):
        tree = tree_in(dialog)
        entry = search_in(dialog)
        click_type_heading(root, tree)
        click_type_heading(root, tree)
        tree.selection_set('record-0')
        tree.event_generate('<<TreeviewSelect>>')
        root.update()
        entry.insert(0, 'Badan')
        root.update()
        assert list(tree.get_children()) == ['record-1', 'record-3']
        assert not tree.selection()
        assert button(dialog, 'Sedot SPT terpilih').instate(['disabled'])
        assert tree.heading('type', 'text') == 'Jenis pajak ▼'
        entry.delete(0, 'end')
        root.update()
        expected = sorted(rows, key=lambda iid: rows[iid][0].casefold(), reverse=True)
        assert list(tree.get_children()) == expected
        assert not tree.selection() and not controller.replies


@pytest.mark.parametrize('payload', [{'records': []}, {'records': [
    {'record_id': 'synthetic-no-type', 'meta': {}}]}])
def test_empty_or_missing_type_sorting_does_not_authorize_records(tmp_path, payload):
    with window(tmp_path, payload) as (root, app, controller, dialog):
        tree = tree_in(dialog)
        original = tuple(tree.get_children())
        for _ in range(2):
            click_type_heading(root, tree)
            assert tuple(tree.get_children()) == original
            assert not tree.selection() and not controller.replies
            assert button(dialog, 'Sedot SPT terpilih').instate(['disabled'])


def test_no_search_matches_can_be_sorted_and_cleared_without_callback_errors(tmp_path):
    payload = inventory()
    rows = source_rows(payload)
    with window(tmp_path, payload) as (root, app, controller, dialog):
        tree = tree_in(dialog)
        entry = search_in(dialog)
        entry.insert(0, 'synthetic-no-matches')
        root.update()
        assert not tree.get_children()
        click_type_heading(root, tree)
        assert not tree.get_children() and not tree.selection()
        entry.delete(0, 'end')
        root.update()
        assert list(tree.get_children()) == sorted(rows, key=lambda iid: rows[iid][0].casefold())
        assert not tree.selection() and not controller.replies
