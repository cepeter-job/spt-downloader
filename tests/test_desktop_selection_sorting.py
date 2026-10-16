"""Real Tk header sorting contracts. GitHub Windows execution only."""
from copy import deepcopy
import pytest
from support_gui import window, widgets, button


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
        assert tuple(tree.get_children()) == ('record-1', 'record-3', 'record-2', 'record-0')
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

# Literal oracles below catch type-only/lexical sorts and reversing all tiers.
def chronological_payload(rows):
    return {'records': [{'record_id': identifier, 'meta': {
        'Jenis Pajak': tax, 'Masa Pajak': period, 'Model SPT': model}}
        for identifier, tax, period, model in rows]}


def visible_ids(tree):
    return [tree.item(iid, 'values')[3] for iid in tree.get_children()]


@pytest.mark.parametrize('clicks', [1, 2, 3])
def test_each_tax_type_sorts_all_twelve_months_chronologically(tmp_path, clicks):
    months = ('Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
              'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember')
    order = (11, 3, 8, 1, 10, 5, 0, 9, 4, 7, 2, 6)
    payload = chronological_payload([
        (f'{tax}-{i + 1}', tax, months[i] + ' 2025', 'Normal')
        for i in order for tax in ('PPN', 'PPh Badan')])
    original = deepcopy(payload)
    with window(tmp_path, payload) as (root, app, controller, dialog):
        tree = tree_in(dialog)
        assert visible_ids(tree) == [f'{tax}-{month}' for tax in ('PPh Badan', 'PPN') for month in range(1, 13)]
        for _ in range(clicks):
            click_type_heading(root, tree)
        taxes = ('PPN', 'PPh Badan') if clicks == 2 else ('PPh Badan', 'PPN')
        assert visible_ids(tree) == [f'{tax}-{month}' for tax in taxes for month in range(1, 13)]
        assert payload == original and not tree.selection() and not controller.replies


@pytest.mark.parametrize('clicks', [1, 2])
def test_normal_then_numeric_amendments_keep_aliases_and_leading_zero_ties(tmp_path, clicks):
    models = [('ten', 'Pembetulan 10'), ('two', 'Pembetulan 2'),
              ('one-padded', 'Pembetulan 01'), ('one', 'Pembetulan 1'),
              ('normal', 'Normal'), ('zero', 'Pembetulan 0'),
              ('alias-two', 'Amendment 002'), ('ke-one', 'Pembetulan ke-1'),
              ('case-normal', 'nOrMaL'), ('unknown', 'Revisi 3'), ('empty', '')]
    payload = chronological_payload([(identifier, 'PPN', 'Januari 2025', model)
                                     for identifier, model in models])
    with window(tmp_path, payload) as (root, app, controller, dialog):
        tree = tree_in(dialog)
        values = source_rows(payload)
        for _ in range(clicks):
            click_type_heading(root, tree)
        assert visible_ids(tree) == ['normal', 'case-normal', 'zero', 'one-padded',
            'one', 'ke-one', 'two', 'alias-two', 'ten', 'unknown', 'empty']
        assert {iid: tuple(tree.item(iid, 'values')) for iid in tree.get_children()} == values


@pytest.mark.parametrize('clicks', [1, 2])
def test_year_before_month_annual_after_months_and_unknown_periods_stay_stable(tmp_path, clicks):
    payload = chronological_payload([
        ('unknown-first', 'PPN', 'Januari - November 2025', 'Pembetulan 10'),
        ('jan25', 'PPN', 'Januari 2025', 'Normal'),
        ('annual24-amended', 'PPN', 'Januari - Desember 2024', 'Pembetulan 2'),
        ('dec24', 'PPN', 'Desember 2024', 'Normal'),
        ('annual24-normal', 'PPN', '2024', 'Normal'),
        ('jan24', 'PPN', 'Januari 2024', 'Normal'),
        ('annual25', 'PPN', '2025', 'Normal'),
        ('unknown-last', 'PPN', '', 'Normal'),
        ('dec25', 'PPN', 'Desember 2025', 'Normal')])
    with window(tmp_path, payload) as (root, app, controller, dialog):
        tree = tree_in(dialog)
        for _ in range(clicks):
            click_type_heading(root, tree)
        assert visible_ids(tree) == ['jan24', 'dec24', 'annual24-normal',
            'annual24-amended', 'jan25', 'dec25', 'annual25', 'unknown-first', 'unknown-last']


@pytest.mark.parametrize('bad_period', [
    'Januari 2025 extra', 'x Januari 2025', 'Januari 25', 'Januari ２０２５',
    'Januari 2025\n', '2025-01', 'Februari - Desember 2025'])
def test_ambiguous_period_is_not_guessed_from_a_substring(tmp_path, bad_period):
    payload = chronological_payload([
        ('unknown-amended', 'PPN', bad_period, 'Pembetulan 10'),
        ('unknown-normal', 'PPN', bad_period, 'Normal'),
        ('known', 'PPN', 'Desember 2025', 'Normal')])
    with window(tmp_path, payload) as (root, app, controller, dialog):
        tree = tree_in(dialog)
        click_type_heading(root, tree)
        assert visible_ids(tree) == ['known', 'unknown-amended', 'unknown-normal']


