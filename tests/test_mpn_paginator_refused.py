"""Synthetic tests for MPN paginator refusal diagnostics (#143).

The paginator safety check records only fixed categories, never the
compared First offset, request values, filters or row contents.
"""
import json

import pytest

from coretax_mpn import MpnSafetyError
from spt_desktop import diagnostics
from test_diagnostics import records
from test_mpn_browser import Request, Response
from test_mpn_pagination import frontier_snapshot, snapshot, source_rows
from test_mpn_source_custody import source_ui

SECRET = 'SYNTHETIC_PRIVATE_FILTER_VALUE'


def paged(ui, packets, *, mutate_second=None):
    """Drive actual observer requests/responses and actual AccountingUI._pages."""
    def respond(packet, mutate=False):
        request = Request(ui.page)
        body = json.loads(request.post_data)
        body['First'] = packet['first']
        if mutate and mutate_second is not None:
            mutate_second(body)
        request.post_data = json.dumps(body)
        ui.observer.on_request(request)
        response = Response(request)
        response._body = packet['raw']
        ui.observer.on_response(response)
        return ui.observer.latest['list']

    class Owner:
        index = 0

        def __init__(self):
            self.first = respond(packets[0])

        def locator(self, selector):
            assert selector == '.p-paginator-next:not([disabled]):not(.p-disabled)'
            return self

        def count(self):
            return int(self.index + 1 < len(packets))

        def is_visible(self):
            return True

        def click(self, *, timeout):
            self.index += 1
            respond(packets[self.index], mutate=True)

    owner = Owner()
    return list(ui._pages('list', owner, owner.first, 100))


def refused(tmp_path, monkeypatch, packets, *, mutate_second=None):
    ui, _, _ = source_ui(tmp_path, monkeypatch)
    root = tmp_path / 'diagnostics'
    try:
        with diagnostics.session(root, 'worker') as log:
            with pytest.raises(MpnSafetyError, match='paginator query/total/offset changed'):
                paged(ui, packets, mutate_second=mutate_second)
            assert log.flush()
    finally:
        ui.observer.close()
    events = [r for r in records(root) if r['event'] == 'mpn.paginator_refused']
    assert len(events) == 1
    assert events[0]['level'] == 'WARNING'
    assert SECRET not in json.dumps(records(root))
    return events[0]


def test_second_page_reset_to_first_records_first_mismatch(tmp_path, monkeypatch):
    rows = source_rows(11)
    packets = [frontier_snapshot(rows[:10], 0, 11), frontier_snapshot(rows[:10], 0, 11)]
    event = refused(tmp_path, monkeypatch, packets)
    assert event['mpn_paginator_kind'] == 'list'
    assert event['mpn_paginator_reason'] == 'first_mismatch'
    assert event['pages'] == 2


def test_second_page_page_size_change_records_binding_changed(tmp_path, monkeypatch):
    rows = source_rows(35)
    packets = [snapshot(rows[:10], total=35), snapshot(rows[10:35], first=10, total=35)]

    def widen(body):
        body['Rows'] = 25

    event = refused(tmp_path, monkeypatch, packets, mutate_second=widen)
    assert event['mpn_paginator_kind'] == 'list'
    assert event['mpn_paginator_reason'] == 'binding_changed'


def test_second_page_added_filter_records_filter_changed(tmp_path, monkeypatch):
    rows = source_rows(11)
    packets = [frontier_snapshot(rows[:10], 0, 11), frontier_snapshot(rows[10:], 10, 11)]

    def add_filter(body):
        body['Filters'] = body['Filters'] + [{
            'PropertyName': 'TransactionDate', 'Value': [SECRET, SECRET],
            'MatchMode': 'between', 'CaseSensitive': True, 'AsString': False}]

    event = refused(tmp_path, monkeypatch, packets, mutate_second=add_filter)
    assert event['mpn_paginator_kind'] == 'list'
    assert event['mpn_paginator_reason'] == 'filter_changed'


def test_unlisted_paginator_reason_is_stripped(tmp_path):
    root = tmp_path / 'diagnostics'
    with diagnostics.session(root, 'worker') as log:
        diagnostics.record('mpn.paginator_refused', level='WARNING',
                           mpn_paginator_kind='list', mpn_paginator_reason=SECRET)
        assert log.flush()
    events = [r for r in records(root) if r['event'] == 'mpn.paginator_refused']
    assert len(events) == 1
    assert 'mpn_paginator_reason' not in events[0]
    assert SECRET not in json.dumps(records(root))
