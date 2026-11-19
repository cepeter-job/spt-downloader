"""Synthetic scoped selection; no browser, network, or real identifiers."""
import json
from pathlib import Path

import pytest

from coretax import _select_corporate_cli_scope
from coretax_resume import load_resume_inventory


def test_corporate_scope_persists_only_matching_record_ids(tmp_path):
    inventory = {
        'npwp': '0000000000000001', 'year': 2025, 'year_basis': 'period',
        'records': [
            {'record_id': 'fake-1', 'key': 'k1',
             'meta': {'Jenis Pajak': 'PPN'}},
            {'record_id': 'fake-2', 'key': 'k2',
             'meta': {'Jenis Pajak': 'PPh Badan'}},
            {'record_id': 'fake-3', 'key': 'k3',
             'meta': {'Jenis Pajak': 'PPh Unifikasi'}},
        ],
        'scope_description': 'Synthetic inventory', 'complete': False,
    }
    (tmp_path / 'inventory.json').write_text(json.dumps(inventory), encoding='utf-8')
    chosen = _select_corporate_cli_scope(inventory, tmp_path, detail_source='dom')
    assert [r['record_id'] for r in chosen['records']] == ['fake-2']
    assert chosen['selection']['inventory_count'] == 3
    assert chosen['cli_detail_scope'] == 'spt-badan-only'
    assert 'mpn' not in chosen
    resumed, source = load_resume_inventory(tmp_path, detail_source='dom')
    assert source == 'dom'
    assert [r['record_id'] for r in resumed['records']] == ['fake-2']
    with pytest.raises(ValueError):
        load_resume_inventory(tmp_path, detail_source='json-first')


def test_no_corporate_candidate_refuses_to_select(tmp_path):
    inventory = {
        'records': [{'record_id': 'fake-1', 'meta': {'Jenis Pajak': 'PPN'}}]}
    with pytest.raises(RuntimeError, match='No inventoried PPh Badan'):
        _select_corporate_cli_scope(inventory, tmp_path, detail_source='dom')
    assert not (tmp_path / 'selection.json').exists()


def test_cli_runs_only_corporate_details_and_never_mpn(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import coretax

    inv = {
        'npwp': '0000000000000001', 'year': 2025, 'year_basis': 'period',
        'taxpayer_name': 'Synthetic company',
        'records': [
            {'record_id': 'fake-1', 'key': 'k1', 'meta': {'Jenis Pajak': 'PPN'}},
            {'record_id': 'fake-2', 'key': 'k2', 'meta': {'Jenis Pajak': 'PPh Badan'}},
        ],
        'sources': [], 'audit': [], 'errors': [], 'inventory_complete': True,
        'scope_description': 'Synthetic submitted SPT',
    }
    output = tmp_path / 'result'
    selected_kinds = []

    def make_inventory(page, npwp, year, basis, folder, **kwargs):
        Path(folder).mkdir(parents=True, exist_ok=True)
        (Path(folder) / 'inventory.json').write_text(json.dumps(inv), encoding='utf-8')
        return inv

    def make_details(page, run, folder, **kwargs):
        selected_kinds.extend(r['meta']['Jenis Pajak'] for r in run['records'])
        run['records'][0]['capture_complete'] = True
        run['complete'] = True

    def fail_mpn(*args, **kwargs):
        pytest.fail('MPN was called during Corporate-only capture')

    page = SimpleNamespace(set_viewport_size=lambda _: None,
                           is_closed=lambda: False, close=lambda: None)
    context = SimpleNamespace(new_page=lambda: page, close=lambda: None)

    class Driver:
        def __enter__(self):
            return SimpleNamespace(chromium=SimpleNamespace(
                launch_persistent_context=lambda *a, **kw: context))

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(coretax, 'sync_playwright', lambda: Driver())
    monkeypatch.setattr(coretax, 'system_ca_manager', lambda mgr: mgr)
    monkeypatch.setattr(coretax, 'authenticate', lambda *args: None)
    monkeypatch.setattr(coretax, 'collect_inventory', make_inventory)
    monkeypatch.setattr(coretax, 'collect_details', make_details)
    monkeypatch.setattr(coretax, 'require_mpn', fail_mpn)
    monkeypatch.setattr(coretax, 'collect_mpn', fail_mpn)
    def saved(run, folder):
        run['output_files'] = ['resume.xlsx']
        return folder / 'resume.xlsx'

    monkeypatch.setattr(coretax, 'save_output', saved)
    code = coretax._main(['--npwp', inv['npwp'], '--year', '2025',
                          '--output', str(output), '--spt-badan-only',
                          '--non-interactive'])
    assert code == 0
    assert selected_kinds == ['PPh Badan']
    assert (output / 'selection.json').exists()
    # The saved DOM/Corporate subset must survive resume, without MPN.
    assert coretax._main(['--resume', str(output), '--spt-badan-only',
                          '--non-interactive']) == 0
    assert selected_kinds == ['PPh Badan', 'PPh Badan']
    # A CLI resume that omits the explicit subset opt-in must never widen.
    with pytest.raises(SystemExit, match='2'):
        coretax._main(['--resume', str(output), '--non-interactive'])


@pytest.mark.parametrize('other_option', ['--inventory-only', '--from-json'])
def test_corporate_only_disallows_non_detail_modes(tmp_path, other_option):
    import coretax
    args = ['--spt-badan-only', other_option]
    if other_option == '--from-json':
        args.append(str(tmp_path / 'fake-run.json'))
    with pytest.raises(SystemExit, match='2'):
        coretax._main(args)


def test_corporate_only_resume_without_selection_fails_closed(tmp_path):
    import coretax
    existing = {
        'npwp': '0000000000000001', 'year': 2025, 'year_basis': 'period',
        'records': [{'record_id': 'fake-corp',
                     'meta': {'Jenis Pajak': 'PPh Badan'}}],
        'scope_description': 'Synthetic inventory',
    }
    (tmp_path / 'inventory.json').write_text(json.dumps(existing), encoding='utf-8')
    # No saved selection: a broad CLI run cannot be silently reinterpreted.
    with pytest.raises(SystemExit, match='2'):
        coretax._main(['--resume', str(tmp_path), '--spt-badan-only',
                       '--non-interactive'])
