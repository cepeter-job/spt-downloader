"""Unsupported attachment controls produce structural evidence without actions."""
from copy import deepcopy
import json

import pytest

from spt_desktop import diagnostics as d
from support_financial_browser import browser as browser, routed as routed, attachments, RECORD, DETAIL
from test_diagnostics import records
from test_financial_discovery import CURRENT_LABEL, file_table


@pytest.mark.parametrize('kind,control,href,handler', [
    ('button', '<button onclick="fetch(\'/synthetic-generation\',{method:\'POST\'})">SYNTHETIC_PRIVATE_FILE.pdf</button>', False, True),
    ('anchor', '<a>SYNTHETIC_PRIVATE_FILE.pdf</a>', False, False),
    ('input', '<input type="button" value="SYNTHETIC_PRIVATE_FILE.pdf">', False, False),
    ('other', '<span role="button" onclick="fetch(\'/synthetic-generation\',{method:\'POST\'})">SYNTHETIC_PRIVATE_FILE.pdf</span>', False, True),
    ('none', 'SYNTHETIC_PRIVATE_FILE.pdf', False, False),
])
def test_pdf_discovery_reports_control_shape_without_leaking_or_acting(routed, tmp_path, kind, control, href, handler):
    page, requests = routed('<section><label>' + CURRENT_LABEL + '</label>' + file_table(control) + '</section>')
    with d.session(tmp_path / 'diagnostics', 'worker') as log:
        result = attachments().download_financial_attachments(page, deepcopy(RECORD), tmp_path)
        assert log.flush()
    assert result and all(item['status'] == 'PARTIAL' for item in result)
    assert requests == [('GET', DETAIL)]
    assert not list(tmp_path.glob('*.pdf'))
    rows = records(tmp_path / 'diagnostics')
    observed = [row for row in rows if row['event'] == 'pdf.discovery' and row.get('control_kind') == kind]
    assert len(observed) == 1
    assert observed[0]['attachment_tables'] == 1
    assert observed[0]['candidate_controls'] == (0 if kind == 'none' else 1)
    assert observed[0]['href_present'] is href
    assert observed[0]['handler_present'] is handler
    assert observed[0]['binding_state'] in {'bound', 'unbound', 'ambiguous', 'no_control'}
    text = json.dumps(rows)
    assert 'SYNTHETIC_PRIVATE_FILE' not in text
    assert 'synthetic-generation' not in text and RECORD['record_id'] not in text


def test_pdf_discovery_schema_rejects_arbitrary_control_details(tmp_path):
    secret = 'SYNTHETIC_PRIVATE_CONTROL_VALUE'
    with d.session(tmp_path, 'worker') as log:
        d.record('pdf.discovery', control_kind='button', binding_state='unbound',
                 href_present=False, handler_present=True, attachment_tables=1, candidate_controls=1,
                 href=secret, label=secret, filename=secret, outerHTML=secret)
        d.record('pdf.discovery', control_kind=secret, binding_state=secret,
                 href_present=secret, handler_present=secret)
        assert log.flush()
    rows = [row for row in records(tmp_path) if row['event'] == 'pdf.discovery']
    assert len(rows) == 2
    assert rows[0]['control_kind'] == 'button' and rows[0]['handler_present'] is True
    assert not {'control_kind', 'binding_state', 'href_present', 'handler_present'} & rows[1].keys()
    assert secret not in json.dumps(rows)
