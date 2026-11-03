"""Synthetic selection shortcuts; execute Tk only on the Windows CI runner."""
from copy import deepcopy

import pytest

from support_gui import button, named_widget, window


LABELS = ('All', 'Pemb. Terakhir', 'PPh Potput', 'PPN')
NAMES = ('select_all', 'select_latest', 'select_potput', 'select_ppn')


def payload(rows):
    return {'records': [{'record_id': rid, 'meta': {
        'Jenis Pajak': tax, 'Masa Pajak': period, 'Model SPT': model}}
        for rid, tax, period, model in rows]}


def inventory():
    return payload([
        ('vat-normal', 'PPN', 'Januari 2025', 'Normal'),
        ('vat-two', 'PPN', 'Januari 2025', 'Pembetulan 2'),
        ('vat-ten', 'PPN', 'Januari 2025', 'Pembetulan 10'),
        ('vat-feb', 'PPN', 'Februari 2025', 'Normal'),
        ('21-normal', 'PPh Pasal 21/26', 'Januari 2025', 'Normal'),
        ('21-one', 'PPh Pasal 21/26', 'Januari 2025', 'Pembetulan 1'),
        ('unifikasi', 'PPh Unifikasi', 'Januari 2025', 'Normal'),
        ('badan-normal', 'PPh Badan', '01122025', 'Normal'),
        ('badan-one', 'PPh Badan', '01122025', 'Amendment 1'),
        ('other', 'Jenis sintetis lain', 'Januari 2025', 'Normal')])


def selected(dialog):
    tree = named_widget(dialog, 'records')
    chosen = set(tree.selection())
    # Consent order is independently checked against the original payload.
    return {tree.item(iid, 'values')[3] for iid in chosen}


def invoke(root, dialog, name):
    named_widget(dialog, name).invoke()
    root.update()


def checked(dialog, name):
    return named_widget(dialog, name).instate(['selected'])


def test_four_top_checkboxes_start_unchecked_without_consent(tmp_path):
    with window(tmp_path, inventory()) as (root, app, controller, dialog):
        controls = [named_widget(dialog, name) for name in NAMES]
        assert tuple(w.cget('text') for w in controls) == LABELS
        assert all(w.winfo_class() == 'TCheckbutton' and not w.instate(['selected']) for w in controls)
        tree = named_widget(dialog, 'records')
        assert all(w.winfo_rooty() + w.winfo_height() <= tree.winfo_rooty() for w in controls)
        assert not selected(dialog) and not controller.replies
        assert button(dialog, 'Sedot SPT terpilih').instate(['disabled'])


def test_all_selects_every_visible_record_and_unchecking_clears_it(tmp_path):
    data = inventory()
    original = deepcopy(data)
    with window(tmp_path, data) as (root, app, controller, dialog):
        invoke(root, dialog, 'select_all')
        assert selected(dialog) == {r['record_id'] for r in data['records']}
        assert checked(dialog, 'select_all') and not controller.replies
        invoke(root, dialog, 'select_all')
        assert not selected(dialog) and not controller.replies and data == original
        assert button(dialog, 'Sedot SPT terpilih').instate(['disabled'])


@pytest.mark.parametrize('name,expected', [
    ('select_potput', {'21-normal', '21-one', 'unifikasi'}),
    ('select_ppn', {'vat-normal', 'vat-two', 'vat-ten', 'vat-feb'}),
    ('select_latest', {'vat-ten', 'vat-feb', '21-one', 'unifikasi', 'badan-one', 'other'})])
def test_each_shortcut_selects_its_exact_scope_without_reply(tmp_path, name, expected):
    with window(tmp_path, inventory()) as (root, app, controller, dialog):
        invoke(root, dialog, name)
        assert selected(dialog) == expected and checked(dialog, name)
        assert not controller.replies


