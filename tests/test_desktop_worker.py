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
