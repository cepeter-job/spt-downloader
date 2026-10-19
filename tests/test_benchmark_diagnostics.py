"""Runner-only benchmark contracts: actual collector/log output, synthetic sources."""
import json
import pytest
import coretax_browser as browser
from spt_desktop import diagnostics as d
from support_json_hybrid import Scenario


def logs(root):
    return [json.loads(line) for f in sorted((root / 'logs').glob('*.jsonl'))
            for line in f.read_text(encoding='utf-8').splitlines()]


def measure():
    fn = getattr(d, 'measure', None)
    assert callable(fn), 'Benchmark phase context is not implemented'
    return fn


def detail_context():
    fn = getattr(d, 'detail_context', None)
    assert callable(fn), 'Anonymous per-detail diagnostic context is not implemented'
    return fn


def test_benchmark_fields_are_whitelisted_without_private_values(tmp_path):
    with d.session(tmp_path, 'worker') as log:
        d.record('detail.source', source_requested='json-first', source_used='dom',
                 source_reason='adapter_ineligible', tax_kind='corporate', ordinal=2,
                 body_rows=15, pages=2, grids=1, forms=1, cached=False,
                 record_id='SYNTHETIC-SECRET-ID', url='https://private.invalid',
                 payload={'token': 'SYNTHETIC-SECRET'})
        assert log.flush()
    rows = logs(tmp_path)
    row = next((r for r in rows if r['event'] == 'detail.source'), None)
    assert row is not None, 'Source decision event must survive safe logging'
    assert {k: row[k] for k in ('source_requested', 'source_used', 'source_reason', 'tax_kind', 'ordinal')} == {
        'source_requested': 'json-first', 'source_used': 'dom',
        'source_reason': 'adapter_ineligible', 'tax_kind': 'corporate', 'ordinal': 2}
    assert row['body_rows'] == 15 and row['pages'] == 2 and row['cached'] is False
    assert 'SYNTHETIC-SECRET' not in json.dumps(rows) and 'private.invalid' not in json.dumps(rows)


def test_benchmark_fields_reject_arbitrary_objects_and_private_numeric_ids(tmp_path):
    class Secret:
        def __str__(self):
            raise AssertionError('No stringification of diagnostic input')
        def __hash__(self):
            raise AssertionError('No hashing of diagnostic input')
    with d.session(tmp_path, 'worker') as log:
        d.record('detail.source', source_requested=Secret(), source_used='https://private.invalid',
                 source_reason='SYNTHETIC-SECRET', tax_kind=Secret(), ordinal=True,
                 body_rows=1234567890123456, pages=-1, cached='yes')
        assert log.flush()
    row = next((r for r in logs(tmp_path) if r['event'] == 'detail.source'), None)
    assert row is not None
    assert not {'source_requested', 'source_used', 'source_reason', 'tax_kind',
                'ordinal', 'body_rows', 'pages', 'cached'} & row.keys()


def test_benchmark_context_correlates_nested_spans_and_resets(tmp_path):
    context, timer = detail_context(), measure()
    with d.session(tmp_path, 'worker') as log:
        with context(ordinal=2, tax_kind='ppn', source_requested='json-first'):
            with timer('return_detail') as result:
                with timer('json_observe'):
                    pass
                result.update(source_used='json', status='COMPLETE', forms=1, cached=False)
        d.record('operation.finished', status='COMPLETE')
        assert log.flush()
    rows = logs(tmp_path)
    row = next(r for r in rows if r['event'] == 'phase.completed' and r.get('phase') == 'return_detail')
    assert row['ordinal'] == 2 and row['source_requested'] == 'json-first'
    assert row['source_used'] == 'json' and row['status'] == 'COMPLETE'
    assert row['duration_ms'] >= 0
    nested = next(r for r in rows if r['event'] == 'phase.completed' and r.get('phase') == 'json_observe')
    assert nested['ordinal'] == 2 and nested['duration_ms'] <= row['duration_ms']
    assert 'ordinal' not in next(r for r in rows if r['event'] == 'operation.finished')


@pytest.mark.parametrize('error,expected', [(ValueError, 'phase.failed'),
                                           (browser.CaptureCancelled, 'phase.cancelled')])
def test_benchmark_preserves_errors_and_stop_without_leaking_messages(tmp_path, error, expected):
    timer = measure()
    with d.session(tmp_path, 'worker') as log:
        with pytest.raises(error):
            with timer('json_observe'):
                raise error('SYNTHETIC-SECRET-ERROR')
        assert log.flush()
    rows = logs(tmp_path)
    assert any(r['event'] == expected and r.get('phase') == 'json_observe' for r in rows)
    assert not any(r['event'] == 'phase.completed' and r.get('phase') == 'json_observe' for r in rows)
    assert 'SYNTHETIC-SECRET' not in json.dumps(rows)


@pytest.mark.parametrize('mode,native,expected', [('dom', False, 'dom'),
                                                ('json-first', True, 'json'),
                                                ('json-first', False, 'dom')])
def test_real_collector_reports_requested_and_actual_source(tmp_path, monkeypatch, mode, native, expected):
    folder = tmp_path / 'capture'; folder.mkdir()
    case = Scenario(folder, monkeypatch, mode=mode)
    if mode == 'json-first' and not native:
        case.forms = []
    with d.session(tmp_path / 'diag', 'worker') as log:
        result = case.collect()
        assert log.flush()
    assert result['complete']
    rows = logs(tmp_path / 'diag')
    wall = [r for r in rows if r['event'] == 'phase.completed' and r.get('phase') == 'return_detail']
    assert len(wall) == 1, 'Every selected record needs an inclusive wall timer'
    assert wall[0]['ordinal'] == 1 and wall[0]['source_requested'] == mode
    assert wall[0]['source_used'] == expected and wall[0]['status'] == 'COMPLETE'
    assert wall[0]['tax_kind'] == 'corporate' and wall[0]['cached'] is False
    decisions = [r for r in rows if r['event'] == 'detail.source']
    assert len(decisions) == 1 and decisions[0]['source_used'] == expected
    phases = {r.get('phase') for r in rows if r['event'] == 'phase.completed'}
    assert {'list_restore', 'open_detail'} <= phases
    if mode == 'json-first':
        assert {'json_observe', 'json_project'} <= phases
    else:
        assert 'json_observe' not in phases
    assert case.record['record_id'] not in json.dumps(rows)
    case.assert_closed()


def test_native_partial_pdf_is_not_logged_as_complete(tmp_path, monkeypatch):
    folder = tmp_path / 'capture'; folder.mkdir()
    case = Scenario(folder, monkeypatch, financial_complete=False)
    with d.session(tmp_path / 'diag', 'worker') as log:
        result = case.collect()
        assert log.flush()
    assert not result['complete']
    wall = [r for r in logs(tmp_path / 'diag') if r['event'] == 'phase.completed' and r.get('phase') == 'return_detail']
    assert len(wall) == 1
    assert wall[0]['source_used'] == 'json' and wall[0]['status'] == 'PARTIAL'


def test_unknown_benchmark_phase_cannot_leak_private_phase_text(tmp_path):
    timer = measure()
    with d.session(tmp_path, 'worker') as log:
        with timer('SYNTHETIC-SECRET-PHASE'):
            pass
        assert log.flush()
    assert 'SYNTHETIC-SECRET' not in json.dumps(logs(tmp_path))