@pytest.mark.parametrize('latest_first', [True, False])
def test_latest_combines_with_both_tax_groups_in_either_order(tmp_path, latest_first):
    with window(tmp_path, inventory()) as (root, app, controller, dialog):
        order = ('select_latest', 'select_potput', 'select_ppn') if latest_first else (
            'select_potput', 'select_ppn', 'select_latest')
        for name in order:
            invoke(root, dialog, name)
        assert selected(dialog) == {'vat-ten', 'vat-feb', '21-one', 'unifikasi'}
        assert all(checked(dialog, name) for name in ('select_latest', 'select_potput', 'select_ppn'))
        invoke(root, dialog, 'select_ppn')
        assert selected(dialog) == {'21-one', 'unifikasi'}
        invoke(root, dialog, 'select_latest')
        assert selected(dialog) == {'21-normal', '21-one', 'unifikasi'}
        invoke(root, dialog, 'select_potput')
        assert not selected(dialog) and not controller.replies


def test_all_replaces_latest_and_category_scope(tmp_path):
    data = inventory()
    with window(tmp_path, data) as (root, app, controller, dialog):
        invoke(root, dialog, 'select_ppn')
        invoke(root, dialog, 'select_latest')
        invoke(root, dialog, 'select_all')
        assert selected(dialog) == {r['record_id'] for r in data['records']}
        assert checked(dialog, 'select_all')
        assert not any(checked(dialog, name) for name in NAMES[1:])
        invoke(root, dialog, 'select_latest')
        assert selected(dialog) == {'vat-ten', 'vat-feb', '21-one', 'unifikasi', 'badan-one', 'other'}
        assert not checked(dialog, 'select_all')
        invoke(root, dialog, 'select_latest')
        assert not selected(dialog)


def test_latest_numeric_aliases_leading_zero_ties_and_years_stay_distinct(tmp_path):
    data = payload([
        ('normal', 'PPN', '01012025', 'Normal'),
        ('zero', 'PPN', '01012025', 'Pembetulan 0'),
        ('two', 'PPN', '01012025', 'Pembetulan ke-2'),
        ('ten', 'PPN', '01012025', 'Amendment 10'),
        ('ten-tie', 'ppn', '01012025', 'Pembetulan 0010'),
        ('other-year', 'PPN', '01012024', 'Normal'),
        ('feb', 'PPN', '02022025', 'Normal'),
        ('annual24', 'PPh Badan', '01122024', 'Normal'),
        ('annual25', 'PPh Badan', '01122025', 'Normal')])
    original = deepcopy(data)
    with window(tmp_path, data) as (root, app, controller, dialog):
        invoke(root, dialog, 'select_latest')
        assert selected(dialog) == {'ten', 'ten-tie', 'other-year', 'feb', 'annual24', 'annual25'}
        assert data == original and not controller.replies


def test_latest_compares_very_long_amendments_without_integer_coercion(tmp_path):
    data = payload([
        ('smaller', 'PPN', 'Januari 2025', 'Pembetulan ' + '9' * 4301),
        ('larger', 'PPN', 'Januari 2025', 'Pembetulan 1' + '0' * 4301)])
    with window(tmp_path, data) as (root, app, controller, dialog):
        invoke(root, dialog, 'select_latest')
        assert selected(dialog) == {'larger'}


def test_latest_matches_known_period_aliases_and_keeps_explicit_years_separate(tmp_path):
    data = payload([
        ('year24', 'PPN', '01', 'Normal'),
        ('year25', 'PPN', '01', 'Pembetulan 1'),
        ('literal-code', 'PPN', '01012025', 'Normal'),
        ('literal-caption', 'PPN', 'Januari 2025', 'Pembetulan 2')])
    data['records'][0]['meta']['Tahun Pajak'] = '2024'
    data['records'][1]['meta']['Tahun Pajak'] = '2025'
    with window(tmp_path, data) as (root, app, controller, dialog):
        invoke(root, dialog, 'select_latest')
        assert selected(dialog) == {'year24', 'literal-caption'}


