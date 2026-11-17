"""Final coordinated snapshot protocol edges; synthetic hosted tests only."""
import pytest

from coretax_browser import CaptureCancelled
from coretax_json import JsonSafetyError
from coretax_json_capture import DetailJsonCapture
from support_json_network import exchange
from test_corporate_component_lifetime import setup, selected, begin, navigate, DETAIL, SCOPE
from test_corporate_l7_history import History, Element, boundaries as l7_boundaries
from test_corporate_l10b_history import boundaries as l10b_boundaries
from test_corporate_l8_history import History as L8History


def histories_setup():
    context, page = setup()
    acquire = page.evaluate_handle
    histories = {'l7': History(), 'l10b': History(), 'l8': L8History()}
    def document(source):
        handle = acquire(source)
        def install(script):
            return (histories['l7'] if 'corporate-l7-history' in script else
                    histories['l10b'] if 'corporate-l10b-history' in script else histories['l8'])
        handle.evaluate_handle = install
        return handle
    page.evaluate_handle = document
    return context, page, histories


@pytest.mark.parametrize('defect', ['healthy', 'rpc-error', 'malformed', 'document', 'owners',
    'l7-unavailable', 'l7-malformed', 'l7-incomplete', 'l10b-unavailable', 'l10b-malformed',
    'l10b-incomplete', 'l7-changed-l10b-unavailable', 'l10b-changed-l7-unavailable',
    'l8-changed', 'l8-malformed', 'l8-unavailable', 'late-json', 'late-html', 'stop'])
def test_final_snapshot_preserves_all_requested_facts_and_local_fences(tmp_path, defect):
    context, page, histories = histories_setup()
    stopped = []
    def cancel():
        if stopped:
            raise CaptureCancelled()
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path, check_cancel=cancel) as capture:
        begin(capture)
        navigate(page, DETAIL)
        exchange(context, page)
        capture.bind_detail_page(page)
        # These protocol doubles exercise validation, not a claim that the
        # mutually exclusive L7 and L8 semantic profiles can both be admitted.
        assert l7_boundaries(capture) and l10b_boundaries(capture)
        assert capture.observe_l8_lifetime()
        document = page.documents[0]
        evaluate = document.evaluate
        final_calls = []
        def final(script, args=None):
            if 'corporate-final-lifetimes' not in script:
                assert not final_calls, 'No browser RPC may follow the final snapshot'
                return evaluate(script, args)
            final_calls.append(script)
            if defect == 'rpc-error':
                raise RuntimeError('SYNTHETIC driver unavailable')
            if defect == 'stop': stopped.append(True)
            if defect.startswith('late-'):
                exchange(context, page, content_type='text/html' if defect == 'late-html' else 'application/json')
            result = evaluate(script, args)
            if defect == 'malformed': return {}
            if defect == 'document': result['same_document'] = False
            if defect == 'owners': result['owners']['detail_owner'] = False
            for child in ('l7', 'l10b'):
                if defect == child + '-unavailable': result[child]['available'] = False
                if defect == child + '-malformed': result[child] = {'available': 1}
                if defect == child + '-incomplete': result[child]['complete'] = False
            if defect == 'l7-changed-l10b-unavailable':
                result['l7'].update(available=False, changed=True)
                result['l10b']['available'] = False
            if defect == 'l10b-changed-l7-unavailable':
                result['l10b'].update(available=False, changed=True)
                result['l7']['available'] = False
            if defect == 'l8-changed': result['l8']['root_changed'] = True
            if defect == 'l8-malformed': result['l8'] = None
            if defect == 'l8-unavailable': result['l8']['initial_clear'] = False
            return result
        document.evaluate = final
        if defect in ('document', 'owners', 'l7-changed-l10b-unavailable',
                      'l10b-changed-l7-unavailable', 'l8-changed', 'stop'):
            with pytest.raises(CaptureCancelled if defect == 'stop' else JsonSafetyError):
                capture.drain()
            assert not list(tmp_path.rglob('manifest.json'))
        else:
            saved = capture.drain()
            for name in ('component', 'corporate_l7', 'corporate_l8', 'corporate_l10b'):
                absent = (defect in ('rpc-error', 'malformed') or
                          defect.startswith(name.removeprefix('corporate_') + '-'))
                assert (name + '_lifetime' not in saved) == absent
            if defect.startswith('late-'):
                assert not saved['complete'] and 'response-after-final-drain' in saved['reasons']
            else:
                assert saved['complete']
        assert len(final_calls) == 1
    assert all(history.disposed and history.disconnected for history in histories.values())
    assert all(document.disposed for document in page.documents)
    assert not any(context.listeners.values()) and not any(page.listeners.values())


@pytest.mark.parametrize('child', ['l7', 'l10b', 'l8'])
def test_stop_on_history_acquisition_retains_every_returned_handle_for_cleanup(tmp_path, child):
    context, page, histories = histories_setup()
    acquire = page.evaluate_handle
    stopped = []
    def cancel():
        if stopped:
            raise CaptureCancelled()
    def document(source):
        handle = acquire(source)
        install = handle.evaluate_handle
        def stopping_install(script):
            result = install(script)
            if result is histories[child]: stopped.append(True)
            return result
        handle.evaluate_handle = stopping_install
        return handle
    page.evaluate_handle = document
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path, check_cancel=cancel) as capture:
        with pytest.raises(CaptureCancelled): begin(capture)
    assert histories[child].disposed and histories[child].disconnected
    assert all(document.disposed for document in page.documents)
    assert not list(tmp_path.rglob('manifest.json'))


def test_stop_on_l10b_element_acquisition_disposes_the_new_handle(tmp_path):
    context, page, histories = histories_setup()
    stopped = []
    def cancel():
        if stopped: raise CaptureCancelled()
    class StopElement(Element):
        def element_handle(self):
            stopped.append(True)
            return self
    element = StopElement()
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        capture.bind_detail_page(page)
        with pytest.raises(CaptureCancelled):
            capture.bind_l10b_structure(element, Element(), Element(), phase='start', check_cancel=cancel)
    assert element.disposed and histories['l10b'].disposed
