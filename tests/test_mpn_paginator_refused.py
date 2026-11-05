"""Synthetic tests for MPN paginator refusal diagnostics (#143).

The paginator safety check records only fixed categories, never the
compared First offset, request values, filters or row contents.
"""
import json
from types import SimpleNamespace

import pytest

from coretax_mpn import MpnSafetyError
from coretax_mpn_ui import AccountingUI
from spt_desktop import diagnostics
from test_diagnostics import records
from test_mpn_browser import Request, Response
from test_mpn_pagination import frontier_snapshot, source_rows
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
    assert 'mpn_paginator_field' not in event
    assert 'mpn_paginator_filter_shape' not in event


def test_second_page_binding_change_records_binding_changed(tmp_path):
    # A non-First binding change the observer rejects upstream (sort
    # order, page size) cannot arrive through the protocol fixture, so
    # drive the _pages classification directly with a stubbed
    # observer/wait; _pages is the unit under test here.
    rows = source_rows(11)
    first = frontier_snapshot(rows[:10], 0, 11)
    second = frontier_snapshot(rows[10:], 10, 11)
    second['request']['SortOrder'] = 1
    ui = AccountingUI.__new__(AccountingUI)
    ui._stop = lambda: None
    ui._state = lambda: None
    ui._owned = lambda: None
    ui._unfiltered = lambda snapshot: True
    ui.observer = SimpleNamespace(sequence=first['sequence'],
                                  latest={'list': {'sequence': first['sequence']}})
    ui._wait = lambda marker, kind: second

    class Owner:
        def locator(self, selector):
            return self

        def count(self):
            return 1

        def is_visible(self):
            return True

        def click(self, *, timeout):
            pass

    root = tmp_path / 'diagnostics'
    with diagnostics.session(root, 'worker') as log:
        with pytest.raises(MpnSafetyError, match='paginator query/total/offset changed'):
            list(ui._pages('list', Owner(), first, 100))
        assert log.flush()
    events = [r for r in records(root) if r['event'] == 'mpn.paginator_refused']
    assert len(events) == 1
    assert events[0]['mpn_paginator_kind'] == 'list'
    assert events[0]['mpn_paginator_reason'] == 'binding_changed'
    assert events[0]['mpn_paginator_field'] == 'sort_order'
    assert events[0]['mpn_paginator_filter_shape'] == 'none'


def test_second_page_explicit_filter_defaults_are_same_query(tmp_path, monkeypatch):
    rows = source_rows(11)
    packets = [frontier_snapshot(rows[:10], 0, 11), frontier_snapshot(rows[10:], 10, 11)]

    def explicit_defaults(body):
        body['Filters'][0].update({'CaseSensitive': True, 'AsString': False})

    ui, _, _ = source_ui(tmp_path, monkeypatch)
    root = tmp_path / 'diagnostics'
    try:
        with diagnostics.session(root, 'worker') as log:
            pages = paged(ui, packets, mutate_second=explicit_defaults)
            assert log.flush()
    finally:
        ui.observer.close()
    assert [page['first'] for page in pages] == [0, 10]
    assert not [r for r in records(root) if r['event'] == 'mpn.paginator_refused']


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


@pytest.mark.parametrize('key,field', [
    ('TaxpayerAggregateIdentifier', 'taxpayer'), ('RecordId', 'record_id'),
    ('Rows', 'rows'), ('SortField', 'sort_field'), ('SortOrder', 'sort_order'),
    ('LanguageId', 'language'), ('Filters', 'filters')])
def test_paginator_field_reports_first_differing_binding_field(key, field):
    binding = {'Rows': 10, 'SortField': 'PostingDate', 'SortOrder': -1,
               'LanguageId': 'id-ID', 'Filters': [], 'TaxpayerAggregateIdentifier': 'SYNTHETIC'}
    current = dict(binding, First=10)
    current[key] = 'SYNTHETIC_CHANGED' if key != 'Rows' else 25
    assert AccountingUI._paginator_field(binding, current) == field


