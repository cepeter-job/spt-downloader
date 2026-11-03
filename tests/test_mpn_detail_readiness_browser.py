"""Synthetic Edge detail-grid refusals keep the original capture gates."""
import json

import pytest

from support_isolated_browser import browser as browser
from test_mpn_capture_browser import portal
from test_mpn import scope_run
from test_diagnostics import records
from spt_desktop import diagnostics


@pytest.mark.parametrize('mode', ['dom', 'json-first'])
@pytest.mark.parametrize('shape', ['missing', 'hidden'])
def test_detail_grid_failure_keeps_partial_and_one_inspected_action(
        browser, tmp_path, monkeypatch, mode, shape):
    import coretax_mpn_ui as module
    from coretax_mpn_browser import collect_mpn
    original = module.AccountingUI._wait
    def wait(self, marker, kind, **kwargs):
        result = original(self, marker, kind, **kwargs)
        if kind == 'detail':
            self.page.locator('#isShowDetail ui-grid').evaluate(
                '(grid, shape) => { if(shape === "missing") grid.replaceWith(...grid.childNodes);'
                'else grid.querySelector("p-table").style.display="none"; }', shape)
        return result
    monkeypatch.setattr(module.AccountingUI, '_wait', wait)
    root = tmp_path / 'diag'
    job = tmp_path / 'job'
    job.mkdir()
    with portal(browser, monkeypatch) as (page, metrics):
        run = scope_run()
        with diagnostics.session(root, 'worker') as log:
            collect_mpn(page, run, job, detail_source=mode)
            assert log.flush()
        assert run['mpn']['status'] == 'PARTIAL' and not run['complete']
        assert run['mpn']['headers'] == 1 and run['mpn']['details'] == 0
        assert run['mpn']['rows'] == [] and len(metrics['detail']) == 1
        assert metrics['unknown'] == 0
    events = records(root)
    readiness, = [row for row in events if row['event'] == 'mpn.detail_readiness_failed']
    assert readiness['mpn_ui_stage'] == 'detail_grid'
    assert readiness['mpn_readiness_state'] == shape
    assert readiness['mpn_readiness_reason'] == 'deadline'
    assert 0 <= readiness['mpn_readiness_budget_ms'] <= 5000
    failed, = [row for row in events if row['event'] == 'mpn.capture_failed']
    assert failed['mpn_ui_stage'] == 'detail_grid'
    assert failed['mpn_capture_stage'] == 'parent_detail'
    assert failed['error']['type'] == 'MpnUnsupported'
    assert not {'selector', 'url', 'body', 'message'} & readiness.keys()
    assert 'SYNTHETIC REF' not in json.dumps(events)
