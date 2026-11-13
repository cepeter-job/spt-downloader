"""Fixed-enum capture-side naming for the optional L7 structural proof.

Hosted-CI only: `bind_l7_structure` must say which custody fact refused the
optional proof without recording nodes, attributes, URLs or values.
"""
import pytest

from coretax_json_capture import DetailJsonCapture
from spt_desktop import diagnostics as d
from support_json_network import exchange
from test_corporate_component_lifetime import begin, navigate, selected, DETAIL, SCOPE
from test_corporate_l7_history import Element, history_setup
from test_diagnostics import records

EVENT = 'corporate.l7_capture_gate'


class MissingHandle(Element):
    def element_handle(self):
        return None


def run(tmp_path, *, available=None, reason=None, element=None, drop_history=False):
    context, page, guard = history_setup()
    if reason is not None:
        guard.reason = reason
    if available is not None:
        guard.state['available'] = available
    with d.session(tmp_path, 'worker'):
        with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
            begin(capture)
            navigate(page, DETAIL)
            exchange(context, page)
            capture.bind_detail_page(page)
            if drop_history:
                capture._l7_history = None
            result = capture.bind_l7_structure(
                *[element or Element() for _ in range(5)], phase='start')
    return result


def gates(tmp_path):
    return [row['corporate_l7_capture_gate'] for row in records(tmp_path)
            if row['event'] == EVENT]


def test_available_history_records_no_gate(tmp_path):
    assert run(tmp_path) is True
    assert gates(tmp_path) == []


def test_missing_history_handle_is_named(tmp_path):
    assert run(tmp_path, drop_history=True) is False
    assert gates(tmp_path) == ['history']


def test_missing_element_handle_is_named(tmp_path):
    assert run(tmp_path, element=MissingHandle()) is False
    assert gates(tmp_path) == ['handle_form']


@pytest.mark.parametrize('reason', ['budget', 'chain', 'enabled', 'roles'])
def test_unavailable_history_reason_is_named(tmp_path, reason):
    assert run(tmp_path, available=False, reason=reason) is False
    assert gates(tmp_path) == ['js_' + reason]


def test_unknown_history_reason_is_named_without_values(tmp_path):
    assert run(tmp_path, available=False, reason='free text with an identity') is False
    assert gates(tmp_path) == ['js_unknown']
