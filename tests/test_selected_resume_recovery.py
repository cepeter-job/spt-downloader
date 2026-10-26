"""Selected desktop recovery must never widen the user's synthetic scope."""
from copy import deepcopy
from contextlib import nullcontext
import importlib
import importlib.util
import json
from types import SimpleNamespace

import pytest

from spt_desktop.interaction import select_records
from support_runs import fixture_run
from support_selected_capture import selected_job


def recovery():
    assert importlib.util.find_spec('coretax_resume'), 'Durable selection recovery is missing'
    return importlib.import_module('coretax_resume')


def selected_inventory(tmp_path, selected_ids):
    inventory = fixture_run()
    inventory['inventory_complete'] = True
    inventory['complete'] = False
    folder = tmp_path / 'job'
    folder.mkdir()
    (folder / 'inventory.json').write_text(json.dumps(inventory), encoding='utf-8')
    return inventory, select_records(inventory, selected_ids), folder


@pytest.mark.parametrize('identifiers', [
    ['21-january', 'unifikasi'], ['badan-normal'], ['21-february', '21-january'],
])
@pytest.mark.parametrize('detail_source', ['dom', 'json-first'])
def test_resume_preserves_selected_order_and_capture_mode(tmp_path, identifiers, detail_source):
    module = recovery()
    inventory, selected, folder = selected_inventory(tmp_path, identifiers)
    original = (folder / 'inventory.json').read_bytes()
    module.persist_selection(selected, folder, detail_source=detail_source)
    loaded, source = module.load_resume_inventory(folder)
    assert [record['record_id'] for record in loaded['records']] == [
        record['record_id'] for record in selected['records']]
    assert loaded['selection'] == selected['selection']
    assert loaded['scope_description'] == selected['scope_description']
    assert source == detail_source
    assert len(inventory['records']) > len(loaded['records'])
    assert (folder / 'inventory.json').read_bytes() == original


@pytest.mark.parametrize('change', ['record', 'scope', 'order', 'mode'])
def test_resume_refuses_changed_inventory_or_capture_policy(tmp_path, change):
    module = recovery()
    inventory, selected, folder = selected_inventory(tmp_path, ['21-january'])
    module.persist_selection(selected, folder, detail_source='json-first')
    if change == 'mode':
        with pytest.raises(ValueError, match='source|mode|selection|scope'):
            module.load_resume_inventory(folder, detail_source='dom')
        return
    changed = deepcopy(inventory)
    if change == 'record':
        changed['records'][2]['record_id'] = 'different-synthetic-record'
    elif change == 'scope':
        changed['year'] = '2024'
    else:
        changed['records'].reverse()
    (folder / 'inventory.json').write_text(json.dumps(changed), encoding='utf-8')
    with pytest.raises(ValueError, match='inventory|selection|scope'):
        module.load_resume_inventory(folder)


def test_saved_selection_cannot_be_replaced_with_a_wider_selection(tmp_path):
    module = recovery()
    inventory, selected, folder = selected_inventory(tmp_path, ['21-january'])
    module.persist_selection(selected, folder)
    wider = select_records(inventory, ['21-january', '21-february'])
    with pytest.raises(ValueError, match='selection|scope'):
        module.persist_selection(wider, folder)
    loaded, _ = module.load_resume_inventory(folder)
    assert [record['record_id'] for record in loaded['records']] == ['21-january']


def test_selection_appearing_at_commit_boundary_is_never_overwritten(tmp_path, monkeypatch):
    module = recovery()
    _, selected, folder = selected_inventory(tmp_path, ['21-january'])
    real_write = module._atomic_checkpoint
    concurrent = b'{"synthetic": "UNAPPROVED CONCURRENT SELECTION"}'
    def write_then_race(path, value):
        real_write(path, value)
        (folder / 'selection.json').write_bytes(concurrent)
    monkeypatch.setattr(module, '_atomic_checkpoint', write_then_race)
    with pytest.raises(ValueError, match='selection scope'):
        module.persist_selection(selected, folder)
    assert (folder / 'selection.json').read_bytes() == concurrent


def test_legacy_cli_inventory_remains_supported_without_desktop_selection(tmp_path):
    module = recovery()
    inventory, _, folder = selected_inventory(tmp_path, ['21-january'])
    loaded, source = module.load_resume_inventory(folder)
    assert loaded == inventory and source == 'dom'


