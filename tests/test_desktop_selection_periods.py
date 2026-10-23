"""Runner-only real Tk period captions; all records are synthetic."""
from copy import deepcopy

import pytest

from support_gui import button, named_widget, widgets, window


def inventory(rows):
    return {'records': [{'record_id': f'synthetic-{index}', 'meta': {
        'Jenis Pajak': tax, 'Masa Pajak': period, 'Model SPT': 'Normal'}}
        for index, (tax, period) in enumerate(rows)]}


def tree_in(dialog):
    return next(widget for widget in widgets(dialog) if widget.winfo_class() == 'Treeview')


@pytest.mark.parametrize('format', ['code', 'number', 'padded', 'caption'])
def test_monthly_periods_display_all_indonesian_month_names(tmp_path, format):
    months = [
        ('01', 'Januari'), ('02', 'Februari'), ('03', 'Maret'), ('04', 'April'),
        ('05', 'Mei'), ('06', 'Juni'), ('07', 'Juli'), ('08', 'Agustus'),
        ('09', 'September'), ('10', 'Oktober'), ('11', 'November'), ('12', 'Desember')]
    periods = {'code': [number + number + '2025' for number, _ in months],
               'number': [str(int(number)) for number, _ in months],
               'padded': [number for number, _ in months],
               'caption': [name + ' 2025' for _, name in months]}[format]
    taxes = ('PPh Pasal 21/26', 'PPh Unifikasi', 'PPN')
    payload = inventory([(taxes[index % 3], period) for index, period in enumerate(periods)])
    original = deepcopy(payload)
    with window(tmp_path, payload) as (root, app, controller, dialog):
        tree = tree_in(dialog)
        assert [tree.item(f'record-{index}', 'values')[1] for index in range(12)] == [
            'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
            'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
        assert payload == original and not tree.selection() and not controller.replies


def test_only_exact_badan_type_displays_tahunan_and_keeps_source_periods(tmp_path):
    payload = inventory([
        ('PPh Badan', '01122025'), ('pph badan', '2024'),
        ('PPh Badan', 'Februari 2023 - Januari 2024'),
        ('PPh Badan extra', '2025'), ('', '2025')])
    original = deepcopy(payload)
    with window(tmp_path, payload) as (root, app, controller, dialog):
        tree = tree_in(dialog)
        assert [tree.item(f'record-{index}', 'values')[1] for index in range(5)] == [
            'Tahunan', 'Tahunan', 'Tahunan', '2025', '2025']
        assert payload == original and not controller.replies


def test_ambiguous_periods_keep_their_literal_source_text(tmp_path):
    periods = ['00', '13', '001', '01022025', '02012023', '01122025', '2025',
               '2025-01', 'Januari 2025 extra', 'Januari 2025\n', '０１',
               '01010000', 'Januari - November 2025', '', 'Januari']
    payload = inventory([('PPN', period) for period in periods])
    with window(tmp_path, payload) as (root, app, controller, dialog):
        tree = tree_in(dialog)
        assert [tree.item(f'record-{index}', 'values')[1] for index in range(len(periods))] == periods
        assert not controller.replies


def test_search_accepts_display_month_annual_caption_and_original_source(tmp_path):
    payload = inventory([('PPN', '02022025'), ('PPh Badan', '01122025')])
    original = deepcopy(payload)
    with window(tmp_path, payload) as (root, app, controller, dialog):
        tree, search = tree_in(dialog), named_widget(dialog, 'search')
        for query, expected in [('Februari', ['synthetic-0']), ('Tahunan', ['synthetic-1']),
                                ('01122025', ['synthetic-1']), ('2025', ['synthetic-1', 'synthetic-0']),
                                ('02022025', ['synthetic-0'])]:
            search.delete(0, 'end')
            search.insert(0, query)
            root.update()
            assert [tree.item(iid, 'values')[3] for iid in tree.get_children()] == expected
            assert not tree.selection() and not controller.replies
        tree.selection_set(tree.get_children()[0])
        tree.event_generate('<<TreeviewSelect>>')
        root.update()
        button(dialog, 'Sedot SPT terpilih').invoke()
        assert controller.replies == [('selection', 'a' * 32, {'selected_ids': ['synthetic-0']})]
        assert payload == original and not controller.stopped


def test_display_captions_do_not_replace_original_year_and_month_sort_keys(tmp_path):
    payload = inventory([('PPN', 'Februari 2025'), ('PPh Badan', '2025'),
                         ('PPN', 'Desember 2024'), ('PPh Badan', '2024'),
                         ('PPN', 'Januari 2025')])
    with window(tmp_path, payload) as (root, app, controller, dialog):
        tree = tree_in(dialog)
        for clicks, expected in [(0, ['synthetic-3', 'synthetic-1', 'synthetic-2', 'synthetic-4', 'synthetic-0']),
                                 (1, ['synthetic-3', 'synthetic-1', 'synthetic-2', 'synthetic-4', 'synthetic-0']),
                                 (2, ['synthetic-2', 'synthetic-4', 'synthetic-0', 'synthetic-3', 'synthetic-1'])]:
            if clicks:
                root.tk.call(tree.heading('type', 'command'))
                root.update()
            assert [tree.item(iid, 'values')[3] for iid in tree.get_children()] == expected
            assert [tree.item(f'record-{index}', 'values')[1] for index in range(5)] == [
                'Februari', 'Tahunan', 'Desember', 'Tahunan', 'Januari']
        assert not tree.selection() and not controller.replies
