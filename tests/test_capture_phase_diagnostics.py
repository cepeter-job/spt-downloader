"""Safe real-fixture timings distinguish corporate panel waits from extraction."""
from copy import deepcopy
import json

import coretax_browser as driver
from spt_desktop import diagnostics as d
from test_corporate_dom_structure import browser as browser, routed as routed, l1d_html, RECORD
from test_diagnostics import records


def test_corporate_capture_reports_panel_ready_expand_and_extract_durations(routed, tmp_path):
    secret = 'SYNTHETIC_PRIVATE_PANEL_VALUE'
    page = routed(l1d_html([], []).replace('value="0000123"', f'value="{secret}"'))
    folder = tmp_path / 'capture'
    folder.mkdir()
    with d.session(tmp_path / 'diagnostics', 'worker') as log:
        result = driver.capture_detail(page, record=deepcopy(RECORD), folder=folder)
        assert log.flush()
    assert result['capture_complete'], result['errors']
    rows = records(tmp_path / 'diagnostics')
    measured = [row for row in rows if row['event'] == 'phase.completed'
                and row.get('form_ordinal') == 1]
    assert {'panel_ready', 'accordion_expand', 'panel_extract'} <= {row.get('phase') for row in measured}
    assert all(row['duration_ms'] >= 0 for row in measured)
    assert secret not in json.dumps(rows)
    assert RECORD['record_id'] not in json.dumps(rows)
