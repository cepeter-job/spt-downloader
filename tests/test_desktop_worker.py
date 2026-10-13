"""Progress/stop tests use only synthetic data and no intranet access."""
import importlib
import importlib.util
from pathlib import Path
import pytest
import coretax_browser as capture


def events():
    assert importlib.util.find_spec('spt_desktop.events'), 'Desktop progress is not implemented'
    return importlib.import_module('spt_desktop.events')


def test_progress_is_count_based_monotone_and_only_complete_can_reach_100():
    messages = []
    progress = events().Progress('fixture-job', messages.append)
    progress.authenticated()
    progress.inventory(1, 2, 50)
    progress.details(1, 4, 1)
    progress.details(4, 4, 3)
    progress.exported()
    progress.publishing()
    progress.finished(False, Path('fixture-output'))
    values = [m['percent'] for m in messages]
    assert values == sorted(values)
    assert messages[-1]['status'] == 'PARTIAL'
    assert max(values) < 100
    assert messages[2]['processed'] == 1 and messages[2]['total'] == 4
    assert all(m['job_id'] == 'fixture-job' for m in messages)


def test_zero_inventory_and_verified_complete_publish_finish_at_100():
    messages = []
    p = events().Progress('fixture-job', messages.append)
    p.authenticated()
    p.inventory(0, 0, 0)
    p.details(0, 0, 0)
    p.exported()
    p.publishing()
    assert all(m['percent'] < 100 for m in messages)
    p.finished(True, Path('fixture-output'))
    assert messages[-1]['percent'] == 100
    assert messages[-1]['status'] == 'COMPLETE'


@pytest.mark.parametrize('name,args', [
    ('capture_table', (None, None, 1, 2)),
    ('capture_detail', (None,)),
    ('collect_inventory', (None, '0000000000000001', 2025, 'period', 'fixture-not-created')),
    ('collect_details', (None, {'records': []}, 'fixture-not-created')),
])
def test_cancel_before_capture_never_touches_browser_or_writes_checkpoint(name,args):
    assert hasattr(capture, 'CaptureCancelled'), 'Cooperative cancellation is missing'
    def cancel():
        raise capture.CaptureCancelled('synthetic stop')
    with pytest.raises(capture.CaptureCancelled):
        getattr(capture, name)(*args, check_cancel=cancel)


def test_worker_counts_verified_details_once_and_keeps_partial_below_100(monkeypatch, tmp_path):
    """Biaya progress harus linear, termasuk detail lengkap dari checkpoint."""
    from contextlib import nullcontext
    from types import SimpleNamespace
    from spt_desktop import worker

    reads = 0

    class Record(dict):
        def get(self, key, default=None):
            nonlocal reads
            if key == 'capture_complete':
                reads += 1
            return super().get(key, default)

    # Nilai True dapat berasal dari capture baru maupun checkpoint tervalidasi.
    outcomes = [True, False, True, True, False] * 40
    run = {'records': [Record(record_id=f'synthetic-{ordinal}',meta={},capture_complete=value)
                       for ordinal,value in enumerate(outcomes)],
           'npwp':'0000000000000001','year':2025,'year_basis':'period',
           'taxpayer_name':'SYNTHETIC WP','complete':False}
    emitted = []
    monkeypatch.setattr(worker, 'playwright_factory', lambda: nullcontext(object()))
    context = SimpleNamespace(close=lambda: None)
    monkeypatch.setattr(worker, 'authenticate_owned', lambda *args: (context, object()))
    monkeypatch.setattr(worker, 'collect_inventory', lambda *args, **kwargs: run)

    def deliver_details(page, data, folder, on_progress, check_cancel):
        for ordinal in range(1, len(data['records']) + 1):
            check_cancel()
            on_progress(data, ordinal)
        return data

    monkeypatch.setattr(worker, 'collect_details', deliver_details)
    monkeypatch.setattr(worker.coretax, 'save_output', lambda *args: None)
    monkeypatch.setattr(worker, 'downloads_folder', lambda: tmp_path / 'Downloads')
    monkeypatch.setattr(worker, 'publish_workbooks', lambda *args, **kwargs: tmp_path / 'hasil-sintetis')
    monkeypatch.setattr(worker, 'existing_outputs', lambda *args: None)
    requests=SimpleNamespace(request=lambda kind,payload,percent:{
        'selected_ids':[record['record_id'] for record in payload['records']]})
    result = worker.run_job('0000000000000001', 2025, tmp_path, 'fixture-progress',
                            'msedge', True, emitted.append, lambda: False,requests=requests)

    details = [event for event in emitted if event['stage'] == 'details']
    assert (details[0]['processed'], details[0]['total'], details[0]['verified']) == (0, len(outcomes), 0)
    expected = 0
    for ordinal, (event, complete) in enumerate(zip(details[1:], outcomes), 1):
        expected += complete
        assert (event['processed'], event['total'], event['verified']) == (ordinal, len(outcomes), expected)
    assert len(details) == len(outcomes) + 1
    assert result == 2 and emitted[-1]['status'] == 'PARTIAL'
    assert max(event['percent'] for event in emitted) < 100
    assert reads <= 2 * len(outcomes), 'Progress memindai ulang seluruh prefix pada tiap detail'