def test_paginator_field_falls_back_to_other_for_unlisted_key():
    assert AccountingUI._paginator_field({'Rows': 10}, {'Rows': 10, 'Unlisted': 1}) == 'other'
    assert AccountingUI._paginator_field({'Rows': 10}, None) == 'rows'


@pytest.mark.parametrize('initial_keys,current_keys,shape', [
    ({'PropertyName', 'Value', 'MatchMode'}, {'PropertyName', 'Value', 'MatchMode'}, 'none'),
    ({'PropertyName', 'Value', 'MatchMode'},
     {'PropertyName', 'Value', 'MatchMode', 'CaseSensitive'}, 'case_sensitive_added'),
    ({'PropertyName', 'Value', 'MatchMode'},
     {'PropertyName', 'Value', 'MatchMode', 'AsString'}, 'as_string_added'),
    ({'PropertyName', 'Value', 'MatchMode'},
     {'PropertyName', 'Value', 'MatchMode', 'CaseSensitive', 'AsString'}, 'both_added'),
    ({'PropertyName', 'Value', 'MatchMode', 'CaseSensitive', 'AsString'},
     {'PropertyName', 'Value', 'MatchMode'}, 'both_removed'),
    ({'PropertyName', 'Value', 'MatchMode', 'CaseSensitive'},
     {'PropertyName', 'Value', 'MatchMode'}, 'case_sensitive_removed'),
    ({'PropertyName', 'Value', 'MatchMode', 'AsString'},
     {'PropertyName', 'Value', 'MatchMode'}, 'as_string_removed'),
    ({'PropertyName', 'Value', 'MatchMode', 'CaseSensitive'},
     {'PropertyName', 'Value', 'MatchMode', 'AsString'}, 'mixed')])
def test_paginator_filter_shape_classifies_optional_key_presence(initial_keys, current_keys, shape):
    initial = [{key: None for key in initial_keys}]
    current = [{key: None for key in current_keys}]
    assert AccountingUI._paginator_filter_shape(initial, current) == shape


@pytest.mark.parametrize('initial,current', [
    (None, []), ([], []), ([{}, {}], [{}]), ([{}], None), ('x', [{}])])
def test_paginator_filter_shape_is_none_without_single_rules(initial, current):
    assert AccountingUI._paginator_filter_shape(initial, current) == 'none'


def test_normalized_query_equates_explicit_filter_defaults():
    from coretax_mpn import normalized_mpn_query
    omitted = {'First': 0, 'Rows': 10, 'Filters': [
        {'PropertyName': 'IsCancelled', 'Value': '0', 'MatchMode': 'equals'}]}
    explicit = {'First': 10, 'Rows': 10, 'Filters': [
        {'PropertyName': 'IsCancelled', 'Value': '0', 'MatchMode': 'equals',
         'CaseSensitive': True, 'AsString': False}]}
    assert normalized_mpn_query(omitted) == normalized_mpn_query(explicit)
    assert 'First' not in normalized_mpn_query(omitted)
    assert omitted['Filters'][0] == {'PropertyName': 'IsCancelled', 'Value': '0',
                                     'MatchMode': 'equals'}, 'Raw request is not rewritten'


def test_normalized_query_keeps_nondefault_filter_values_distinct():
    from coretax_mpn import normalized_mpn_query
    omitted = {'First': 0, 'Filters': [
        {'PropertyName': 'IsCancelled', 'Value': '0', 'MatchMode': 'equals'}]}
    nondefault = {'First': 10, 'Filters': [
        {'PropertyName': 'IsCancelled', 'Value': '0', 'MatchMode': 'equals',
         'CaseSensitive': False}]}
    assert normalized_mpn_query(omitted) != normalized_mpn_query(nondefault)


@pytest.mark.parametrize('request,expected', [
    (None, None), ('x', 'x'), ({'First': 0, 'Filters': 'x'}, {'Filters': 'x'}),
    ({'First': 0, 'Filters': ['x']}, {'Filters': ['x']})])
def test_normalized_query_passes_through_unsupported_shapes(request, expected):
    from coretax_mpn import normalized_mpn_query
    assert normalized_mpn_query(request) == expected