def test_latest_annual_aliases_share_one_year_without_rewriting_source(tmp_path):
    data = payload([
        ('normal', 'PPh Badan', '2025', 'Normal'),
        ('one', 'PPh Badan', 'Januari - Desember 2025', 'Pembetulan 1'),
        ('two', 'PPh Badan', '01122025', 'Pembetulan 2'),
        ('prior-year', 'PPh Badan', '2024', 'Normal')])
    original = deepcopy(data)
    with window(tmp_path, data) as (root, app, controller, dialog):
        invoke(root, dialog, 'select_latest')
        assert selected(dialog) == {'two', 'prior-year'}
        assert data == original and not controller.replies


def test_latest_refuses_unknown_periods_and_contradictory_source_year(tmp_path):
    data = payload([
        ('range', 'PPN', '01022025', 'Pembetulan 1'),
        ('unknown', 'PPN', 'Januari 2025 extra', 'Normal'),
        ('contradiction', 'PPN', 'Januari 2025', 'Pembetulan 2'),
        ('known', 'PPN', 'Februari 2025', 'Normal')])
    data['records'][2]['meta']['Tahun Pajak'] = '2024'
    with window(tmp_path, data) as (root, app, controller, dialog):
        invoke(root, dialog, 'select_latest')
        assert selected(dialog) == {'known'}


@pytest.mark.parametrize('unknown_model', ['Pembetulan terakhir', '', None, 2])
def test_unknown_models_and_missing_identity_require_manual_selection(tmp_path, unknown_model):
    data = payload([
        ('normal-with-unknown', 'PPN', 'Januari 2025', 'Normal'),
        ('unknown', 'PPN', 'Januari 2025', unknown_model),
        ('missing-period', 'PPh Badan', '', 'Normal'),
        ('missing-tax', '', 'Januari 2025', 'Normal'),
        ('known', 'PPN', 'Februari 2025', 'Normal')])
    with window(tmp_path, data) as (root, app, controller, dialog):
        invoke(root, dialog, 'select_latest')
        assert selected(dialog) == {'known'}
        notice = named_widget(dialog, 'notice')
        assert 'manual' in str(notice.getvar(str(notice.cget('textvariable')))).casefold()
        invoke(root, dialog, 'select_all')
        assert selected(dialog) == {r['record_id'] for r in data['records']}


def test_zero_amendment_still_supersedes_normal_and_missing_year_is_manual(tmp_path):
    data = payload([
        ('normal', 'PPN', 'Januari 2025', 'Normal'),
        ('zero', 'PPN', 'Januari 2025', 'Pembetulan 0'),
        ('invalid-year', 'PPN', 'Februari 2025', 'Normal')])
    data['records'][2]['meta']['Tahun Pajak'] = None
    with window(tmp_path, data) as (root, app, controller, dialog):
        invoke(root, dialog, 'select_latest')
        assert selected(dialog) == {'zero'}


@pytest.mark.parametrize('tax', ['PPh Badan extra', 'PPh Pasal 21/26 extra', 'PPh Unifikasi extra', 'PPN extra', ''])
def test_tax_shortcuts_do_not_guess_substring_aliases(tmp_path, tax):
    with window(tmp_path, payload([('unknown', tax, 'Januari 2025', 'Normal')])) as (
            root, app, controller, dialog):
        assert named_widget(dialog, 'select_potput').instate(['disabled'])
        assert named_widget(dialog, 'select_ppn').instate(['disabled'])
        assert not selected(dialog) and not controller.replies


def test_search_never_promotes_an_older_model_when_latest_is_hidden(tmp_path):
    with window(tmp_path, inventory()) as (root, app, controller, dialog):
        named_widget(dialog, 'search').insert(0, 'vat-normal')
        root.update()
        invoke(root, dialog, 'select_latest')
        assert not selected(dialog) and not controller.replies
        assert button(dialog, 'Sedot SPT terpilih').instate(['disabled'])
        invoke(root, dialog, 'select_all')
        assert selected(dialog) == {'vat-normal'}


