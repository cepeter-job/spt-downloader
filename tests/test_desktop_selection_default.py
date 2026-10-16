"""Default selection order uses real Tk, never a worker or live capture."""
from copy import deepcopy
import json

from support_gui import window, widgets, button


def payload(rows):
    return {'records': [{'record_id': rid, 'meta': {
        'Jenis Pajak': tax, 'Masa Pajak': period, 'Model SPT': model}}
        for rid, tax, period, model in rows]}


def tree_in(dialog):
    return next(w for w in widgets(dialog) if w.winfo_class() == 'Treeview')


def visible_ids(tree):
    return [tree.item(iid, 'values')[3] for iid in tree.get_children()]


def mixed_inventory():
    return payload([
        ('unknown', 'AAA other type', '2025', 'Normal'),
        ('ppn', 'PPN', 'Januari 2025', 'Normal'),
        ('unifikasi', 'PPh Unifikasi', 'Januari 2025', 'Normal'),
        ('21', 'PPh Pasal 21/26', 'Januari 2025', 'Normal'),
        ('badan', 'PPh Badan', '2025', 'Normal')])


def test_default_priority_before_any_click_and_manual_header_still_alphabetical(tmp_path):
    records = mixed_inventory()
    original = deepcopy(records)
    with window(tmp_path, records) as (root, app, controller, dialog):
        tree = tree_in(dialog)
        assert visible_ids(tree) == ['badan', '21', 'unifikasi', 'ppn', 'unknown']
        assert not tree.selection() and button(dialog, 'Sedot SPT terpilih').instate(['disabled'])
        root.tk.call(tree.heading('type', 'command')); root.update()
        assert visible_ids(tree) == ['unknown', 'badan', '21', 'unifikasi', 'ppn']
        root.tk.call(tree.heading('type', 'command')); root.update()
        assert visible_ids(tree) == ['ppn', 'unifikasi', '21', 'badan', 'unknown']
        assert records == original and not controller.replies and not controller.stopped


def test_default_priority_matches_whole_casefolded_caption_not_substrings(tmp_path):
    records = payload([
        ('lookalike', 'PPh Badan extra', '2025', 'Normal'),
        ('missing', '', '2025', 'Normal'),
        ('ppn', 'ppn', '2025', 'Normal'),
        ('unifikasi', 'pPh uNiFiKaSi', '2025', 'Normal'),
        ('21', 'pPh pAsAl 21/26', '2025', 'Normal'),
        ('badan', 'pph badan', '2025', 'Normal')])
    with window(tmp_path, records) as (root, app, controller, dialog):
        assert visible_ids(tree_in(dialog)) == ['badan', '21', 'unifikasi', 'ppn', 'missing', 'lookalike']
        assert not controller.replies


def test_default_chronology_in_all_four_types_without_header_click(tmp_path):
    months = ('Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
              'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember')
    records = payload([(f'{tax}-{month}', tax, months[month - 1] + ' 2025', 'Normal')
        for month in (12, 4, 9, 2, 11, 6, 1, 10, 5, 8, 3, 7)
        for tax in ('PPN', 'PPh Unifikasi', 'PPh Pasal 21/26', 'PPh Badan')])
    with window(tmp_path, records) as (root, app, controller, dialog):
        expected = [f'{tax}-{month}' for tax in
            ('PPh Badan', 'PPh Pasal 21/26', 'PPh Unifikasi', 'PPN') for month in range(1, 13)]
        assert visible_ids(tree_in(dialog)) == expected
        assert not controller.replies


def test_default_numeric_amendments_and_source_ties_within_month(tmp_path):
    records = payload([
        ('ten', 'PPh Unifikasi', 'Januari 2025', 'Pembetulan 10'),
        ('feb', 'PPh Unifikasi', 'Februari 2025', 'Normal'),
        ('two', 'PPh Unifikasi', 'Januari 2025', 'Pembetulan 2'),
        ('one-padded', 'PPh Unifikasi', 'Januari 2025', 'Pembetulan 01'),
        ('normal', 'PPh Unifikasi', 'Januari 2025', 'Normal'),
        ('one', 'PPh Unifikasi', 'Januari 2025', 'Pembetulan 1')])
    with window(tmp_path, records) as (root, app, controller, dialog):
        assert visible_ids(tree_in(dialog)) == ['normal', 'one-padded', 'one', 'two', 'ten', 'feb']


def test_filter_clear_keeps_default_priority_without_restoring_consent(tmp_path):
    with window(tmp_path, mixed_inventory()) as (root, app, controller, dialog):
        tree = tree_in(dialog)
        tree.selection_set('record-1'); tree.event_generate('<<TreeviewSelect>>'); root.update()
        entry = next(w for w in widgets(dialog) if w.winfo_class() == 'TEntry')
        entry.insert(0, 'PPh'); root.update()
        assert visible_ids(tree) == ['badan', '21', 'unifikasi']
        assert not tree.selection()
        entry.delete(0, 'end'); root.update()
        assert visible_ids(tree) == ['badan', '21', 'unifikasi', 'ppn', 'unknown']
        assert not tree.selection() and not controller.replies
        assert button(dialog, 'Sedot SPT terpilih').instate(['disabled'])


def test_default_display_does_not_reorder_confirmed_inventory_ids(tmp_path):
    with window(tmp_path, mixed_inventory()) as (root, app, controller, dialog):
        tree = tree_in(dialog)
        assert visible_ids(tree) == ['badan', '21', 'unifikasi', 'ppn', 'unknown']
        tree.selection_set(('record-4', 'record-1'))
        tree.event_generate('<<TreeviewSelect>>'); root.update()
        button(dialog, 'Sedot SPT terpilih').invoke(); root.update()
        assert controller.replies == [('selection', 'a' * 32, {'selected_ids': ['ppn', 'badan']})]


def test_source_and_frozen_selftest_observes_initial_order_including_unifikasi(tmp_path):
    from spt_gui import self_test
    path = tmp_path / 'default-order.json'
    assert self_test(path) == 0
    sorting = json.loads(path.read_text(encoding='utf-8'))['selection_sorting_control']
    assert sorting.get('default_ordered_ids') == [
        'synthetic-badan-two', 'synthetic-badan-one', 'synthetic-21', 'synthetic-unifikasi',
        'synthetic-ppn-normal', 'synthetic-ppn-one', 'synthetic-ppn-two',
        '::synthetic {return}; [literal] / id', 'synthetic-ppn-feb']