def test_legacy_selected_desktop_run_without_manifest_refuses_scope_expansion(tmp_path):
    module = recovery()
    _, selected, folder = selected_inventory(tmp_path, ['21-january'])
    (folder / 'run.json').write_text(json.dumps(selected), encoding='utf-8')
    with pytest.raises(ValueError, match='selection|desktop|manifest'):
        module.load_resume_inventory(folder)


def test_worker_persists_selected_scope_before_starting_detail_capture(tmp_path, monkeypatch):
    observed = []
    def before_capture(run, events):
        manifest = tmp_path / 'workspace' / 'jobs' / 'selected-job' / 'selection.json'
        observed.append(manifest.is_file())
    status, events, state, inventory = selected_job(
        tmp_path, monkeypatch, ['21-january'], before_capture=before_capture)
    assert observed == [True], 'Selected scope must survive before the first detail opens'
    assert status == 0 and state['captured'] == ['21-january']


def test_cli_continuation_consumes_saved_desktop_selection_and_mode(tmp_path, monkeypatch):
    module = recovery()
    import coretax
    _, selected, folder = selected_inventory(tmp_path, ['21-january'])
    module.persist_selection(selected, folder, detail_source='json-first')
    page = SimpleNamespace(set_viewport_size=lambda value: None, is_closed=lambda: False,
                           close=lambda: None)
    context = SimpleNamespace(new_page=lambda: page, close=lambda: None)
    browser = SimpleNamespace(launch_persistent_context=lambda *args, **kwargs: context)
    monkeypatch.setattr(coretax, 'sync_playwright', lambda: nullcontext(SimpleNamespace(chromium=browser)))
    monkeypatch.setattr(coretax, 'authenticate', lambda *args: None)
    observed = []
    def capture(page, run, folder, **kwargs):
        observed.append(([record['record_id'] for record in run['records']], kwargs['detail_source']))
        run['complete'] = True
        return run
    def save(run, destination):
        run['output_files'] = ['resume.xlsx']
        return destination / 'resume.xlsx'
    monkeypatch.setattr(coretax, 'collect_details', capture)
    from test_mpn_job_flow import capture_result
    monkeypatch.setattr(coretax, 'collect_mpn', lambda page, run, folder, **kwargs: capture_result(run))
    monkeypatch.setattr(coretax, 'save_output', save)
    assert coretax._main(['--resume', str(folder), '--non-interactive']) == 0
    assert observed == [(['21-january'], 'json-first')]


@pytest.mark.parametrize('mode', ['dom', 'json-first'])
def test_nonprefix_selection_reuses_real_first_ordinal_checkpoint_without_navigation(tmp_path, mode):
    module = recovery()
    import coretax_browser as driver
    import support_browser_protocol as protocol
    inventory = protocol.run_fixture()
    original = deepcopy(inventory['records'][0])
    inventory['records'] = [
        {**deepcopy(original), 'key': 'unselected-key-one', 'record_id': 'unselected-one'},
        {**deepcopy(original), 'key': 'unselected-key-two', 'record_id': 'unselected-two'},
        original]
    (tmp_path / 'inventory.json').write_text(json.dumps(inventory), encoding='utf-8')
    module.persist_selection(select_records(inventory, [original['record_id']]), tmp_path,
                             detail_source=mode)
    protocol.write_checkpoint(tmp_path, original, ordinal=1)
    checkpoint = tmp_path / 'returns' / '0001.json'
    checkpoint_bytes = checkpoint.read_bytes()
    other = tmp_path / 'returns' / '0002.json'
    other.write_bytes(b'SYNTHETIC UNSELECTED ORDINAL MUST NOT BE READ OR MODIFIED')
    selected, source = module.load_resume_inventory(tmp_path)
    page = protocol.SourcePage()
    result = driver.collect_details(page, selected, tmp_path, detail_source=source)
    assert result['complete'] is True and not page.navigated
    assert [record['record_id'] for record in result['records']] == [original['record_id']]
    assert result['records'][0]['sections'][0]['name'] == 'Synthetic saved section'
    assert checkpoint.read_bytes() == checkpoint_bytes
    assert other.read_bytes() == b'SYNTHETIC UNSELECTED ORDINAL MUST NOT BE READ OR MODIFIED'