def test_filter_change_resets_shortcuts_and_consent_without_reselecting(tmp_path):
    with window(tmp_path, inventory()) as (root, app, controller, dialog):
        invoke(root, dialog, 'select_all')
        search = named_widget(dialog, 'search')
        search.insert(0, 'Januari')
        root.update()
        assert not selected(dialog) and not any(checked(dialog, name) for name in NAMES)
        invoke(root, dialog, 'select_ppn')
        assert selected(dialog) == {'vat-normal', 'vat-two', 'vat-ten'}
        search.delete(0, 'end')
        root.update()
        assert not selected(dialog) and not any(checked(dialog, name) for name in NAMES)
        assert not controller.replies


def test_manual_selection_overrides_preset_and_sorting_preserves_it(tmp_path):
    with window(tmp_path, inventory()) as (root, app, controller, dialog):
        invoke(root, dialog, 'select_latest')
        tree = named_widget(dialog, 'records')
        root.tk.call(tree.heading('type', 'command'))
        root.update()
        assert checked(dialog, 'select_latest') and 'vat-ten' in selected(dialog)
        tree.selection_set('record-0')
        root.update()
        assert selected(dialog) == {'vat-normal'}
        assert not any(checked(dialog, name) for name in NAMES)
        assert not controller.replies


def test_confirm_sends_literal_ids_in_original_inventory_order_only(tmp_path):
    data = inventory()
    data['records'][2]['record_id'] = '::synthetic {return}; [literal] / id'
    original = deepcopy(data)
    with window(tmp_path, data) as (root, app, controller, dialog):
        invoke(root, dialog, 'select_ppn')
        invoke(root, dialog, 'select_latest')
        tree = named_widget(dialog, 'records')
        root.tk.call(tree.heading('type', 'command'))
        root.update()
        assert not controller.replies
        button(dialog, 'Sedot SPT terpilih').invoke()
        assert controller.replies == [('selection', 'a' * 32, {
            'selected_ids': ['::synthetic {return}; [literal] / id', 'vat-feb']})]
        assert data == original and not controller.stopped


@pytest.mark.parametrize('empty', [True, False])
def test_empty_or_no_match_disables_shortcuts_and_confirmation(tmp_path, empty):
    with window(tmp_path, {'records': []} if empty else inventory()) as (root, app, controller, dialog):
        if not empty:
            named_widget(dialog, 'search').insert(0, 'synthetic-no-matches')
            root.update()
        assert all(named_widget(dialog, name).instate(['disabled']) for name in NAMES)
        assert not selected(dialog) and not controller.replies
        assert button(dialog, 'Sedot SPT terpilih').instate(['disabled'])


def test_stale_job_shortcut_cannot_select_or_reply(tmp_path):
    with window(tmp_path, inventory()) as (root, app, controller, dialog):
        controller.job_id = 'different-synthetic-job'
        named_widget(dialog, 'select_all').invoke()
        root.update()
        assert not selected(dialog) and not controller.replies and not controller.stopped


def test_shortcuts_fit_the_compact_dialog_without_horizontal_clipping(tmp_path):
    with window(tmp_path, inventory()) as (root, app, controller, dialog):
        dialog.geometry('600x500')
        root.update()
        body = named_widget(dialog, 'selection_shortcuts')
        for name in NAMES:
            control = named_widget(dialog, name)
            assert control.winfo_rootx() >= body.winfo_rootx()
            assert control.winfo_rootx() + control.winfo_width() <= body.winfo_rootx() + body.winfo_width()
        assert not controller.replies


def test_source_and_frozen_selftest_exercises_actual_shortcuts(tmp_path):
    import json
    from spt_gui import self_test
    path = tmp_path / 'shortcuts.json'
    assert self_test(path) == 0
    report = json.loads(path.read_text(encoding='utf-8'))['selection_shortcuts_control']
    assert report['labels'] == list(LABELS) and report['all_count'] == 9 and report['cleared'] is True
    assert report['combined_ids'] == [
        '::synthetic {return}; [literal] / id', 'synthetic-21', 'synthetic-ppn-feb', 'synthetic-unifikasi']
