"""Synthetic JSON evidence export/publication contracts; runner execution only."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest

import coretax
from coretax_json_capture import DetailJsonCapture, checkpoint_bodies
from spt_desktop import output
from support_json_network import Context, exchange
from support_runs import model_run
from test_json_capture import Page, LIST_URL, DETAIL_URL, RECORD, RAW


def captured_run(source, *, partial=False, fallback=False):
    source.mkdir(parents=True, exist_ok=True)
    run = model_run(models=('Normal',))
    record = run['records'][0]
    scope = [run['npwp'], run['year'], run['year_basis']]
    record.update(record_id=RECORD, key=RECORD, list_url=LIST_URL,
                  detail_url=DETAIL_URL, scope=scope, source_status='SPT Dilaporkan')
    context = Context()
    page = Page(context, DETAIL_URL)
    with DetailJsonCapture(context, page, record, scope, source, ordinal=1) as capture:
        exchange(context, page, raw=RAW)
        capture.bind_detail_page(page)
        saved = capture.drain()
    if partial:
        record['capture_complete'] = False
        run['complete'] = False
    record['detail_source'] = {'version': 1, 'requested': 'json-first',
                               'used': 'dom' if fallback else 'json', 'capture': saved}
    return run


def evidence(run, source):
    capture = run['records'][0]['detail_source']['capture']
    references = [capture['manifest'], *[r['relative_path'] for r in capture['responses']]]
    return {name.removeprefix('returns/'): (source / name).read_bytes() for name in references}


def assert_evidence(run, source, final):
    expected = evidence(run, source)
    actual = {p.relative_to(final).as_posix(): p.read_bytes() for p in (final / 'json').rglob('*.json')}
    assert actual == expected, 'Declared original JSON is missing from the final SPT/json folder'
    assert run.get('output_json') == list(expected), 'JSON output names must be declared separately'
    assert all(name.endswith('.xlsx') for name in run['output_files'])
    coretax.verify_outputs(run, final)


@pytest.mark.parametrize('partial,fallback', [(False, False), (True, False), (False, True)])
def test_cli_and_desktop_retain_exact_declared_json_with_truthful_status(tmp_path, partial, fallback):
    source = tmp_path / 'private-job'
    run = captured_run(source, partial=partial, fallback=fallback)
    before = deepcopy(run['records'])
    coretax.save_output(run, source)
    assert_evidence(run, source, source)
    final = output.publish_workbooks(run, source, tmp_path / 'Downloads', 'json-result')
    assert_evidence(run, source, final)
    assert not (final / 'returns').exists() and not (final / 'run.json').exists()
    assert run['records'] == before and run['complete'] is (not partial)
    capture = run['records'][0]['detail_source']['capture']
    assert checkpoint_bodies(source, capture, run['records'][0], capture['scope'])[0]['body'] == RAW


def test_dom_only_output_has_no_json_directory(tmp_path):
    source = tmp_path / 'private-job'
    run = model_run(models=('Normal',))
    coretax.save_output(run, source)
    final = output.publish_workbooks(run, source, tmp_path / 'Downloads', 'dom-result')
    assert not (final / 'json').exists()
    assert run.get('output_json', []) == []


def test_only_selected_attempt_is_published_and_originals_remain(tmp_path):
    source = tmp_path / 'private-job'
    stale = captured_run(source)
    stale_files = evidence(stale, source)
    run = captured_run(source)
    (source / 'unrelated.json').write_text('{"SYNTHETIC":"UNRELATED"}')
    coretax.save_output(run, source)
    final = output.publish_workbooks(run, source, tmp_path / 'Downloads', 'selected-json')
    assert_evidence(run, source, final)
    assert not (final / 'unrelated.json').exists()
    assert all(not (final / name).exists() for name in stale_files)
    assert evidence(stale, source) == stale_files


@pytest.mark.parametrize('which', ['manifest', 'body', 'scope', 'traversal'])
def test_invalid_source_evidence_cannot_be_exported(tmp_path, which):
    source = tmp_path / 'private-job'
    run = captured_run(source)
    capture = run['records'][0]['detail_source']['capture']
    if which in ('manifest', 'body'):
        name = capture['manifest'] if which == 'manifest' else capture['responses'][0]['relative_path']
        (source / name).write_bytes(b'{"SYNTHETIC":"CHANGED"}')
    elif which == 'scope':
        capture['scope'][0] = '0000000000000002'
    else:
        capture['manifest'] = '../escape.json'
    with pytest.raises((ValueError, RuntimeError)):
        coretax.save_output(run, source)
    assert not (source / 'resume.xlsx').exists()


@pytest.mark.parametrize('which', ['manifest', 'body', 'declaration'])
def test_modified_published_json_or_declaration_fails_verification(tmp_path, which):
    source = tmp_path / 'private-job'
    run = captured_run(source)
    coretax.save_output(run, source)
    expected = evidence(run, source)
    assert expected and all((source / name).exists() for name in expected), 'JSON output is absent'
    if which == 'declaration':
        run['output_json'] = []
    else:
        name = next(name for name in expected if (name.endswith('manifest.json')) == (which == 'manifest'))
        (source / name).write_bytes(b'{"SYNTHETIC":"CHANGED"}')
    with pytest.raises((ValueError, RuntimeError)):
        coretax.verify_outputs(run, source)


def test_overwrite_preserves_prior_unselected_json_and_detects_concurrent_edits(tmp_path):
    downloads = tmp_path / 'Downloads'
    first_source = tmp_path / 'first-job'
    first = captured_run(first_source)
    coretax.save_output(first, first_source)
    final = output.publish_workbooks(first, first_source, downloads, 'first-json')
    old = evidence(first, first_source)
    assert all((final / name).exists() for name in old), 'Initial JSON output is absent'
    source = tmp_path / 'next-job'
    run = captured_run(source)
    coretax.save_output(run, source)
    snapshot = output.existing_outputs(run, downloads)
    changed = final / next(iter(old))
    changed.write_bytes(b'{"SYNTHETIC":"CONCURRENT EDIT"}')
    with pytest.raises((ValueError, RuntimeError)):
        output.publish_workbooks(run, source, downloads, 'changed-json', overwrite=True, expected_outputs=snapshot)
    changed.write_bytes(old[next(iter(old))])
    final2 = output.publish_workbooks(run, source, downloads, 'next-json', overwrite=True)
    assert final2 == final and all((final / name).read_bytes() == data for name, data in old.items())
    assert all((final / name).read_bytes() == data for name, data in evidence(run, source).items())


def test_cancellation_after_json_install_rolls_back_all_outputs(tmp_path, monkeypatch):
    source = tmp_path / 'private-job'
    run = captured_run(source)
    coretax.save_output(run, source)
    downloads = tmp_path / 'Downloads'
    final = output.publish_workbooks(run, source, downloads, 'initial-json')
    assert_evidence(run, source, final)
    before = {p.relative_to(final).as_posix(): p.read_bytes() for p in final.rglob('*') if p.is_file()}
    real_move = output._move_no_replace
    stopped = [False]
    def move(original, target):
        result = real_move(original, target)
        if Path(target).is_relative_to(final / 'json') and Path(target).suffix == '.json':
            stopped[0] = True
        return result
    def cancel():
        if stopped[0]:
            raise RuntimeError('Synthetic Stop after JSON install')
    monkeypatch.setattr(output, '_move_no_replace', move)
    with pytest.raises(RuntimeError, match='Synthetic Stop'):
        output.publish_workbooks(run, source, downloads, 'cancel-json', overwrite=True, check_cancel=cancel)
    assert {p.relative_to(final).as_posix(): p.read_bytes() for p in final.rglob('*') if p.is_file()} == before


def test_restart_recovers_json_and_workbooks_after_process_death(tmp_path):
    source = tmp_path / 'private-job'
    run = captured_run(source)
    coretax.save_output(run, source)
    downloads = tmp_path / 'Downloads'
    final = output.publish_workbooks(run, source, downloads, 'initial-json')
    assert_evidence(run, source, final)
    before = {p.relative_to(final).as_posix(): p.read_bytes() for p in final.rglob('*') if p.is_file()}
    child = r'''
import json, os, sys
from pathlib import Path
from spt_desktop import output
source, downloads, final = map(Path, sys.argv[1:])
run = json.loads((source / 'run.json').read_text(encoding='utf-8'))
real_move = output._move_no_replace
def move(original, target):
    result = real_move(original, target)
    if Path(target).is_relative_to(final / 'json') and Path(target).suffix == '.json':
        os._exit(73)
    return result
output._move_no_replace = move
output.publish_workbooks(run, source, downloads, 'crash-json', overwrite=True)
'''
    result = subprocess.run([sys.executable, '-c', child, str(source), str(downloads), str(final)],
                            capture_output=True, text=True, timeout=90)
    assert result.returncode == 73, result.stderr
    from spt_desktop.publication_recovery import recover_publication
    assert recover_publication(source, downloads) == final
    assert {p.relative_to(final).as_posix(): p.read_bytes() for p in final.rglob('*') if p.is_file()} == before
