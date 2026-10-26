"""Synthetic named JSON publication, migration and custody; runners only."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

import coretax
from coretax_json import JsonSafetyError
from coretax_json_capture import (checkpoint_bodies, copy_held_json, json_custody,
                                  json_output_names, verified_json_names)
from spt_desktop import output
from test_json_output_folder import captured_run


KINDS = [('PPh Badan', 'PPh Badan'), ('PPh Pasal 21/26', 'SPT PPh 21'),
         ('PPh Unifikasi', 'SPT PPh Unifikasi'), ('PPN', 'PPN')]
LAYOUT = 'tax-kind-v1'


def original_bytes(run, source):
    return {name: (source / name).read_bytes() for record in run['records']
            for name in [record['detail_source']['capture']['manifest'],
                         *[r['relative_path'] for r in record['detail_source']['capture']['responses']]]}


def named_bytes(run, source, label):
    return {'json/' + label + '/' + name.removeprefix('returns/json/'): data
            for name, data in original_bytes(run, source).items()}


def legacy_export(run, source):
    """Build a real old-layout output independently of the new producer."""
    assert 'json_output_layout' not in run
    run['output_json'] = [name.removeprefix('returns/') for name in original_bytes(run, source)]
    run['output_attachments'] = coretax.attachment_declarations(run)
    with json_custody(run, source, published=False) as (items, streams):
        copy_held_json(items, streams, source)
    run['template_mapping'] = []
    run['output_files'] = list(coretax.export_split_workbooks(
        run, source, mapping_reports=run['template_mapping']))
    coretax.verify_outputs(run, source)
    (source / 'run.json').write_text(json.dumps(run), encoding='utf-8')


@pytest.mark.parametrize('tax,label', KINDS)
@pytest.mark.parametrize('fallback', [False, True])
def test_cli_and_desktop_use_spt_names_without_changing_original_evidence(tmp_path, tax, label, fallback):
    source = tmp_path / 'private'
    run = captured_run(source, tax=tax, ordinal=4, fallback=fallback)
    before = deepcopy(run['records'])
    raw = original_bytes(run, source)
    expected = named_bytes(run, source, label)
    coretax.save_output(run, source)
    assert run.get('json_output_layout') == LAYOUT
    assert run['output_json'] == list(expected)
    assert all(Path(name).parts[:3] == ('json', label, '0004') for name in run['output_json'])
    saved = json.loads((source / 'run.json').read_text(encoding='utf-8'))
    assert saved['json_output_layout'] == LAYOUT and saved['records'] == before
    final = output.publish_workbooks(run, source, tmp_path / 'Downloads', 'named')
    assert {p.relative_to(final).as_posix(): p.read_bytes()
            for p in (final / 'json').rglob('*.json')} == expected
    assert original_bytes(run, source) == raw and run['records'] == before
    for record in run['records']:
        capture = record['detail_source']['capture']
        assert capture['manifest'].startswith('returns/json/0004/')
        assert checkpoint_bodies(final, capture, record, capture['scope'],
                                 published=True, output_layout=LAYOUT)
    coretax.verify_outputs(run, final)


@pytest.mark.parametrize('tax', ['../unsafe', 'PPh Badan/PPN', 'UNRECOGNIZED', 'Unsupported tax'])
def test_unknown_tax_uses_fixed_safe_name_and_preserves_literal_metadata(tmp_path, tax):
    source = tmp_path / 'private'
    run = captured_run(source, tax=tax)
    before = deepcopy(run['records'])
    expected = named_bytes(run, source, 'SPT Lainnya')
    coretax.save_output(run, source)
    assert run['output_json'] == list(expected)
    assert run['records'] == before
    assert all((source / name).read_bytes() == data for name, data in expected.items())


def test_same_tax_records_keep_original_ordinals_and_attempts(tmp_path):
    source = tmp_path / 'private'
    first = captured_run(source, tax='PPh Pasal 21/26', ordinal=2, identifier='fixture-first')
    second = captured_run(source, tax='PPh Pasal 21/26', ordinal=5, identifier='fixture-second')
    first['records'] += second['records']
    before = deepcopy(first['records'])
    expected = named_bytes(first, source, 'SPT PPh 21')
    coretax.save_output(first, source)
    assert first['output_json'] == list(expected)
    assert {Path(n).parts[2] for n in first['output_json']} == {'0002', '0005'}
    assert first['records'] == before
    coretax.verify_outputs(first, source)


@pytest.mark.parametrize('layout', [None, '', 'legacy', 'tax-kind-v2', True, 1, [], {}])
def test_explicit_unknown_layout_is_refused_before_output_io(tmp_path, layout):
    source = tmp_path / 'private'
    run = captured_run(source)
    run['json_output_layout'] = layout
    with pytest.raises(JsonSafetyError):
        json_output_names(run)
    with pytest.raises(JsonSafetyError):
        coretax.save_output(run, source)
    assert not (source / 'resume.xlsx').exists()


def test_duplicate_private_capture_cannot_hide_across_tax_folders(tmp_path):
    run = captured_run(tmp_path / 'private')
    run['json_output_layout'] = LAYOUT
    other = deepcopy(run['records'][0])
    other['meta']['Jenis Pajak'] = 'PPN'
    run['records'].append(other)
    with pytest.raises(JsonSafetyError):
        json_output_names(run)


@pytest.mark.parametrize('in_place', [False, True])
def test_legacy_offline_reexport_reads_old_paths_then_writes_named_paths(tmp_path, in_place):
    source = tmp_path / 'legacy'
    run = captured_run(source, tax='PPh Pasal 21/26', ordinal=3)
    legacy_export(run, source)
    old = {name: (source / name).read_bytes() for name in run['output_json']}
    before = deepcopy(run['records'])
    expected = named_bytes(run, source, 'SPT PPh 21')
    target = source if in_place else tmp_path / 'new'
    assert coretax.main(['--from-json', str(source / 'run.json'), '--output', str(target),
                         '--detail-source', 'json-first']) == 0
    saved = json.loads((target / 'run.json').read_text(encoding='utf-8'))
    assert saved.get('json_output_layout') == LAYOUT and saved['records'] == before
    assert saved['output_json'] == list(expected)
    assert all((target / name).read_bytes() == data for name, data in expected.items())
    assert all((source / name).read_bytes() == data for name, data in old.items())
    coretax.verify_outputs(saved, target)


@pytest.mark.parametrize('location', ['legacy', 'named'])
@pytest.mark.parametrize('which', ['manifest', 'body'])
def test_changed_selected_evidence_in_either_layout_blocks_replacement(tmp_path, location, which):
    source = tmp_path / 'source'
    run = captured_run(source)
    coretax.save_output(run, source)
    final = output.publish_workbooks(run, source, tmp_path / 'Downloads', 'initial')
    raw = original_bytes(run, source)
    refs = list(raw)
    selected = refs[0] if which == 'manifest' else refs[1]
    relative = selected.removeprefix('returns/') if location == 'legacy' else (
        'json/PPh Badan/' + selected.removeprefix('returns/json/'))
    target = final / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b'{"SYNTHETIC":"CHANGED SELECTED"}')
    before = {p.relative_to(final).as_posix(): p.read_bytes() for p in final.rglob('*.xlsx')}
    with pytest.raises((RuntimeError, ValueError)):
        output.publish_workbooks(run, source, tmp_path / 'Downloads', 'replacement', overwrite=True)
    assert {p.relative_to(final).as_posix(): p.read_bytes() for p in final.rglob('*.xlsx')} == before


@pytest.mark.parametrize('location', ['legacy', 'named'])
def test_case_alias_in_either_selected_layout_is_refused(tmp_path, location):
    source = tmp_path / 'source'
    run = captured_run(source)
    coretax.save_output(run, source)
    destination = tmp_path / 'destination'
    destination.mkdir()
    name = next(iter(original_bytes(run, source))).removeprefix('returns/json/')
    relative = 'json/PPH BADAN/' + name if location == 'named' else 'JSON/' + name
    alias = destination / relative
    alias.parent.mkdir(parents=True)
    alias.write_bytes(b'{"SYNTHETIC":"ALIAS"}')
    with pytest.raises((RuntimeError, ValueError)):
        coretax.save_output(run, destination, json_source=source)
    assert not (destination / 'resume.xlsx').exists()


def test_missing_layout_keeps_legacy_reader_and_declaration_contract(tmp_path):
    source = tmp_path / 'legacy'
    run = captured_run(source)
    legacy_export(run, source)
    assert verified_json_names(run) == list(run['output_json'])
    assert all(Path(n).parts[1] == '0001' for n in run['output_json'])
    final = output.publish_workbooks(run, source, tmp_path / 'Downloads', 'old-reader')
    coretax.verify_outputs(run, final)