@pytest.mark.parametrize('bad_model', [
    'Pembetulan 1 extra', 'x Pembetulan 1', 'Pembetulan -1',
    'Pembetulan １', 'Amendment 1\n', 'Normal 1'])
def test_unknown_model_is_not_guessed_from_embedded_digits(tmp_path, bad_model):
    payload = chronological_payload([
        ('unknown', 'PPN', 'Januari 2025', bad_model),
        ('known', 'PPN', 'Januari 2025', 'Pembetulan 2'),
        ('normal', 'PPN', 'Januari 2025', 'Normal')])
    with window(tmp_path, payload) as (root, app, controller, dialog):
        tree = tree_in(dialog)
        click_type_heading(root, tree)
        assert visible_ids(tree) == ['normal', 'known', 'unknown']


@pytest.mark.parametrize('clicks', [1, 2])
def test_chronology_preserves_filtered_selection_focus_and_inventory_order_reply(tmp_path, clicks):
    special = '::synthetic {january}; [literal] / id'
    payload = chronological_payload([
        (special, 'PPN', 'Januari 2025', 'Pembetulan 10'),
        ('hidden', 'PPh Badan', '2025', 'Normal'),
        ('normal', 'ppn', 'Januari 2025', 'Normal'),
        ('two', 'PPN', 'Januari 2025', 'Pembetulan 2'),
        ('feb', 'PPN', 'Februari 2025', 'Normal')])
    with window(tmp_path, payload) as (root, app, controller, dialog):
        tree = tree_in(dialog)
        entry = search_in(dialog)
        entry.insert(0, 'PPN')
        root.update()
        chosen = ('record-0', 'record-2')
        tree.selection_set(chosen)
        tree.focus('record-0')
        tree.event_generate('<<TreeviewSelect>>')
        root.update()
        for _ in range(clicks):
            click_type_heading(root, tree)
            assert visible_ids(tree) == ['normal', 'two', special, 'feb']
            assert set(tree.selection()) == set(chosen) and tree.focus() == 'record-0'
            assert entry.get() == 'PPN' and not controller.replies
            assert any(w.winfo_class() == 'TLabel' and
                       str(w.cget('text')).startswith('2 SPT dipilih') for w in widgets(dialog))
        button(dialog, 'Sedot SPT terpilih').invoke()
        assert controller.replies == [('selection', 'a' * 32, {'selected_ids': [special, 'normal']})]


def test_chronology_survives_filter_clear_without_restoring_consent(tmp_path):
    payload = chronological_payload([
        ('feb', 'PPN', 'Februari 2025', 'Normal'),
        ('ten', 'PPN', 'Januari 2025', 'Pembetulan 10'),
        ('jan', 'PPN', 'Januari 2025', 'Normal')])
    with window(tmp_path, payload) as (root, app, controller, dialog):
        tree = tree_in(dialog)
        entry = search_in(dialog)
        click_type_heading(root, tree)
        click_type_heading(root, tree)
        tree.selection_set('record-1')
        tree.event_generate('<<TreeviewSelect>>')
        root.update()
        entry.insert(0, 'Januari')
        root.update()
        assert visible_ids(tree) == ['jan', 'ten'] and not tree.selection()
        assert button(dialog, 'Sedot SPT terpilih').instate(['disabled'])
        entry.delete(0, 'end')
        root.update()
        assert visible_ids(tree) == ['jan', 'ten', 'feb'] and not tree.selection()
        assert tree.heading('type', 'text') == 'Jenis pajak ▼' and not controller.replies


def test_source_selftest_observes_chronology_in_both_type_directions(tmp_path):
    import json
    from spt_gui import self_test
    path = tmp_path / 'chronological-sorting.json'
    assert self_test(path) == 0
    data = json.loads(path.read_text(encoding='utf-8'))
    sorting = data['selection_sorting_control']
    assert sorting.get('hierarchy') == ['type', 'year', 'month', 'model']
    assert sorting['ordered_ids'] == [
        ['synthetic-badan-two', 'synthetic-badan-one', 'synthetic-21',
         'synthetic-ppn-normal', 'synthetic-ppn-one', 'synthetic-ppn-two',
         '::synthetic {return}; [literal] / id', 'synthetic-ppn-feb'],
        ['synthetic-ppn-normal', 'synthetic-ppn-one', 'synthetic-ppn-two',
         '::synthetic {return}; [literal] / id', 'synthetic-ppn-feb',
         'synthetic-21', 'synthetic-badan-two', 'synthetic-badan-one']]
    assert sorting['selection_preserved'] is True
    assert sorting['confirmed_ids'] == ['::synthetic {return}; [literal] / id', 'synthetic-badan-two']
